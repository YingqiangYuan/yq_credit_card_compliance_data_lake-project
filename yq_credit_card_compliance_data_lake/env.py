# -*- coding: utf-8 -*-

"""
Multi-environment management with automatic environment detection.

This module provides comprehensive multi-environment support for cloud-native applications,
enabling seamless deployment and operation across development, testing, and production
environments with intelligent runtime-based environment detection and flexible AWS account mapping.

.. seealso::

    :ref:`Understand-Multi-Environment`
"""

import which_env.api as which_env

from .runtime import runtime


class EnvNameEnum(which_env.BaseEnvNameEnum):
    """
    Environment enumeration defining supported deployment environments.
    
    Extends the base enumeration to define project-specific environments including DevOps,
    development, testing, and production, providing a foundation for multi-environment
    configuration management and deployment orchestration across AWS accounts.
    """

    devops = which_env.CommonEnvNameEnum.devops.value
    dev = which_env.CommonEnvNameEnum.dev.value
    tst = which_env.CommonEnvNameEnum.tst.value
    prd = which_env.CommonEnvNameEnum.prd.value


def detect_current_env() -> str:
    """
    Detect the current runtime environment.
    """
    # ----------------------------------------------------------------------
    # you can uncomment this line to force to use certain env
    # from your local laptop to run application code, tests, ...
    # ----------------------------------------------------------------------
    # return EnvNameEnum.prd.value

    return which_env.detect_current_env(
        env_name_enum_class=EnvNameEnum,
        runtime=runtime,
    )
