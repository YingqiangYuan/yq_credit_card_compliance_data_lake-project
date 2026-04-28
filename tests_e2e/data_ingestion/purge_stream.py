# -*- coding: utf-8 -*-

"""
Drain the test Kinesis stream and discard every record.

Run before ``run_producer.py`` if you want a clean slate so that the
follow-up ``run_consumer.py`` only sees the freshly-produced batch.

Note: Kinesis does not support a true "delete records" API; the only ways to
empty a stream are (a) wait for the retention period, (b) recreate the stream,
or (c) read everything and ignore it. This script implements (c) — fast,
no CDK changes, but the records remain in the shard until retention expires.
For ``run_consumer.py`` semantics that's fine: a fresh ``TRIM_HORIZON``
iterator started after this purge sees only records produced after it.

Usage::

    python tests_e2e/data_ingestion/purge_stream.py
"""

from yq_credit_card_compliance_data_lake.api import one
from yq_credit_card_compliance_data_lake.logger import logger

from ._common import drain_shard, get_test_stream_name, iter_shard_ids


def main() -> None:
    stream = get_test_stream_name()
    logger.info(f"purging {stream}")

    grand_total = 0
    for shard_id in iter_shard_ids(one.kinesis_client, stream):
        count = sum(1 for _ in drain_shard(one.kinesis_client, stream, shard_id))
        logger.info(f"shard {shard_id}: discarded {count} records")
        grand_total += count

    logger.info(f"purge complete: {grand_total} records consumed and discarded")


if __name__ == "__main__":
    main()
