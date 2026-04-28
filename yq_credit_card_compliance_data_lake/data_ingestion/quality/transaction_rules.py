# -*- coding: utf-8 -*-

"""
Quality rules for the Kinesis transaction stream.

Rules implemented (per doc1 §1.1 / §3):

- **Schema completeness & types** — :class:`Transaction` Pydantic validation
  covers required fields, type/enum, ``amount`` in ``[0, 50_000]``, 4-char
  ``mcc_code``.  Pydantic ValidationError is rendered into reason codes of
  the form ``MISSING_FIELD:<loc>`` / ``INVALID_FIELD:<loc>:<pydantic_type>``.
- **Timestamp freshness** — drift versus a reference "now" must be ≤ 1 h;
  otherwise reason ``TIMESTAMP_DRIFT`` is added.

Phase 4 treats every rule violation as ``ERROR`` severity (the record is
quarantined, not let through with a warning tag).  Doc1 §3 calls
``TIMESTAMP_DRIFT`` a ``WARNING``; Phase 5 will reintroduce that distinction
once the rules registry exists.  Until then, "let it through with a warning"
adds branching that pays for itself only once we have multiple sources.
"""

import typing as T
from datetime import datetime, UTC

from pydantic import BaseModel, Field, ValidationError

from ..models import Transaction


TIMESTAMP_DRIFT_THRESHOLD_SECONDS: int = 3600
"""Max seconds between record's ``transaction_ts`` and reference ``now``.

Module-level so a future test or Phase 5 registry can override it for
fixture-based time-travel scenarios; doc1 §3 (rule TXN_002) cites 1 h.
"""


class ValidationResult(BaseModel):
    """Outcome of validating a single record.

    Two-shape design: on success ``transaction`` is populated and ``reasons``
    is empty; on failure the reverse.  Lets the caller route directly
    without re-parsing the dict on the happy path.
    """

    is_valid: bool = Field(...)
    transaction: T.Optional[Transaction] = Field(default=None)
    reasons: list[str] = Field(default_factory=list)


def _format_pydantic_errors(exc: ValidationError) -> list[str]:
    """Render a Pydantic ValidationError into a flat list of reason codes.

    The mapping is intentionally lossy-but-greppable: ``"missing"`` becomes
    ``"MISSING_FIELD:<loc>"`` (matches the doc1 examples), and every other
    pydantic error type falls through to ``"INVALID_FIELD:<loc>:<type>"``.
    Phase 5's rules registry will replace this stringly-typed format with
    structured rule IDs; for now stable greppable strings are good enough
    for ops dashboards.
    """
    reasons: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "<root>"
        etype = err["type"]
        if etype == "missing":
            reasons.append(f"MISSING_FIELD:{loc}")
        else:
            reasons.append(f"INVALID_FIELD:{loc}:{etype}")
    return reasons


def validate_transaction(
    payload: dict[str, T.Any],
    *,
    now: T.Optional[datetime] = None,
) -> ValidationResult:
    """Run Phase 4 quality rules on a single decoded transaction payload.

    :param payload: dict produced by :func:`decode_kinesis_records`.  Not yet
        validated — this function is the first place schema is enforced.
    :param now: timestamp used as the reference point for the freshness
        check.  Default ``datetime.now(UTC)``; tests inject a fixed value
        to make the "drift > 1 h" branch deterministic.
    """
    try:
        txn = Transaction.model_validate(payload)
    except ValidationError as exc:
        return ValidationResult(
            is_valid=False,
            reasons=_format_pydantic_errors(exc),
        )

    reasons: list[str] = []

    reference_now = now if now is not None else datetime.now(UTC)
    drift_seconds = abs((reference_now - txn.transaction_ts).total_seconds())
    if drift_seconds > TIMESTAMP_DRIFT_THRESHOLD_SECONDS:
        reasons.append("TIMESTAMP_DRIFT")

    if reasons:
        return ValidationResult(is_valid=False, reasons=reasons)
    return ValidationResult(is_valid=True, transaction=txn)
