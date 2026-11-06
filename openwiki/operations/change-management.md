---
type: Operations
title: Infrastructure Change Management
description: How Terraform and Bigeye changes ship through platform-infra. Plan on every PR, one dp-platform-admins approval, apply from main, state in dp-tfstate, and no individual production write access.
tags: [terraform, change-management, platform-infra, governance]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-6fa0e591d6f275aeb428d46e
    resource: repo://docs/onboarding/access-requests.md
  - id: openwiki-source-bd40399435347d5ee9699a8e
    resource: repo://docs/runbooks/snowflake-warehouse-saturation.md
  - id: openwiki-source-d20e6f36edb08fabf7cda47f
    resource: repo://platform-infra/README.md
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Infrastructure Change Management

`platform-infra/` holds Terraform for [Databricks](../platforms/databricks.md) and
[Snowflake](../platforms/snowflake.md), plus Bigeye monitors
([Data Quality Monitoring with Bigeye](../data-quality/bigeye-monitors.md)).

## How a change ships

1. Open a pull request. `terraform plan` runs on every PR.
2. Get one approval from `dp-platform-admins`.
3. Merge to `main`. `terraform apply` runs from the `main` branch pipeline.

Terraform state lives in the `dp-tfstate` storage account, one state file per workspace.

## Rules

- Production write access is never granted to individuals. Changes ship through pipelines.
- Only leads are in `dp-platform-admins`, the group that approves applies.
- An emergency change made by hand, such as adding a cluster in
  [Runbook: Snowflake Warehouse Saturation](runbooks/snowflake-warehouse-saturation.md),
  must be followed by a PR that makes it permanent or reverts it.
