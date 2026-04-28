#!/usr/bin/env python3

from yq_credit_card_compliance_data_lake.one.api import one
from yq_credit_card_compliance_data_lake.cdk.stack_enum import stack_enum

# Initialize Lambda stack instance to register it with the CDK application
# This triggers lazy initialization of all stack constructs and dependencies
_ = stack_enum.infra_stack
_ = stack_enum.lambda_stack

# Synthesize CDK application to generate CloudFormation templates
# Produces infrastructure-as-code artifacts in the cdk.out directory
stack_enum.app.synth()

print(f"Preview stack at: {one.config.cloudformation_stack_url}")
