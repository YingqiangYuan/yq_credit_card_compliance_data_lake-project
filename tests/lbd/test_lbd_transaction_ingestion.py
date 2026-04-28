# -*- coding: utf-8 -*-

"""
Unit tests for the transaction ingestion Lambda handler.

These tests exercise :func:`_process` (the handler's pure-function core)
with explicit dependencies so every external resource is moto-bound.

Polars's NDJSON write goes through the Rust ``object_store`` crate and
**cannot** be intercepted by moto — so :func:`write_ndjson_to_s3` is
swapped via ``monkeypatch`` for a recorder that captures the records and
URI without hitting S3.  The actual S3 round-trip is exercised by the
Phase 4 e2e smoke scripts.

Coverage:

- All-valid batch  → bronze write only, DDB row SUCCESS, valid == total.
- All-invalid batch (decode + validation)  → quarantine only, PARTIAL.
- Mixed batch  → bronze + quarantine writes, PARTIAL.
- Empty batch  → no S3 writes, DDB row SUCCESS with all zero counts.
- ``run_id`` format — chronological-prefix invariant (``___`` separator).
- DDB row reflects the exact bronze / quarantine S3 URIs.
"""

import json
import typing as T
from datetime import datetime, timedelta, UTC
from uuid import uuid4

import moto
import pytest
from boto_session_manager import BotoSesManager
from pynamodb_session_manager.api import use_boto_session
from s3pathlib import S3Path

from yq_credit_card_compliance_data_lake.constants import (
    AuthStatus,
    Channel,
    Currency,
    PipelineName,
    PipelineStatus,
)
from yq_credit_card_compliance_data_lake.data_ingestion.dynamodb_table import (
    PipelineMetadata,
)
from yq_credit_card_compliance_data_lake.lbd import transaction_ingestion


_REGION = "us-east-1"
_TABLE_NAME = "test-pipeline-metadata"
_FIXED_NOW = datetime(2026, 4, 28, 14, 0, 0, tzinfo=UTC)
_REQUEST_ID = "test-req-abc123"
_S3_BRONZE = S3Path("s3://demo-bucket/bronze/transactions/").to_dir()
_S3_QUARANTINE = S3Path("s3://demo-bucket/quarantine/transactions/").to_dir()


def _valid_payload_bytes() -> bytes:
    """A canonical valid Transaction payload, as Lambda would receive it."""
    return json.dumps(
        {
            "transaction_id": str(uuid4()),
            "card_id": "4111111111111111",
            "merchant_id": "MERCH-ABCDEF12",
            "amount": 12.34,
            "currency": Currency.USD.value,
            "transaction_ts": _FIXED_NOW.isoformat(),
            "mcc_code": "5411",
            "auth_status": AuthStatus.APPROVED.value,
            "channel": Channel.POS.value,
        }
    ).encode("utf-8")


def _validation_failure_payload_bytes() -> bytes:
    """Decodes fine but fails Pydantic — amount above the $50k cap."""
    return json.dumps(
        {
            "transaction_id": str(uuid4()),
            "card_id": "4111111111111111",
            "merchant_id": "MERCH-ABCDEF12",
            "amount": 999_999.99,  # rejected by Field(le=50_000)
            "currency": Currency.USD.value,
            "transaction_ts": _FIXED_NOW.isoformat(),
            "mcc_code": "5411",
            "auth_status": AuthStatus.APPROVED.value,
            "channel": Channel.POS.value,
        }
    ).encode("utf-8")


def _decode_failure_payload_bytes() -> bytes:
    """Will fail UTF-8 decoding."""
    return b"\xff\xfe\xff"


class _WriterRecorder:
    """Captures every call to ``write_ndjson_to_s3`` (records + uri).

    Indexed by ``"bronze"`` / ``"quarantine"`` based on which S3 prefix the
    URI starts with — keeps the assertions in tests readable.
    """

    def __init__(self):
        self.bronze_calls: list[dict] = []
        self.quarantine_calls: list[dict] = []

    def __call__(self, records: list[dict], s3_uri: str, storage_options: dict) -> None:
        bucket = "bronze" if "/bronze/" in s3_uri else "quarantine"
        target = self.bronze_calls if bucket == "bronze" else self.quarantine_calls
        target.append({"records": records, "uri": s3_uri, "storage_options": storage_options})


@pytest.fixture
def writer_recorder(monkeypatch) -> _WriterRecorder:
    recorder = _WriterRecorder()
    monkeypatch.setattr(transaction_ingestion, "write_ndjson_to_s3", recorder)
    return recorder


def _setup_ddb_table(bsm: BotoSesManager) -> None:
    PipelineMetadata.Meta.table_name = _TABLE_NAME
    with use_boto_session(PipelineMetadata, bsm):
        PipelineMetadata.create_table(
            wait=True, read_capacity_units=1, write_capacity_units=1
        )


def _read_ddb_row(bsm: BotoSesManager, run_id: str) -> PipelineMetadata:
    PipelineMetadata.Meta.table_name = _TABLE_NAME
    with use_boto_session(PipelineMetadata, bsm):
        return PipelineMetadata.get(
            hash_key=PipelineName.TRANSACTION_INGESTION.value,
            range_key=run_id,
        )


def _process(
    raw_payloads: list[bytes],
    bsm: BotoSesManager,
    *,
    now: T.Optional[datetime] = None,
):
    return transaction_ingestion._process(
        raw_payloads=raw_payloads,
        request_id=_REQUEST_ID,
        s3dir_bronze=_S3_BRONZE,
        s3dir_quarantine=_S3_QUARANTINE,
        pipeline_metadata_table_name=_TABLE_NAME,
        bsm=bsm,
        polars_storage_options={"AWS_REGION": _REGION},
        now=now if now is not None else _FIXED_NOW,
    )


# ------------------------------------------------------------------------------
# All-valid batch
# ------------------------------------------------------------------------------
@moto.mock_aws
def test_all_valid_batch_writes_bronze_only(writer_recorder):
    bsm = BotoSesManager(region_name=_REGION)
    _setup_ddb_table(bsm)

    raws = [_valid_payload_bytes() for _ in range(3)]
    output = _process(raws, bsm)

    assert output.total == 3
    assert output.valid == 3
    assert output.quarantined == 0
    assert output.run_status == PipelineStatus.SUCCESS.value
    assert output.bronze_s3_uri is not None
    assert output.quarantine_s3_uri is None

    # Writer was called exactly once, on the bronze prefix.
    assert len(writer_recorder.bronze_calls) == 1
    assert len(writer_recorder.quarantine_calls) == 0
    bronze_call = writer_recorder.bronze_calls[0]
    assert len(bronze_call["records"]) == 3
    assert "year=2026/month=04/day=28" in bronze_call["uri"]
    assert bronze_call["uri"].endswith(f"{output.run_id}.ndjson")

    # DDB row reflects the same.
    row = _read_ddb_row(bsm, output.run_id)
    assert row.run_status == PipelineStatus.SUCCESS.value
    assert row.total_records == 3
    assert row.valid_records == 3
    assert row.quarantine_records == 0
    assert row.s3_output_path == output.bronze_s3_uri
    assert row.s3_quarantine_path is None


# ------------------------------------------------------------------------------
# All-invalid batch (decode + validation)
# ------------------------------------------------------------------------------
@moto.mock_aws
def test_all_invalid_batch_writes_quarantine_only(writer_recorder):
    bsm = BotoSesManager(region_name=_REGION)
    _setup_ddb_table(bsm)

    raws = [
        _decode_failure_payload_bytes(),
        _validation_failure_payload_bytes(),
    ]
    output = _process(raws, bsm)

    assert output.total == 2
    assert output.valid == 0
    assert output.quarantined == 2
    assert output.run_status == PipelineStatus.PARTIAL.value
    assert output.bronze_s3_uri is None
    assert output.quarantine_s3_uri is not None

    assert len(writer_recorder.bronze_calls) == 0
    assert len(writer_recorder.quarantine_calls) == 1
    quarantine_call = writer_recorder.quarantine_calls[0]
    assert len(quarantine_call["records"]) == 2
    assert "year=2026/month=04/day=28" in quarantine_call["uri"]

    # Decode-failure entry preserves its raw bytes; validation-failure entry
    # carries the full original payload + reason codes.
    reasons = [r["_quarantine_reason"][0] for r in quarantine_call["records"]]
    assert any(r.startswith("DECODE_ERROR:utf8") for r in reasons)
    assert any(r.startswith("INVALID_FIELD:amount") for r in reasons)


# ------------------------------------------------------------------------------
# Mixed batch
# ------------------------------------------------------------------------------
@moto.mock_aws
def test_mixed_batch_routes_each_record_correctly(writer_recorder):
    bsm = BotoSesManager(region_name=_REGION)
    _setup_ddb_table(bsm)

    raws = [
        _valid_payload_bytes(),
        _decode_failure_payload_bytes(),
        _valid_payload_bytes(),
        _validation_failure_payload_bytes(),
    ]
    output = _process(raws, bsm)

    assert output.total == 4
    assert output.valid == 2
    assert output.quarantined == 2
    assert output.run_status == PipelineStatus.PARTIAL.value
    assert output.bronze_s3_uri is not None
    assert output.quarantine_s3_uri is not None

    assert len(writer_recorder.bronze_calls[0]["records"]) == 2
    assert len(writer_recorder.quarantine_calls[0]["records"]) == 2

    # Bronze and Quarantine share the same partition + file basename.  The
    # basename is ``{run_id}.ndjson`` and run_id is unique per invocation,
    # so even at scale the two URIs only differ in the prefix.
    bronze_uri = writer_recorder.bronze_calls[0]["uri"]
    quarantine_uri = writer_recorder.quarantine_calls[0]["uri"]
    bronze_tail = bronze_uri.replace(_S3_BRONZE.uri, "")
    quarantine_tail = quarantine_uri.replace(_S3_QUARANTINE.uri, "")
    assert bronze_tail == quarantine_tail


# ------------------------------------------------------------------------------
# Empty batch — defensive but should not happen with EventSourceMapping
# ------------------------------------------------------------------------------
@moto.mock_aws
def test_empty_batch_writes_zero_count_metadata(writer_recorder):
    bsm = BotoSesManager(region_name=_REGION)
    _setup_ddb_table(bsm)

    output = _process([], bsm)

    assert output.total == 0
    assert output.valid == 0
    assert output.quarantined == 0
    assert output.run_status == PipelineStatus.SUCCESS.value
    assert output.bronze_s3_uri is None
    assert output.quarantine_s3_uri is None
    assert writer_recorder.bronze_calls == []
    assert writer_recorder.quarantine_calls == []

    # DDB row still written — empty batch is technically successful.
    row = _read_ddb_row(bsm, output.run_id)
    assert row.run_status == PipelineStatus.SUCCESS.value
    assert row.total_records == 0


# ------------------------------------------------------------------------------
# Run-id contract
# ------------------------------------------------------------------------------
@moto.mock_aws
def test_run_id_is_iso_ts_underscore_request_id(writer_recorder):
    """The chronological-prefix invariant lets queries like
    ``"last 100 runs"`` use the main key directly without a GSI.
    """
    bsm = BotoSesManager(region_name=_REGION)
    _setup_ddb_table(bsm)

    output = _process([_valid_payload_bytes()], bsm)

    ts_part, _, req_part = output.run_id.partition("___")
    assert datetime.fromisoformat(ts_part) == _FIXED_NOW
    assert req_part == _REQUEST_ID


# ------------------------------------------------------------------------------
# Freshness — drift > 1h sends a record to quarantine
# ------------------------------------------------------------------------------
@moto.mock_aws
def test_drifted_timestamp_routed_to_quarantine(writer_recorder):
    bsm = BotoSesManager(region_name=_REGION)
    _setup_ddb_table(bsm)

    drifted = json.loads(_valid_payload_bytes())
    drifted["transaction_ts"] = (_FIXED_NOW - timedelta(hours=2)).isoformat()
    raw = json.dumps(drifted).encode("utf-8")

    output = _process([raw], bsm)

    assert output.valid == 0
    assert output.quarantined == 1
    quarantine_record = writer_recorder.quarantine_calls[0]["records"][0]
    assert "TIMESTAMP_DRIFT" in quarantine_record["_quarantine_reason"]


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.lbd.transaction_ingestion",
        preview=False,
    )
