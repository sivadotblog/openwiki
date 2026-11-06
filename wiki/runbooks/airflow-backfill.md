---
type: runbook
title: Airflow backfill
description: 'How to re-run a date range for an Airflow DAG: pause, clear, batch by 7 days, watch Bigeye,
  unpause, announce.'
tags:
- airflow
- runbook
- backfill
owner: dp-platform-oncall
status: stable
sources:
- resource: src://orchestration/airflow/dags/orders_ingest.py
- resource: src://team-docs/oncall.md
- resource: src://team-docs/runbooks/airflow-backfill.md
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
---

# Airflow backfill

Use when a DAG missed runs or produced bad data for a range of dates.

## Steps

1. Pause the DAG in the UI so the scheduler does not compete with the backfill.
2. Clear the affected task instances, for example:
   `airflow tasks clear orders_ingest -s 2026-10-01 -e 2026-10-03 --yes`
3. For more than 7 days, run in batches of 7 days. [orders_ingest](../orchestration/airflow.md#orders_ingest)
   has `max_active_runs=1`, so runs execute one at a time.
4. Watch Bigeye freshness on the downstream tables until it is green ([data quality](../governance/data-quality.md)).
5. Unpause the DAG and post the date range in `#dp-oncall`.

Mention any backfill still running in the Monday [on-call handoff](oncall.md#handoff).
