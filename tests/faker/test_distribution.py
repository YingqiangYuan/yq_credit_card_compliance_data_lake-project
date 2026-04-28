# -*- coding: utf-8 -*-

"""
Unit tests for ``faker/faker_01_distribution.py``.

Covers ``weighted_choice`` (length validation, deterministic output via
injected ``rng``, weight-honouring distribution) and ``long_tail_amount``
(positive-only output, clamping, rounding).
"""

import random
import statistics

import pytest

from yq_credit_card_compliance_data_lake.faker.api import (
    weighted_choice,
    long_tail_amount,
)


def test_weighted_choice_returns_one_of_items():
    rng = random.Random(0)
    out = weighted_choice(["a", "b", "c"], [1.0, 1.0, 1.0], rng=rng)
    assert out in {"a", "b", "c"}


def test_weighted_choice_length_mismatch_raises():
    with pytest.raises(ValueError, match="length mismatch"):
        weighted_choice(["a", "b"], [1.0], rng=random.Random(0))


def test_weighted_choice_honours_weights():
    """Heavily weighted item should dominate sampling."""
    rng = random.Random(42)
    counts = {"common": 0, "rare": 0}
    for _ in range(10_000):
        pick = weighted_choice(["common", "rare"], [99.0, 1.0], rng=rng)
        counts[pick] += 1
    assert counts["common"] > counts["rare"] * 50


def test_weighted_choice_deterministic_with_seed():
    a = weighted_choice([1, 2, 3, 4], [1, 1, 1, 1], rng=random.Random(7))
    b = weighted_choice([1, 2, 3, 4], [1, 1, 1, 1], rng=random.Random(7))
    assert a == b


def test_long_tail_amount_within_bounds():
    rng = random.Random(0)
    for _ in range(1000):
        amount = long_tail_amount(rng=rng)
        assert 0.01 <= amount <= 50_000.0


def test_long_tail_amount_clamping():
    """A degenerate distribution (sigma huge) should still respect cap and floor."""
    rng = random.Random(0)
    samples = [long_tail_amount(mu=100.0, sigma=50.0, rng=rng) for _ in range(50)]
    assert all(s <= 50_000.0 for s in samples)
    samples = [long_tail_amount(mu=-100.0, sigma=50.0, rng=rng) for _ in range(50)]
    assert all(s >= 0.01 for s in samples)


def test_long_tail_amount_two_decimal_places():
    rng = random.Random(0)
    for _ in range(100):
        amount = long_tail_amount(rng=rng)
        # round() may strip trailing zeros, so compare via cents
        cents = round(amount * 100)
        assert abs(amount * 100 - cents) < 1e-6


def test_long_tail_amount_distribution_is_skewed():
    """Median should be much smaller than max — that's the whole point."""
    rng = random.Random(0)
    samples = [long_tail_amount(rng=rng) for _ in range(2000)]
    median = statistics.median(samples)
    assert median < max(samples) / 5


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.faker.faker_01_distribution",
        preview=False,
    )
