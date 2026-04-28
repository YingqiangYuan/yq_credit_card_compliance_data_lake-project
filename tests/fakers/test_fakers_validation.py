# -*- coding: utf-8 -*-

"""
Unit tests for ``faker/faker_02_validation.py``.

Verifies that ``make_with_retry`` retries until validation succeeds, raises the
last ``ValidationError`` after the retry budget is exhausted, and rejects an
invalid ``max_attempts`` argument up front.
"""

import pytest
from pydantic import BaseModel, Field, ValidationError

from yq_credit_card_compliance_data_lake.fakers.api import make_with_retry


class _M(BaseModel):
    n: int = Field(..., ge=10)


def test_succeeds_immediately():
    calls: list[int] = []

    def factory():
        calls.append(1)
        return _M(n=42)

    out = make_with_retry(factory, max_attempts=5)
    assert out.n == 42
    assert len(calls) == 1


def test_retries_until_valid():
    """Factory fails twice, then succeeds — total 3 calls, success returned."""
    seq = iter([0, 5, 99])

    def factory():
        return _M(n=next(seq))

    out = make_with_retry(factory, max_attempts=5)
    assert out.n == 99


def test_exhausts_and_raises_last_error():
    def factory():
        return _M(n=0)  # always invalid

    with pytest.raises(ValidationError) as exc_info:
        make_with_retry(factory, max_attempts=3)
    assert len(exc_info.value.errors()) >= 1


def test_max_attempts_zero_rejected():
    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        make_with_retry(lambda: _M(n=42), max_attempts=0)


def test_max_attempts_negative_rejected():
    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        make_with_retry(lambda: _M(n=42), max_attempts=-1)


def test_only_validation_error_is_caught():
    """Non-Pydantic exceptions must propagate immediately, not retry."""

    def factory():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        make_with_retry(factory, max_attempts=5)


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.faker.faker_02_validation",
        preview=False,
    )
