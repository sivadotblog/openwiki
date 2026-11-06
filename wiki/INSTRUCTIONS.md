---
type: reference
title: Wiki charter
description: What this wiki covers, who it is for, and the rules the maintaining agent follows.
---

# Data Platform Team Wiki: charter

This wiki is maintained by an agent and reviewed by the team through pull requests.
Humans own this file. The agent reads it on every run.

## Audience

1. Engineers on the data platform team, especially whoever is on call.
2. Engineers on consuming teams who need to know how to use the platform.
3. Coding agents (Claude Code and others) that query the wiki over MCP.

## Scope

- Platforms: Databricks (workspace, Unity Catalog, cluster policies, SQL warehouses) and
  Snowflake (warehouses, resource monitors). How they are configured and why.
- Orchestration: Airflow and Prefect. Which pipelines run where, schedules, retries, SLAs,
  and the migration direction set by ADR-003.
- Governance and data quality: Bigeye monitors, alert routing, ownership.
- Runbooks: step-by-step operational procedures. Keep commands exact.
- Catalog: tier-1 and tier-2 datasets, owners, freshness SLAs, lineage.
- Onboarding: access, channels, first-week tasks.

## Rules

- Every page must be grounded in a source. If the sources do not say it, the wiki does not say it.
- Prefer one page per durable topic. Link instead of repeating.
- Keep runbook steps in the order of the source runbook. Do not add steps that are not in a source.
- Name owners, schedules, thresholds, and SLAs explicitly. These are the facts people look up.
- Never copy secrets, credentials, or personal data, even if a source contains them.
- Mark pages `status: deprecated` instead of deleting them when a platform is being retired.
