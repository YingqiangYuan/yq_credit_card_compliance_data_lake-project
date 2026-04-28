# -*- coding: utf-8 -*-

"""
Configuration management mixin with runtime-aware loading and deployment operations.

This module provides comprehensive configuration management with adaptive loading strategies
based on runtime context, supporting local JSON files for development, SSM Parameter Store
for CI/CD and production, with automated secret management and multi-environment deployment.
"""

import typing as T
import os
from functools import cached_property

from ..runtime import runtime
from ..config.api import Config
from ..config.api import LbdFunc

if T.TYPE_CHECKING:  # pragma: no cover
    from .one_00_main import One


class OneConfigMixin:
    """
    Mixin providing runtime-aware configuration loading and management operations.
    """

    @cached_property
    def config(self: "One") -> Config:
        if runtime.is_aws_lambda:
            lbd_func_hello = None
            lbd_func_s3sync = None
            lbd_func_transaction_ingestion = None
        else:
            from dotenv import load_dotenv

            load_dotenv()
            load_dotenv(".env.shared")

            lbd_func_hello = LbdFunc(
                short_name=os.environ["LBD_FUNC_HELLO_SHORT_NAME"],
                handler=os.environ["LBD_FUNC_HELLO_HANDLER"],
                timeout=int(os.environ["LBD_FUNC_HELLO_TIMEOUT"]),
                memory=int(os.environ["LBD_FUNC_HELLO_MEMORY"]),
                layers=[
                    os.environ["LBD_FUNC_LAYER_VERSION"],
                ],
            )
            lbd_func_s3sync = LbdFunc(
                short_name=os.environ["LBD_FUNC_S3_SYNC_SHORT_NAME"],
                handler=os.environ["LBD_FUNC_S3_SYNC_HANDLER"],
                timeout=int(os.environ["LBD_FUNC_S3_SYNC_TIMEOUT"]),
                memory=int(os.environ["LBD_FUNC_S3_SYNC_MEMORY"]),
                layers=[
                    os.environ["LBD_FUNC_LAYER_VERSION"],
                ],
            )
            lbd_func_transaction_ingestion = LbdFunc(
                short_name=os.environ["LBD_FUNC_TRANSACTION_INGESTION_SHORT_NAME"],
                handler=os.environ["LBD_FUNC_TRANSACTION_INGESTION_HANDLER"],
                timeout=int(os.environ["LBD_FUNC_TRANSACTION_INGESTION_TIMEOUT"]),
                memory=int(os.environ["LBD_FUNC_TRANSACTION_INGESTION_MEMORY"]),
                layers=[
                    os.environ["LBD_FUNC_LAYER_VERSION"],
                ],
            )

        config = Config(
            project_name=os.environ["PROJECT_NAME"],
            aws_region=os.environ["AWS_REGION"],
            local_aws_profile=os.environ.get("LOCAL_AWS_PROFILE"),
            lbd_func_py_ver=os.environ.get("LBD_FUNC_PY_VER"),
            lbd_func_hello=lbd_func_hello,
            lbd_func_s3sync=lbd_func_s3sync,
            lbd_func_transaction_ingestion=lbd_func_transaction_ingestion,
        )

        if runtime.is_aws_lambda is False:
            config.lbd_func_hello._config = config
            config.lbd_func_s3sync._config = config
            config.lbd_func_transaction_ingestion._config = config

        return config
