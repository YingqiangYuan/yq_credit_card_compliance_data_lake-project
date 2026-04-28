# -*- coding: utf-8 -*-

"""
Push N fake transactions into the test Kinesis stream.

Usage::

    python tests_e2e/data_ingestion/run_producer.py            # default 100
    python tests_e2e/data_ingestion/run_producer.py 1500       # 3 batches

Pre-req: ``cdk deploy yq-credit-card-compliance-data-lake-test`` so the test
stream exists.
"""

import sys

from yq_credit_card_compliance_data_lake.api import one
from yq_credit_card_compliance_data_lake.data_ingestion.api import (
    TransactionFaker,
    send_records,
)
from yq_credit_card_compliance_data_lake.logger import logger

from ._common import get_test_stream_name


def main(n: int) -> None:
    stream = get_test_stream_name()
    logger.info(f"producing {n} fake transactions → {stream}")

    faker = TransactionFaker()
    txns = faker.make_many(n)
    result = send_records(one.kinesis_client, stream, txns)

    logger.info(
        f"done: total={result.total} "
        f"success={result.success_count} "
        f"failed={result.failed_count}"
    )
    if result.failed_count:
        logger.info(f"first failure: {result.failed_entries[0]}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    main(n)
