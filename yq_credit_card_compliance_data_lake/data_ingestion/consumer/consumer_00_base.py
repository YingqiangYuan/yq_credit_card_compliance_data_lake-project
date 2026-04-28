# -*- coding: utf-8 -*-

"""
Consumer base utilities — free functions for shard discovery and one-shot
draining.  The long-running, multi-shard ``Consumer`` class lives in
``consumer_01_kinesis.py``.
"""

import time
import typing as T
from collections.abc import Iterator

if T.TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_kinesis.client import KinesisClient


def iter_shard_ids(client: "KinesisClient", stream_name: str) -> Iterator[str]:
    """Yield every shard id for ``stream_name`` (paginated)."""
    paginator = client.get_paginator("list_shards")
    for page in paginator.paginate(StreamName=stream_name):
        for shard in page["Shards"]:
            yield shard["ShardId"]


def drain_shard(
    client: "KinesisClient",
    stream_name: str,
    shard_id: str,
    iterator_type: str = "TRIM_HORIZON",
    shard_iterator: str | None = None,
    limit: int = 500,
    max_empty_polls: int = 3,
    poll_sleep_seconds: float = 1.0,
) -> Iterator[dict]:
    """Drain ``shard_id`` until ``max_empty_polls`` consecutive empty
    responses, yielding each boto3 record dict.

    "Currently in the shard" is defined as: keep polling until
    ``max_empty_polls`` consecutive empty responses come back.  This avoids
    relying on ``MillisBehindLatest`` which can flicker.

    :param shard_iterator: if provided, resume from this iterator string
        (skips the ``GetShardIterator`` call entirely).  Useful when caller
        has its own checkpoint store.  When ``None``, a fresh iterator of
        ``iterator_type`` is requested for ``shard_id``.
    :param limit: max records per ``GetRecords`` call.  Kinesis hard limit
        is 10000; 500 keeps memory bounded and roughly matches a 1 MB/s
        shard-second of typical traffic.
    """
    if shard_iterator is None:
        shard_iterator = client.get_shard_iterator(
            StreamName=stream_name,
            ShardId=shard_id,
            ShardIteratorType=iterator_type,
        )["ShardIterator"]

    iterator: T.Optional[str] = shard_iterator
    empty_polls = 0
    while iterator and empty_polls < max_empty_polls:
        resp = client.get_records(ShardIterator=iterator, Limit=limit)
        records = resp["Records"]
        if not records:
            empty_polls += 1
            time.sleep(poll_sleep_seconds)
        else:
            empty_polls = 0
            yield from records
        iterator = resp.get("NextShardIterator")
