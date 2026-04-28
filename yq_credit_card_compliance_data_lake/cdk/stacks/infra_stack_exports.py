# -*- coding: utf-8 -*-

"""
CloudFormation Stack Exports Interface

This module provides a standardized interface for external projects to access CloudFormation 
stack outputs and exports maintained by the current project. This is a good design pattern 
that solves common problems when accessing CloudFormation resources across projects.

**Core Values:**

1. **Avoid Reverse Engineering**: Other projects don't need to guess or reverse engineer 
   to determine available output value names
2. **Type Safety**: Provides typed property methods to access stack outputs, reducing 
   spelling errors
3. **Copy-Pasteable**: External projects can directly copy and paste this file into 
   their own codebase
4. **Unified Interface**: Whether accessing OutputKey or ExportName, both use unified 
   property methods

**Use Cases:**

When your project needs to access AWS resources maintained by other projects, you don't need to:

- Check source code to find out available output values
- Manually construct export names or output keys
- Worry about errors caused by naming changes

**How It Works:**

This module works in conjunction with the following files:

- lbd_stack_00_main.py: Defines the main Lambda stack structure
- lbd_stack_01_iam.py: Defines IAM-related resources and creates CloudFormation outputs and exports

In lbd_stack_01_iam.py, we create CloudFormation outputs:

.. code-block:: python

    self.output_iam_role_for_lambda_arn = cdk.CfnOutput(
        self,
        "IamRoleForLambdaArn",  # OutputKey
        value=self.iam_role_for_lambda.role_arn,
        export_name=f"{self.conf_env.prefix_name_slug}-lambda-role-arn",  # ExportName
    )

Then provide corresponding property methods in this module:

.. code-block:: python

    @cached_property
    def iam_role_for_lambda_arn(self) -> str:
        export_key = f"{self.prefix_name_slug}-lambda-role-arn"
        return self.exports[export_key]

**Typical Usage:**

.. code-block:: python

    # In external projects
    import boto3
    from some_project.exports import StackExports
    
    # Load stack exports
    cf_client = boto3.client("cloudformation")
    stack_exports = StackExports.load(cf_client=cf_client, env_name="dev")
    
    # Type-safe access to resource ARN
    lambda_role_arn = stack_exports.iam_role_for_lambda_arn
    
    # Use in your own CDK stack
    imported_role = iam.Role.from_role_arn(
        self, "ImportedLambdaRole", 
        role_arn=lambda_role_arn
    )

**Extension Guide:**

When you need to add new export values:

1. Create CfnOutput in the corresponding stack file (e.g., lbd_stack_01_iam.py)
2. Add corresponding @cached_property method in this file
3. External projects update this file to gain new access capabilities

This pattern is particularly suitable for infrastructure code management in microservice 
architectures, where each service can independently maintain its own infrastructure while 
providing standardized interfaces for other services to use.
"""

import typing as T
import dataclasses
from functools import cached_property

if T.TYPE_CHECKING:
    from mypy_boto3_cloudformation.client import CloudFormationClient
    from mypy_boto3_cloudformation.type_defs import DescribeStacksOutputTypeDef

# this value has to match the ``config.project_name``
project_name = "yq_credit_card_compliance_data_lake"
project_name_snake = project_name.replace("-", "_")
project_name_slug = project_name.replace("_", "-")
stack_name = f"{project_name_slug}-infra"


@dataclasses.dataclass
class StackExports:
    """
    CloudFormation Stack Exports Accessor

    This class provides a type-safe interface to access CloudFormation stack outputs and exports.
    It encapsulates interactions with the CloudFormation API and provides caching mechanisms
    to improve performance.

    **Main Features:**

    - Automatically construct stack name from environment name
    - Cache CloudFormation API responses for better performance
    - Provide type-safe property methods to access specific export values
    - Support accessing both OutputKey and ExportName approaches

    **Usage Examples:**

    .. code-block:: python

        import boto3

        # Create CloudFormation client
        cf_client = boto3.client("cloudformation")

        # Load stack exports for specific environment
        stack_exports = StackExports.load(cf_client=cf_client, env_name="dev")

        # Access specific export values
        lambda_role_arn = stack_exports.iam_role_for_lambda_arn
        print(f"Lambda IAM Role ARN: {lambda_role_arn}")

        # Or directly access raw output/export dictionaries
        all_outputs = stack_exports.outputs  # OutputKey -> OutputValue
        all_exports = stack_exports.exports  # ExportName -> ExportValue

    **Internal Implementation Details:**

    - env_name: Environment name (e.g., "dev", "test", "prod") used to construct stack name
    - response: Cached response from CloudFormation describe_stacks API to avoid repeated calls
    - All property access uses @cached_property decorator for caching optimization

    **Steps to Extend New Export Values:**

    1. Add CfnOutput in the corresponding stack mixin
    2. Add corresponding @cached_property method in this class
    3. Ensure property names are descriptive and follow snake_case naming convention
    """

    response: "DescribeStacksOutputTypeDef" = dataclasses.field(init=False)

    @classmethod
    def load(
        cls,
        cf_client: "CloudFormationClient",
    ):
        """
        Load stack export information from CloudFormation for specified environment

        This factory method creates a StackExports instance and loads stack information
        from AWS CloudFormation service. It automatically constructs the stack name
        based on project name and environment name, then calls the describe_stacks API.

        :param cf_client: boto3 CloudFormation client instance with permission to read stack info

        :return: StackExports instance with loaded stack information
        """
        stack_exports = cls()
        response = cf_client.describe_stacks(StackName=stack_name)
        stack_exports.response = response
        return stack_exports

    @cached_property
    def outputs(self) -> dict[str, str]:
        output_list = self.response["Stacks"][0]["Outputs"]
        outputs = {dct["OutputKey"]: dct["OutputValue"] for dct in output_list}
        return outputs

    @cached_property
    def exports(self) -> dict[str, str]:
        output_list = self.response["Stacks"][0]["Outputs"]
        exports = {dct["ExportName"]: dct["OutputValue"] for dct in output_list}
        return exports

    # --------------------------------------------------------------------------
    # access output value or export value
    # --------------------------------------------------------------------------
    # @cached_property
    # def iam_role_for_lambda_arn(self) -> str:
    #     """
    #     Get the IAM Role ARN used by Lambda functions.
    #     """
    #     output_key = f"IamRoleForLambdaArn"
    #     return self.outputs[output_key]

    @cached_property
    def iam_role_for_lambda_arn(self) -> str:
        """
        Get the IAM Role ARN used by Lambda functions.
        """
        export_key = f"{project_name_slug}-lambda-role-arn"
        return self.exports[export_key]


# ------------------------------------------------------------------------------
# Usage example
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    import boto3

    boto_ses = boto3.Session(profile_name=os.environ["LOCAL_AWS_PROFILE"])
    cf_client = boto_ses.client("cloudformation")
    stack_exports = StackExports.load(cf_client=cf_client)
    print(stack_exports.iam_role_for_lambda_arn)
