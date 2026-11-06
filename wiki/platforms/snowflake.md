---
type: platform
title: Snowflake
description: Snowflake warehouses TRANSFORM_WH and BI_WH, their scaling settings, and the monthly credit
  monitor.
tags:
- snowflake
- warehouses
- cost
owner: data-platform-eng
status: stable
sources:
- resource: src://platform-infra/terraform/snowflake/warehouses.tf
- resource: src://team-docs/onboarding/access-requests.md
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
---

# Snowflake

Snowflake serves transformation loads and BI queries. Warehouses and resource monitors
are defined in `platform-infra/terraform/snowflake/warehouses.tf`.

## Warehouses

| Warehouse | Size | Clusters | Scaling | Auto-suspend | Used by |
| --- | --- | --- | --- | --- | --- |
| `TRANSFORM_WH` | LARGE | 1 to 3 | STANDARD | 120 s | dbt and Airflow loads |
| `BI_WH` | MEDIUM | 1 to 6 | ECONOMY | 60 s | dashboards and analysts |

## Cost guardrail

`TRANSFORM_WH` is attached to the resource monitor `TRANSFORM_MONTHLY`: 4000 credits per
month, notifications at 75 and 90 percent, and suspension at 100 percent. When the monitor
suspends the warehouse, every Snowflake load stops, including
[gold_daily_revenue](../orchestration/airflow.md#orders_ingest).

## Operating it

- Queueing or slow loads: follow [Snowflake warehouse saturation](../runbooks/snowflake-warehouse-saturation.md).
- Access: request `dp-snowflake-transform`. See [New engineer onboarding](../onboarding/new-engineer.md).
