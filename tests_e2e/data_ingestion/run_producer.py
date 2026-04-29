# -*- coding: utf-8 -*-

"""
Thin entry-point that invokes the packaged ``produce`` flow.

The real logic lives in
``yq_credit_card_compliance_data_lake.tests.e2e.data_ingestion.producer``;
this script just parses CLI args and calls it.

Usage::

    # 10 records per burst, every 1.0s, 10 bursts (default = 100 records total)
    python -m tests_e2e.data_ingestion.run_producer

    # 50 records per burst, every 0.5s, 5 bursts (250 records total)
    python -m tests_e2e.data_ingestion.run_producer -k 50 -n 0.5 -t 5

    # Run forever until Ctrl+C
    python -m tests_e2e.data_ingestion.run_producer --forever

    # Phase 4 end-to-end smoke — push to PROD stream so the deployed
    # Lambda consumer picks records up and writes Bronze + DDB.
    python -m tests_e2e.data_ingestion.run_producer --prod -t 3
"""

import argparse

from yq_credit_card_compliance_data_lake.tests.e2e.api import produce_transactions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push fake transactions to a Kinesis stream in bursts."
    )
    parser.add_argument(
        "-k", "--burst-size", type=int, default=10,
        help="records per burst (default: 10)",
    )
    parser.add_argument(
        "-n", "--interval", type=float, default=5.0,
        help="seconds between bursts (default: 1.0)",
    )
    parser.add_argument(
        "-t", "--bursts", type=int, default=10,
        help="number of bursts (default: 10). Ignored if --forever is set.",
    )
    parser.add_argument(
        "--forever", action="store_true",
        help="run until Ctrl+C; overrides --bursts",
    )
    parser.add_argument(
        "--no-purge", action="store_true",
        help="skip the pre-run purge step (purge is auto-disabled with --prod)",
    )
    parser.add_argument(
        "--prod", action="store_true",
        help="send to the PRODUCTION transaction stream — Phase 4 end-to-end "
             "smoke against the deployed Lambda consumer. Mutually exclusive "
             "with purge: a prod stream is never purged.",
    )
    args = parser.parse_args()

    produce_transactions(
        burst_size=args.burst_size,
        interval_seconds=args.interval,
        total_bursts=None if args.forever else args.bursts,
        purge_first=not args.no_purge,
        prod=args.prod,
    )


if __name__ == "__main__":
    main()
