#!/usr/bin/env python3

from yq_credit_card_compliance_data_lake.one.api import one
from yq_credit_card_compliance_data_lake.cdk.stack_enum import stack_enum

# Initialize stack instances to register them with the CDK application.
# Touching each cached_property triggers lazy construction and synthesis.
_ = stack_enum.infra_stack
_ = stack_enum.lambda_stack
_ = stack_enum.test_stack

# Synthesize CDK application to generate CloudFormation templates
# Produces infrastructure-as-code artifacts in the cdk.out directory
stack_enum.app.synth()

print(f"Preview stack at: {one.config.cloudformation_stack_url}")
