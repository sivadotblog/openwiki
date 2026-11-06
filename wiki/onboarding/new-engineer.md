---
type: onboarding
title: New engineer onboarding
description: Access groups to request in week one, Slack channels to join, and the no-individual-prod-write
  rule.
tags:
- onboarding
- access
status: stable
sources:
- resource: src://team-docs/onboarding/access-requests.md
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
---

# New engineer onboarding

## Week one access

Request these groups in the access portal:

| Group | What it grants |
| --- | --- |
| `dp-engineers` | Databricks workspace user, `lakehouse` catalog USE, Airflow viewer |
| `dp-snowflake-transform` | Snowflake role TRANSFORMER and `TRANSFORM_WH` usage |
| `dp-prefect-devs` | Prefect workspace developer |
| `dp-platform-admins` | Terraform apply approvals. Leads only. |

Production write access is never granted to individuals. Changes ship through pipelines
([change management](../governance/change-management.md)).

## Slack

Join `#dp-platform-help`, `#dp-oncall`, and `#dp-data-quality-alerts`.

## Read next

1. [Databricks](../platforms/databricks.md) and [Snowflake](../platforms/snowflake.md)
2. [Airflow](../orchestration/airflow.md), [Prefect](../orchestration/prefect.md), and [ADR-003](../governance/adr-003-prefect-for-new-pipelines.md)
3. [On-call](../runbooks/oncall.md)
