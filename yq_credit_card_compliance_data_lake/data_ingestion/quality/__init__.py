# -*- coding: utf-8 -*-

"""
Data-quality validators for ingestion sources.

Phase 4 simplification: rules are inlined as Python (Pydantic + a few extra
range checks).  Phase 5 will replace this subpackage with a
configuration-driven rules registry shared across sources.
"""
