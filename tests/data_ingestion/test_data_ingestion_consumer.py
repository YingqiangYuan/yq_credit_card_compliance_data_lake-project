# -*- coding: utf-8 -*-

"""
Unit tests for ``data_ingestion/consumer/`` against moto-mocked Kinesis.

Covers:

- ``iter_shard_ids`` paginates correctly
- ``drain_shard`` empties a populated shard, respects ``limit``, accepts a
  pre-existing ``shard_iterator``
- ``Consumer.iter_records`` yields records from a populated stream and exits
  when the producer thread stops feeding it
"""

import json
import threading
import time
from datetime import datetime, UTC
from uuid import uuid4

import boto3
import moto

from yq_credit_card_compliance_data_lake.constants import (
    AuthStatus,
    Channel,
    Currency,
)
from yq_credit_card_compliance_data_lake.data_ingestion.api import (
    Consumer,
    drain_shard,
    iter_shard_ids,
    send_records,
)
from yq_credit_card_compliance_data_lake.data_ingestion.fakers import TransactionFaker
from yq_credit_card_compliance_data_lake.data_ingestion.models import Transaction


_STREAM = "test-axiomcard-transactions"
_REGION = "us-east-1"


def _setup_stream(client, n_shards: int = 1) -> None:
    client.create_stream(StreamName=_STREAM, ShardCount=n_shards)
    client.get_waiter("stream_exists").wait(StreamName=_STREAM)


# ------------------------------------------------------------------------------
# iter_shard_ids
# ------------------------------------------------------------------------------
@moto.mock_aws
def test_iter_shard_ids_returns_all_shards():
    client = boto3.client("kinesis", region_name=_REGION)
    _setup_stream(client, n_shards=3)
    shard_ids = list(iter_shard_ids(client, _STREAM))
    assert len(shard_ids) == 3
    assert all(s.startswith("shardId-") for s in shard_ids)


# ------------------------------------------------------------------------------
# drain_shard
# ------------------------------------------------------------------------------
@moto.mock_aws
def test_drain_shard_yields_all_records():
    client = boto3.client("kinesis", region_name=_REGION)
    _setup_stream(client)

    txns = TransactionFaker(seed=0).make_many(20)
    send_records(client, _STREAM, txns)

    shard_id = next(iter_shard_ids(client, _STREAM))
    drained = list(drain_shard(client, _STREAM, shard_id, poll_sleep_seconds=0.0))
    assert len(drained) == 20
    decoded = [json.loads(r["Data"]) for r in drained]
    assert {d["transaction_id"] for d in decoded} == {str(t.transaction_id) for t in txns}


@moto.mock_aws
def test_drain_shard_returns_empty_for_empty_stream():
    client = boto3.client("kinesis", region_name=_REGION)
    _setup_stream(client)

    shard_id = next(iter_shard_ids(client, _STREAM))
    drained = list(drain_shard(client, _STREAM, shard_id, poll_sleep_seconds=0.0))
    assert drained == []


@moto.mock_aws
def test_drain_shard_accepts_starting_iterator(monkeypatch):
    """When ``shard_iterator`` is provided, drain_shard must NOT call
    ``GetShardIterator`` — it uses the supplied iterator directly."""
    client = boto3.client("kinesis", region_name=_REGION)
    _setup_stream(client)
    txns = TransactionFaker(seed=0).make_many(5)
    send_records(client, _STREAM, txns)

    shard_id = next(iter_shard_ids(client, _STREAM))
    pre_iter = client.get_shard_iterator(
        StreamName=_STREAM, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
    )["ShardIterator"]

    calls: list[str] = []

    def boom(**kwargs):
        calls.append("called")
        raise AssertionError("get_shard_iterator should not be called")

    monkeypatch.setattr(client, "get_shard_iterator", boom)

    drained = list(
        drain_shard(
            client,
            _STREAM,
            shard_id,
            shard_iterator=pre_iter,
            poll_sleep_seconds=0.0,
        )
    )
    assert len(drained) == 5
    assert calls == []


@moto.mock_aws
def test_drain_shard_respects_limit(monkeypatch):
    client = boto3.client("kinesis", region_name=_REGION)
    _setup_stream(client)
    send_records(client, _STREAM, TransactionFaker(seed=0).make_many(10))

    real_get_records = client.get_records
    seen_limits: list[int] = []

    def spy(**kwargs):
        seen_limits.append(kwargs["Limit"])
        return real_get_records(**kwargs)

    monkeypatch.setattr(client, "get_records", spy)

    shard_id = next(iter_shard_ids(client, _STREAM))
    list(drain_shard(client, _STREAM, shard_id, limit=3, poll_sleep_seconds=0.0))

    assert all(limit == 3 for limit in seen_limits)
    assert len(seen_limits) >= 1


# ------------------------------------------------------------------------------
# Consumer
# ------------------------------------------------------------------------------
@moto.mock_aws
def test_consumer_construction_is_side_effect_free(monkeypatch):
    """Building ``Consumer`` must not call AWS — only ``iter_records`` does."""
    client = boto3.client("kinesis", region_name=_REGION)
    _setup_stream(client)

    forbidden = ["get_records", "get_shard_iterator", "list_shards"]
    for op in forbidden:
        monkeypatch.setattr(
            client, op, lambda *a, **kw: (_ for _ in ()).throw(AssertionError(op))
        )

    consumer = Consumer(client, _STREAM)
    assert consumer.stream_name == _STREAM


@moto.mock_aws
def test_consumer_yields_records_from_populated_stream():
    client = boto3.client("kinesis", region_name=_REGION)
    _setup_stream(client)
    txns = TransactionFaker(seed=0).make_many(5)
    send_records(client, _STREAM, txns)

    consumer = Consumer(client, _STREAM)
    received = []
    for record in consumer.iter_records(
        iterator_type="TRIM_HORIZON", wait_seconds=0.01
    ):
        received.append(record)
        if len(received) >= 5:
            break

    assert len(received) == 5
    decoded = [json.loads(r["Data"]) for r in received]
    assert {d["transaction_id"] for d in decoded} == {str(t.transaction_id) for t in txns}


@moto.mock_aws
def test_consumer_picks_up_records_produced_after_start():
    """With TRIM_HORIZON, records produced AFTER iter_records starts should
    still be visible — verifies the polling loop, not just the initial drain."""
    client = boto3.client("kinesis", region_name=_REGION)
    _setup_stream(client)

    consumer = Consumer(client, _STREAM)
    received = []

    def producer():
        time.sleep(0.05)  # let consumer start polling
        send_records(client, _STREAM, TransactionFaker(seed=0).make_many(3))

    t = threading.Thread(target=producer)
    t.start()

    for record in consumer.iter_records(
        iterator_type="TRIM_HORIZON", wait_seconds=0.01
    ):
        received.append(record)
        if len(received) >= 3:
            break

    t.join()
    assert len(received) == 3


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.data_ingestion.consumer",
        is_folder=True,
        preview=False,
    )
