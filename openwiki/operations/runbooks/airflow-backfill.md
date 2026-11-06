---
type: Runbook
title: "Runbook: Airflow Backfill"
description: How to re-run a date range for an Airflow DAG such as orders_ingest. Pause, clear, batch by 7 days, watch Bigeye freshness, unpause, and announce.
tags: [runbook, airflow, backfill, oncall]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-d22be3a02877334445a4c79c
    resource: repo://docs/oncall.md
  - id: openwiki-source-7bee04a12f8a089b8a1923d3
    resource: repo://docs/runbooks/airflow-backfill.md
  - id: openwiki-source-20169f6e4dbf1977aa60b153
    resource: repo://orchestration/airflow/dags/orders_ingest.py
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Runbook: Airflow Backfill

Source: `docs/runbooks/airflow-backfill.md`. Use it when a DAG missed runs or produced bad
data for a range of dates.

## Steps

1. Pause the DAG in the UI so the scheduler does not compete with the backfill.
2. Clear the affected task instances, for example:

   ```sh
   airflow tasks clear orders_ingest -s 2026-10-01 -e 2026-10-03 --yes
   ```

3. For more than 7 days, run backfills in batches of 7 days. `orders_ingest` has
   `max_active_runs=1`, so its runs execute one at a time
   ([Airflow and the orders_ingest DAG](../../orchestration/airflow-orders-ingest.md)).
4. Watch Bigeye freshness on the downstream tables until it is green
   ([Data Quality Monitoring with Bigeye](../../data-quality/bigeye-monitors.md)).
5. Unpause the DAG and post the date range in `#dp-oncall`.

## After

List any backfill that is still running in the Monday handoff note ([On-call](../oncall.md)).
