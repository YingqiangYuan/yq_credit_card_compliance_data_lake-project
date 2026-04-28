# Phase 3 — Data Ingestion E2E Smoke Scripts

End-to-end smoke scripts that exercise the **real** Kinesis stream provisioned by `TestStack`. These are not pytest tests — run them by hand to verify a producer → consumer round-trip is alive.

## Prerequisites

- `.env` configured with `LOCAL_AWS_PROFILE` pointing at an AWS account where you can create Kinesis streams
- `mise run inst` (deps installed)

## Lifecycle

```bash
# 1. Provision the test stream (once per testing session)
cd cdk && uv run cdk deploy yq-credit-card-compliance-data-lake-test

# 2. (Optional) drain anything left over from a previous run
uv run python -m tests_e2e.data_ingestion.purge_stream

# 3. Push N fake transactions (default 100)
uv run python -m tests_e2e.data_ingestion.run_producer
uv run python -m tests_e2e.data_ingestion.run_producer 1500   # 3 batches of 500

# 4. Read them back; expect to see the same N records
uv run python -m tests_e2e.data_ingestion.run_consumer

# 5. Tear down the stream when done — Kinesis bills per stream-hour
cd cdk && uv run cdk destroy yq-credit-card-compliance-data-lake-test
```

## What each script does

| Script | Purpose | Reads | Writes |
|--------|---------|-------|--------|
| `purge_stream.py` | Drain the stream and discard records — leaves the stream empty (from a fresh `TRIM_HORIZON` iterator's POV) | All records currently retained | nothing |
| `run_producer.py [N]` | Generate `N` fake transactions via `TransactionFaker` and push them via `send_records` | nothing | `N` records into the test stream |
| `run_consumer.py` | Drain every shard from `TRIM_HORIZON`, pretty-print each transaction | All records currently retained | nothing |

All three share helpers in `_common.py` so they iterate shards and drain them with identical semantics.

## What this is NOT

- **Not pytest tests.** No assertions, no CI integration. The "test" is your eyeballs verifying the consumer prints what the producer pushed.
- **Not a separate AWS environment.** `TestStack` lives in the same account/region as `InfraStack`; it just collects extra resources you can deploy and destroy in a single CDK command.
- **Not an integration test for Lambda.** Phase 4 will add a real `lbd/transaction_ingestion.py` consumer Lambda + automated `tests_int/` coverage. Until then, `run_consumer.py` here plays the consumer role.

## Cost

Kinesis on-demand mode: `~$0.04 per stream-hour` plus per-GB ingestion. A 30-minute smoke session costs roughly **$0.02** if you destroy the stack right after. Leaving the stream up "for next time" costs about `$30/month` even with zero traffic — please `cdk destroy` when done.
