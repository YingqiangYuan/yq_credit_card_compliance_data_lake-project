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

    # Kinesis stream names — Phase 2
    assert config.kinesis_stream_transaction == f"{config.project_name_slug}-transaction-stream"
    assert config.kinesis_stream_transaction_test == f"{config.kinesis_stream_transaction}-test"

    # DynamoDB tables — Phase 4.  This Config property is the source of
    # truth; ``data_ingestion.dynamodb_table.PipelineMetadata.Meta.table_name``
    # hardcodes the same string, and the assertion below guards against the
    # two drifting apart (see dynamodb_table.py module docstring for why
    # both exist).
    from yq_credit_card_compliance_data_lake.data_ingestion.dynamodb_table import (
        PipelineMetadata,
    )
    assert (
        config.dynamodb_table_pipeline_metadata
        == f"{config.project_name_slug}-pipeline-metadata"
    )
    assert (
        config.dynamodb_table_pipeline_metadata
        == PipelineMetadata.Meta.table_name
    )

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
