# Runbook: Airflow backfill

Use when a DAG missed runs or produced bad data for a range of dates.

1. Pause the DAG in the UI so the scheduler does not compete with the backfill.
2. Clear the affected task instances: `airflow tasks clear orders_ingest -s 2026-10-01 -e 2026-10-03 --yes`
3. For more than 7 days, run backfills in batches of 7 days. `max_active_runs=1` means runs are serial.
4. Watch Bigeye freshness on the downstream tables until it is green.
5. Unpause the DAG and post the date range in #dp-oncall.
