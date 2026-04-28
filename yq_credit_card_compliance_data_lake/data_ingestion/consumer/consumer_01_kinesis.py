# -*- coding: utf-8 -*-

"""
Long-running Kinesis consumer over all shards of a stream.

Unlike :func:`drain_shard` (which exits after a few empty polls), the
``Consumer`` class keeps polling forever — it is the right primitive for an
"always-on" pipeline.  The caller breaks the loop or sends
``KeyboardInterrupt``.
"""

import time
import typing as T
from collections.abc import Iterator

from .consumer_00_base import iter_shard_ids

if T.TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_kinesis.client import KinesisClient


class Consumer:
    """Side-effect-free constructor; all AWS calls happen inside
    :meth:`iter_records`.

    Usage::

        consumer = Consumer(kinesis_client, "my-stream")
        for record in consumer.iter_records(wait_seconds=2.0):
            process(record)   # Ctrl+C to stop

    Production note: this class does **not** persist shard iterators between
    runs.  A real long-lived consumer must checkpoint progress (e.g., to
    DynamoDB) and resume via :func:`drain_shard`'s ``shard_iterator`` arg or
    by storing sequence numbers and fetching ``AT_SEQUENCE_NUMBER``-typed
    iterators.  Phase 4 will add a Lambda-powered consumer that delegates
    checkpointing to the AWS Lambda Event Source Mapping; this class is the
    "naive long-poller" used by e2e smoke tests.
    """

    def __init__(
        self,
        kinesis_client: "KinesisClient",
        stream_name: str,
    ):
        self._client = kinesis_client
        self._stream_name = stream_name

    @property
    def stream_name(self) -> str:
        return self._stream_name

    def iter_records(
        self,
        iterator_type: str = "LATEST",
        wait_seconds: float = 1.0,
        limit: int = 500,
    ) -> Iterator[dict]:
        """Yield boto3 record dicts as they arrive across all shards.

        Polls each shard round-robin.  When a full pass yields no records,
        sleeps ``wait_seconds`` before the next pass.  Closed shards
        (``NextShardIterator is None``) are dropped from the polling set;
        the loop ends only when all shards close — in normal operation this
        is effectively forever.

        :param iterator_type: where to start.  ``LATEST`` (default) reads
            only records that arrive after this call begins.
            ``TRIM_HORIZON`` reads from the oldest record still retained —
            useful when you want to catch records produced moments before.
        :param wait_seconds: idle sleep between empty polling passes.
        :param limit: max records per ``GetRecords`` call.
        """
        shard_iterators: dict[str, T.Optional[str]] = {}
        for shard_id in iter_shard_ids(self._client, self._stream_name):
            shard_iterators[shard_id] = self._client.get_shard_iterator(
                StreamName=self._stream_name,
                ShardId=shard_id,
                ShardIteratorType=iterator_type,
            )["ShardIterator"]

        while shard_iterators:
            saw_records = False
            for shard_id in list(shard_iterators.keys()):
                iterator = shard_iterators[shard_id]
                if iterator is None:
                    del shard_iterators[shard_id]
                    continue
                resp = self._client.get_records(ShardIterator=iterator, Limit=limit)
                if resp["Records"]:
                    saw_records = True
                    yield from resp["Records"]
                shard_iterators[shard_id] = resp.get("NextShardIterator")
            if not saw_records:
                time.sleep(wait_seconds)
