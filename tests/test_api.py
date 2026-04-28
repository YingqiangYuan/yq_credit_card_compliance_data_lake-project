# -*- coding: utf-8 -*-

"""
Smoke test for the public API module.

Verifies that ``yq_credit_card_compliance_data_lake.api`` can be imported without errors.
This catches broken re-exports, missing dependencies, and import-time
exceptions early — before any functional tests run.
"""

from yq_credit_card_compliance_data_lake import api


def test():
    _ = api


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.api",
        preview=False,
    )
