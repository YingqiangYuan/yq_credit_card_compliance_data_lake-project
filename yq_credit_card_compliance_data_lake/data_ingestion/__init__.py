# -*- coding: utf-8 -*-

"""
Data ingestion subpackage — code that lands raw events from upstream sources
into the data lake.

Layout:

- ``models.py``    : Pydantic models for each ingestion source
- ``faker.py``     : Business-specific fake-data generators (TransactionFaker,
  …) — strictly dev/test tooling
- ``producer/``    : Sync writers that push records to Kinesis / Kafka / S3
  Landing Zone
- ``consumer/``    : (Phase 2) Lambda-side parsing, validation, Bronze write
- ``quality/``     : (Phase 5) Centralized data-quality rule registry/engine

This subpackage **must not** depend on ``one/`` or ``lbd/``. The Lambda
handlers in ``lbd/`` may depend on this package, not the other way around.
"""
