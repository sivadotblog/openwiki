# Runbook: Snowflake warehouse saturation

Symptoms: queries queue on TRANSFORM_WH or BI_WH, Airflow Snowflake tasks run long,
dashboard latency alerts.

1. Check queueing: `select * from table(information_schema.warehouse_load_history(date_range_start=>dateadd('hour',-2,current_timestamp()))) where warehouse_name = 'TRANSFORM_WH';`
2. If `avg_queued_load` > 1 for 15 minutes, temporarily raise `max_cluster_count` by one
   with `alter warehouse TRANSFORM_WH set max_cluster_count = 4;` and open a PR in
   platform-infra to make it permanent or revert it.
3. Find the heaviest queries in `snowflake.account_usage.query_history` and contact the owner.
4. If the resource monitor is above 90 percent of quota, tell #dp-oncall before resizing.
   At 100 percent the monitor suspends TRANSFORM_WH.

Do not resize warehouses above LARGE without approval from the platform lead.
