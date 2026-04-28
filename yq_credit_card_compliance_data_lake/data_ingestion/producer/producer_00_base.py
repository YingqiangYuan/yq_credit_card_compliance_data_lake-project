# -*- coding: utf-8 -*-

"""
Producer base utilities — serialization primitives shared across Kinesis /
Kafka / S3 producers.

For batching, prefer the stdlib ``itertools.batched`` (Python 3.12+) over a
hand-rolled wrapper.
"""

from pydantic import BaseModel, Field


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
