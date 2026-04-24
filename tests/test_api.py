# -*- coding: utf-8 -*-

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
