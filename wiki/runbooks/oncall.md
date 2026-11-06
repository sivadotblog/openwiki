---
type: runbook
title: On-call
description: The dp-platform-oncall rotation, severity definitions, response times, and the Monday handoff.
tags:
- oncall
- pagerduty
- severity
owner: dp-platform-oncall
status: stable
sources:
- resource: src://team-docs/oncall.md
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:20:00+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:20:00+00:00'
---

# On-call

The rotation is `dp-platform-oncall` in PagerDuty. Shifts are one week, Monday 10:00 ET to
the next Monday 10:00 ET, with a primary and a secondary. Because of
[ADR-003](../governance/adr-003-prefect-for-new-pipelines.md), on-call covers both
[Airflow](../orchestration/airflow.md) and [Prefect](../orchestration/prefect.md).

## Severity

| Severity | Trigger | Response |
| --- | --- | --- |
| SEV1 | A tier-1 pipeline misses its SLA, or a production warehouse is down | Page primary now. Secondary joins after 15 minutes without ack. |
| SEV2 | A tier-2 pipeline fails, or a data quality monitor fires on a gold table | Within 4 business hours |
| SEV3 | Anything else | Weekly triage |

## Handoff

Every Monday post a note in `#dp-oncall` with open incidents, silenced monitors, and pending backfills.

## Runbooks

- [Snowflake warehouse saturation](snowflake-warehouse-saturation.md)
- [Airflow backfill](airflow-backfill.md)
