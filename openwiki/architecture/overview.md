---
type: Architecture
title: Data Platform Architecture
description: End-to-end view of the data platform. Databricks lakehouse, Snowflake warehouses, Airflow and Prefect orchestration, Bigeye monitoring, and the path from landing files to gold tables.
tags: [architecture, databricks, snowflake, airflow, prefect, bigeye, lineage]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-7f4abc321e337592a937097a
    resource: repo://catalog/unity_catalog_export.json
  - id: openwiki-source-4446a1abb0d28405ec4bfb89
    resource: repo://docs/decisions/adr-003-prefect-for-new-pipelines.md
  - id: openwiki-source-20169f6e4dbf1977aa60b153
    resource: repo://orchestration/airflow/dags/orders_ingest.py
  - id: openwiki-source-1cb10e597b0e3271f22ccbea
    resource: repo://orchestration/README.md
  - id: openwiki-source-4f5c72f8067c7832ed9fedc0
    resource: repo://platform-infra/bigeye/monitors.yml
  - id: openwiki-source-d20e6f36edb08fabf7cda47f
    resource: repo://platform-infra/README.md
  - id: openwiki-source-3ee5b145f908a0729746d8c8
    resource: repo://platform-infra/terraform/databricks/workspace.tf
  - id: openwiki-source-178a531d070990870b315117
    resource: repo://platform-infra/terraform/snowflake/warehouses.tf
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Data Platform Architecture

The platform has four layers. Storage and compute run on Databricks and Snowflake.
Orchestration runs on Airflow and Prefect. Bigeye monitors the data. Terraform and config
files in `platform-infra/` define the infrastructure.

## Components

| Component | Role | Defined in |
| --- | --- | --- |
| Databricks Unity Catalog | Metastore and the `lakehouse` catalog with bronze, silver, and gold schemas | `platform-infra/terraform/databricks/workspace.tf` |
| Databricks jobs | Spark merges into silver tables, run under the `jobs-standard` policy | same file |
| Snowflake `TRANSFORM_WH` | dbt and Airflow loads | `platform-infra/terraform/snowflake/warehouses.tf` |
| Snowflake `BI_WH` | Dashboards and analyst queries | same file |
| Airflow (`dp-airflow-prod`) | Existing pipelines, including tier-1 `orders_ingest` | `orchestration/airflow/dags/` |
| Prefect (`dp-k8s-pool`) | All new pipelines | `orchestration/prefect/` |
| Bigeye | Freshness, volume, null, and duplicate monitors | `platform-infra/bigeye/monitors.yml` |

## Data flow

<!-- openwiki: mermaid parse failed and this diagram was converted to a text fence so it does not break rendering. Fix the diagram source and restore the mermaid fence. Parser error: Heuristic: an unescaped angle bracket inside a label breaks rendering; rephrase the label. -->
```text
flowchart LR
  landing["Landing zone<br/>/landing/orders/ds/_SUCCESS"] --> sensor["Airflow orders_ingest<br/>wait_for_landing"]
  sensor --> dbx["Databricks job<br/>silver_orders_merge"]
  dbx --> silver["lakehouse.silver.orders"]
  silver --> snow["Snowflake TRANSFORM_WH<br/>GOLD.BUILD_DAILY_REVENUE"]
  snow --> gold["lakehouse.gold.daily_revenue"]
  sftp["Vendor SFTP drop"] --> prefect["Prefect reference-data-refresh"]
  prefect --> ref["lakehouse.silver.reference_codes"]
  silver -.monitored.-> bigeye["Bigeye"]
  gold -.monitored.-> bigeye
  bigeye --> pd["PagerDuty dp-platform-oncall"]
```

The daily orders path is tier-1. It starts at 05:30 UTC and has a 4 hour SLA. The
reference data path is tier-2 and runs weekly. Details are in
[Airflow and the orders_ingest DAG](../orchestration/airflow-orders-ingest.md) and
[Prefect and the reference-data-refresh flow](../orchestration/prefect-reference-data.md).

## Two orchestrators

New pipelines go to Prefect. Existing Airflow DAGs stay until their owners migrate them,
and tier-1 DAGs move last. Both tools read connections such as `databricks_default` and
`snowflake_transform` from the same secrets backend. See
[ADR-003](../decisions/adr-003-prefect.md).

## Cost and safety controls

- Databricks cluster policies force the `cost_center = data-platform` tag and cap workers.
- Snowflake `TRANSFORM_WH` is tied to a monthly credit monitor that suspends it at 100 percent.
- Infrastructure changes ship only through pull requests. See
  [Infrastructure Change Management](../operations/change-management.md).

## Related pages

- [Databricks Lakehouse](../platforms/databricks.md)
- [Snowflake Warehouses](../platforms/snowflake.md)
- [Lakehouse Tables](../datasets/lakehouse-tables.md)
- [Data Quality Monitoring with Bigeye](../data-quality/bigeye-monitors.md)
