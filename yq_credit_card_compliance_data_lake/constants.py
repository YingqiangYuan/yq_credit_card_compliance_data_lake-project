# -*- coding: utf-8 -*-

"""
Project-wide constants for Lambda deployment configuration.

These constants define fixed values that are referenced across the codebase —
CDK stacks, config classes, and deployment scripts. Centralizing them here
ensures consistency and makes it easy to audit all "magic strings" in one place.

All cross-module string enums (``StrEnum``) also live here. Modules must NOT
define inline enums in their own ``models.py`` — keeping every enum value in
one file makes auditing and refactoring a single grep operation.
"""

import enum


LATEST = "$LATEST"
"""
The special Lambda function version name that is used for the latest version.
"""

LIVE = "LIVE"
"""
The Lambda function alias name that serving incoming traffics.
"""


IS_LAMBDA_X86 = True
"""
Indicates whether the lambda function is running on an x86 architecture or ARM architecture.
if True, the lambda function is running on an x86 architecture.
if False, the lambda function is running on an ARM architecture.
"""


# ------------------------------------------------------------------------------
# Data Ingestion — Transaction stream enums
# ------------------------------------------------------------------------------
class AuthStatus(enum.StrEnum):
    """Credit-card transaction authorization outcome."""

    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    PENDING = "PENDING"


class Channel(enum.StrEnum):
    """Channel through which a transaction was initiated."""

    POS = "POS"
    ECOM = "ECOM"
    ATM = "ATM"
    PHONE = "PHONE"
    RECURRING = "RECURRING"


class Currency(enum.StrEnum):
    """ISO 4217 currency codes accepted by the platform.

    Start with the six most-common; add more as business onboards new corridors.
    """

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CNY = "CNY"
    JPY = "JPY"
    CAD = "CAD"


# ------------------------------------------------------------------------------
# Data Quality — severity level for validation rule violations
# ------------------------------------------------------------------------------
class Severity(enum.StrEnum):
    """Severity of a data-quality rule violation.

    - ``ERROR``   : record is quarantined (does not enter Bronze).
    - ``WARNING`` : record passes through but is tagged with ``_quality_warnings``.
    """

    ERROR = "ERROR"
    WARNING = "WARNING"


# ------------------------------------------------------------------------------
# Pipeline metadata — values stored on every DynamoDB ``pipeline-metadata`` row
# ------------------------------------------------------------------------------
class PipelineStatus(enum.StrEnum):
    """Lifecycle state of a pipeline run.

    - ``RUNNING`` : row written at handler entry, before any work happens.
    - ``SUCCESS`` : every record in the batch ended up in Bronze.
    - ``PARTIAL`` : at least one record landed in Quarantine but the batch
      itself completed normally; **not** treated as a failure for paging.
    - ``FAILED``  : exception escaped the handler — the batch will be retried
      by the Event Source Mapping and (after exhausting retries) sent to the
      DLQ.
    """

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class PipelineName(enum.StrEnum):
    """Stable identifiers used as the ``pipeline_name`` partition key in the
    DynamoDB metadata table.

    Treat values as **append-only**: once a name is in production, never
    rename it — that would orphan all historical metadata rows.  New
    pipelines (Phase 6 Kafka, Phase 7 batch sources) append entries here.
    """

    TRANSACTION_INGESTION = "txn-realtime-ingestion"
