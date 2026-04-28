# -*- coding: utf-8 -*-

"""
PynamoDB models for project-managed DynamoDB tables.

One file per project — every DynamoDB table this project writes to gets a
``Model`` subclass here.  Phase 4 introduces ``PipelineMetadata``; later
phases (e.g. quality-rule registry, replay-state) append more models below
without splitting into a subpackage until the file genuinely warrants it.

Connection routing follows the ``pynamodb-session-manager`` pattern: the
caller wraps DynamoDB I/O in ``use_boto_session(Model, bsm)`` so every
PynamoDB request goes through the project's :class:`BotoSesManager` (i.e.
``one.bsm``) rather than PynamoDB's default global connection.  See the
sibling project ``yq_dynamodb_poc/examples/00-minimal-poc/s01_minimal_poc.py``
for the canonical usage shape.
"""

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.constants import PAY_PER_REQUEST_BILLING_MODE


# Hardcoded table name kept in sync with ``Config.dynamodb_table_pipeline_metadata``
# by ``tests/config/test_config.py``.  Why hardcode instead of computing from
# Config?  Doing so would require ``data_ingestion`` to import ``one``/``Config``
# (an instance is needed, not just the class), which violates the dependency
# invariant in ``source-code-architect.md`` §3.1.  The duplication is one line
# guarded by a sync-test — acceptable.
_PIPELINE_METADATA_TABLE_NAME = "yq-credit-card-compliance-data-lake-pipeline-metadata"


class _PipelineStatusIndex(GlobalSecondaryIndex):
    """GSI ``status-index`` — query "all runs with status X, ordered by start_ts".

    Use case: oncall runbook asks "show me every FAILED pipeline run in the
    past 24 h".  Without this GSI it would require a full table scan
    filtered by ``run_status``.  ``AllProjection`` is fine here because the
    metadata row is small (~12 attributes, all scalar) — projecting every
    column makes the query result self-contained.
    """

    class Meta:
        index_name = "status-index"
        projection = AllProjection()

    run_status = UnicodeAttribute(hash_key=True)
    start_ts = UnicodeAttribute(range_key=True)


class PipelineMetadata(Model):
    """One row per pipeline run — see doc1 §6.

    Range key format: ``f"{utc_iso_seconds}___{lambda_request_id}"``.  The
    triple-underscore separator (instead of ``#``) means the same string can
    be reused inside S3 file names without escaping — Bronze and Quarantine
    both write a ``{run_id}.ndjson`` file per invocation.  Sort order on the
    range key is therefore chronological, so "last 100 runs of pipeline X"
    needs no GSI.

    Attribute set is a superset of doc1 §6: we also store
    ``s3_quarantine_path`` because Phase 4 emits quarantine files in
    addition to Bronze, and the ops dashboard needs both URIs to triage a
    PARTIAL run.
    """

    class Meta:
        table_name = _PIPELINE_METADATA_TABLE_NAME
        region = "us-east-1"
        billing_mode = PAY_PER_REQUEST_BILLING_MODE

    # --- keys ---
    pipeline_name = UnicodeAttribute(hash_key=True)
    run_id = UnicodeAttribute(range_key=True)

    # --- status & timing ---
    run_status = UnicodeAttribute()
    start_ts = UnicodeAttribute()
    end_ts = UnicodeAttribute(null=True)

    # --- counts ---
    total_records = NumberAttribute()
    valid_records = NumberAttribute()
    quarantine_records = NumberAttribute()

    # --- locations ---
    s3_output_path = UnicodeAttribute(null=True)
    s3_quarantine_path = UnicodeAttribute(null=True)

    # --- diagnostics ---
    error_message = UnicodeAttribute(null=True)
    lambda_request_id = UnicodeAttribute(null=True)

    # --- indexes ---
    status_index = _PipelineStatusIndex()
