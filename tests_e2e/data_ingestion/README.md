# Phase 3 — Data Ingestion E2E Smoke Scripts

End-to-end smoke scripts that exercise the **real** Kinesis stream provisioned by `TestStack`. These are not pytest tests — run them by hand to verify a producer → consumer round-trip is alive.

## Architecture

The actual logic lives inside the package at `yq_credit_card_compliance_data_lake/tests/e2e/data_ingestion/`. The two scripts in this directory are thin entry-points: they parse `argv`, then call `produce_transactions()` or `consume_transactions()`.

```
yq_credit_card_compliance_data_lake/tests/e2e/data_ingestion/
├── _kinesis.py      ← shard discovery, draining, purge_stream()
├── producer.py      ← produce(n)  — purges first, then generates + sends
└── consumer.py      ← consume()   — drains every shard, prints each record

tests_e2e/data_ingestion/
├── run_producer.py  ← thin wrapper around produce_transactions
└── run_consumer.py  ← thin wrapper around consume_transactions
```

## Prerequisites

- `.env` with `LOCAL_AWS_PROFILE` pointing at an AWS account where you can create Kinesis streams
- `mise run inst` (deps installed)

## Lifecycle

```bash
# 1. Provision the test stream (once per testing session, ~ 30 sec)
cd cdk && uv run cdk deploy yq-credit-card-compliance-data-lake-test
cd ..

# 2. Push N fake transactions. The first step inside produce() is to purge any
#    leftovers from a previous run, so you never need to run a separate purge.
uv run python -m tests_e2e.data_ingestion.run_producer          # default 100
uv run python -m tests_e2e.data_ingestion.run_producer 1500     # 3 batches

# 3. Read them back. Expect to see the same records you just produced.
uv run python -m tests_e2e.data_ingestion.run_consumer

# 4. Tear down — Kinesis bills per stream-hour, even on-demand.
cd cdk && uv run cdk destroy yq-credit-card-compliance-data-lake-test
```

## What you will see

Both producer and consumer emit one numbered visual log line per record so you can eyeball that the same UUIDs appear on both sides:

```
+----- produce 100 transactions → ...transaction-stream-test ------+
| [001/100] 550e8400-e29b-41d4-a716-446655440000 $    12.34 USD APPROVED  POS        card=41111111… mcc=5411
| [002/100] e1f4a8c2-...
...
+----- send_records --------------+
| total=100 success=100 failed=0
+----- producer complete ---------+

+----- consume from ...transaction-stream-test ------+
| shard shardId-000000000000
|   [0001] 550e8400-e29b-41d4-a716-446655440000 $    12.34 USD APPROVED  POS        card=41111111… mcc=5411
|   [0002] e1f4a8c2-...
...
+----- consumer complete — 100 total ----+
```

## Cost

Kinesis on-demand mode: ~$0.04 per stream-hour plus per-GB. A 30-minute smoke session with `cdk destroy` afterwards costs roughly **$0.02**. Leaving the stream up costs about **$30/month** even with zero traffic — please `cdk destroy` when done.
