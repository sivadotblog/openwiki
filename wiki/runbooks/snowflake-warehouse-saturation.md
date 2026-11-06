---
type: runbook
title: Snowflake warehouse saturation
description: 'Steps when queries queue on TRANSFORM_WH or BI_WH: check load history, add a cluster, find
  heavy queries, watch the credit monitor.'
tags:
- snowflake
- runbook
- oncall
owner: dp-platform-oncall
status: stable
sources:
- resource: src://platform-infra/terraform/snowflake/warehouses.tf
- resource: src://team-docs/runbooks/snowflake-warehouse-saturation.md
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
---

# Snowflake warehouse saturation

**Symptoms:** queries queue on `TRANSFORM_WH` or `BI_WH`, Airflow Snowflake tasks run long,
dashboard latency alerts. Warehouse settings are on the [Snowflake](../platforms/snowflake.md) page.

## Steps

1. Check queueing for the last two hours:
   ```sql
   select * from table(information_schema.warehouse_load_history(
     date_range_start=>dateadd('hour',-2,current_timestamp())))
   where warehouse_name = 'TRANSFORM_WH';
   ```
2. If `avg_queued_load` is above 1 for 15 minutes, add one cluster:
   `alter warehouse TRANSFORM_WH set max_cluster_count = 4;`
   Then open a PR in `platform-infra` to make it permanent or revert it
   ([change management](../governance/change-management.md)).
3. Find the heaviest queries in `snowflake.account_usage.query_history` and contact the owner.
4. If `TRANSFORM_MONTHLY` is above 90 percent of quota, tell `#dp-oncall` before resizing.
   At 100 percent the monitor suspends `TRANSFORM_WH`.

## Guardrail

Do not resize warehouses above LARGE without approval from the platform lead.
