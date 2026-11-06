---
type: dataset
title: Commerce and reference tables
description: Owners, freshness SLAs, columns, and lineage for lakehouse.silver.orders, lakehouse.gold.daily_revenue,
  and lakehouse.silver.reference_codes.
tags:
- catalog
- orders
- revenue
- lineage
status: stable
sources:
- resource: catalog://lakehouse-catalog/lakehouse.gold.daily_revenue
- resource: catalog://lakehouse-catalog/lakehouse.silver.orders
- resource: catalog://lakehouse-catalog/lakehouse.silver.reference_codes
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:20:00+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:20:00+00:00'
---

# Commerce and reference tables

Table metadata comes from the Unity Catalog export.

```mermaid
flowchart LR
  raw["landing.orders_raw"] --> orders["lakehouse.silver.orders"]
  orders --> rev["lakehouse.gold.daily_revenue"]
  sftp["vendor_sftp.code_sets"] --> ref["lakehouse.silver.reference_codes"]
```

## lakehouse.silver.orders

- Owner `data-platform-eng`. Tier 1. Freshness SLA 26 hours.
- One row per order, merged daily by `silver_orders_merge` ([orders_ingest](../orchestration/airflow.md#orders_ingest)).
- Columns: `order_id` (primary key), `customer_key` (surrogate key, not PII), `order_ts` (UTC),
  `amount` (USD), `status` (placed, shipped, cancelled).

## lakehouse.gold.daily_revenue

- Owner `analytics-eng`. Tier 1. Freshness SLA 30 hours.
- Revenue by day and status. Built in Snowflake by `GOLD.BUILD_DAILY_REVENUE` and mirrored.

## lakehouse.silver.reference_codes

- Owner `data-platform-eng`. Tier 2. Freshness SLA 192 hours (8 days).
- Vendor code sets refreshed weekly by [reference-data-refresh](../orchestration/prefect.md#reference-data-refresh).
