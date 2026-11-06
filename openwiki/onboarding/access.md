---
type: Onboarding
title: Onboarding and Access
description: Access groups a new data platform engineer requests in week one and what each grants, the Slack channels to join, and what to read first.
tags: [onboarding, access, groups, slack]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-6fa0e591d6f275aeb428d46e
    resource: repo://docs/onboarding/access-requests.md
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Onboarding and Access

Source: `docs/onboarding/access-requests.md`.

## Week one access

Request these groups in the access portal:

| Group | Grants |
| --- | --- |
| `dp-engineers` | Databricks workspace user, `USE` on the `lakehouse` catalog, Airflow viewer |
| `dp-snowflake-transform` | Snowflake role `TRANSFORMER` and `TRANSFORM_WH` usage |
| `dp-prefect-devs` | Prefect workspace developer |
| `dp-platform-admins` | Terraform apply approvals. Leads only. |

Production write access is never granted to individuals. Changes ship through pipelines.
See [Infrastructure Change Management](../operations/change-management.md).

## Slack channels

- `#dp-platform-help` for questions and missing connections
- `#dp-oncall` for incidents and the weekly handoff
- `#dp-data-quality-alerts` for Bigeye alerts

## Read next

1. [Quickstart](../quickstart.md)
2. [Data Platform Architecture](../architecture/overview.md)
3. [On-call](../operations/oncall.md)
