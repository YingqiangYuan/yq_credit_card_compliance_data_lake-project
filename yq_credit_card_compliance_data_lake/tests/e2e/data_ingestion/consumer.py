# -*- coding: utf-8 -*-

"""
E2e consumer — wraps the long-running :class:`Consumer` class with a visual
log.

Runs forever; stop with ``KeyboardInterrupt``.  Each record received is
printed on its own numbered line so you can match UUIDs against the producer
output.
"""

import json
import typing as T

from ....api import one
from ....data_ingestion.api import Consumer
from ....logger import logger
from ._kinesis import get_test_stream_name


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


def consume(
    iterator_type: str = "TRIM_HORIZON",
    wait_seconds: float = 1.0,
    limit: int = 500,
) -> int:
    """Run the long-running consumer flow.

    Returns the number of records read before the user pressed ``Ctrl+C``.

    :param iterator_type: where to start reading.  Default ``TRIM_HORIZON``
        (oldest available) so this picks up records produced moments before
        the consumer started — what an operator usually wants for a
        side-by-side smoke test.  Pass ``"LATEST"`` to only see records that
        arrive after the consumer is up.
    :param wait_seconds: idle sleep between empty polling passes.
    :param limit: max records per ``GetRecords`` call.
    """
    stream = get_test_stream_name()
    consumer = Consumer(one.kinesis_client, stream)

    logger.ruler(
        f"consume {stream} from={iterator_type} wait={wait_seconds}s limit={limit}"
    )
    logger.info("Ctrl+C to stop")

    grand_total = 0
    try:
        for record in consumer.iter_records(
            iterator_type=iterator_type,
            wait_seconds=wait_seconds,
            limit=limit,
        ):
            grand_total += 1
            txn: dict[str, T.Any] = json.loads(record["Data"])
            logger.info(_format_record(grand_total, txn))
    except KeyboardInterrupt:
        pass

    logger.ruler(f"consumer stopped — {grand_total} records")
    return grand_total
