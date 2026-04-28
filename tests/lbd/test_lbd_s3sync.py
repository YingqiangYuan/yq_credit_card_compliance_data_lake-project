# -*- coding: utf-8 -*-

"""
Unit test for the ``s3sync`` Lambda function using mocked AWS (moto).

Demonstrates the ``BaseMockAwsTest`` pattern for tests that need AWS services:

1. Set ``use_mock = True`` to use moto (set ``False`` for integration testing).
2. Override ``setup_class_post_hook`` to create fixtures (S3 buckets, seed data).
3. Test the business logic by calling the handler's ``sync()`` method directly,
   passing the mocked ``s3_client`` so it hits moto instead of real AWS.

This test verifies that a file written to the source prefix is correctly copied
to the target prefix.
"""

from yq_credit_card_compliance_data_lake.lbd.s3sync import Input

from yq_credit_card_compliance_data_lake.one.api import one
from yq_credit_card_compliance_data_lake.tests.mock_aws import BaseMockAwsTest


class Test(BaseMockAwsTest):
    use_mock = True

    s3path_source = None
    s3path_target = None

    @classmethod
    def setup_class_post_hook(cls):
        cls.create_s3_bucket(bucket_name=one.s3dir_data.bucket)
        cls.s3path_source = one.s3dir_source.joinpath("file.txt")
        cls.s3path_target = one.s3dir_target.joinpath("file.txt")
        cls.s3path_source.write_text("hello", bsm=cls.s3_client)

    def test_sync(
        self,
        disable_logger,
    ):
        assert self.s3path_source.exists(bsm=self.s3_client) is True
        assert self.s3path_target.exists(bsm=self.s3_client) is False

        output = Input(s3uri_source=self.s3path_source.uri).sync(s3_client=self.s3_client)
        assert output.s3path_target.exists(bsm=self.s3_client) is True
        assert output.s3path_target.read_text(bsm=self.s3_client) == "hello"


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.lbd.s3sync",
        preview=False,
    )
