# -*- coding: utf-8 -*-

"""
Unit tests for ``data_ingestion/faker.py``.

Verifies that :class:`TransactionFaker` produces Pydantic-valid records,
honours its seed for reproducibility, and respects the configured pool sizes.
"""

from yq_credit_card_compliance_data_lake.constants import (
    AuthStatus,
    Channel,
    Currency,
)
from yq_credit_card_compliance_data_lake.data_ingestion.fakers import TransactionFaker
from yq_credit_card_compliance_data_lake.data_ingestion.models import Transaction


def test_make_one_returns_valid_transaction():
    faker = TransactionFaker(seed=0)
    txn = faker.make_one()
    assert isinstance(txn, Transaction)
    assert txn.auth_status in AuthStatus
    assert txn.channel in Channel
    assert txn.currency in Currency
    assert 0 <= txn.amount <= 50_000


def test_make_many_returns_correct_count():
    faker = TransactionFaker(seed=0)
    out = faker.make_many(25)
    assert len(out) == 25
    assert all(isinstance(t, Transaction) for t in out)


def test_seed_reproducible_across_instances():
    a = TransactionFaker(seed=42).make_many(5)
    b = TransactionFaker(seed=42).make_many(5)
    # transaction_id uses uuid4 (non-deterministic), so compare other fields
    keys_a = [(t.card_id, t.amount, t.merchant_id) for t in a]
    keys_b = [(t.card_id, t.amount, t.merchant_id) for t in b]
    assert keys_a == keys_b


def test_different_seeds_produce_different_data():
    a = TransactionFaker(seed=1).make_many(20)
    b = TransactionFaker(seed=2).make_many(20)
    keys_a = {(t.card_id, t.amount) for t in a}
    keys_b = {(t.card_id, t.amount) for t in b}
    assert keys_a != keys_b


def test_card_pool_is_bounded():
    """All generated transactions should draw from the configured card pool."""
    faker = TransactionFaker(seed=0, card_pool_size=10)
    txns = faker.make_many(500)
    unique_cards = {t.card_id for t in txns}
    assert len(unique_cards) <= 10


def test_merchant_pool_is_bounded():
    faker = TransactionFaker(seed=0, merchant_pool_size=5)
    txns = faker.make_many(500)
    unique_merchants = {t.merchant_id for t in txns}
    assert len(unique_merchants) <= 5


def test_card_id_is_16_digits():
    faker = TransactionFaker(seed=0)
    txn = faker.make_one()
    assert len(txn.card_id) == 16
    assert txn.card_id.isdigit()


def test_merchant_id_format():
    faker = TransactionFaker(seed=0)
    txn = faker.make_one()
    assert txn.merchant_id.startswith("MERCH-")


def test_partition_key_matches_card_id():
    faker = TransactionFaker(seed=0)
    txn = faker.make_one()
    assert txn.partition_key == txn.card_id


def test_auth_status_distribution_skewed_to_approved():
    """95% APPROVED weight should dominate over a large sample."""
    faker = TransactionFaker(seed=0)
    txns = faker.make_many(2000)
    approved = sum(1 for t in txns if t.auth_status is AuthStatus.APPROVED)
    assert approved / len(txns) > 0.85


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.data_ingestion.faker",
        preview=False,
    )
