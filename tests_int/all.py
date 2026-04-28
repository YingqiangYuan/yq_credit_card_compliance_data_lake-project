# -*- coding: utf-8 -*-

"""
Run **all** integration tests.

Integration tests (``tests_int/``) hit real AWS resources — deployed Lambda
functions, real S3 buckets, and live CloudFormation stacks.  They require valid
AWS credentials and a prior deployment (``cdk deploy``).

**Why separate ``tests/`` and ``tests_int/``?**  Unit tests (``tests/``) use
moto mocks and run in seconds with no AWS account; integration tests verify
end-to-end behavior against real infrastructure.  Keeping them in separate
directories lets you run ``pytest tests/`` in CI (fast, no credentials) and
``pytest tests_int/`` after a deployment (slower, needs credentials).
"""

if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_unit_test

    run_unit_test(
        __file__,
        is_folder=True,
    )
