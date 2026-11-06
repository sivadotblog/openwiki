---
type: Operations
title: Data Quality Monitoring with Bigeye
description: Bigeye monitors defined as code, their thresholds on lakehouse.silver.orders and lakehouse.gold.daily_revenue, alert routing to Slack and PagerDuty, and how they match table SLAs.
tags: [bigeye, data-quality, monitoring, alerts, freshness]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-7f4abc321e337592a937097a
    resource: repo://catalog/unity_catalog_export.json
  - id: openwiki-source-d22be3a02877334445a4c79c
    resource: repo://docs/oncall.md
  - id: openwiki-source-7bee04a12f8a089b8a1923d3
    resource: repo://docs/runbooks/airflow-backfill.md
  - id: openwiki-source-4f5c72f8067c7832ed9fedc0
    resource: repo://platform-infra/bigeye/monitors.yml
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Data Quality Monitoring with Bigeye

Bigeye monitors are defined as code in `platform-infra/bigeye/monitors.yml` (Bigconfig).
They ship through the same pull request flow as Terraform
([Infrastructure Change Management](../operations/change-management.md)).

## Monitors

| Table | Metric | Threshold |
| --- | --- | --- |
| `lakehouse.silver.orders` | Freshness | at most 26 hours |
| `lakehouse.silver.orders` | Row count | autothreshold, medium sensitivity |
| `lakehouse.silver.orders.order_id` | Percent null | 0 |
| `lakehouse.silver.orders.order_id` | Duplicates | 0 |
| `lakehouse.gold.daily_revenue` | Freshness | at most 30 hours |

The freshness limits match the SLAs in the catalog: 26 hours for orders and 30 hours for
daily revenue. See [Lakehouse Tables](../datasets/lakehouse-tables.md).

## Alert routing

Every monitor notifies two channels:

- Slack `#dp-data-quality-alerts`
- PagerDuty service `dp-platform-oncall`

A monitor that fires on a gold table is a SEV2. See [On-call](../operations/oncall.md).

## Gaps

`lakehouse.silver.reference_codes` has no Bigeye monitor in `monitors.yml`.

## Related

- After a backfill, watch Bigeye freshness until it is green.
  See [Runbook: Airflow Backfill](../operations/runbooks/airflow-backfill.md).
