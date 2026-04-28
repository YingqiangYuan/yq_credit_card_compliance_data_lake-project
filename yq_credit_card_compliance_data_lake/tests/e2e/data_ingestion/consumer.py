# -*- coding: utf-8 -*-

"""
E2e consumer — drain every shard from ``TRIM_HORIZON`` and emit one numbered
visual log line per record received.
"""

import json

from ....api import one
from ....logger import logger
from ._kinesis import drain_shard, get_test_stream_name, iter_shard_ids


def _format_record(idx: int, txn: dict) -> str:
    """One-line, fixed-width visual representation of a single transaction."""
    return (
        f"[{idx:04d}] "
        f"{txn['transaction_id']} "
        f"${txn['amount']:>9.2f} {txn['currency']} "
        f"{txn['auth_status']:<9s} "
        f"{txn['channel']:<10s} "
        f"card={txn['card_id'][:8]}… "
        f"mcc={txn['mcc_code']}"
    )


def consume() -> int:
    """Run the consumer flow: list shards, drain each, log per record.

    Returns the total number of records read across all shards.
    """
    stream = get_test_stream_name()
    client = one.kinesis_client

    logger.ruler(f"consume from {stream}")

    grand_total = 0
    for shard_id in iter_shard_ids(client, stream):
        logger.info(f"shard {shard_id}")
        shard_total = 0
        for record in drain_shard(client, stream, shard_id):
            shard_total += 1
            grand_total += 1
            txn = json.loads(record["Data"])
            logger.info(_format_record(grand_total, txn), indent=1)
        logger.info(f"shard {shard_id}: {shard_total} records")

    logger.ruler(f"consumer complete — {grand_total} total")
    return grand_total
