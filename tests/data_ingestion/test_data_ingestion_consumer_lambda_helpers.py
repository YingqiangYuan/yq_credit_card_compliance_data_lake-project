# -*- coding: utf-8 -*-

"""
Unit tests for ``data_ingestion/consumer/consumer_02_lambda_helpers.py``.

Exercises every branch of :func:`decode_kinesis_records`:

- Happy path — utf-8 + JSON object → ``decoded`` list.
- Mixed batch — some valid, some bad — partition correctly.
- ``DECODE_ERROR:utf8`` — invalid utf-8 bytes.
- ``DECODE_ERROR:json`` — utf-8 ok but not valid JSON.
- ``DECODE_ERROR:not_dict`` — JSON ok but not an object (e.g. an array).
- Empty input — both result lists are empty.
- Quarantine entry shape — ``_raw_b64`` round-trips back to the original
  payload (so an analyst can recover exact bytes from the quarantine NDJSON).
"""

import base64
import json

from yq_credit_card_compliance_data_lake.data_ingestion.consumer.api import (
    decode_kinesis_records,
)


def _payload_bytes(d: dict) -> bytes:
    return json.dumps(d).encode("utf-8")


# ------------------------------------------------------------------------------
# Happy path
# ------------------------------------------------------------------------------
def test_all_valid_payloads_land_in_decoded():
    raws = [
        _payload_bytes({"transaction_id": "t1", "amount": 1.0}),
        _payload_bytes({"transaction_id": "t2", "amount": 2.0}),
    ]
    decoded, errors = decode_kinesis_records(raws)
    assert errors == []
    assert decoded == [
        {"transaction_id": "t1", "amount": 1.0},
        {"transaction_id": "t2", "amount": 2.0},
    ]


def test_empty_input_returns_two_empty_lists():
    decoded, errors = decode_kinesis_records([])
    assert decoded == []
    assert errors == []


# ------------------------------------------------------------------------------
# Decode failure branches
# ------------------------------------------------------------------------------
def test_invalid_utf8_lands_in_errors_with_utf8_reason():
    bad_bytes = b"\xff\xfe\xff"  # not valid utf-8
    decoded, errors = decode_kinesis_records([bad_bytes])
    assert decoded == []
    assert len(errors) == 1
    err = errors[0]
    assert err["_quarantine_reason"][0].startswith("DECODE_ERROR:utf8:")
    # Round-trip the raw bytes to verify they are recoverable.
    assert base64.b64decode(err["_raw_b64"]) == bad_bytes


def test_invalid_json_lands_in_errors_with_json_reason():
    raw = b"not json at all"
    decoded, errors = decode_kinesis_records([raw])
    assert decoded == []
    assert len(errors) == 1
    assert errors[0]["_quarantine_reason"][0].startswith("DECODE_ERROR:json:")
    assert base64.b64decode(errors[0]["_raw_b64"]) == raw


def test_json_array_lands_in_errors_with_not_dict_reason():
    raw = json.dumps(["not", "a", "dict"]).encode("utf-8")
    decoded, errors = decode_kinesis_records([raw])
    assert decoded == []
    assert len(errors) == 1
    reason = errors[0]["_quarantine_reason"][0]
    assert reason == "DECODE_ERROR:not_dict:list"


def test_json_scalar_lands_in_errors_with_not_dict_reason():
    raw = json.dumps(42).encode("utf-8")
    decoded, errors = decode_kinesis_records([raw])
    assert decoded == []
    assert errors[0]["_quarantine_reason"][0] == "DECODE_ERROR:not_dict:int"


# ------------------------------------------------------------------------------
# Mixed batch
# ------------------------------------------------------------------------------
def test_mixed_batch_partitions_correctly():
    raws = [
        _payload_bytes({"transaction_id": "ok-1"}),
        b"\xff",  # utf-8 fail
        b"this is not json",  # json fail
        _payload_bytes({"transaction_id": "ok-2"}),
        json.dumps([1, 2]).encode("utf-8"),  # not_dict
    ]
    decoded, errors = decode_kinesis_records(raws)
    assert [r["transaction_id"] for r in decoded] == ["ok-1", "ok-2"]
    assert len(errors) == 3
    error_codes = {err["_quarantine_reason"][0].split(":")[1] for err in errors}
    assert error_codes == {"utf8", "json", "not_dict"}


# ------------------------------------------------------------------------------
# Quarantine entry shape
# ------------------------------------------------------------------------------
def test_error_entry_has_expected_shape():
    decoded, errors = decode_kinesis_records([b"\xff"])
    err = errors[0]
    assert set(err.keys()) == {"_raw_b64", "_quarantine_reason", "_quarantine_ts"}
    assert isinstance(err["_quarantine_reason"], list)
    assert isinstance(err["_quarantine_ts"], str)
    # ts is ISO 8601 with timezone — basic sanity (year prefix).
    assert err["_quarantine_ts"].startswith("20")


def test_all_errors_in_one_batch_share_the_same_quarantine_ts():
    """One batch = one Lambda invocation = one arrival window.  Sharing the
    timestamp keeps the quarantine NDJSON queryable by ``_quarantine_ts``
    for "all decode failures from invocation X" without per-record clutter.
    """
    decoded, errors = decode_kinesis_records([b"\xff", b"\xfe", b"not json"])
    assert len({err["_quarantine_ts"] for err in errors}) == 1


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.data_ingestion.consumer.consumer_02_lambda_helpers",
        preview=False,
    )
