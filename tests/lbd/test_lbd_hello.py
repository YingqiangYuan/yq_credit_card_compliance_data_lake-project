# -*- coding: utf-8 -*-

"""
Unit test for the ``hello`` Lambda function.

Tests the business logic directly by instantiating ``Input`` and calling
``main()`` — no AWS services involved.  The ``disable_logger`` fixture
suppresses log output for cleaner test output.

This is the simplest example of the handler testing pattern: construct the
Pydantic ``Input`` model, call ``main()``, and assert on the ``Output`` fields.
"""

from yq_credit_card_compliance_data_lake.lbd.hello import Input


def test_hello(
    disable_logger,
):
    # invoke api
    output = Input(name="alice").main()
    # validate response
    assert output.message == "hello alice"


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.lbd.hello",
        preview=False,
    )
