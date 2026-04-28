# -*- coding: utf-8 -*-

"""
Validation-aware retry helpers for faker factories.

When a faker mixes random sampling with strict Pydantic constraints, occasional
draws can violate field validators (extreme distribution tails, edge-case
combinations). ``make_with_retry`` lets the faker keep its simple, fast happy
path and recover from rare misses without surfacing ``ValidationError`` to
callers.
"""

import typing as T

from pydantic import BaseModel, ValidationError

T_Model = T.TypeVar("T_Model", bound=BaseModel)


def make_with_retry(
    factory: T.Callable[[], T_Model],
    max_attempts: int = 5,
) -> T_Model:
    """Call ``factory()`` until it returns a Pydantic-valid model.

    On each ``ValidationError`` the failure is suppressed and the factory is
    re-invoked, up to ``max_attempts`` times. If all attempts fail, the *last*
    ``ValidationError`` is re-raised so the caller sees a real diagnostic.

    The retry count is intentionally a parameter (default 5) so callers that
    use tighter constraints can dial it up.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    last_exc: ValidationError | None = None
    for _ in range(max_attempts):
        try:
            return factory()
        except ValidationError as e:
            last_exc = e
    assert last_exc is not None
    raise last_exc
