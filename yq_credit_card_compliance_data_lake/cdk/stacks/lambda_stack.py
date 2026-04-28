# -*- coding: utf-8 -*-

"""
Lambda stack — frequently-deployed compute resources (functions, layers, event sources).

This stack is the counterpart to ``infra_stack.py`` (see its module docstring
for why they are separate).  It owns everything that changes on a typical
deploy: Lambda function code, layer versions, environment variables, and event
source mappings.

**Key design decisions:**

- **Source code from S3** — the function code is not bundled inline.  Instead,
  ``build_lambda_source`` (in ``one_04_devops.py``) uploads a zip to S3, and
  this stack reads the S3 URI from a local file
  (``path_enum.path_lambda_source_s3uri``).  This keeps the CDK template small
  and makes artifact versioning explicit.

- **IAM role imported, not created** — the role ARN is imported from the infra
  stack via ``Fn.import_value``, enforcing the separation described above.

- **Section numbering** (``s01_``, ``s02_02_``): execution order of construct
  creation is encoded in the method prefix so ``__init__`` reads top-down.
"""

import typing as T
import dataclasses
from functools import cached_property

from s3pathlib import S3Path

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3_notifications
from aws_cdk import aws_lambda as lambda_

from constructs import Construct

from ...constants import LIVE
from ...paths import PACKAGE_NAME, path_enum
from ...config.api import LbdFunc
from ...one.api import One

if T.TYPE_CHECKING:  # pragma: no cover
    from .lbd_stack_00_main import LambdaStack


@dataclasses.dataclass
class Lbd:
    """
    Dataclass to hold Lambda function and its alias.
    """
    func: lambda_.Function
    alias: lambda_.Alias


class LambdaStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        one: One,
        **kwargs,
    ) -> None:
        self.one = one

        super().__init__(
            scope=scope,
            id=f"{self.one.config.project_name_slug}-lbd",
            **kwargs,
        )

        # self.s01_create_lambda_functions()
        # self.s02_02_configure_s3_event_source()

    def get_lambda_layers_construct_for_function(
        self,
        lbd_func_config: LbdFunc,
    ) -> list[lambda_.LayerVersion]:
        """
        Create lambda layer declarations from config for a specific lambda function.
        """
        layers = list()
        for ith, layer_arn in enumerate(lbd_func_config.layers, start=1):
            # layer_arn can be either a full arn or a layer version id (1, 2, ...)
            if not layer_arn.startswith("arn:"):  # pragma: no cover
                final_layer_arn = (
                    f"arn:aws:lambda:{self.one.aws_region}:{self.one.aws_account_id}:layer"
                    f":{self.one.config.lambda_layer_name}:{layer_arn}"
                )
            else:  # pragma: no cover
                final_layer_arn = layer_arn

            layer = lambda_.LayerVersion.from_layer_version_arn(
                self,
                f"LambdaLayer{lbd_func_config.short_name_camel}{ith}",
                layer_version_arn=final_layer_arn,
            )
            layers.append(layer)

        return layers

    @cached_property
    def lambda_function_env_vars(self: "LambdaStack") -> dict[str, str]:
        env_vars = dict(self.one.config.lbd_func_env_vars)
        # AWS_ACCOUNT_ALIAS is baked in at CDK synthesis time (runs locally with full IAM
        # permissions) rather than being resolved at Lambda runtime. This avoids an
        # iam:ListAccountAliases API call inside the Lambda handler, which was observed to
        # hang for the full function timeout — likely due to cold-start connection overhead
        # to the IAM global endpoint. The alias is static per deployment, so computing it
        # once at synth time and passing it as an env var is both correct and efficient.
        # See one_02_boto_ses.py: aws_account_alias reads from this env var when present.
        #
        # Measured Lambda performance (128 MB, us-east-1, after this fix):
        #   cold start:  init = ~1.1s (module import), execution = ~1.8s (first run)
        #   warm start:  execution = ~0.15s
        env_vars["AWS_ACCOUNT_ALIAS"] = self.one.aws_account_alias
        return env_vars

    def get_iam_role_construct_for_function(
        self: "LambdaStack",
        lbd_func_config: LbdFunc,
    ) -> iam.IRole:
        if lbd_func_config.iam_role is None:
            return iam.Role.from_role_arn(
                self,
                id=f"ImportedLambdaRole{lbd_func_config.short_name_camel}",
                # match infra_stack.py
                role_arn=cdk.Fn.import_value(f"{self.one.config.project_name_slug}-lambda-role-arn"),
            )
        # use role managed by external projects
        else:  # pragma: no cover
            return iam.Role.from_role_arn(
                self,
                id=f"ImportedLambdaRole{lbd_func_config.short_name_camel}",
                role_arn=lbd_func_config.iam_role,
            )

    @cached_property
    def s3_bucket_artifacts(self: "LambdaStack") -> s3.IBucket:
        return s3.Bucket.from_bucket_name(
            self,
            id="ImportedArtifactsBucket",
            bucket_name=self.one.s3dir_artifacts.bucket,
        )

    def get_lambda_function_construct_for_function(
        self: "LambdaStack",
        lbd_func_config: LbdFunc,
    ) -> lambda_.Function:
        py_ver = f"PYTHON_{self.one.config.lbd_func_py_ver_major}_{self.one.config.lbd_func_py_ver_minor}"
        runtime = getattr(lambda_.Runtime, py_ver)
        s3uri = path_enum.path_lambda_source_s3uri.read_text(encoding="utf-8").strip()
        s3path = S3Path(s3uri)
        lbd_func = lambda_.Function(
            self,
            id=f"LambdaFunc{lbd_func_config.short_name_camel}",
            current_version_options=lambda_.VersionOptions(
                removal_policy=cdk.RemovalPolicy.RETAIN,
                retry_attempts=1,
            ),
            function_name=lbd_func_config.name,
            code=lambda_.Code.from_bucket(
                bucket=self.s3_bucket_artifacts,
                key=s3path.key,
            ),
            handler=f"{PACKAGE_NAME}.lambda_function.{lbd_func_config.handler}",
            runtime=runtime,
            memory_size=lbd_func_config.memory,
            timeout=cdk.Duration.seconds(lbd_func_config.timeout),
            layers=self.get_lambda_layers_construct_for_function(lbd_func_config),
            environment=self.lambda_function_env_vars,
            role=self.get_iam_role_construct_for_function(lbd_func_config),
            reserved_concurrent_executions=lbd_func_config.reserved_concurrency,
        )
        # Add custom tags to the Lambda function
        # cdk.Tags.of(lbd_func).add("your_key_here", "your_value_here")
        return lbd_func

    def s01_create_lambda_functions(self: "LambdaStack"):
        self.lambda_func_mappings: dict[str, lambda_.Function] = dict()
        for lbd_func_config in self.one.config.lbd_func_mappings.values():
            lbd_func = self.get_lambda_function_construct_for_function(lbd_func_config)
            self.lambda_func_mappings[lbd_func_config.short_name] = lbd_func

    def s02_02_configure_s3_event_source(self: "LambdaStack"):
        # ----------------------------------------------------------------------
        # Configure S3 Notification
        #
        # note:
        # based on this issue: https://github.com/aws/aws-cdk/issues/23940
        # it is impossible to use S3Bucket that is not defined in this stack
        # for ``aws_cdk.aws_lambda_event_sources.S3EventSource``
        # this is the only choice for now
        # ----------------------------------------------------------------------
        bucket = s3.Bucket.from_bucket_attributes(
            self,
            id="ImportedBucket",
            bucket_arn=f"arn:aws:s3:::{self.one.s3dir_source.bucket}",
        )

        # --- use latest version
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notifications.LambdaDestination(
                self.lambda_func_mappings[self.one.config.lbd_func_s3sync.short_name],
            ),
            s3.NotificationKeyFilter(
                prefix=f"{self.one.s3dir_source.key}",
            ),
        )
