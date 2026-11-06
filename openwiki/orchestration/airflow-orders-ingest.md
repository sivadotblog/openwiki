---
type: Pipeline
title: Airflow and the orders_ingest DAG
description: The dp-airflow-prod environment and its connections, and the tier-1 orders_ingest DAG with its schedule, retries, SLA, landing sensor, and task chain.
tags: [airflow, orders_ingest, tier-1, pipeline, databricks, snowflake]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-d22be3a02877334445a4c79c
    resource: repo://docs/oncall.md
  - id: openwiki-source-20169f6e4dbf1977aa60b153
    resource: repo://orchestration/airflow/dags/orders_ingest.py
  - id: openwiki-source-1cb10e597b0e3271f22ccbea
    resource: repo://orchestration/README.md
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Airflow and the orders_ingest DAG

Airflow 2 runs on the managed environment `dp-airflow-prod`. Existing tier-1 pipelines
stay on Airflow until they are migrated. New pipelines go to Prefect
([ADR-003](../decisions/adr-003-prefect.md)).

Connections such as `databricks_default` and `snowflake_transform` come from the secrets
backend, never from DAG code. If a connection is missing, ask in `#dp-platform-help`.

## orders_ingest

Source: `orchestration/airflow/dags/orders_ingest.py`. The DAG moves orders from the
landing zone to Databricks silver and then to a Snowflake gold table.

<!-- openwiki: mermaid parse failed and this diagram was converted to a text fence so it does not break rendering. Fix the diagram source and restore the mermaid fence. Parser error: Heuristic: an unescaped angle bracket inside a label breaks rendering; rephrase the label. -->
```text
flowchart LR
  A["wait_for_landing<br/>FileSensor"] --> B["silver_orders<br/>Databricks silver_orders_merge"]
  B --> C["gold_daily_revenue<br/>Snowflake GOLD.BUILD_DAILY_REVENUE"]
```

| Setting | Value |
| --- | --- |
| Schedule | `30 5 * * *`, 05:30 UTC daily |
| Owner | `data-platform-eng` |
| Tags | `orders`, `tier-1` |
| Retries | 3, with 10 minutes between attempts |
| SLA | 4 hours |
| Catchup | off |
| Concurrent runs | 1 (`max_active_runs=1`) |
| Failure email | off |

### Tasks

1. `wait_for_landing` waits for `/landing/orders/{{ ds }}/_SUCCESS`. It checks every
   5 minutes, gives up after 3 hours, and frees its worker slot between checks
   (`mode="reschedule"`).
2. `silver_orders` runs the Databricks job `silver_orders_merge` with `run_date` set to the
   run date. It writes [lakehouse.silver.orders](../datasets/lakehouse-tables.md).
3. `gold_daily_revenue` runs `CALL GOLD.BUILD_DAILY_REVENUE('{{ ds }}')` on `TRANSFORM_WH`
   through `snowflake_transform`. It builds
   [lakehouse.gold.daily_revenue](../datasets/lakehouse-tables.md).

## When it breaks

- A tier-1 SLA miss is a SEV1. See [On-call](../operations/oncall.md).
- Landing files late: the sensor fails after 3 hours, then normal retries apply.
- `gold_daily_revenue` slow or stuck: check queueing and the credit monitor in
  [Runbook: Snowflake Warehouse Saturation](../operations/runbooks/snowflake-warehouse-saturation.md).
- Bad or missing dates: [Runbook: Airflow Backfill](../operations/runbooks/airflow-backfill.md).
  Because `max_active_runs=1`, backfilled runs execute one at a time.
