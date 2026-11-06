---
type: Operations
title: On-call
description: The dp-platform-oncall PagerDuty rotation, shift times, SEV1 to SEV3 definitions and response times, and the Monday handoff note.
tags: [oncall, pagerduty, severity, incident-response]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-4446a1abb0d28405ec4bfb89
    resource: repo://docs/decisions/adr-003-prefect-for-new-pipelines.md
  - id: openwiki-source-d22be3a02877334445a4c79c
    resource: repo://docs/oncall.md
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# On-call

Source: `docs/oncall.md`.

## Rotation

- PagerDuty rotation: `dp-platform-oncall`.
- Shifts are one week, Monday 10:00 ET to the next Monday 10:00 ET.
- Each shift has a primary and a secondary.
- On-call covers both Airflow and Prefect ([ADR-003](../decisions/adr-003-prefect.md)).

## Severity

| Level | Trigger | Response |
| --- | --- | --- |
| SEV1 | A tier-1 pipeline (tag `tier-1`) misses its SLA, or a production warehouse is down | Page the primary at once. The secondary joins after 15 minutes without acknowledgement. |
| SEV2 | A tier-2 pipeline fails, or a data quality monitor fires on a gold table | Respond within 4 business hours |
| SEV3 | Anything else | Handle in the weekly triage |

Examples: an [orders_ingest](../orchestration/airflow-orders-ingest.md) SLA miss is SEV1.
A failed [reference-data-refresh](../orchestration/prefect-reference-data.md) run is SEV2.
A Bigeye alert on `lakehouse.gold.daily_revenue` is SEV2
([Data Quality Monitoring with Bigeye](../data-quality/bigeye-monitors.md)).

## Handoff

Every Monday, post a handoff note in `#dp-oncall` with:

- open incidents
- silenced monitors
- pending backfills

## Runbooks

- [Runbook: Snowflake Warehouse Saturation](runbooks/snowflake-warehouse-saturation.md)
- [Runbook: Airflow Backfill](runbooks/airflow-backfill.md)
