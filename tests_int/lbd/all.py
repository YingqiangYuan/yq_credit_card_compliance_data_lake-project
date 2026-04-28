# -*- coding: utf-8 -*-

"""
Run all Lambda function integration tests.
"""

if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_unit_test

    run_unit_test(
        __file__,
        is_folder=True,
    )
