# -*- coding: utf-8 -*-

"""
E2e-only Kinesis helpers.

The reusable shard iteration / drain logic now lives in
:mod:`yq_credit_card_compliance_data_lake.data_ingestion.consumer` and is
imported here.  This module keeps just two e2e-specific concerns:

- ``get_test_stream_name`` — the singular test stream from ``Config``
- ``purge_stream`` — drain & discard all records, called automatically at the
  start of each producer run so the next consumer run starts clean
"""

import typing as T

from ....api import one
from ....data_ingestion.consumer.api import drain_shard, iter_shard_ids
from ....logger import logger


def get_test_stream_name() -> str:
    """The Kinesis stream provisioned by ``TestStack``."""
    return one.config.kinesis_stream_transaction_test


def purge_stream(stream_name: T.Optional[str] = None) -> int:
    """Drain every shard and discard records.  Returns total purged.

    Called automatically at the start of :func:`producer.produce` so the
    follow-up :func:`consumer.consume` only sees freshly produced records.
    Safe to call when the stream is already empty (returns 0).
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
