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
from ._kinesis import get_prod_stream_name, get_test_stream_name


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
    iterator_type: str = "LATEST",
    wait_seconds: float = 1.0,
    limit: int = 500,
    prod: bool = False,
) -> int:
    """Run the long-running consumer flow.

    Returns the number of records read before the user pressed ``Ctrl+C``.

    :param iterator_type: where to start reading.  Default ``LATEST`` —
        only records produced *after* the consumer starts are surfaced.
        This is the right default because:

        - Kinesis has no per-record delete API, so any previous session's
          records still in the retention window would otherwise flood a
          ``TRIM_HORIZON`` consumer at startup.
        - The intended workflow is two-terminal: start consumer first,
          then start producer in another terminal — consumer should only
          see what the producer is currently emitting.

        Pass ``"TRIM_HORIZON"`` only when you genuinely want a forensic dump
        of every record still retained in the stream.
    :param wait_seconds: idle sleep between empty polling passes.
    :param limit: max records per ``GetRecords`` call.
    :param prod: when ``True``, tail the production transaction stream
        instead of the test stream.  Each Kinesis consumer maintains its
        own iterator independently of any other reader, so doing this
        does *not* steal records from the deployed Lambda consumer — both
        see the same records.  Useful as a debug tap to see what Lambda
        is currently being asked to process.
    """
    stream = get_prod_stream_name() if prod else get_test_stream_name()
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
