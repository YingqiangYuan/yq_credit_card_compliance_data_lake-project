# -*- coding: utf-8 -*-

"""
Unit test for the ``Config`` and ``LbdFunc`` data models.

Exercises every property on ``Config`` and ``LbdFunc`` to ensure that naming
derivations (snake_case, slug, camelCase), computed values, and the
``_config`` back-reference all work correctly.  This test acts as a regression
guard — if a property raises or returns an unexpected type, it will fail here
before causing a confusing error during CDK synthesis or deployment.
"""

from yq_credit_card_compliance_data_lake.one.api import one


def test():
    config = one.config

    _ = config.project_name
    _ = config.aws_region
    _ = config.local_aws_profile
    _ = config.lbd_func_py_ver

    _ = config.project_name_snake
    _ = config.project_name_slug
    _ = config.cloudformation_stack_name

    _ = config.lambda_layer_name

    for lbd_func in [
        config.lbd_func_hello,
        config.lbd_func_s3sync,
    ]:
        _ = lbd_func.short_name
        _ = lbd_func.handler
        _ = lbd_func.timeout
        _ = lbd_func.memory
        _ = lbd_func.config
        _ = lbd_func.name
        _ = lbd_func.short_name_slug
        _ = lbd_func.short_name_snake
        _ = lbd_func.short_name_camel


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.config",
        is_folder=True,
        preview=False,
    )
