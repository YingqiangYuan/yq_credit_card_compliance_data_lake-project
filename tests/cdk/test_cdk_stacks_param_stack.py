# -*- coding: utf-8 -*-

"""
CDK synthesis smoke test.

Verifies that all stacks can be synthesized without errors — i.e., the CDK
constructs, resource references, and cross-stack imports are wired up
correctly.  This catches common mistakes like missing environment variables,
invalid ``Fn.import_value`` references, or incompatible construct versions
**before** deploying to AWS.

Note: this test uses ``run_unit_test`` (no coverage) instead of
``run_cov_test`` because CDK synthesis exercises AWS CDK internals rather
than project business logic.
"""


class Test:
    def test_synth(self):
        from yq_credit_card_compliance_data_lake.cdk.stack_enum import stack_enum

        _ = stack_enum.infra_stack
        _ = stack_enum.lambda_stack

        stack_enum.app.synth()


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_unit_test

    run_unit_test(__file__)
