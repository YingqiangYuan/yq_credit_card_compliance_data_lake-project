# -*- coding: utf-8 -*-

"""
Lambda function deployment related configurations.
"""

import typing as T


if T.TYPE_CHECKING:  # pragma: no cover
    from .config_00_main import Config


class LbdFuncDeployMixin:
    """
    Lambda function deployment related configurations.
    """

    @property
    def lambda_layer_name(self: "Config") -> str:
        """
        Lambda function layer name.

        Because the Lambda layer is an immutable artifact, we only need one
        lambda layer across all envs, so we don't need to include env name in the
        layer name.
        """

        return self.project_name_snake
