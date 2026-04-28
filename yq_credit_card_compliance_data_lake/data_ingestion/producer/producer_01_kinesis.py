# -*- coding: utf-8 -*-

"""
Synchronous Kinesis Stream producer.

Responsibilities: batch records → ``put_records`` → collect partial failures →
return :class:`SendResult`. Explicitly **not** in scope: retries, throttling,
async dispatch, record validation.
"""

import typing as T
from itertools import batched

from pydantic import BaseModel

from .producer_00_base import to_kinesis_record, SendResult

if T.TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_kinesis.client import KinesisClient


KINESIS_PUT_RECORDS_BATCH_LIMIT = 500


def send_records(
    kinesis_client: "KinesisClient",
    stream_name: str,
    records: list[BaseModel],
) -> SendResult:
    """Push ``records`` to the named Kinesis stream synchronously.

    Records are split into batches of 500 (the Kinesis API limit) via
    :func:`itertools.batched` and submitted via ``put_records``. Per-record
    failures within a batch are collected into :attr:`SendResult.failed_entries`
    rather than raising; the caller decides whether to retry, log, or alert.
    """
    total = len(records)
    if total == 0:
        return SendResult(total=0, success_count=0, failed_count=0)

    success_count = 0
    failed_entries: list[dict] = []

    for batch in batched(records, KINESIS_PUT_RECORDS_BATCH_LIMIT):
        entries = [to_kinesis_record(r) for r in batch]
        response = kinesis_client.put_records(
            StreamName=stream_name,
            Records=entries,
        )
        batch_failed = response.get("FailedRecordCount", 0)
        success_count += len(batch) - batch_failed
        if batch_failed > 0:
            for record, result in zip(batch, response["Records"]):
                if "ErrorCode" in result:
                    failed_entries.append(
                        {
                            "ErrorCode": result["ErrorCode"],
                            "ErrorMessage": result.get("ErrorMessage", ""),
                            "record": record.model_dump(mode="json"),
                        }
                    )

    return SendResult(
        total=total,
        success_count=success_count,
        failed_count=len(failed_entries),
        failed_entries=failed_entries,
    )
