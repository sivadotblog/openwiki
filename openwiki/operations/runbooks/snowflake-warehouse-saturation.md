---
type: Runbook
title: "Runbook: Snowflake Warehouse Saturation"
description: Symptoms, the load history query, the add-a-cluster mitigation, finding heavy queries, credit monitor escalation, and the resize guardrail for queued Snowflake warehouses.
tags: [runbook, snowflake, oncall, performance]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-bd40399435347d5ee9699a8e
    resource: repo://docs/runbooks/snowflake-warehouse-saturation.md
  - id: openwiki-source-178a531d070990870b315117
    resource: repo://platform-infra/terraform/snowflake/warehouses.tf
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Runbook: Snowflake Warehouse Saturation

Source: `docs/runbooks/snowflake-warehouse-saturation.md`. Warehouse settings are on
[Snowflake Warehouses](../../platforms/snowflake.md).

## Symptoms

- Queries queue on `TRANSFORM_WH` or `BI_WH`.
- Airflow Snowflake tasks run long, for example `gold_daily_revenue`.
- Dashboard latency alerts.

## Steps

1. Check queueing over the last 2 hours:

   ```sql
   select * from table(information_schema.warehouse_load_history(
     date_range_start=>dateadd('hour',-2,current_timestamp())))
   where warehouse_name = 'TRANSFORM_WH';
   ```

2. If `avg_queued_load` is above 1 for 15 minutes, raise `max_cluster_count` by one:

   ```sql
   alter warehouse TRANSFORM_WH set max_cluster_count = 4;
   ```

   Terraform sets it to 3 today, so this is the step from 3 to 4. Then open a PR in
   `platform-infra` to make the change permanent or revert it
   ([Infrastructure Change Management](../change-management.md)).
3. Find the heaviest queries in `snowflake.account_usage.query_history` and contact the owner.
4. If the resource monitor is above 90 percent of quota, tell `#dp-oncall` before resizing.
   At 100 percent the monitor suspends `TRANSFORM_WH`.

## Guardrail

Do not resize a warehouse above LARGE without approval from the platform lead.
