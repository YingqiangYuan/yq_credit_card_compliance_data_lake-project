# -*- coding: utf-8 -*-

"""
Thin entry-point that invokes the packaged ``consume`` flow.

The real logic lives in
``yq_credit_card_compliance_data_lake.tests.e2e.data_ingestion.consumer``;
this script just parses CLI args and calls it.  Runs until ``Ctrl+C``.

Usage::

    python -m tests_e2e.data_ingestion.run_consumer
    python -m tests_e2e.data_ingestion.run_consumer --from-latest --wait 2.0
"""

import argparse

from yq_credit_card_compliance_data_lake.tests.e2e.api import consume_transactions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Long-poll the test Kinesis stream and pretty-print every record."
    )
    parser.add_argument(
        "--from-beginning", action="store_true",
        help="read from TRIM_HORIZON (every record still in retention); "
             "default LATEST reads only records produced after consumer starts",
    )
    parser.add_argument(
        "--wait", type=float, default=5.0,
        help="seconds to sleep between empty polls (default: 5.0)",
    )
    parser.add_argument(
        "--limit", type=int, default=500,
        help="max records per GetRecords call (default: 500)",
    )
    args = parser.parse_args()

    consume_transactions(
        iterator_type="TRIM_HORIZON" if args.from_beginning else "LATEST",
        wait_seconds=args.wait,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
