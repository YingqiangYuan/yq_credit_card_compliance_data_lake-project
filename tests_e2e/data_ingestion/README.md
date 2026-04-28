# Phase 3 — Data Ingestion E2E Smoke Scripts

End-to-end smoke scripts that exercise the **real** Kinesis stream provisioned by `TestStack`. These are not pytest tests — run them by hand to verify a producer → consumer round-trip is alive.

## Architecture

Real logic lives in the package; this directory holds two thin entry-point scripts.

```
yq_credit_card_compliance_data_lake/
├── data_ingestion/
│   ├── producer/                                   ← Phase 1, send_records
│   └── consumer/                                   ← Phase 3, Consumer class
│       ├── consumer_00_base.py                     ← iter_shard_ids, drain_shard
│       └── consumer_01_kinesis.py                  ← Consumer (long-running)
└── tests/e2e/data_ingestion/
    ├── _kinesis.py                                 ← purge_stream + stream-name helper
    ├── producer.py                                 ← produce(burst_size, interval, total_bursts)
    └── consumer.py                                 ← consume() wraps Consumer with visual log

tests_e2e/data_ingestion/
├── run_producer.py                                 ← argparse → produce_transactions(...)
└── run_consumer.py                                 ← argparse → consume_transactions(...)
```

## Prerequisites

- `.env` with `LOCAL_AWS_PROFILE` pointing at an AWS account where you can create Kinesis streams
- `mise run inst` (deps installed)

## Lifecycle

The producer and consumer are designed to run **in two terminals concurrently** — start the consumer first, then have the producer send bursts at it.

```bash
# 1. Provision the test stream (once per session, ~ 30 sec).
#    1 PROVISIONED shard ≈ $0.015/hour ≈ $0.01 for a 30-min smoke session.
cd cdk && uv run cdk deploy yq-credit-card-compliance-data-lake-test
cd ..

# 2. (Terminal A) start the long-poll consumer — blocks, prints records as they arrive
uv run python -m tests_e2e.data_ingestion.run_consumer

# 3. (Terminal B) start the burst producer — purges the stream first, then dumps
#    10 records every 1 second, 10 times (default).
uv run python -m tests_e2e.data_ingestion.run_producer

# Or: run forever with custom rate
uv run python -m tests_e2e.data_ingestion.run_producer -k 50 -n 0.5 --forever

# 4. When done, Ctrl+C the consumer and tear down.
cd cdk && uv run cdk destroy yq-credit-card-compliance-data-lake-test
```

## Producer CLI

| Flag | Default | Meaning |
|------|---------|---------|
| `-k`, `--burst-size` | 10 | records per burst |
| `-n`, `--interval` | 1.0 | seconds between bursts |
| `-t`, `--bursts` | 10 | number of bursts (ignored with `--forever`) |
| `--forever` | off | run until Ctrl+C |
| `--no-purge` | off | skip the pre-run drain step |

## Consumer CLI

| Flag | Default | Meaning |
|------|---------|---------|
| `--from-latest` | off | read only records arriving after consumer starts (default reads from oldest available, i.e. `TRIM_HORIZON`) |
| `--wait` | 1.0 | seconds to sleep between empty polls |
| `--limit` | 500 | max records per `GetRecords` call |

## What you will see

Both producer and consumer emit one numbered visual log line per record so you can eyeball that the same UUIDs appear on both sides:

```
+----- produce 10/burst × 10 every 1.0s → ...transaction-stream-test -----+
| --- burst 1/10 ---
|   [0001] 550e8400-e29b-41d4-a716-446655440000 $    12.34 USD APPROVED  POS        card=41111111… mcc=5411
|   [0002] e1f4a8c2-...
| ...
|   burst 1: sent=10 failed=0
| --- burst 2/10 ---
|   [0011] ...
+----- producer complete — 10 bursts, 100 records --+

+----- consume ...transaction-stream-test from=TRIM_HORIZON wait=1.0s limit=500 ----+
| Ctrl+C to stop
| [0001] 550e8400-e29b-41d4-a716-446655440000 $    12.34 USD APPROVED  POS        card=41111111… mcc=5411
| [0002] e1f4a8c2-...
| ...
+----- consumer stopped — 100 records ----+
```

## Cost

1 PROVISIONED shard at `$0.015/hour` ≈ **$0.008** for a 30-min smoke session. Leaving the stream up costs about **$11/month** with zero traffic — please `cdk destroy` when done.
