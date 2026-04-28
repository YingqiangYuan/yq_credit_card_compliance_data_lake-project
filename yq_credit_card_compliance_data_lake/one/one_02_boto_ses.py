# -*- coding: utf-8 -*-

"""
Boto session management mixin for AWS service access and credential handling.
"""

import os
import typing as T
from functools import cached_property

import boto3

from ..runtime import runtime

if T.TYPE_CHECKING:  # pragma: no cover
    from .one_00_main import One


class OneBotoSesMixin:  # pragma: no cover
    """
    Mixin providing lazy-loaded boto session management and AWS console access.
    """

    @cached_property
    def boto_ses(self: "One") -> boto3.Session:
        if runtime.is_aws_lambda:
            return boto3.Session(region_name=self.config.aws_region)
        else:
            return boto3.Session(
                profile_name=self.config.local_aws_profile,
                region_name=self.config.aws_region,
            )

    @cached_property
    def aws_region(self: "One") -> str:
        return self.config.aws_region

    @cached_property
    def aws_account_id(self: "One") -> str:
        return self.boto_ses.client("sts").get_caller_identity()["Account"]

    @cached_property
    def aws_account_alias(self: "One") -> str:
        if "AWS_ACCOUNT_ALIAS" in os.environ:
            return os.environ["AWS_ACCOUNT_ALIAS"]
        try:
            res = self.boto_ses.client("iam").list_account_aliases()
            return res["AccountAliases"][0]
        except IndexError:
            return "dummy-us-east-1-data"

    @cached_property
    def s3_client(self: "One"):
        return self.boto_ses.client("s3")

    @cached_property
    def lambda_client(self: "One"):
        return self.boto_ses.client("lambda")

    @cached_property
    def cloudformation_client(self: "One"):
        return self.boto_ses.client("cloudformation")

    @cached_property
    def kinesis_client(self: "One"):
        return self.boto_ses.client("kinesis")

    @cached_property
    def polars_storage_options(self: "One") -> dict:
        creds = self.boto_ses.get_credentials().get_frozen_credentials()
        storage_options = {
            "AWS_REGION": self.aws_region,
            "AWS_ACCESS_KEY_ID": creds.access_key,
            "AWS_SECRET_ACCESS_KEY": creds.secret_key,
            "AWS_SESSION_TOKEN": creds.token or "",
            "AWS_S3_ALLOW_UNSAFE_RENAME": "true",  # skip DynamoDB lock
        }
        return storage_options
