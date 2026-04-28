# -*- coding: utf-8 -*-

"""
Producer base utilities — serialization and batching primitives shared across
Kinesis / Kafka / S3 producers.
"""

import typing as T
from collections.abc import Iterator

from pydantic import BaseModel, Field

T_Record = T.TypeVar("T_Record", bound=BaseModel)


def chunk(records: list[T_Record], size: int = 500) -> Iterator[list[T_Record]]:
    """Split ``records`` into sub-lists of at most ``size`` entries.

    Default ``size=500`` is the Kinesis ``put_records`` per-call limit. Kafka
    producers can typically take more, but batching at 500 keeps memory and
    request size predictable across backends.
    """
    for i in range(0, len(records), size):
        yield records[i : i + size]


def to_kinesis_record(record: BaseModel) -> dict:
    """Serialize ``record`` into the dict shape Kinesis ``put_records`` expects.

    The record must expose a ``partition_key`` attribute (Phase 1: only
    :class:`Transaction`; Phase 3 will add :class:`FraudAlert`). Duck-typed
    rather than constrained to a base class — see the implementation doc for
    the rationale.
    """
    return {
        "Data": record.model_dump_json().encode("utf-8"),
        "PartitionKey": str(record.partition_key),  # type: ignore[attr-defined]
    }


class SendResult(BaseModel):
    """Outcome of a :func:`send_records` call.

    Failed records are surfaced verbatim for the caller to decide on
    retry / log / alert — the producer itself never retries.
    """

    total: int = Field(..., description="Total records submitted in this call")
    success_count: int = Field(...)
    failed_count: int = Field(...)
    failed_entries: list[dict] = Field(
        default_factory=list,
        description=(
            "One entry per failure: {ErrorCode, ErrorMessage, record} where "
            "``record`` is the JSON-serialized form of the original input."
        ),
    )
