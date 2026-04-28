# -*- coding: utf-8 -*-

"""
Project-wide constants for Lambda deployment configuration.

These constants define fixed values that are referenced across the codebase —
CDK stacks, config classes, and deployment scripts. Centralizing them here
ensures consistency and makes it easy to audit all "magic strings" in one place.
"""

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
