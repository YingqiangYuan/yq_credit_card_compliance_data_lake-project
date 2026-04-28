# -*- coding: utf-8 -*-

"""
Integration test for the ``s3sync`` Lambda function (S3 event-driven).

This is the most complex integration test in the project because it validates
an **asynchronous** pipeline:

1. Write a file to the S3 *source* prefix.
2. S3 fires an event notification → invokes the ``s3sync`` Lambda.
3. Lambda copies the file to the S3 *target* prefix.
4. Poll the target prefix until the file appears (or timeout after ~10 s).

The polling loop is intentional — S3 event delivery and Lambda execution are
not instantaneous, so the test retries several times before failing.
"""

import time
import uuid

from yq_credit_card_compliance_data_lake.api import one
from yq_credit_card_compliance_data_lake.logger import logger


def test():
    # --------------------------------------------------------------------------
    # before
    # --------------------------------------------------------------------------
    basename = "test.txt"
    s3path_source = one.s3dir_source.joinpath(basename)
    s3path_target = one.s3dir_target.joinpath(basename)

    logger.info(f"preview s3 source: {s3path_source.console_url}")
    logger.info(f"preview s3 target: {s3path_target.console_url}")

    s3path_target.delete(bsm=one.s3_client)
    content = uuid.uuid4().hex
    s3path_source.write_text(content, bsm=one.s3_client)

    # Check the target immediately after writing to source
    # S3 event and LBD should not have propagated yet
    assert s3path_target.exists(bsm=one.s3_client) is False

    # --------------------------------------------------------------------------
    # after
    # --------------------------------------------------------------------------
    time.sleep(3)
    n = 7
    succeeded = False
    for i in range(n):
        time.sleep(1)
        if s3path_target.exists(bsm=one.s3_client):
            assert s3path_target.read_text(bsm=one.s3_client) == content
            succeeded = True
            break
    if succeeded is False:
        raise RuntimeError(
            f"s3path target {s3path_target} does not exist!"
            f"S3 event and Lambda function did not work!"
        )


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_unit_test

    run_unit_test(__file__)
