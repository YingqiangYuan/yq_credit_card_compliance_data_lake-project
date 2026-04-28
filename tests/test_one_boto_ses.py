# -*- coding: utf-8 -*-

"""
Integration-style test for the ``One`` singleton's boto session.

Calls ``sts:GetCallerIdentity`` to verify that the boto session is correctly
configured and that AWS credentials are available.  This test requires real
AWS credentials (via the profile configured in ``.env``) and is **not** mocked.
"""

from yq_credit_card_compliance_data_lake.one.api import one


def test():
    _ = one.boto_ses.client("sts").get_caller_identity()


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.config",
        is_folder=True,
        preview=False,
    )
