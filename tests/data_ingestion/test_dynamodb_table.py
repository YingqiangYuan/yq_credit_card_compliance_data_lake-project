# -*- coding: utf-8 -*-

"""
Unit tests for ``data_ingestion/dynamodb_table.py``.

Exercises ``PipelineMetadata`` against a moto-mocked DynamoDB.  PynamoDB
requests are routed through ``BotoSesManager`` via
``pynamodb_session_manager.use_boto_session`` so moto's boto3 patching
intercepts them — no real AWS calls.
"""

import moto
import pytest
from boto_session_manager import BotoSesManager
from pynamodb_session_manager.api import use_boto_session

from yq_credit_card_compliance_data_lake.constants import (
    PipelineName,
    PipelineStatus,
)
from yq_credit_card_compliance_data_lake.data_ingestion.dynamodb_table import (
    PipelineMetadata,
)


_REGION = "us-east-1"


def _bsm() -> BotoSesManager:
    return BotoSesManager(region_name=_REGION)


# ------------------------------------------------------------------------------
# Plain-instantiation tests — no AWS needed
# ------------------------------------------------------------------------------
def test_required_attributes_round_trip_in_memory():
    rec = PipelineMetadata(
        pipeline_name=PipelineName.TRANSACTION_INGESTION.value,
        run_id="2026-04-28T14:00:00Z___abc123",
        run_status=PipelineStatus.SUCCESS.value,
        start_ts="2026-04-28T14:00:00Z",
        total_records=100,
        valid_records=95,
        quarantine_records=5,
    )
    assert rec.pipeline_name == "txn-realtime-ingestion"
    assert rec.run_id == "2026-04-28T14:00:00Z___abc123"
    assert rec.run_status == "SUCCESS"
    assert rec.total_records == 100
    assert rec.valid_records == 95
    assert rec.quarantine_records == 5


def test_nullable_attributes_default_to_none():
    rec = PipelineMetadata(
        pipeline_name=PipelineName.TRANSACTION_INGESTION.value,
        run_id="2026-04-28T14:00:00Z___abc123",
        run_status=PipelineStatus.RUNNING.value,
        start_ts="2026-04-28T14:00:00Z",
        total_records=0,
        valid_records=0,
        quarantine_records=0,
    )
    assert rec.end_ts is None
    assert rec.s3_output_path is None
    assert rec.s3_quarantine_path is None
    assert rec.error_message is None
    assert rec.lambda_request_id is None


def test_status_index_is_registered():
    """Subtle: pynamodb GSIs must be assigned as class attributes for the
    DescribeTable schema generation to include them.  This guard fails fast
    if a future refactor accidentally drops the ``status_index`` attribute.
    """
    assert hasattr(PipelineMetadata, "status_index")
    meta = PipelineMetadata.status_index.Meta
    assert meta.index_name == "status-index"


# ------------------------------------------------------------------------------
# Moto round-trip — save / get / query / GSI
# ------------------------------------------------------------------------------
@moto.mock_aws
def test_save_and_get_round_trip():
    bsm = _bsm()
    with use_boto_session(PipelineMetadata, bsm):
        PipelineMetadata.create_table(
            wait=True, read_capacity_units=1, write_capacity_units=1
        )

        rec = PipelineMetadata(
            pipeline_name=PipelineName.TRANSACTION_INGESTION.value,
            run_id="2026-04-28T14:00:00Z___abc123",
            run_status=PipelineStatus.SUCCESS.value,
            start_ts="2026-04-28T14:00:00Z",
            end_ts="2026-04-28T14:00:05Z",
            total_records=100,
            valid_records=95,
            quarantine_records=5,
            s3_output_path="s3://bucket/bronze/...ndjson",
            lambda_request_id="abc123",
        )
        rec.save()

        got = PipelineMetadata.get(
            hash_key=PipelineName.TRANSACTION_INGESTION.value,
            range_key="2026-04-28T14:00:00Z___abc123",
        )
        assert got.total_records == 100
        assert got.valid_records == 95
        assert got.quarantine_records == 5
        assert got.s3_output_path == "s3://bucket/bronze/...ndjson"
        assert got.lambda_request_id == "abc123"


@moto.mock_aws
def test_query_main_key_chronologically():
    """``run_id`` is built so lexical sort = chronological sort, which lets
    the main key answer "last N runs" without a GSI.  This test asserts the
    sort property still holds when rows are written out-of-order.
    """
    bsm = _bsm()
    with use_boto_session(PipelineMetadata, bsm):
        PipelineMetadata.create_table(
            wait=True, read_capacity_units=1, write_capacity_units=1
        )

        # Insert three runs out of chronological order.
        for ts, req_id in [
            ("2026-04-28T14:02:00Z", "third"),
            ("2026-04-28T14:00:00Z", "first"),
            ("2026-04-28T14:01:00Z", "second"),
        ]:
            PipelineMetadata(
                pipeline_name=PipelineName.TRANSACTION_INGESTION.value,
                run_id=f"{ts}___{req_id}",
                run_status=PipelineStatus.SUCCESS.value,
                start_ts=ts,
                total_records=1,
                valid_records=1,
                quarantine_records=0,
            ).save()

        results = list(
            PipelineMetadata.query(
                hash_key=PipelineName.TRANSACTION_INGESTION.value,
                scan_index_forward=False,  # newest first
                limit=2,
            )
        )
        assert [r.run_id.split("___")[-1] for r in results] == ["third", "second"]


@moto.mock_aws
def test_status_index_query_finds_failed_runs():
    bsm = _bsm()
    with use_boto_session(PipelineMetadata, bsm):
        PipelineMetadata.create_table(
            wait=True, read_capacity_units=1, write_capacity_units=1
        )

        for run_status, run_id in [
            (PipelineStatus.SUCCESS, "ok-1"),
            (PipelineStatus.FAILED, "bad-1"),
            (PipelineStatus.SUCCESS, "ok-2"),
            (PipelineStatus.FAILED, "bad-2"),
        ]:
            PipelineMetadata(
                pipeline_name=PipelineName.TRANSACTION_INGESTION.value,
                run_id=f"2026-04-28T14:00:00Z___{run_id}",
                run_status=run_status.value,
                start_ts="2026-04-28T14:00:00Z",
                total_records=1,
                valid_records=1 if run_status == PipelineStatus.SUCCESS else 0,
                quarantine_records=0,
            ).save()

        failed = list(
            PipelineMetadata.status_index.query(
                hash_key=PipelineStatus.FAILED.value,
            )
        )
        run_ids = sorted(r.run_id for r in failed)
        assert run_ids == [
            "2026-04-28T14:00:00Z___bad-1",
            "2026-04-28T14:00:00Z___bad-2",
        ]


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.data_ingestion.dynamodb_table",
        preview=False,
    )
