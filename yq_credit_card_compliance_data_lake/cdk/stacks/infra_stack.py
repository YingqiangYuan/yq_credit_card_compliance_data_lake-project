# -*- coding: utf-8 -*-

"""
Infrastructure stack — long-lived, shared resources (IAM, production data
streams).

**Why a separate stack from Lambda?**

CDK deploys each stack independently.  Infrastructure resources like IAM roles
and Kinesis streams change **rarely**, while Lambda function code changes
**frequently** (every feature iteration).  Splitting them into two stacks gives
us:

1. **Faster deploys** — the common case (code change) only touches the Lambda
   stack.  No need to diff or re-deploy IAM resources on every push.
2. **Blast-radius isolation** — a bad Lambda deploy cannot accidentally modify
   IAM permissions or destroy a stream that downstream consumers depend on, and
   vice versa.  Each stack has its own CloudFormation changeset and rollback
   boundary.
3. **Cross-stack references** — the infra stack exports the IAM role ARN via
   ``CfnOutput``.  The Lambda stack imports it with ``Fn.import_value``.  This
   is a standard CloudFormation pattern for decoupling stacks that share
   resources.

**Section numbering convention** (``s01_``, ``s02_``, …): methods are prefixed
with a section number so that ``__init__`` reads like a table of contents and
the execution order is unambiguous.
"""

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kinesis as kinesis

from constructs import Construct

from ...one.api import One


class InfraStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        one: One,
        **kwargs,
    ) -> None:
        self.one = one

        super().__init__(
            scope=scope,
            id=f"{self.one.config.project_name_slug}-infra",
            **kwargs,
        )

        self.s01_create_iam_roles()
        # self.s02_create_kinesis_streams()

    def s01_create_iam_roles(self):
        """
        IAM related resources.

        Ref:

        - IAM Object quotas: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_iam-quotas.html#reference_iam-quotas-entities
        """

        self.stat_iam_list_account_aliases = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["iam:ListAccountAliases"],
            resources=["*"],
        )

        self.stat_s3_bucket_read = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:ListBucket",
                "s3:GetObject",
                "s3:GetObjectAttributes",
                "s3:GetObjectTagging",
            ],
            resources=[
                f"arn:aws:s3:::{self.one.s3dir_data.bucket}",
                f"arn:aws:s3:::{self.one.s3dir_data.bucket}/{self.one.s3dir_data.key}*",
            ],
        )

        self.stat_s3_bucket_write = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:PutObjectTagging",
                "s3:DeleteObjectTagging",
            ],
            resources=[
                f"arn:aws:s3:::{self.one.s3dir_data.bucket}",
                f"arn:aws:s3:::{self.one.s3dir_data.bucket}/{self.one.s3dir_data.key}*",
            ],
        )

        # declare iam role
        self.iam_role_for_lambda = iam.Role(
            scope=self,
            id="IamRoleForLambda",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=f"{self.one.config.project_name_snake}-{cdk.Aws.REGION}-lambda",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
            inline_policies={
                f"{self.one.config.project_name_snake}-{cdk.Aws.REGION}-lambda": iam.PolicyDocument(
                    statements=[
                        self.stat_iam_list_account_aliases,
                        self.stat_s3_bucket_read,
                        self.stat_s3_bucket_write,
                    ]
                )
            },
        )

        self.output_iam_role_for_lambda_arn = cdk.CfnOutput(
            self,
            "IamRoleForLambdaArn",
            value=self.iam_role_for_lambda.role_arn,
            export_name=f"{self.one.config.project_name_slug}-lambda-role-arn",
        )

    def s02_create_kinesis_streams(self):
        """Production Kinesis stream(s).

        Lightweight demo configuration: 1 PROVISIONED shard, 7-day retention,
        ``DESTROY`` removal policy.  Original doc1 §1.1 spec called for 4
        shards to handle ~800 TPS peak, but this project is a portfolio demo
        and a single shard (1 MB/s, 1000 records/s) is more than enough.
        """
        self.kinesis_stream_transaction = kinesis.Stream(
            scope=self,
            id="KinesisStreamTransaction",
            stream_name=self.one.config.kinesis_stream_transaction,
            shard_count=1,
            retention_period=cdk.Duration.days(7),
            stream_mode=kinesis.StreamMode.PROVISIONED,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        self.output_kinesis_stream_transaction_arn = cdk.CfnOutput(
            self,
            "KinesisStreamTransactionArn",
            value=self.kinesis_stream_transaction.stream_arn,
            export_name=f"{self.one.config.project_name_slug}-transaction-stream-arn",
        )
