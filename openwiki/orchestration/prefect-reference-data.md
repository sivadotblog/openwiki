---
type: Pipeline
title: Prefect and the reference-data-refresh flow
description: How Prefect deployments run on the dp-k8s-pool work pool, and the weekly reference-data-refresh flow with its tasks, retries, validation rule, and resources.
tags: [prefect, reference-data, tier-2, pipeline, kubernetes]
verified:
  - by: openwiki/0.9.0
    at: 2026-11-06T00:45:25.143Z
sources:
  - id: openwiki-source-7f4abc321e337592a937097a
    resource: repo://catalog/unity_catalog_export.json
  - id: openwiki-source-d22be3a02877334445a4c79c
    resource: repo://docs/oncall.md
  - id: openwiki-source-4ad74d654e2e2f292fd04026
    resource: repo://orchestration/prefect/flows/reference_data_refresh.py
  - id: openwiki-source-02b3077f1259958cb5576485
    resource: repo://orchestration/prefect/prefect.yaml
  - id: openwiki-source-1cb10e597b0e3271f22ccbea
    resource: repo://orchestration/README.md
generated: { by: "claude-code", at: "2026-11-06T00:45:25.143Z" }
---

# Prefect and the reference-data-refresh flow

All new pipelines are Prefect 3 flows ([ADR-003](../decisions/adr-003-prefect.md)).
Flows run on the Kubernetes work pool `dp-k8s-pool`. Deployments are declared in
`orchestration/prefect/prefect.yaml` under the project `dp-orchestration` (Prefect 3.1.0).

## reference-data-refresh

Source: `orchestration/prefect/flows/reference_data_refresh.py`. The flow pulls vendor code
sets from an SFTP drop, checks them, and publishes them to
[lakehouse.silver.reference_codes](../datasets/lakehouse-tables.md).

<!-- openwiki: mermaid parse failed and this diagram was converted to a text fence so it does not break rendering. Fix the diagram source and restore the mermaid fence. Parser error: Heuristic: an unescaped angle bracket inside a label breaks rendering; rephrase the label. -->
```text
flowchart LR
  F["fetch_drop<br/>4 retries, exponential backoff"] --> V["validate<br/>reject if rows drop over 20%"]
  V --> P["publish<br/>MERGE on code_system, code"]
```

| Task | What it does |
| --- | --- |
| `fetch_drop` | Fetches the drop for the run date. Retries 4 times with exponential backoff (factor 30). |
| `validate` | Rejects a file whose row count drops more than 20 percent from the previous drop. |
| `publish` | Merges into `lakehouse.silver.reference_codes` on `(code_system, code)`. |

The flow times out after 2 hours.

## Deployment

| Setting | Value |
| --- | --- |
| Name | `reference-data-refresh-weekly` |
| Schedule | `0 6 * * 1`, Mondays 06:00 America/New_York |
| Work pool | `dp-k8s-pool` |
| Image | `dpregistry.azurecr.io/prefect-flows:2026.10` |
| Resources | 1 CPU, 4Gi memory requested |
| Tags | `reference-data`, `tier-2` |

## When it breaks

A tier-2 failure is a SEV2 with a 4 business hour response. See [On-call](../operations/oncall.md).
The table's freshness SLA is 192 hours, so one missed weekly run leaves a short margin
before the next scheduled run.

## Access

The `dp-prefect-devs` group grants developer access to the Prefect workspace. See
[Onboarding and Access](../onboarding/access.md).
