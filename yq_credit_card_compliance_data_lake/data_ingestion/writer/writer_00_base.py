# -*- coding: utf-8 -*-

"""
NDJSON writer + Hive-style partition path builder.

This module **does not** import :mod:`one`; the caller passes
``storage_options`` (typically ``one.polars_storage_options``) explicitly so
the ``data_ingestion`` package keeps the dependency-direction invariant
declared in ``source-code-architect.md`` §3.1.
"""

from datetime import datetime
import typing as T

import polars as pl


def build_partition_path(now: datetime) -> str:
    """Return a Hive-style partition prefix ``year=YYYY/month=MM/day=DD``.

    No leading or trailing slash — caller composes with the base directory
    and file name.  Hive style is chosen so Glue / Athena partition
    projection works without re-mapping; doc1 §10.2 (Q2) standardises on
    day-level granularity for Phase 4 (the 1-shard demo would emit
    sub-100 KB files at ``hour=`` granularity, which is wasteful).

    Zero-padding is enforced on month and day so lexicographic sort matches
    chronological sort — required for tools that pick partitions
    alphabetically.
    """
    return f"year={now.year}/month={now.month:02d}/day={now.day:02d}"


def write_ndjson_to_s3(
    records: list[dict[str, T.Any]],
    s3_uri: str,
    storage_options: dict[str, str],
) -> None:
    """Write ``records`` as NDJSON at ``s3_uri`` using polars.

    Empty input is a no-op — this avoids leaving zero-byte files in Bronze
    when a batch is entirely quarantined (and vice versa).  The caller is
    expected to omit the corresponding ``s3_*_path`` field on the
    ``PipelineMetadata`` row in that case.

    :param records: list of plain dicts.  Heterogeneous schemas are tolerated
        — polars unifies columns across rows and fills missing values with
        null.  This is what the quarantine sink relies on (decode-error
        records share only ``_quarantine_*`` columns with validation-error
        records).
    :param s3_uri: full ``s3://bucket/key`` target.
    :param storage_options: dict accepted by polars's cloud-write layer;
        callers normally pass ``one.polars_storage_options``.
    """
    if not records:
        return
    df = pl.DataFrame(records)
    df.write_ndjson(s3_uri, storage_options=storage_options)
