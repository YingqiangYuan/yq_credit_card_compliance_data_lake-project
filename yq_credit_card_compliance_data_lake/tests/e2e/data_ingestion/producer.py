# -*- coding: utf-8 -*-

"""
E2e producer — purge the test stream, generate N fake transactions, push them
via :func:`send_records`, and emit one numbered visual log line per record.
"""

from ....api import one
from ....data_ingestion.api import TransactionFaker, send_records
from ....logger import logger
from ._kinesis import get_test_stream_name, purge_stream


def _format_record(idx: int, total: int, txn) -> str:
    """One-line, fixed-width visual representation of a single transaction."""
    width = len(str(total))
    return (
        f"[{idx:0{width}d}/{total}] "
        f"{txn.transaction_id} "
        f"${txn.amount:>9.2f} {txn.currency.value} "
        f"{txn.auth_status.value:<9s} "
        f"{txn.channel.value:<10s} "
        f"card={txn.card_id[:8]}… "
        f"mcc={txn.mcc_code}"
    )


def produce(n: int = 100, purge_first: bool = True) -> None:
    """Run the producer flow: optional purge, generate, send, log per record.

    :param n: number of fake transactions to generate.
    :param purge_first: drain leftovers from a previous session before
        producing. Default ``True`` so a fresh consumer run after this only
        sees the new batch.
    """
    stream = get_test_stream_name()

    if purge_first:
        purge_stream(stream)

    logger.ruler(f"produce {n} transactions → {stream}")

    txns = TransactionFaker().make_many(n)
    for idx, txn in enumerate(txns, start=1):
        logger.info(_format_record(idx, n, txn))

    logger.ruler("send_records")
    result = send_records(one.kinesis_client, stream, txns)
    logger.info(
        f"total={result.total} "
        f"success={result.success_count} "
        f"failed={result.failed_count}"
    )
    if result.failed_count:
        logger.info(f"first failure: {result.failed_entries[0]}")
    logger.ruler("producer complete")
