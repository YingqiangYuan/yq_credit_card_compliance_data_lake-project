# -*- coding: utf-8 -*-

"""
Unit tests for ``data_ingestion/quality/transaction_rules.py``.

Covers:

- Happy path: valid payload returns ``is_valid=True`` with ``transaction``
  populated and ``reasons`` empty.
- Schema completeness: missing required field produces ``MISSING_FIELD:<loc>``.
- Type / range: invalid amount, currency, mcc length produce
  ``INVALID_FIELD:<loc>:<pydantic_type>``.
- Freshness: timestamp drift > 1 h produces ``TIMESTAMP_DRIFT``; at the
  threshold edge it remains valid.
- Determinism: ``now`` injection lets tests pin the freshness reference.
"""

from datetime import datetime, timedelta, UTC
from uuid import uuid4

from yq_credit_card_compliance_data_lake.constants import (
    AuthStatus,
    Channel,
    Currency,
)
from yq_credit_card_compliance_data_lake.data_ingestion.quality.api import (
    TIMESTAMP_DRIFT_THRESHOLD_SECONDS,
    ValidationResult,
    validate_transaction,
)


_FIXED_NOW = datetime(2026, 4, 28, 14, 0, 0, tzinfo=UTC)


def _payload(**overrides) -> dict:
    """Baseline-valid payload as a plain dict (post-decode shape)."""
    base = dict(
        transaction_id=str(uuid4()),
        card_id="4111111111111111",
        merchant_id="MERCH-ABCDEF12",
        amount=12.34,
        currency=Currency.USD.value,
        transaction_ts=_FIXED_NOW.isoformat(),
        mcc_code="5411",
        auth_status=AuthStatus.APPROVED.value,
        channel=Channel.POS.value,
    )
    base.update(overrides)
    return base


# ------------------------------------------------------------------------------
# Happy path
# ------------------------------------------------------------------------------
def test_valid_payload_returns_transaction():
    result = validate_transaction(_payload(), now=_FIXED_NOW)
    assert isinstance(result, ValidationResult)
    assert result.is_valid is True
    assert result.transaction is not None
    assert result.reasons == []
    assert result.transaction.amount == 12.34
    assert result.transaction.currency == Currency.USD


# ------------------------------------------------------------------------------
# Schema completeness
# ------------------------------------------------------------------------------
def test_missing_required_field_produces_missing_field_reason():
    payload = _payload()
    del payload["card_id"]
    result = validate_transaction(payload, now=_FIXED_NOW)
    assert result.is_valid is False
    assert result.transaction is None
    assert any(r.startswith("MISSING_FIELD:card_id") for r in result.reasons)


def test_multiple_missing_fields_produce_multiple_reasons():
    payload = _payload()
    del payload["card_id"]
    del payload["amount"]
    result = validate_transaction(payload, now=_FIXED_NOW)
    assert result.is_valid is False
    reason_locs = {r.split(":")[1] for r in result.reasons if r.startswith("MISSING_FIELD")}
    assert reason_locs == {"card_id", "amount"}


# ------------------------------------------------------------------------------
# Type / range
# ------------------------------------------------------------------------------
def test_invalid_amount_above_cap_produces_invalid_field_reason():
    result = validate_transaction(_payload(amount=999_999.0), now=_FIXED_NOW)
    assert result.is_valid is False
    assert any(r.startswith("INVALID_FIELD:amount") for r in result.reasons)


def test_invalid_amount_negative_produces_invalid_field_reason():
    result = validate_transaction(_payload(amount=-1.0), now=_FIXED_NOW)
    assert result.is_valid is False
    assert any(r.startswith("INVALID_FIELD:amount") for r in result.reasons)


def test_invalid_currency_enum_produces_invalid_field_reason():
    result = validate_transaction(_payload(currency="ZZZ"), now=_FIXED_NOW)
    assert result.is_valid is False
    assert any(r.startswith("INVALID_FIELD:currency") for r in result.reasons)


def test_invalid_mcc_length_produces_invalid_field_reason():
    result = validate_transaction(_payload(mcc_code="123"), now=_FIXED_NOW)
    assert result.is_valid is False
    assert any(r.startswith("INVALID_FIELD:mcc_code") for r in result.reasons)


# ------------------------------------------------------------------------------
# Freshness
# ------------------------------------------------------------------------------
def test_timestamp_within_threshold_is_valid():
    """Drift exactly at the threshold (1 h) is still valid — boundary check."""
    near_edge = _FIXED_NOW - timedelta(seconds=TIMESTAMP_DRIFT_THRESHOLD_SECONDS)
    result = validate_transaction(
        _payload(transaction_ts=near_edge.isoformat()), now=_FIXED_NOW
    )
    assert result.is_valid is True


def test_timestamp_beyond_threshold_produces_drift_reason():
    way_old = _FIXED_NOW - timedelta(seconds=TIMESTAMP_DRIFT_THRESHOLD_SECONDS + 1)
    result = validate_transaction(
        _payload(transaction_ts=way_old.isoformat()), now=_FIXED_NOW
    )
    assert result.is_valid is False
    assert "TIMESTAMP_DRIFT" in result.reasons
    assert result.transaction is None


def test_timestamp_drift_in_the_future_also_flags():
    """``abs(...)`` — clock-skewed records ahead of ``now`` are equally bad."""
    way_future = _FIXED_NOW + timedelta(seconds=TIMESTAMP_DRIFT_THRESHOLD_SECONDS + 1)
    result = validate_transaction(
        _payload(transaction_ts=way_future.isoformat()), now=_FIXED_NOW
    )
    assert result.is_valid is False
    assert "TIMESTAMP_DRIFT" in result.reasons


def test_default_now_uses_current_utc():
    """When ``now`` is omitted, freshness uses real ``datetime.now(UTC)``.

    A timestamp generated at call time should always pass freshness; this
    guards against a regression where the default-arg path is silently
    broken.
    """
    fresh = datetime.now(UTC).isoformat()
    result = validate_transaction(_payload(transaction_ts=fresh))
    assert result.is_valid is True


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.data_ingestion.quality",
        is_folder=True,
        preview=False,
    )
