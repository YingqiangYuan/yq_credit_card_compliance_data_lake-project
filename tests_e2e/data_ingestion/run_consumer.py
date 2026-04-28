# -*- coding: utf-8 -*-

"""
Drain the test Kinesis stream once and pretty-print every record.

Reads each shard from ``TRIM_HORIZON`` (oldest available) so this picks up
records produced by ``run_producer.py`` even if the consumer starts seconds
later. Exits when all shards return empty for several consecutive polls.

Usage::

    python tests_e2e/data_ingestion/run_consumer.py
"""

import json

from yq_credit_card_compliance_data_lake.api import one
from yq_credit_card_compliance_data_lake.logger import logger

from ._common import drain_shard, get_test_stream_name, iter_shard_ids


def _format(txn: dict) -> str:
    return (
        f"{txn['transaction_id']}  "
        f"{txn['amount']:>10.2f} {txn['currency']}  "
        f"{txn['auth_status']:<9s} "
        f"{txn['channel']:<10s} "
        f"card={txn['card_id'][:8]}…  "
        f"mcc={txn['mcc_code']}"
    )


def main() -> None:
    stream = get_test_stream_name()
    logger.info(f"consuming from {stream}")

    grand_total = 0
    for shard_id in iter_shard_ids(one.kinesis_client, stream):
        shard_total = 0
        for record in drain_shard(one.kinesis_client, stream, shard_id):
            txn = json.loads(record["Data"])
            print("  " + _format(txn))
            shard_total += 1
        logger.info(f"shard {shard_id}: {shard_total} records")
        grand_total += shard_total

    logger.info(f"total: {grand_total} records")


if __name__ == "__main__":
    main()
