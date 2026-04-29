# Data Ingestion E2E Smoke Scripts

End-to-end smoke scripts that hit **real AWS** — either the disposable Kinesis stream provisioned by `TestStack` (Phase 3 producer ↔ consumer round-trip) or the production stream + Lambda + Bronze S3 + DynamoDB pipeline (Phase 4 end-to-end).

These are not pytest tests — run them by hand to verify a path is alive.

## Architecture

Real logic lives in the package; this directory holds two thin entry-point scripts.

```
yq_credit_card_compliance_data_lake/
├── data_ingestion/
│   ├── producer/                                   ← Phase 1, send_records
│   ├── consumer/                                   ← Phase 3, Consumer + decode_kinesis_records
│   ├── quality/                                    ← Phase 4, validate_transaction
│   ├── writer/                                     ← Phase 4, NDJSON to S3
│   └── dynamodb_table.py                           ← Phase 4, PipelineMetadata model
├── lbd/transaction_ingestion.py                    ← Phase 4, Lambda consumer
└── tests/e2e/data_ingestion/
    ├── _kinesis.py                                 ← stream-name + purge_stream helpers
    ├── producer.py                                 ← produce(burst_size, interval, total_bursts, prod)
    └── consumer.py                                 ← consume(iterator_type, ..., prod)

tests_e2e/data_ingestion/
├── run_producer.py                                 ← argparse → produce_transactions(...)
└── run_consumer.py                                 ← argparse → consume_transactions(...)
```

## Prerequisites

- `.env` with `LOCAL_AWS_PROFILE` pointing at the AWS account where the streams are provisioned
- `mise run inst` (deps installed)

---

## Phase 3 — Producer ↔ Consumer round-trip on the **test** stream

The producer and consumer are designed to run **in two terminals concurrently** — start the consumer first, then have the producer send bursts at it.

```bash
# 1. Provision the test stream (once per session, ~30 sec).
#    1 PROVISIONED shard ≈ $0.015/hour ≈ $0.01 for a 30-min smoke session.
cd cdk && uv run cdk deploy yq-credit-card-compliance-data-lake-test
cd ..

# 2. (Terminal A) start the long-poll consumer — blocks, prints records as they arrive
uv run python -m tests_e2e.data_ingestion.run_consumer

# 3. (Terminal B) start the burst producer — purges first, then dumps
#    10 records every 1 second, 10 times (default).
uv run python -m tests_e2e.data_ingestion.run_producer

# Or: run forever with custom rate
uv run python -m tests_e2e.data_ingestion.run_producer -k 50 -n 0.5 --forever

# 4. When done, Ctrl+C the consumer and tear down.
cd cdk && uv run cdk destroy yq-credit-card-compliance-data-lake-test
```

---

## Phase 4 — End-to-end against the deployed Lambda consumer

Once the prod resources are deployed (`InfraStack` with Kinesis prod stream + DynamoDB pipeline-metadata + SQS DLQ; `LambdaStack` with the `transaction_ingestion` function + Event Source Mapping) you can drive a full pipeline smoke from a single terminal.

```bash
# 1. Push a small batch to the PROD stream.  --prod also forces purge off.
uv run python -m tests_e2e.data_ingestion.run_producer --prod -t 3

# 2. Wait ~15-20 seconds (Lambda Event Source Mapping waits up to 10 s
#    to fill its 100-record batch window before invoking).

# 3. Verify the pipeline ran:
#    a. CloudWatch Logs: see the handler's "run_id=... status=..." line.
#    b. DynamoDB pipeline-metadata: query the latest run by pipeline_name.
#    c. S3 Bronze: list ${s3dir_bronze_transactions}/year=YYYY/month=MM/day=DD/
#       — there should be one .ndjson file per Lambda invocation.

# Optional: tail the prod stream from a separate terminal as a debug
# observer.  Independent iterator — does not steal records from Lambda.
uv run python -m tests_e2e.data_ingestion.run_consumer --prod --from-beginning
```

The producer never purges in `--prod` mode, regardless of `--no-purge` / `--purge`. The prod stream is shared with the deployed Lambda; purging it would silently lose records.

---

## Producer CLI

| Flag | Default | Meaning |
|------|---------|---------|
| `-k`, `--burst-size` | 10 | records per burst |
| `-n`, `--interval` | 5.0 | seconds between bursts |
| `-t`, `--bursts` | 10 | number of bursts (ignored with `--forever`) |
| `--forever` | off | run until Ctrl+C |
| `--no-purge` | off | skip the pre-run drain step (auto-disabled with `--prod`) |
| `--prod` | off | send to prod stream — drives Phase 4 end-to-end smoke |

## Consumer CLI

| Flag | Default | Meaning |
|------|---------|---------|
| `--from-beginning` | off | read from `TRIM_HORIZON` (every record still in retention); default `LATEST` reads only records produced after consumer starts |
| `--wait` | 5.0 | seconds to sleep between empty polls |
| `--limit` | 500 | max records per `GetRecords` call |
| `--prod` | off | tail prod stream as a debug observer; independent of the deployed Lambda |

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

+----- consume ...transaction-stream-test from=LATEST wait=1.0s limit=500 ----+
| Ctrl+C to stop
| [0001] 550e8400-e29b-41d4-a716-446655440000 $    12.34 USD APPROVED  POS        card=41111111… mcc=5411
| [0002] e1f4a8c2-...
| ...
+----- consumer stopped — 100 records ----+
```

## Cost

- **Test stream** (`TestStack`): 1 PROVISIONED shard at `$0.015/hour` ≈ **$0.008** for a 30-min Phase 3 smoke session. Idle cost ≈ **$11/month** — `cdk destroy` when done.
- **Prod stream** (`InfraStack`): 1 PROVISIONED shard, same per-hour cost. Lives full-time alongside the deployed Lambda; tear it down only when retiring the project.
- **DynamoDB pipeline-metadata**: `PAY_PER_REQUEST`, ≤ 1 cent/month at smoke volumes.
- **SQS DLQ**: standard queue, free at smoke volumes.
