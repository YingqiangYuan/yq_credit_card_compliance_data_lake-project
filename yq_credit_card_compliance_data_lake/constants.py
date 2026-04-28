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
