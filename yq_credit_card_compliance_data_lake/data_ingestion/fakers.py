# -*- coding: utf-8 -*-

"""
Business-specific fake-data generators for ingestion sources.

Each ``*Faker`` class produces records for one ingestion source. Generic
distribution helpers and validation-retry plumbing live in the top-level
``faker/`` subpackage; only domain knowledge (MCC pools, channel weights,
card-id format) belongs here.

This module deliberately uses only the stdlib ``random`` module plus our own
distribution helpers — no dependency on the third-party ``Faker`` library.
That keeps the ``data_ingestion`` package installable without ``[dev]``
extras: ``TransactionFaker`` is callable from production-style code paths
(e.g. an e2e producer running in CI) without ``ImportError``.

If a future faker class genuinely needs ``Faker`` primitives (e.g. realistic
addresses for a customer faker), import it from ``..lazy_imports`` and add
``Faker`` to the ``[project]`` main dependencies first.
"""

import random
import string
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from ..constants import AuthStatus, Channel, Currency
from ..fakers.api import weighted_choice, long_tail_amount, make_with_retry
from .models import Transaction


# ------------------------------------------------------------------------------
# Distribution constants — tuned by hand to roughly match production telemetry
# ------------------------------------------------------------------------------
_MCC_POOL: tuple[str, ...] = (
    "5411",  # Grocery stores
    "5812",  # Eating places / restaurants
    "5541",  # Gas stations
    "4111",  # Local transit
    "5732",  # Electronics
    "5311",  # Department stores
    "4899",  # Cable / streaming
    "4511",  # Airlines
    "7011",  # Lodging
    "5999",  # Misc retail
)

_CURRENCY_CHOICES: tuple[Currency, ...] = (
    Currency.USD,
    Currency.EUR,
    Currency.GBP,
    Currency.CNY,
    Currency.JPY,
    Currency.CAD,
)
_CURRENCY_WEIGHTS: tuple[float, ...] = (80.0, 8.0, 5.0, 4.0, 2.0, 1.0)

_AUTH_STATUS_CHOICES: tuple[AuthStatus, ...] = (
    AuthStatus.APPROVED,
    AuthStatus.DECLINED,
    AuthStatus.PENDING,
)
_AUTH_STATUS_WEIGHTS: tuple[float, ...] = (95.0, 4.0, 1.0)

_CHANNEL_CHOICES: tuple[Channel, ...] = (
    Channel.POS,
    Channel.ECOM,
    Channel.ATM,
    Channel.PHONE,
    Channel.RECURRING,
)
_CHANNEL_WEIGHTS: tuple[float, ...] = (40.0, 50.0, 5.0, 3.0, 2.0)


class TransactionFaker:
    """Generate plausible :class:`Transaction` records.

    A bounded card-id and merchant-id pool is pre-built at construction time so
    that successive calls to :meth:`make_one` produce the same cards / merchants
    repeatedly — modelling the real-world "same card, many swipes" pattern that
    downstream per-card aggregations rely on.

    Pass ``seed`` to make output deterministic (useful in unit tests). The
    ``Random`` instance is private to the faker, so seeding here does **not**
    perturb the global ``random`` state.
    """

    def __init__(
        self,
        seed: int | None = None,
        card_pool_size: int = 1000,
        merchant_pool_size: int = 200,
        timestamp_drift_seconds: int = 60,
        max_validation_attempts: int = 5,
    ):
        self._rng = random.Random(seed)
        self._timestamp_drift_seconds = timestamp_drift_seconds
        self._max_validation_attempts = max_validation_attempts

        self._card_pool: tuple[str, ...] = tuple(
            self._fake_card_id() for _ in range(card_pool_size)
        )
        self._merchant_pool: tuple[str, ...] = tuple(
            self._fake_merchant_id() for _ in range(merchant_pool_size)
        )

    # --- private helpers ------------------------------------------------------

    def _fake_card_id(self) -> str:
        """Synthetic card identifier — 16 random digits, **not** a real PAN."""
        return "".join(self._rng.choices(string.digits, k=16))

    def _fake_merchant_id(self) -> str:
        """Merchant id of the form ``MERCH-XXXXXXXX`` (8 hex chars)."""
        suffix = "".join(self._rng.choices(string.hexdigits.upper()[:16], k=8))
        return f"MERCH-{suffix}"

    def _build_transaction(self) -> Transaction:
        """Single attempt at building a Transaction (may raise ValidationError)."""
        now = datetime.now(UTC)
        drift = self._rng.randint(0, self._timestamp_drift_seconds)
        return Transaction(
            transaction_id=uuid4(),
            card_id=self._rng.choice(self._card_pool),
            merchant_id=self._rng.choice(self._merchant_pool),
            amount=long_tail_amount(rng=self._rng),
            currency=weighted_choice(
                list(_CURRENCY_CHOICES), list(_CURRENCY_WEIGHTS), rng=self._rng
            ),
            transaction_ts=now - timedelta(seconds=drift),
            mcc_code=self._rng.choice(_MCC_POOL),
            auth_status=weighted_choice(
                list(_AUTH_STATUS_CHOICES), list(_AUTH_STATUS_WEIGHTS), rng=self._rng
            ),
            channel=weighted_choice(
                list(_CHANNEL_CHOICES), list(_CHANNEL_WEIGHTS), rng=self._rng
            ),
        )

    # --- public API -----------------------------------------------------------

    def make_one(self) -> Transaction:
        """Build one Transaction, retrying up to ``max_validation_attempts``.

        Pydantic validation can fail for an unlucky distribution draw (e.g., an
        amount round-tripped to 0 still passes ``ge=0``, but tighter future
        constraints might not). Wrapping the build in
        :func:`make_with_retry` keeps callers from ever seeing transient
        :class:`ValidationError`s while still surfacing real bugs after the
        retry budget is exhausted.
        """
        return make_with_retry(
            self._build_transaction,
            max_attempts=self._max_validation_attempts,
        )

    def make_many(self, n: int) -> list[Transaction]:
        """Build ``n`` Transactions. Suitable for one-shot ``put_records`` batches."""
        return [self.make_one() for _ in range(n)]
