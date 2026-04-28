# -*- coding: utf-8 -*-

"""
Integration test for the ``hello`` Lambda function.

Invokes the **deployed** Lambda function via ``lambda_client.invoke()`` and
validates the response payload.  Tests two cases:

1. Normal input (``{"name": "bob"}``) — expects ``"hello bob"``.
2. Missing input (``{}``) — expects the default ``"hello Mr X"``.

This test exercises the full Lambda lifecycle: cold/warm start, handler
routing through ``lambda_function.py``, Pydantic validation, and the
``LogResult`` output.
"""

import json
import base64

from yq_credit_card_compliance_data_lake.api import one


def test(
    disable_logger,
):
    # test case 1
    payload = {"name": "bob"}
    response = one.lambda_client.invoke(
        FunctionName=one.config.lbd_func_hello.name,
        InvocationType="RequestResponse",
        LogType="Tail",
        Payload=json.dumps(payload),
    )
    log = base64.b64decode(response["LogResult"].encode("utf-8")).decode("utf-8")
    # print(log)  # for debug only
    result: dict = json.loads(response["Payload"].read().decode("utf-8"))
    assert result["message"] == "hello bob"

    # test case 2
    payload = {}
    response = one.lambda_client.invoke(
        FunctionName=one.config.lbd_func_hello.name,
        InvocationType="RequestResponse",
        LogType="Tail",
        Payload=json.dumps(payload),
    )
    log = base64.b64decode(response["LogResult"].encode("utf-8")).decode("utf-8")
    # print(log)  # for debug only
    result: dict = json.loads(response["Payload"].read().decode("utf-8"))
    assert result["message"] == "hello Mr X"


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_unit_test

    run_unit_test(__file__)
