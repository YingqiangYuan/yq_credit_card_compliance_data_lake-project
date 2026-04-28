# -*- coding: utf-8 -*-

"""
Lambda handler entry point — the module that AWS Lambda's runtime invokes.

**Why a separate file that just re-exports handlers?**

The Lambda ``handler`` setting in CDK (and in the AWS console) is a dotted path
like ``yq_credit_card_compliance_data_lake.lambda_function.hello_handler``.  By funneling
all handlers through this single module, we get:

1. **One predictable import path** — the CDK stack only needs to know
   ``lambda_function.<name>_handler``; it never reaches into ``lbd/`` internals.
2. **Controlled import order** — any shared setup that must happen before
   handler execution (e.g., logger initialization) can be placed here.
3. **Easy auditing** — one glance at this file shows every handler that is
   deployed.

When adding a new Lambda function, import its ``lambda_handler`` here with an
alias and register it in ``config_00_main.py``.
"""

# fmt: off
from yq_credit_card_compliance_data_lake.lbd.hello import lambda_handler as hello_handler
from yq_credit_card_compliance_data_lake.lbd.s3sync import lambda_handler as s3sync_handler
from yq_credit_card_compliance_data_lake.lbd.transaction_ingestion import lambda_handler as transaction_ingestion_handler
# fmt: on
