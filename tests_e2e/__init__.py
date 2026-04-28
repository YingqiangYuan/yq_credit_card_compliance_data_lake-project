# -*- coding: utf-8 -*-

"""
End-to-end smoke scripts that exercise real AWS resources.

This directory is **not** unit tests (mocked, fast, run in CI) and **not**
integration tests (automated, may hit cloud). It holds **manually-run scripts**
that a developer invokes to verify a full producer → consumer loop against a
live Kinesis stream provisioned by the ``TestStack``.

Workflow per data-ingestion path::

    cdk deploy yq-credit-card-compliance-data-lake-test
    python tests_e2e/<source>/purge_stream.py     # optional, drain leftovers
    python tests_e2e/<source>/run_producer.py 100 # push 100 fake records
    python tests_e2e/<source>/run_consumer.py     # read & pretty-print them
    cdk destroy yq-credit-card-compliance-data-lake-test

Each subdirectory targets one ingestion source (Phase 3 covers
``data_ingestion``).
"""
