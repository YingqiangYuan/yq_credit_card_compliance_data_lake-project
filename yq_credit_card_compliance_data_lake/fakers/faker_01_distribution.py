# -*- coding: utf-8 -*-

"""
Generic distribution helpers — random sampling primitives that the third-party
``Faker`` library does not provide and that are reusable across business
domains.
"""

import random
import typing as T

T_Item = T.TypeVar("T_Item")


def weighted_choice(
    items: list[T_Item],
    weights: list[float],
    rng: random.Random | None = None,
) -> T_Item:
    """Pick a single element from ``items`` using ``weights`` for probability.

    Thin semantic wrapper over ``random.choices(weights=..., k=1)[0]`` so call
    sites read like business intent rather than RNG plumbing. Accepting an
    optional ``rng`` instance lets callers achieve deterministic output without
    polluting the global ``random`` state — important when tests run in
    parallel.
    """
    if len(items) != len(weights):
        raise ValueError(
            f"items and weights length mismatch: {len(items)} vs {len(weights)}"
        )
    r = rng if rng is not None else random
    return r.choices(items, weights=weights, k=1)[0]


def long_tail_amount(
    mu: float = 3.5,
    sigma: float = 1.0,
    floor: float = 0.01,
    cap: float = 50_000.0,
    rng: random.Random | None = None,
) -> float:
    """Sample a positive amount from a log-normal (long-tail) distribution.

    Default parameters yield: median ≈ $33, p95 ≈ $200, occasional values up to
    ``cap``. Suitable for transaction amounts, order totals, or any
    "mostly small, rarely huge" monetary quantity.

    The result is clamped to ``[floor, cap]`` and rounded to 2 decimal places.
    """
    r = rng if rng is not None else random
    raw = r.lognormvariate(mu, sigma)
    clamped = max(floor, min(raw, cap))
    return round(clamped, 2)
