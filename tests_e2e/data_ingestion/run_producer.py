# -*- coding: utf-8 -*-

"""
Thin entry-point that invokes the packaged ``produce`` flow.

The real logic lives in ``yq_credit_card_compliance_data_lake.tests.e2e``;
this script just parses ``argv`` and calls it.

Usage::

    python -m tests_e2e.data_ingestion.run_producer        # default 100
    python -m tests_e2e.data_ingestion.run_producer 1500   # 3 batches
"""

import sys

from yq_credit_card_compliance_data_lake.tests.e2e.api import produce_transactions


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    produce_transactions(n)
