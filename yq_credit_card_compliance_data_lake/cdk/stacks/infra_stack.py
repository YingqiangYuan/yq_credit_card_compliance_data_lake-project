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
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_sqs as sqs

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
        self.s02_create_kinesis_streams()
        self.s03_create_dynamodb_tables()
        self.s04_create_dlq_queues()

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

        # Kinesis read — scoped to the prod transaction stream so any future
        # Lambda subscribed to a different stream must be granted explicitly.
        # ``SubscribeToShard`` is required only for enhanced fan-out, but
        # adding it here costs nothing and keeps the policy aligned with
        # AWS's recommended consumer policy template.
        self.stat_kinesis_transaction_read = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kinesis:GetRecords",
                "kinesis:GetShardIterator",
                "kinesis:DescribeStream",
                "kinesis:DescribeStreamSummary",
                "kinesis:ListShards",
                "kinesis:SubscribeToShard",
            ],
            resources=[
                f"arn:aws:kinesis:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                f":stream/{self.one.config.kinesis_stream_transaction}",
            ],
        )

        # DynamoDB write — scoped to the pipeline-metadata table and *all*
        # of its indexes (the trailing ``/index/*`` covers the status-index
        # GSI added in s03 plus any future GSI additions without an IAM
        # change).
        self.stat_dynamodb_pipeline_metadata_write = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:Query",
                "dynamodb:UpdateItem",
                "dynamodb:BatchWriteItem",
                "dynamodb:DescribeTable",
            ],
            resources=[
                f"arn:aws:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                f":table/{self.one.config.dynamodb_table_pipeline_metadata}",
                f"arn:aws:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                f":table/{self.one.config.dynamodb_table_pipeline_metadata}/index/*",
            ],
        )

        # SQS DLQ send — needed by the Lambda's Event Source Mapping
        # ``on_failure`` destination (configured in lambda_stack).
        self.stat_sqs_transaction_dlq_send = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "sqs:SendMessage",
                "sqs:GetQueueAttributes",
                "sqs:GetQueueUrl",
            ],
            resources=[
                f"arn:aws:sqs:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                f":{self.one.config.project_name_slug}-transaction-ingestion-dlq",
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
                        self.stat_kinesis_transaction_read,
                        self.stat_dynamodb_pipeline_metadata_write,
                        self.stat_sqs_transaction_dlq_send,
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

    def s03_create_dynamodb_tables(self):
        """Pipeline-metadata table — see doc1 §6 for schema rationale and
        ``data_ingestion.dynamodb_table.PipelineMetadata`` for attribute
        layout.

        Billing is ``PAY_PER_REQUEST``: demo traffic produces at most a few
        thousand writes/day, well under the on-demand free tier; provisioned
        throughput would burn idle cost for nothing.

        ``RemovalPolicy.DESTROY`` reflects that this table holds audit data,
        not source-of-truth state — losing it on stack tear-down is
        acceptable, and avoiding a tombstoned ``RETAIN`` table simplifies
        ``cdk destroy`` during demo iteration.
        """
        self.dynamodb_pipeline_metadata = dynamodb.Table(
            scope=self,
            id="DynamoDbTablePipelineMetadata",
            table_name=self.one.config.dynamodb_table_pipeline_metadata,
            partition_key=dynamodb.Attribute(
                name="pipeline_name",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="run_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # GSI ``status-index``: answers "all FAILED runs in the past 24 h"
        # without a full scan.  Mirrors the GSI declared on the pynamodb
        # model in ``data_ingestion/dynamodb_table.py``.
        self.dynamodb_pipeline_metadata.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(
                name="run_status",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="start_ts",
                type=dynamodb.AttributeType.STRING,
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        self.output_dynamodb_pipeline_metadata_arn = cdk.CfnOutput(
            self,
            "DynamoDbPipelineMetadataArn",
            value=self.dynamodb_pipeline_metadata.table_arn,
            export_name=f"{self.one.config.project_name_slug}-pipeline-metadata-table-arn",
        )

    def s04_create_dlq_queues(self):
        """SQS DLQ for the transaction-ingestion Lambda.

        Sized per doc1 §3 (Dead Letter Queue Design): records that fail
        Lambda processing 3 times after batch bisection land here.
        ``retention_period=14 days`` matches the doc; ``visibility_timeout
        =5 min`` matches the Lambda's own max execution time so a redrive
        consumer can finish its work without the message reappearing.
        """
        self.sqs_dlq_transaction_ingestion = sqs.Queue(
            scope=self,
            id="SqsDlqTransactionIngestion",
            queue_name=f"{self.one.config.project_name_slug}-transaction-ingestion-dlq",
            retention_period=cdk.Duration.days(14),
            visibility_timeout=cdk.Duration.minutes(5),
        )

        self.output_sqs_dlq_transaction_ingestion_arn = cdk.CfnOutput(
            self,
            "SqsDlqTransactionIngestionArn",
            value=self.sqs_dlq_transaction_ingestion.queue_arn,
            export_name=f"{self.one.config.project_name_slug}-transaction-ingestion-dlq-arn",
        )
