# -*- coding: utf-8 -*-

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