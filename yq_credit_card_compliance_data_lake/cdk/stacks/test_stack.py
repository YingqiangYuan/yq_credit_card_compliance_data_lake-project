# -*- coding: utf-8 -*-

"""
Test stack — auxiliary resources used by Phase 3 e2e smoke scripts.

**This is NOT a separate test environment.**  The project has a single AWS
environment; this stack only collects extra resources that exist *alongside*
the production stack and are intended for hands-on developer testing — for
example, a small Kinesis stream that ``tests_e2e/`` scripts can produce to and
consume from without polluting the real ingestion firehose.

**Lifecycle: deploy on demand, destroy when idle.**  Resources here have a
non-trivial idle cost (Kinesis bills per shard-hour even when idle), so the
intended workflow is::

    cdk deploy yq-credit-card-compliance-data-lake-test    # before testing
    # ... run scripts in tests_e2e/ ...
    cdk destroy yq-credit-card-compliance-data-lake-test   # after

Keeping these resources in their own stack makes that lifecycle a single
``cdk`` command without touching IAM or Lambda.

**What goes here:**  any resource that is *only* used during local/manual
testing — Kinesis test streams, scratch DynamoDB tables, dev-only S3 prefixes.
Shared production resources stay in :class:`InfraStack`; Lambda code stays in
:class:`LambdaStack`.

**Section numbering convention** (``s01_``, ``s02_``, …) matches the rest of
the CDK package.
"""

import aws_cdk as cdk
from aws_cdk import aws_kinesis as kinesis

from constructs import Construct

from ...one.api import One


class TestStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        one: One,
        **kwargs,
    ) -> None:
        self.one = one

        super().__init__(
            scope=scope,
            id=f"{self.one.config.project_name_slug}-test",
            **kwargs,
        )

        self.s01_create_kinesis_streams()

    def s01_create_kinesis_streams(self):
        """Auxiliary Kinesis stream for e2e smoke tests.

        1 shard (~ $11/mo idle) — sized for hand-driven traffic, not the
        production firehose. Retention dropped to 24 hours since these tests
        are run-and-forget; nobody needs to replay yesterday's smoke data.

        ``removal_policy=DESTROY`` lets ``cdk destroy`` actually delete the
        stream — opposite of the production stream which we never want to lose
        accidentally.
        """
        self.kinesis_stream_transaction_test = kinesis.Stream(
            scope=self,
            id="KinesisStreamTransactionTest",
            stream_name=self.one.config.kinesis_stream_transaction_test,
            retention_period=cdk.Duration.hours(24),
            stream_mode=kinesis.StreamMode.ON_DEMAND,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        self.output_kinesis_stream_transaction_test_arn = cdk.CfnOutput(
            self,
            "KinesisStreamTransactionTestArn",
            value=self.kinesis_stream_transaction_test.stream_arn,
            export_name=f"{self.one.config.project_name_slug}-transaction-stream-test-arn",
        )
