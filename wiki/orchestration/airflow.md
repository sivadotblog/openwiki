---
type: platform
title: Airflow
description: Airflow on dp-airflow-prod, the orders_ingest tier-1 DAG, and how Airflow relates to the
  Prefect migration.
tags:
- airflow
- orchestration
- tier-1
owner: data-platform-eng
status: stable
sources:
- resource: src://orchestration/README.md
- resource: src://orchestration/airflow/dags/orders_ingest.py
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
---

# Airflow

Airflow 2 runs on the managed environment `dp-airflow-prod`. Existing tier-1 pipelines stay
here until they migrate. New pipelines go to [Prefect](prefect.md) per
[ADR-003](../governance/adr-003-prefect-for-new-pipelines.md).

Connections such as `databricks_default` and `snowflake_transform` come from the secrets
backend, never from DAG code.

## orders_ingest

Tier-1 DAG that moves orders from the landing zone to Databricks silver and then to a
Snowflake gold table.

```mermaid
flowchart LR
  L["wait_for_landing\n/landing/orders/ds/_SUCCESS"] --> S["silver_orders\nDatabricks job silver_orders_merge"]
  S --> G["gold_daily_revenue\nCALL GOLD.BUILD_DAILY_REVENUE on TRANSFORM_WH"]
```

| Setting | Value |
| --- | --- |
| Schedule | `30 5 * * *` (05:30 UTC daily) |
| Owner | `data-platform-eng` |
| Retries | 3, 10 minutes apart |
| SLA | 4 hours |
| Concurrency | `max_active_runs=1`, `catchup=False` |
| Sensor | pokes every 5 minutes, times out after 3 hours, reschedule mode |

Outputs: [lakehouse.silver.orders and lakehouse.gold.daily_revenue](../catalog/commerce-tables.md).

## When it breaks

- Missed SLA on a tier-1 DAG is a SEV1. See [On-call](../runbooks/oncall.md).
- Re-running a date range: [Airflow backfill](../runbooks/airflow-backfill.md).
- Slow `gold_daily_revenue`: [Snowflake warehouse saturation](../runbooks/snowflake-warehouse-saturation.md).
