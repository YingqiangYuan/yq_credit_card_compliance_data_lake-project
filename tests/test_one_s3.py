# -*- coding: utf-8 -*-

"""
Unit test for the ``OneS3Mixin`` cached-property layout.

Hits real AWS for ``aws_account_alias`` (used to compute bucket names), so it
runs in the same "needs credentials" tier as ``test_one_boto_ses.py``. The
assertions are pure-Python derivations — no S3 calls — so the test is fast
once the alias has been cached.
"""

from yq_credit_card_compliance_data_lake.one.api import one


def test_medallion_layers_are_under_data_root():
    data_uri = one.s3dir_data.uri
    for s3dir in [
        one.s3dir_bronze,
        one.s3dir_silver,
        one.s3dir_gold,
        one.s3dir_quarantine,
        one.s3dir_landing,
        one.s3dir_manifest,
    ]:
        assert s3dir.uri.startswith(data_uri)
        assert s3dir.uri.endswith("/")


def test_layer_names_match_property_names():
    assert one.s3dir_bronze.uri.rstrip("/").endswith("/bronze")
    assert one.s3dir_silver.uri.rstrip("/").endswith("/silver")
    assert one.s3dir_gold.uri.rstrip("/").endswith("/gold")
    assert one.s3dir_quarantine.uri.rstrip("/").endswith("/quarantine")
    assert one.s3dir_landing.uri.rstrip("/").endswith("/landing")
    assert one.s3dir_manifest.uri.rstrip("/").endswith("/manifest")


def test_transaction_subdirs_nest_under_correct_layers():
    assert one.s3dir_bronze_transactions.uri.startswith(one.s3dir_bronze.uri)
    assert one.s3dir_bronze_transactions.uri.rstrip("/").endswith("/transactions")

    assert one.s3dir_quarantine_transactions.uri.startswith(one.s3dir_quarantine.uri)
    assert one.s3dir_quarantine_transactions.uri.rstrip("/").endswith("/transactions")


if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake.one.one_03_s3",
        preview=False,
    )
