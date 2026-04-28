# -*- coding: utf-8 -*-

"""
E2e producer — long-running burst generator.

Emits ``burst_size`` fake transactions every ``interval_seconds`` seconds for
``total_bursts`` rounds (``None`` = run until ``KeyboardInterrupt``).  Each
record is logged on its own numbered line so the operator can eyeball-match
UUIDs against the consumer's output.
"""

import time
import typing as T

from ....api import one
from ....data_ingestion.api import TransactionFaker, send_records
from ....logger import logger
from ._kinesis import get_test_stream_name, purge_stream


def _format_record(idx: int, txn) -> str:
    """One-line, fixed-width visual representation of a single transaction."""
    return (
        f"[{idx:04d}] "
        f"{txn.transaction_id} "
        f"${txn.amount:>9.2f} {txn.currency.value} "
        f"{txn.auth_status.value:<9s} "
        f"{txn.channel.value:<10s} "
        f"card={txn.card_id[:8]}… "
        f"mcc={txn.mcc_code}"
    )


def produce(
    burst_size: int = 10,
    interval_seconds: float = 1.0,
    total_bursts: T.Optional[int] = 10,
    purge_first: bool = True,
) -> None:
    """Long-running producer.

    :param burst_size: records emitted per burst.
    :param interval_seconds: sleep between bursts.
    :param total_bursts: number of bursts to emit; ``None`` runs forever
        until ``KeyboardInterrupt``.
    :param purge_first: drain leftovers from the stream once before the
        first burst.  Default ``True`` so the next consumer run sees a
        clean slate.
    """
    stream = get_test_stream_name()

    if purge_first:
        purge_stream(stream)

    bursts_label = "∞" if total_bursts is None else str(total_bursts)
    logger.ruler(
        f"produce {burst_size}/burst × {bursts_label} every {interval_seconds}s "
        f"→ {stream}"
    )

    faker = TransactionFaker()
    burst_idx = 0
    grand_total = 0
    try:
        while total_bursts is None or burst_idx < total_bursts:
            burst_idx += 1
            txns = faker.make_many(burst_size)

            logger.info(f"--- burst {burst_idx}/{bursts_label} ---")
            for txn in txns:
                grand_total += 1
                logger.info(_format_record(grand_total, txn), indent=1)

            result = send_records(one.kinesis_client, stream, txns)
            logger.info(
                f"burst {burst_idx}: sent={result.success_count} "
                f"failed={result.failed_count}",
                indent=1,
            )

            if total_bursts is not None and burst_idx >= total_bursts:
                break
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        logger.info(
            f"interrupted after {burst_idx} bursts ({grand_total} records)"
        )

    logger.ruler(
        f"producer complete — {burst_idx} bursts, {grand_total} records"
    )
