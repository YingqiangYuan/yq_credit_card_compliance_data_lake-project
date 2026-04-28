# -*- coding: utf-8 -*-

"""
Unit tests for ``data_ingestion/models.py``.

Exercises the Pydantic field constraints on :class:`Transaction` and the
``partition_key`` derivation.
"""

from datetime import datetime, UTC
from uuid import uuid4

import pytest
from pydantic import ValidationError

from yq_credit_card_compliance_data_lake.constants import (
    AuthStatus,
    Channel,
    Currency,
)
from yq_credit_card_compliance_data_lake.data_ingestion.models import Transaction


def _make(**overrides) -> Transaction:
    """Build a baseline-valid Transaction; tests override one field at a time."""
    defaults = dict(
        transaction_id=uuid4(),
        card_id="4111111111111111",
        merchant_id="MERCH-ABCDEF12",
        amount=12.34,
        currency=Currency.USD,
        transaction_ts=datetime.now(UTC),
        mcc_code="5411",
        auth_status=AuthStatus.APPROVED,
        channel=Channel.POS,
    )
    defaults.update(overrides)
    return Transaction(**defaults)


def test_baseline_construction_succeeds():
    txn = _make()
    assert txn.amount == 12.34
    assert txn.auth_status is AuthStatus.APPROVED


def test_partition_key_is_card_id():
    txn = _make(card_id="9999999999999999")
    assert txn.partition_key == "9999999999999999"


def test_amount_negative_rejected():
    with pytest.raises(ValidationError):
        _make(amount=-0.01)


def test_amount_above_cap_rejected():
    with pytest.raises(ValidationError):
        _make(amount=50_000.01)


def test_amount_zero_allowed():
    """``ge=0`` includes zero — refunds and reversals can legitimately be 0."""
    txn = _make(amount=0.0)
    assert txn.amount == 0.0


def test_amount_at_cap_allowed():
    txn = _make(amount=50_000.0)
    assert txn.amount == 50_000.0


def test_invalid_mcc_length_rejected():
    with pytest.raises(ValidationError):
        _make(mcc_code="123")
    with pytest.raises(ValidationError):
        _make(mcc_code="12345")


def test_invalid_currency_rejected():
    with pytest.raises(ValidationError):
        _make(currency="XYZ")  # type: ignore[arg-type]


def test_invalid_auth_status_rejected():
    with pytest.raises(ValidationError):
        _make(auth_status="UNKNOWN")  # type: ignore[arg-type]


def test_empty_card_id_rejected():
    with pytest.raises(ValidationError):
        _make(card_id="")


def test_empty_merchant_id_rejected():
    with pytest.raises(ValidationError):
        _make(merchant_id="")


def test_invalid_uuid_rejected():
    with pytest.raises(ValidationError):
        _make(transaction_id="not-a-uuid")  # type: ignore[arg-type]


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.data_ingestion.models",
        preview=False,
    )
