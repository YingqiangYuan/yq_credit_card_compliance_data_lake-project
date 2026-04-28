# -*- coding: utf-8 -*-

"""
Thin entry-point that invokes the packaged ``consume`` flow.

The real logic lives in ``yq_credit_card_compliance_data_lake.tests.e2e``;
this script just calls it.

Usage::

    python -m tests_e2e.data_ingestion.run_consumer
"""

from yq_credit_card_compliance_data_lake.tests.e2e.api import consume_transactions


if __name__ == "__main__":
    consume_transactions()
