---
type: Decision
title: "ADR-003: Prefect for New Pipelines"
description: Accepted decision that new pipelines are Prefect 3 flows while existing Airflow DAGs migrate over time, tier-1 last, and what that means for on-call.
tags: [adr, decision, prefect, airflow, orchestration]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-4446a1abb0d28405ec4bfb89
    resource: repo://docs/decisions/adr-003-prefect-for-new-pipelines.md
  - id: openwiki-source-20169f6e4dbf1977aa60b153
    resource: repo://orchestration/airflow/dags/orders_ingest.py
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# ADR-003: Prefect for New Pipelines

Status: accepted in 2025-09. Source: `docs/decisions/adr-003-prefect-for-new-pipelines.md`.

## Why

- Airflow passed 400 DAGs.
- Scheduler latency reached several minutes during the 05:00 to 07:00 UTC peak.
- Python-native flows with dynamic tasks were hard to express as DAGs.

## Decision

- All new pipelines are Prefect 3 flows on the `dp-k8s-pool` work pool. See
  [Prefect and the reference-data-refresh flow](../orchestration/prefect-reference-data.md).
- Existing Airflow DAGs stay until their owning team migrates them.
- Tier-1 DAGs migrate last. `orders_ingest` is tier-1, so it stays on Airflow for now. See
  [Airflow and the orders_ingest DAG](../orchestration/airflow-orders-ingest.md).

## Consequences

- Two orchestrators run in parallel through at least 2026.
- On-call must know both tools. See [On-call](../operations/oncall.md).
- Shared connections live in the secrets backend, so both tools use the same credentials path.
