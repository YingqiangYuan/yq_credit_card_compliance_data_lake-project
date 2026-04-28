# -*- coding: utf-8 -*-

"""
Run all generic faker unit tests with coverage scoped to ``faker/``.
"""

if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.faker",
        is_folder=True,
        preview=False,
    )
