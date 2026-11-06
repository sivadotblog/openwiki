---
type: Platform
title: Databricks Lakehouse
description: Unity Catalog metastore and the lakehouse catalog, the jobs-standard and interactive-small cluster policies, the bi-serving SQL warehouse, and cost tagging.
tags: [databricks, unity-catalog, cluster-policy, sql-warehouse, terraform]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-6fa0e591d6f275aeb428d46e
    resource: repo://docs/onboarding/access-requests.md
  - id: openwiki-source-20169f6e4dbf1977aa60b153
    resource: repo://orchestration/airflow/dags/orders_ingest.py
  - id: openwiki-source-3ee5b145f908a0729746d8c8
    resource: repo://platform-infra/terraform/databricks/workspace.tf
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Databricks Lakehouse

Databricks runs the lakehouse. All of it is defined in
`platform-infra/terraform/databricks/workspace.tf` and changed through pull requests
([Infrastructure Change Management](../operations/change-management.md)).

## Unity Catalog

- Metastore `dp-primary-metastore` in region `eastus2`. Its storage root is the
  `metastore` container in the `dpplatformlake` storage account. `force_destroy` is off.
- Catalog `lakehouse` holds the curated bronze, silver, and gold schemas. Its owner is
  `dp-platform-admins`.
- Table owners, tiers, and SLAs are listed in [Lakehouse Tables](../datasets/lakehouse-tables.md).

## Cluster policies

| Policy | For | Limits |
| --- | --- | --- |
| `jobs-standard` | Scheduled jobs | Runtime 15.x only, auto-terminate fixed at 20 minutes, `Standard_D8ds_v5` or `Standard_D16ds_v5` nodes, at most 16 workers |
| `interactive-small` | Notebooks | Auto-terminate up to 60 minutes (default 30), at most 4 workers |

Both policies fix the tag `cost_center = data-platform`, so all cluster spend is charged
to the platform.

## SQL warehouse

`bi-serving` is a serverless SQL warehouse, size Medium. It scales from 1 to 4 clusters
and stops after 15 idle minutes.

## Who uses it

The Airflow DAG `orders_ingest` triggers the Databricks job `silver_orders_merge` through
the `databricks_default` connection. See
[Airflow and the orders_ingest DAG](../orchestration/airflow-orders-ingest.md).

## Access

The `dp-engineers` group grants workspace user and `USE` on the `lakehouse` catalog. See
[Onboarding and Access](../onboarding/access.md).
