# Snowflake virtual warehouses and resource monitors.
# Sample source for the dpwiki prototype. Values are illustrative.

resource "snowflake_warehouse" "transform_wh" {
  name                = "TRANSFORM_WH"
  warehouse_size      = "LARGE"
  auto_suspend        = 120
  auto_resume         = true
  min_cluster_count   = 1
  max_cluster_count   = 3
  scaling_policy      = "STANDARD"
  resource_monitor    = snowflake_resource_monitor.transform_monthly.name
  comment             = "dbt and Airflow loads. Owned by data-platform-eng."
}

resource "snowflake_warehouse" "bi_wh" {
  name              = "BI_WH"
  warehouse_size    = "MEDIUM"
  auto_suspend      = 60
  auto_resume       = true
  min_cluster_count = 1
  max_cluster_count = 6
  scaling_policy    = "ECONOMY"
  comment           = "Dashboards and analyst queries."
}

resource "snowflake_resource_monitor" "transform_monthly" {
  name            = "TRANSFORM_MONTHLY"
  credit_quota    = 4000
  frequency       = "MONTHLY"
  notify_triggers = [75, 90]
  suspend_trigger = 100
}
