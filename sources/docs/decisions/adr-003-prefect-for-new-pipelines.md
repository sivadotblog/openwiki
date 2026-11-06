# ADR-003: Prefect for new pipelines

Status: accepted (2025-09)

## Context

Airflow DAG count passed 400 and scheduler latency during the 05:00 to 07:00 UTC peak
reached several minutes. Python-native flows with dynamic tasks were hard to express.

## Decision

All new pipelines are written as Prefect 3 flows on the `dp-k8s-pool` work pool.
Existing Airflow DAGs stay until their owning team migrates them. Tier-1 DAGs migrate last.

## Consequences

Two orchestrators run in parallel for at least 2026. On-call must know both.
Shared connections live in the secrets backend so both tools use the same credentials path.
