---
type: decision
title: 'ADR-003: Prefect for new pipelines'
description: Accepted decision that new pipelines use Prefect 3 while existing Airflow DAGs migrate over
  time, tier-1 last.
tags:
- adr
- prefect
- airflow
status: stable
sources:
- resource: src://team-docs/decisions/adr-003-prefect-for-new-pipelines.md
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:07:53+00:00'
---

# ADR-003: Prefect for new pipelines

Accepted in 2025-09.

## Why

Airflow passed 400 DAGs and scheduler latency during the 05:00 to 07:00 UTC peak reached
several minutes. Dynamic, Python-native flows were hard to express as DAGs.

## What was decided

- New pipelines are Prefect 3 flows on `dp-k8s-pool`. See [Prefect](../orchestration/prefect.md).
- Existing [Airflow](../orchestration/airflow.md) DAGs stay until their owning team migrates them.
- Tier-1 DAGs migrate last.

## What it means day to day

Two orchestrators run in parallel through at least 2026, so on-call needs to know both.
Shared connections live in the secrets backend so both tools use the same credentials path.
