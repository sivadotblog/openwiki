---
type: workflow
title: How infrastructure changes ship
description: Terraform plan on every PR, apply from main after a dp-platform-admins approval, and where
  state lives.
tags:
- terraform
- change-management
owner: dp-platform-admins
status: stable
sources:
- resource: src://platform-infra/README.md
- resource: src://team-docs/onboarding/access-requests.md
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
---

# How infrastructure changes ship

`platform-infra` holds Terraform for [Databricks](../platforms/databricks.md) and
[Snowflake](../platforms/snowflake.md), and Bigeye config for [data quality](data-quality.md).

1. Open a pull request. `terraform plan` runs on every PR.
2. Get one approval from `dp-platform-admins`.
3. Merge. `terraform apply` runs from the `main` branch pipeline.

State lives in the `dp-tfstate` storage account, one state file per workspace.

Production write access is never granted to individuals, so emergency changes made by hand
(for example in the [Snowflake saturation runbook](../runbooks/snowflake-warehouse-saturation.md))
must be followed by a PR that makes them permanent or reverts them.
