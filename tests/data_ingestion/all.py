# -*- coding: utf-8 -*-

"""
Run all data-ingestion unit tests with coverage scoped to ``data_ingestion/``.
"""

if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.data_ingestion",
        is_folder=True,
        preview=False,
    )
