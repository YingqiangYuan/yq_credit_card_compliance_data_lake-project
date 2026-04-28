# -*- coding: utf-8 -*-

"""
Bronze / Quarantine writers for the data-ingestion path.

NDJSON via polars is the Phase 4 raw format; Bronze→Silver conversion
to Parquet happens in a later phase.  Polars is the project's data-frame
library of record, so using it here keeps the writing side of the data lake
speaking one library throughout.
"""
