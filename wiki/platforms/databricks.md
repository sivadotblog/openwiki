---
type: platform
title: Databricks
description: Databricks workspace, Unity Catalog metastore, cluster policies, and the BI SQL warehouse.
tags:
- databricks
- unity-catalog
- terraform
owner: dp-platform-admins
status: stable
sources:
- resource: src://orchestration/airflow/dags/orders_ingest.py
- resource: src://platform-infra/terraform/databricks/workspace.tf
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
---

# Databricks

Databricks runs the lakehouse: Spark jobs that build bronze and silver tables, and a
serverless SQL warehouse for BI. Everything here is managed in Terraform in
`platform-infra/terraform/databricks`. See [How infrastructure changes ship](../governance/change-management.md).

## Unity Catalog

- Metastore `dp-primary-metastore` in `eastus2`, rooted in the `dpplatformlake` storage account.
- Catalog `lakehouse` holds the curated bronze, silver, and gold schemas. Owner is `dp-platform-admins`.
- Table-level ownership and SLAs are in the [catalog pages](../catalog/commerce-tables.md).

## Cluster policies

| Policy | Use | Key limits |
| --- | --- | --- |
| `jobs-standard` | Scheduled jobs | Runtime 15.x, auto-terminate fixed at 20 min, max 16 workers, D8ds_v5 or D16ds_v5 nodes |
| `interactive-small` | Notebooks | Auto-terminate up to 60 min (default 30), max 4 workers |

Both policies force the tag `cost_center = data-platform`, so all spend is attributed to the platform.

## SQL warehouse

`bi-serving` is a serverless Medium warehouse that scales from 1 to 4 clusters and stops
after 15 idle minutes.

## Who calls it

The [orders_ingest DAG](../orchestration/airflow.md#orders_ingest) triggers the
`silver_orders_merge` job through the `databricks_default` connection.
