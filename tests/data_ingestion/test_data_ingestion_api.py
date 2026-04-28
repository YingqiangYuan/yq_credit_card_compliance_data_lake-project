# -*- coding: utf-8 -*-

"""
Smoke test for ``data_ingestion/api.py`` — verifies the public re-exports
import without errors.
"""

from yq_credit_card_compliance_data_lake.data_ingestion import api


def test():
    _ = api.Transaction
    _ = api.TransactionFaker
    _ = api.send_records
    _ = api.SendResult
    _ = api.Consumer
    _ = api.drain_shard
    _ = api.iter_shard_ids
    # Phase 4 additions
    _ = api.decode_kinesis_records
    _ = api.ValidationResult
    _ = api.validate_transaction
    _ = api.build_partition_path
    _ = api.write_ndjson_to_s3
    _ = api.PipelineMetadata


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.data_ingestion.api",
        preview=False,
    )
