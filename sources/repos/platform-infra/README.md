# platform-infra

Terraform and config-as-code for the data platform.

- `terraform/databricks`: workspace, Unity Catalog metastore, cluster policies, SQL warehouses.
- `terraform/snowflake`: virtual warehouses and resource monitors.
- `bigeye/`: data quality monitors (Bigconfig).

Changes go through pull requests. `terraform plan` runs on every PR and `terraform apply`
runs from the `main` branch pipeline after one approval from `dp-platform-admins`.
State is stored in the `dp-tfstate` storage account with one state file per workspace.
