---
type: platform
title: Prefect
description: Prefect 3 is the default orchestrator for new pipelines; covers the dp-k8s-pool work pool
  and the reference-data-refresh flow.
tags:
- prefect
- orchestration
- kubernetes
owner: data-platform-eng
status: stable
sources:
- resource: src://orchestration/prefect/flows/reference_data_refresh.py
- resource: src://orchestration/prefect/prefect.yaml
- resource: src://team-docs/decisions/adr-003-prefect-for-new-pipelines.md
- resource: src://team-docs/onboarding/access-requests.md
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:20:00+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:20:00+00:00'
---

# Prefect

All new pipelines are Prefect 3 flows ([ADR-003](../governance/adr-003-prefect-for-new-pipelines.md)).
Flows run on the Kubernetes work pool `dp-k8s-pool`. Deployments are declared in
`orchestration/prefect/prefect.yaml`.

## reference-data-refresh

Pulls vendor code sets from the SFTP drop, validates them, and merges them into
`lakehouse.silver.reference_codes` on `(code_system, code)`.

| Setting | Value |
| --- | --- |
| Deployment | `reference-data-refresh-weekly` |
| Schedule | Mondays 06:00 America/New_York |
| Tier | tier-2 |
| Image | `prefect-flows:2026.10`, 1 CPU, 4Gi memory |
| Timeout | 2 hours |
| Fetch retries | 4, exponential backoff |
| Validation | rejects a file whose row count drops more than 20 percent from the previous drop |

A failure here is a SEV2 (tier-2). See [On-call](../runbooks/oncall.md).

## Access

Request `dp-prefect-devs` for developer access to the Prefect workspace.
