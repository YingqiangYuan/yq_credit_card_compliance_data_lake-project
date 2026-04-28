# -*- coding: utf-8 -*-

"""
Unit tests for ``data_ingestion/writer/writer_00_base.py``.

Covers:

- ``build_partition_path`` — Hive-style format, zero-padding, no trailing
  slash.
- ``write_ndjson_to_s3`` — empty-records short-circuit (no polars call).
- Polars NDJSON serialisation sanity — round-trip via a local file path.
  (The actual S3 write path goes through polars's Rust object_store, which
  moto cannot intercept; that path is exercised by the Phase 4 e2e smoke
  scripts in ``tests_e2e/`` instead.)
"""

import json
from datetime import datetime, UTC
from unittest.mock import patch

import polars as pl

from yq_credit_card_compliance_data_lake.data_ingestion.writer.api import (
    build_partition_path,
    write_ndjson_to_s3,
)


# ------------------------------------------------------------------------------
# build_partition_path
# ------------------------------------------------------------------------------
def test_build_partition_path_zero_pads_single_digit_components():
    now = datetime(2026, 1, 5, tzinfo=UTC)
    assert build_partition_path(now) == "year=2026/month=01/day=05"


def test_build_partition_path_two_digit_components():
    now = datetime(2026, 12, 25, tzinfo=UTC)
    assert build_partition_path(now) == "year=2026/month=12/day=25"


def test_build_partition_path_no_trailing_slash():
    now = datetime(2026, 4, 28, tzinfo=UTC)
    assert not build_partition_path(now).endswith("/")
    assert not build_partition_path(now).startswith("/")


def test_build_partition_path_ignores_subday_components():
    """Hour / minute / second must NOT leak into the prefix — Phase 4 is
    day-level partitioning by design (doc1 §10.2 Q2)."""
    a = datetime(2026, 4, 28, 0, 0, 0, tzinfo=UTC)
    b = datetime(2026, 4, 28, 23, 59, 59, tzinfo=UTC)
    assert build_partition_path(a) == build_partition_path(b)


# ------------------------------------------------------------------------------
# write_ndjson_to_s3
# ------------------------------------------------------------------------------
def test_write_ndjson_empty_records_short_circuits():
    """Empty input must not invoke polars at all — guards against a regression
    where the function attempts an empty DataFrame write that would either
    create a zero-byte file or raise."""
    with patch.object(pl, "DataFrame") as mock_df:
        write_ndjson_to_s3([], "s3://does-not-matter/x.ndjson", {"AWS_REGION": "us-east-1"})
        mock_df.assert_not_called()


# ------------------------------------------------------------------------------
# Polars NDJSON serialisation — sanity
# ------------------------------------------------------------------------------
def test_polars_ndjson_round_trips_one_object_per_line(tmp_path):
    """Sanity: polars NDJSON output is one JSON object per line.

    Not a strict spec test (polars owns the format), but a guard against
    polars semantic changes that would break Athena's NDJSON parser.
    """
    records = [
        {"a": 1, "b": "x"},
        {"a": 2, "b": "y"},
        {"a": 3, "b": "z"},
    ]
    out = tmp_path / "out.ndjson"
    df = pl.DataFrame(records)
    df.write_ndjson(str(out))

    text = out.read_text(encoding="utf-8")
    lines = [ln for ln in text.split("\n") if ln]
    assert len(lines) == 3
    decoded = [json.loads(ln) for ln in lines]
    assert decoded == records


def test_polars_ndjson_handles_heterogeneous_schema(tmp_path):
    """Quarantine sink mixes decode-error rows (only ``_quarantine_*`` cols)
    with validation-error rows (full Transaction shape).  Polars must fill
    missing columns with null rather than raising.
    """
    records = [
        {"_raw_b64": "abc==", "_quarantine_reason": ["DECODE_ERROR:json"]},
        {
            "transaction_id": "00000000-0000-0000-0000-000000000000",
            "amount": 12.34,
            "_quarantine_reason": ["INVALID_FIELD:currency:enum"],
        },
    ]
    out = tmp_path / "quarantine.ndjson"
    df = pl.DataFrame(records)
    df.write_ndjson(str(out))

    decoded = [json.loads(ln) for ln in out.read_text().splitlines() if ln]
    assert len(decoded) == 2
    # Each record contains all keys (with None for missing values).
    union_keys = {"_raw_b64", "_quarantine_reason", "transaction_id", "amount"}
    for row in decoded:
        assert set(row.keys()) == union_keys


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.data_ingestion.writer",
        is_folder=True,
        preview=False,
    )
