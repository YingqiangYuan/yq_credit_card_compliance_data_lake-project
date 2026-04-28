# -*- coding: utf-8 -*-

"""
Shared helpers for the Phase 3 e2e scripts.

Centralizes Kinesis shard discovery and per-shard draining so the producer,
consumer, and purge scripts share the exact same scanning semantics.
"""

import time
import typing as T
from collections.abc import Iterator

from yq_credit_card_compliance_data_lake.api import one


def get_test_stream_name() -> str:
    """The Kinesis stream provisioned by ``TestStack``."""
    return one.config.kinesis_stream_transaction_test


def iter_shard_ids(client, stream_name: str) -> Iterator[str]:
    """Yield every shard ID for ``stream_name`` (paginated)."""
    paginator = client.get_paginator("list_shards")
    for page in paginator.paginate(StreamName=stream_name):
        for shard in page["Shards"]:
            yield shard["ShardId"]


def drain_shard(
    client,
    stream_name: str,
    shard_id: str,
    iterator_type: str = "TRIM_HORIZON",
    max_empty_polls: int = 3,
    poll_sleep_seconds: float = 1.0,
) -> Iterator[dict]:
    """Yield every record currently in a shard, then return.

    "Currently" is defined as: keep polling until ``max_empty_polls``
    consecutive empty responses come back. This avoids the ambiguity of trying
    to read until ``MillisBehindLatest == 0`` (which can flicker).

    Each yielded item is a raw boto3 record dict — the caller decides whether
    to JSON-decode the ``Data`` field.
    """
    iterator: T.Optional[str] = client.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType=iterator_type,
    )["ShardIterator"]

    empty_polls = 0
    while iterator and empty_polls < max_empty_polls:
        resp = client.get_records(ShardIterator=iterator, Limit=500)
        records = resp["Records"]
        if not records:
            empty_polls += 1
            time.sleep(poll_sleep_seconds)
        else:
            empty_polls = 0
            yield from records
        iterator = resp.get("NextShardIterator")
