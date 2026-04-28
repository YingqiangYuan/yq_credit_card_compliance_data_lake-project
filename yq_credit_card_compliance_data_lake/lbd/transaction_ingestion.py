# -*- coding: utf-8 -*-

"""
Lambda handler for the Kinesis transaction ingestion firehose.

Subscribed to the production Kinesis transaction stream via an Event Source
Mapping (configured in :mod:`...cdk.stacks.lambda_stack`).  Splits each batch
into Bronze (validated) and Quarantine (failed validation or decode), writes
both to S3 as NDJSON, and records a row in the pipeline-metadata DynamoDB
table.

Pipeline shape::

    KinesisStreamEvent
      ├── decode_kinesis_records  → decoded dicts + decode_errors
      │                              (utf8 / json / not_dict failures)
      ├── validate_transaction    → valid Transactions + validation_errors
      ├── write Bronze NDJSON     (only if any record passes validation)
      ├── write Quarantine NDJSON (only if any record fails)
      └── PipelineMetadata.save() — final status SUCCESS / PARTIAL

**FAILED rows are intentionally not written.**  An exception escaping the
handler is caught by the Event Source Mapping, which retries with batch
bisection and routes irrecoverable batches to the SQS DLQ; that path is the
authoritative failure signal for ops.  Adding a FAILED metadata write here
would require either nesting another bsm round-trip inside the failure path
(and swallowing its own errors) or breaking the "only successful runs
recorded" contract.  Phase 5 may revisit this once the rules registry exists.
"""

import typing as T
from datetime import datetime, UTC

from pydantic import Field
from s3pathlib import S3Path
from aws_lambda_powertools.utilities.data_classes import (
    event_source,
    KinesisStreamEvent,
)
from pynamodb_session_manager.api import use_boto_session

from ..constants import PipelineName, PipelineStatus
from ..data_ingestion.api import (
    PipelineMetadata,
    build_partition_path,
    decode_kinesis_records,
    validate_transaction,
    write_ndjson_to_s3,
)
from ..logger import logger
from ..one.api import one
from .base import BaseInput, BaseOutput

if T.TYPE_CHECKING:  # pragma: no cover
    from boto_session_manager import BotoSesManager


_PIPELINE_NAME = PipelineName.TRANSACTION_INGESTION.value


class Output(BaseOutput):
    """Run summary returned by the handler.

    The four count fields satisfy ``total == valid + quarantined``;
    ``run_status`` is the final PipelineStatus value (Phase 4 only emits
    SUCCESS or PARTIAL — see module docstring).
    """

    run_id: str = Field(...)
    total: int = Field(...)
    valid: int = Field(...)
    quarantined: int = Field(...)
    bronze_s3_uri: T.Optional[str] = Field(default=None)
    quarantine_s3_uri: T.Optional[str] = Field(default=None)
    run_status: str = Field(...)


class Input(BaseInput[Output]):
    """Decoded payload list + the request id used to mint ``run_id``."""

    raw_payloads: list[bytes] = Field(...)
    request_id: str = Field(...)

    def main(self, context=None) -> Output:
        """Resolve dependencies from ``one`` and delegate to :func:`_process`.

        Splitting the orchestrator out of the Pydantic input lets the unit
        test substitute moto-bound replacements for every external resource
        without monkey-patching ``one``.
        """
        return _process(
            raw_payloads=self.raw_payloads,
            request_id=self.request_id,
            s3dir_bronze=one.s3dir_bronze_transactions,
            s3dir_quarantine=one.s3dir_quarantine_transactions,
            pipeline_metadata_table_name=one.config.dynamodb_table_pipeline_metadata,
            bsm=one.bsm,
            polars_storage_options=one.polars_storage_options,
        )


def _process(
    *,
    raw_payloads: list[bytes],
    request_id: str,
    s3dir_bronze: S3Path,
    s3dir_quarantine: S3Path,
    pipeline_metadata_table_name: str,
    bsm: "BotoSesManager",
    polars_storage_options: dict,
    now: T.Optional[datetime] = None,
) -> Output:
    """Pure-function form of the handler.

    Every external dependency is explicit so the unit test can substitute
    moto-bound replacements.  The caller's ``now`` (if provided) is the
    reference point for both freshness validation and the partition path,
    keeping the two consistent on the second-boundary edge.
    """
    reference_now = (
        now if now is not None else datetime.now(UTC)
    ).replace(microsecond=0)
    run_id = f"{reference_now.isoformat()}___{request_id}"
    start_ts = reference_now.isoformat()
    total = len(raw_payloads)

    decoded, decode_errors = decode_kinesis_records(raw_payloads)

    bronze_records: list[dict] = []
    quarantine_records: list[dict] = list(decode_errors)

    # Single quarantine timestamp for the whole batch.  This is the
    # validation-side cousin of the same convention in
    # ``decode_kinesis_records``; analysts get one ts per Lambda
    # invocation, regardless of which failure path each record took.
    quarantine_ts = datetime.now(UTC).isoformat()
    for payload in decoded:
        result = validate_transaction(payload, now=reference_now)
        if result.is_valid:
            bronze_records.append(result.transaction.model_dump(mode="json"))
        else:
            quarantine_records.append(
                {
                    **payload,
                    "_quarantine_reason": result.reasons,
                    "_quarantine_ts": quarantine_ts,
                }
            )

    valid_count = len(bronze_records)
    quarantine_count = len(quarantine_records)

    file_basename = f"{run_id}.ndjson"
    partition = build_partition_path(reference_now)

    bronze_uri: T.Optional[str] = None
    quarantine_uri: T.Optional[str] = None

    if bronze_records:
        bronze_path = s3dir_bronze.joinpath(partition, file_basename)
        write_ndjson_to_s3(bronze_records, bronze_path.uri, polars_storage_options)
        bronze_uri = bronze_path.uri

    if quarantine_records:
        quarantine_path = s3dir_quarantine.joinpath(partition, file_basename)
        write_ndjson_to_s3(
            quarantine_records, quarantine_path.uri, polars_storage_options
        )
        quarantine_uri = quarantine_path.uri

    end_ts = datetime.now(UTC).isoformat()
    final_status = (
        PipelineStatus.SUCCESS
        if quarantine_count == 0
        else PipelineStatus.PARTIAL
    )

    # PynamoDB session routing — see dynamodb_table.py module docstring for
    # the rationale.  ``Meta.table_name`` is overridden each call so this
    # module remains decoupled from the project name (the model file
    # hardcodes a sane default; the handler injects the live config value).
    PipelineMetadata.Meta.table_name = pipeline_metadata_table_name
    with use_boto_session(PipelineMetadata, bsm):
        PipelineMetadata(
            pipeline_name=_PIPELINE_NAME,
            run_id=run_id,
            run_status=final_status.value,
            start_ts=start_ts,
            end_ts=end_ts,
            total_records=total,
            valid_records=valid_count,
            quarantine_records=quarantine_count,
            s3_output_path=bronze_uri,
            s3_quarantine_path=quarantine_uri,
            lambda_request_id=request_id,
        ).save()

    logger.info(
        f"run_id={run_id} status={final_status.value} "
        f"total={total} valid={valid_count} quarantined={quarantine_count}"
    )

    return Output(
        run_id=run_id,
        total=total,
        valid=valid_count,
        quarantined=quarantine_count,
        bronze_s3_uri=bronze_uri,
        quarantine_s3_uri=quarantine_uri,
        run_status=final_status.value,
    )


@event_source(data_class=KinesisStreamEvent)
def lambda_handler(event: KinesisStreamEvent, context):  # pragma: no cover
    """Lambda entry point — powertools decodes the event, ``Input.main``
    dispatches to :func:`_process`.

    Exceptions propagate back to the Event Source Mapping, which is
    configured (in ``cdk/stacks/lambda_stack.py``) for retry-3 +
    bisect-on-error + SQS DLQ.  See module docstring for why FAILED
    metadata rows are intentionally not written from here.
    """
    return (
        Input(
            raw_payloads=[r.kinesis.data_as_bytes() for r in event.records],
            request_id=context.aws_request_id,
        )
        .main(context)
        .model_dump()
    )
