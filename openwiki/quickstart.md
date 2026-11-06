---
type: Quickstart
title: Quickstart
description: Start here. What this data platform repository contains, how the pieces connect, and which wiki page answers which question.
tags: [quickstart, onboarding, data-platform, navigation]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-20169f6e4dbf1977aa60b153
    resource: repo://orchestration/airflow/dags/orders_ingest.py
  - id: openwiki-source-02b3077f1259958cb5576485
    resource: repo://orchestration/prefect/prefect.yaml
  - id: openwiki-source-4f5c72f8067c7832ed9fedc0
    resource: repo://platform-infra/bigeye/monitors.yml
  - id: openwiki-source-d20e6f36edb08fabf7cda47f
    resource: repo://platform-infra/README.md
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Quickstart

This repository holds the code and docs for a small data platform. The wiki explains how
it is built and how to run it day to day.

## What is in the repository

| Folder | What it holds |
| --- | --- |
| `platform-infra/` | Terraform for Databricks and Snowflake, and Bigeye monitors as code |
| `orchestration/` | Airflow DAGs and Prefect flows with their deployments |
| `docs/` | On-call guide, runbooks, onboarding, and decision records |
| `catalog/` | A Unity Catalog export with table owners, tiers, and freshness SLAs |

## The platform in one paragraph

Orders land in a landing zone. The Airflow DAG `orders_ingest` waits for the landing
files, runs a Databricks job that merges them into `lakehouse.silver.orders`, and then
builds the gold revenue table in Snowflake on `TRANSFORM_WH`. A Prefect flow refreshes
vendor reference codes every week. Bigeye watches freshness and quality on the key tables
and pages the on-call rotation. See [Data Platform Architecture](architecture/overview.md).

## Where to go

| I need to | Read |
| --- | --- |
| Get access in my first week | [Onboarding and Access](onboarding/access.md) |
| Understand the whole platform | [Data Platform Architecture](architecture/overview.md) |
| Know Databricks limits and policies | [Databricks Lakehouse](platforms/databricks.md) |
| Know Snowflake sizes and credit limits | [Snowflake Warehouses](platforms/snowflake.md) |
| Debug the daily orders pipeline | [Airflow and the orders_ingest DAG](orchestration/airflow-orders-ingest.md) |
| Debug the reference data refresh | [Prefect and the reference-data-refresh flow](orchestration/prefect-reference-data.md) |
| Decide where a new pipeline goes | [ADR-003: Prefect for New Pipelines](decisions/adr-003-prefect.md) |
| Find a table owner or SLA | [Lakehouse Tables](datasets/lakehouse-tables.md) |
| Understand a data quality alert | [Data Quality Monitoring with Bigeye](data-quality/bigeye-monitors.md) |
| Handle a page | [On-call](operations/oncall.md) |
| Fix queued Snowflake queries | [Runbook: Snowflake Warehouse Saturation](operations/runbooks/snowflake-warehouse-saturation.md) |
| Re-run a date range | [Runbook: Airflow Backfill](operations/runbooks/airflow-backfill.md) |
| Change infrastructure | [Infrastructure Change Management](operations/change-management.md) |
