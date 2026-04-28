# -*- coding: utf-8 -*-

"""
Shared Kinesis primitives for the e2e producer / consumer / purge flows.

Centralizing shard discovery and per-shard draining ensures the producer's
purge step, the standalone purge invocation, and the consumer all use the
exact same scanning semantics.
"""

import time
import typing as T
from collections.abc import Iterator

from ....api import one
from ....logger import logger


def get_test_stream_name() -> str:
    """The Kinesis stream provisioned by ``TestStack``."""
    return one.config.kinesis_stream_transaction_test


def iter_shard_ids(client, stream_name: str) -> Iterator[str]:
    """Yield every shard id for ``stream_name`` (paginated)."""
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

    "Currently" means: keep polling until ``max_empty_polls`` consecutive empty
    responses come back. Avoids the flicker of relying on ``MillisBehindLatest``.

    Each yielded item is a raw boto3 record dict — callers JSON-decode the
    ``Data`` field themselves.
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


def purge_stream(stream_name: T.Optional[str] = None) -> int:
    """Drain every shard and discard records. Returns total records purged.

    Called automatically at the start of :func:`producer.produce` so the
    follow-up ``consume`` only sees freshly produced records. Safe to call
    when the stream is already empty (returns 0).
    """
    stream = stream_name or get_test_stream_name()
    client = one.kinesis_client

    logger.ruler(f"purge {stream}")
    grand_total = 0
    for shard_id in iter_shard_ids(client, stream):
        count = sum(1 for _ in drain_shard(client, stream, shard_id))
        logger.info(f"shard {shard_id}: discarded {count}")
        grand_total += count
    logger.info(f"purge complete — {grand_total} records discarded")
    return grand_total
