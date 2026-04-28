# -*- coding: utf-8 -*-

"""
Pydantic data models for ingestion sources.

Phase 1 contains only ``Transaction``. As more sources are onboarded
(``FraudAlert`` in Phase 3, batch sources in Phase 4) this file may grow into a
``models/`` subpackage; the trigger is "more than ~4 models or single file
exceeds ~400 lines", not phase number.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ..constants import AuthStatus, Channel, Currency


class Transaction(BaseModel):
    """A single credit-card transaction record.

    Field set mirrors ``doc1_data_ingestion_pipelines.md`` §1.1 — the nine
    required attributes that the upstream payment switch emits per swipe.
    """

    transaction_id: UUID = Field(..., description="Globally unique transaction id")
    card_id: str = Field(
        ...,
        min_length=1,
        description="Hashed card identifier — never the raw PAN",
    )
    merchant_id: str = Field(..., min_length=1)
    amount: float = Field(..., ge=0, le=50_000)
    currency: Currency = Field(...)
    transaction_ts: datetime = Field(..., description="UTC time the swipe occurred")
    mcc_code: str = Field(..., min_length=4, max_length=4)
    auth_status: AuthStatus = Field(...)
    channel: Channel = Field(...)

    @property
    def partition_key(self) -> str:
        """Kinesis partition key.

        Using ``card_id`` keeps every transaction for the same card on the same
        shard, so downstream per-card aggregations see records in the order
        they occurred (see doc1 §1.1 "Shard 策略").
        """
        return self.card_id
