# Databricks workspace and Unity Catalog for the data platform.
# Sample source for the dpwiki prototype. Values are illustrative.

resource "databricks_metastore" "primary" {
  name          = "dp-primary-metastore"
  storage_root  = "abfss://metastore@dpplatformlake.dfs.core.windows.net/"
  region        = "eastus2"
  force_destroy = false
}

resource "databricks_catalog" "lakehouse" {
  metastore_id = databricks_metastore.primary.id
  name         = "lakehouse"
  comment      = "Curated bronze, silver and gold schemas owned by platform domains"
  owner        = "dp-platform-admins"
}

resource "databricks_cluster_policy" "jobs_standard" {
  name = "jobs-standard"
  definition = jsonencode({
    "spark_version" : { "type" : "regex", "pattern" : "15\\.[0-9]+\\.x-scala.*" },
    "autotermination_minutes" : { "type" : "fixed", "value" : 20 },
    "node_type_id" : { "type" : "allowlist", "values" : ["Standard_D8ds_v5", "Standard_D16ds_v5"] },
    "autoscale.max_workers" : { "type" : "range", "maxValue" : 16 },
    "custom_tags.cost_center" : { "type" : "fixed", "value" : "data-platform" }
  })
}

resource "databricks_cluster_policy" "interactive_small" {
  name = "interactive-small"
  definition = jsonencode({
    "autotermination_minutes" : { "type" : "range", "maxValue" : 60, "defaultValue" : 30 },
    "autoscale.max_workers" : { "type" : "range", "maxValue" : 4 },
    "custom_tags.cost_center" : { "type" : "fixed", "value" : "data-platform" }
  })
}

resource "databricks_sql_endpoint" "bi_serving" {
  name                      = "bi-serving"
  cluster_size              = "Medium"
  min_num_clusters          = 1
  max_num_clusters          = 4
  auto_stop_mins            = 15
  enable_serverless_compute = true
}
