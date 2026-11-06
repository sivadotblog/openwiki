---
type: Platform
title: Snowflake Warehouses
description: Sizing and scaling of TRANSFORM_WH and BI_WH, the TRANSFORM_MONTHLY credit monitor, and what stops when the monitor suspends the transform warehouse.
tags: [snowflake, warehouses, resource-monitor, cost, terraform]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-6fa0e591d6f275aeb428d46e
    resource: repo://docs/onboarding/access-requests.md
  - id: openwiki-source-20169f6e4dbf1977aa60b153
    resource: repo://orchestration/airflow/dags/orders_ingest.py
  - id: openwiki-source-178a531d070990870b315117
    resource: repo://platform-infra/terraform/snowflake/warehouses.tf
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Snowflake Warehouses

Snowflake runs transformation loads and BI queries. Warehouses and the resource monitor
are defined in `platform-infra/terraform/snowflake/warehouses.tf`.

## Warehouses

| Warehouse | Size | Clusters | Scaling policy | Auto-suspend | Used for |
| --- | --- | --- | --- | --- | --- |
| `TRANSFORM_WH` | LARGE | 1 to 3 | STANDARD | 120 seconds | dbt and Airflow loads, owned by `data-platform-eng` |
| `BI_WH` | MEDIUM | 1 to 6 | ECONOMY | 60 seconds | Dashboards and analyst queries |

Both warehouses resume automatically when a query arrives.

## Credit monitor

`TRANSFORM_WH` is attached to the resource monitor `TRANSFORM_MONTHLY`.

- Quota: 4000 credits per month.
- Notifications at 75 and 90 percent.
- Suspension at 100 percent.

When the monitor suspends `TRANSFORM_WH`, Snowflake loads stop. That includes the
`gold_daily_revenue` task in [orders_ingest](../orchestration/airflow-orders-ingest.md),
which runs on this warehouse.

`BI_WH` has no resource monitor in the Terraform.

## Operating it

- Queued queries: [Runbook: Snowflake Warehouse Saturation](../operations/runbooks/snowflake-warehouse-saturation.md).
- Resizing or changing limits: open a PR. See [Infrastructure Change Management](../operations/change-management.md).
- Access: the `dp-snowflake-transform` group grants role `TRANSFORMER` and `TRANSFORM_WH` usage.
