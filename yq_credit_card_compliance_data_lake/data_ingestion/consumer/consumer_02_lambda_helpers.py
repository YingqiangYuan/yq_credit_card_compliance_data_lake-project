# -*- coding: utf-8 -*-

"""
Lambda-event-side decoding helpers for the Kinesis consumer path.

These helpers operate on raw payload bytes already extracted from a
``KinesisStreamEvent`` (powertools-decoded) by the Lambda handler.  Keeping
them stdlib-only preserves the ``data_ingestion/consumer/`` invariant
declared in ``source-code-architect.md`` §3.1 ("consumer 仅依赖 boto3 +
stdlib") and makes them trivially unit-testable without any AWS layer.
"""

import base64
import json
from datetime import datetime, UTC


def decode_kinesis_records(
    raw_payloads: list[bytes],
) -> tuple[list[dict], list[dict]]:
    """Decode Kinesis-record payloads into dicts; partition decode failures.

    :param raw_payloads: list of bytes — already base64-decoded by the
        Lambda runtime / powertools wrapper (i.e.
        ``KinesisStreamEvent.records[*].kinesis.data_as_bytes()``).
    :returns: ``(decoded, decode_errors)``.  ``decoded`` is the list of dict
        payloads ready for downstream Pydantic validation.  ``decode_errors``
        holds quarantine-shaped entries
        ``{"_raw_b64": ..., "_quarantine_reason": [...], "_quarantine_ts": ...}``
        so the caller can append them to the quarantine sink without
        re-shaping.

    Reason codes:

    - ``DECODE_ERROR:utf8:<reason>`` — payload bytes are not valid UTF-8.
    - ``DECODE_ERROR:json:<msg>`` — text parsed but not valid JSON.
    - ``DECODE_ERROR:not_dict:<type>`` — JSON parsed but is not an object
      (e.g. an array or bare scalar); downstream schemas all require object
      shape.

    The original payload bytes are preserved as base64 in ``_raw_b64`` so an
    analyst can recover exact bytes from the quarantine NDJSON file.
    """
    decoded: list[dict] = []
    decode_errors: list[dict] = []

    # Single timestamp for the whole batch — every record in the same Lambda
    # invocation shares an arrival window, so per-record now() calls would
    # be noise without precision benefit.
    quarantine_ts = datetime.now(UTC).isoformat()

    for raw in raw_payloads:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            decode_errors.append(
                _decode_error_entry(raw, f"DECODE_ERROR:utf8:{exc.reason}", quarantine_ts)
            )
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            decode_errors.append(
                _decode_error_entry(raw, f"DECODE_ERROR:json:{exc.msg}", quarantine_ts)
            )
            continue
        if not isinstance(payload, dict):
            decode_errors.append(
                _decode_error_entry(
                    raw,
                    f"DECODE_ERROR:not_dict:{type(payload).__name__}",
                    quarantine_ts,
                )
            )
            continue
        decoded.append(payload)

    return decoded, decode_errors


def _decode_error_entry(raw: bytes, reason: str, ts: str) -> dict:
    return {
        "_raw_b64": base64.b64encode(raw).decode("ascii"),
        "_quarantine_reason": [reason],
        "_quarantine_ts": ts,
    }
