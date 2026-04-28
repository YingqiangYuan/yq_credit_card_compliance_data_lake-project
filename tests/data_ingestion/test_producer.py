# -*- coding: utf-8 -*-

"""
Unit tests for ``data_ingestion/producer/`` using moto-mocked Kinesis.

Covers:

- ``to_kinesis_record`` serialisation (JSON bytes + partition key)
- ``send_records`` happy path (single batch, multi-batch via ``itertools.batched``)
- ``send_records`` empty input short-circuit
- ``send_records`` partial-failure collection (simulated by patching the
  ``put_records`` response — moto itself does not produce per-record failures)
"""

import json
from datetime import datetime, UTC
from unittest.mock import MagicMock
from uuid import uuid4

import boto3
import moto

from yq_credit_card_compliance_data_lake.constants import (
    AuthStatus,
    Channel,
    Currency,
)
from yq_credit_card_compliance_data_lake.data_ingestion.faker import TransactionFaker
from yq_credit_card_compliance_data_lake.data_ingestion.models import Transaction
from yq_credit_card_compliance_data_lake.data_ingestion.producer.api import (
    SendResult,
    send_records,
    to_kinesis_record,
)


_STREAM = "test-axiomcard-transactions"
_REGION = "us-east-1"


def _build_txn() -> Transaction:
    return Transaction(
        transaction_id=uuid4(),
        card_id="4111111111111111",
        merchant_id="MERCH-ABCDEF12",
        amount=42.0,
        currency=Currency.USD,
        transaction_ts=datetime.now(UTC),
        mcc_code="5411",
        auth_status=AuthStatus.APPROVED,
        channel=Channel.POS,
    )


# ------------------------------------------------------------------------------
# to_kinesis_record
# ------------------------------------------------------------------------------
def test_to_kinesis_record_shape():
    txn = _build_txn()
    entry = to_kinesis_record(txn)
    assert set(entry.keys()) == {"Data", "PartitionKey"}
    assert isinstance(entry["Data"], bytes)
    assert entry["PartitionKey"] == txn.card_id


def test_to_kinesis_record_data_round_trips():
    txn = _build_txn()
    entry = to_kinesis_record(txn)
    decoded = json.loads(entry["Data"].decode("utf-8"))
    assert decoded["amount"] == 42.0
    assert decoded["card_id"] == txn.card_id


# ------------------------------------------------------------------------------
# send_records — happy paths against moto Kinesis
# ------------------------------------------------------------------------------
def test_send_records_empty_short_circuits():
    # No client call should happen — pass a MagicMock and assert it's never used
    client = MagicMock()
    result = send_records(client, _STREAM, [])
    assert isinstance(result, SendResult)
    assert result.total == 0
    assert result.success_count == 0
    assert result.failed_count == 0
    client.put_records.assert_not_called()


@moto.mock_aws
def test_send_records_single_batch():
    client = boto3.client("kinesis", region_name=_REGION)
    client.create_stream(StreamName=_STREAM, ShardCount=1)
    client.get_waiter("stream_exists").wait(StreamName=_STREAM)

    txns = TransactionFaker(seed=0).make_many(50)
    result = send_records(client, _STREAM, txns)

    assert result.total == 50
    assert result.success_count == 50
    assert result.failed_count == 0
    assert result.failed_entries == []


@moto.mock_aws
def test_send_records_multi_batch_split_at_500():
    client = boto3.client("kinesis", region_name=_REGION)
    client.create_stream(StreamName=_STREAM, ShardCount=1)
    client.get_waiter("stream_exists").wait(StreamName=_STREAM)

    txns = TransactionFaker(seed=0).make_many(1200)
    result = send_records(client, _STREAM, txns)

    assert result.total == 1200
    assert result.success_count == 1200
    assert result.failed_count == 0


@moto.mock_aws
def test_send_records_calls_put_records_correct_number_of_times(monkeypatch):
    client = boto3.client("kinesis", region_name=_REGION)
    client.create_stream(StreamName=_STREAM, ShardCount=1)
    client.get_waiter("stream_exists").wait(StreamName=_STREAM)

    real_put = client.put_records
    call_sizes: list[int] = []

    def spy(**kwargs):
        call_sizes.append(len(kwargs["Records"]))
        return real_put(**kwargs)

    monkeypatch.setattr(client, "put_records", spy)

    txns = TransactionFaker(seed=0).make_many(1234)
    send_records(client, _STREAM, txns)

    assert call_sizes == [500, 500, 234]


# ------------------------------------------------------------------------------
# send_records — partial failure path (simulated client)
# ------------------------------------------------------------------------------
def test_send_records_collects_partial_failures():
    """When Kinesis reports per-record failures, they surface in failed_entries."""
    client = MagicMock()
    client.put_records.return_value = {
        "FailedRecordCount": 1,
        "Records": [
            {"SequenceNumber": "1", "ShardId": "shardId-000000000000"},
            {
                "ErrorCode": "ProvisionedThroughputExceededException",
                "ErrorMessage": "Rate exceeded",
            },
            {"SequenceNumber": "3", "ShardId": "shardId-000000000000"},
        ],
    }

    txns = TransactionFaker(seed=0).make_many(3)
    result = send_records(client, _STREAM, txns)

    assert result.total == 3
    assert result.success_count == 2
    assert result.failed_count == 1
    assert len(result.failed_entries) == 1
    entry = result.failed_entries[0]
    assert entry["ErrorCode"] == "ProvisionedThroughputExceededException"
    assert entry["ErrorMessage"] == "Rate exceeded"
    assert entry["record"]["card_id"] == txns[1].card_id


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.data_ingestion.producer",
        is_folder=True,
        preview=False,
    )
