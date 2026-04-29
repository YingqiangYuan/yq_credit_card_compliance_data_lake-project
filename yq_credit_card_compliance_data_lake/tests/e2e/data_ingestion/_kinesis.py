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


def get_prod_stream_name() -> str:
    """The production Kinesis stream provisioned by :class:`InfraStack`.

    Used by the Phase 4 ``--prod`` flag on the e2e scripts to drive an
    end-to-end smoke against the deployed Lambda consumer.  Purging this
    stream is never appropriate; ``purge_stream`` must not be called with
    this name.
    """
    return one.config.kinesis_stream_transaction


def purge_stream(stream_name: T.Optional[str] = None) -> int:
    """Drain every shard with a side iterator and discard the records.
    Returns the total count read.

    **Caveat**: Kinesis has no per-record delete API.  This function reads
    records into oblivion using its own iterator, but the records remain
    in the stream until the retention window (24 hours for the test
    stream) expires.  A *separate* consumer that subsequently starts a
    fresh ``TRIM_HORIZON`` iterator will see those same records again.

    Useful mainly as an audit step ("how many records were sitting in the
    stream before I produced?") and as a sanity check against the
    producer's own output count.  The default e2e ``consume()`` flow uses
    ``LATEST`` to avoid stale-data flooding entirely, which makes this
    purge call cosmetic for that workflow.
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
