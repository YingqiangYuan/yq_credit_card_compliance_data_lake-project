# -*- coding: utf-8 -*-

"""
Integration test for CloudFormation stack exports.

Verifies that the ``StackExports`` dataclass can load real exported values from
a deployed infra stack.  This catches mismatches between the export names
defined in ``infra_stack.py`` and the property names in
``infra_stack_exports.py``.

Requires a prior ``cdk deploy`` of the infra stack.
"""

from yq_credit_card_compliance_data_lake.api import one
from yq_credit_card_compliance_data_lake.cdk.stacks.infra_stack_exports import StackExports


class TestLbdStackExports:
    def test(self):
        stack_exports = StackExports.load(
            cf_client=one.cloudformation_client,
        )
        _ = stack_exports.iam_role_for_lambda_arn


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_unit_test

    run_unit_test(__file__)
