---
type: concept
title: Data quality monitoring
description: 'Bigeye monitors as code: freshness, volume, null, and duplicate checks on tier-1 tables,
  and where alerts go.'
tags:
- bigeye
- data-quality
- alerts
owner: data-platform-eng
status: stable
sources:
- resource: src://platform-infra/bigeye/monitors.yml
- resource: src://team-docs/oncall.md
generated:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:20:00+00:00'
verified:
  by: dpwiki/0.1.0
  at: '2026-11-06T00:20:00+00:00'
---

# Data quality monitoring

Bigeye monitors are defined as code in `platform-infra/bigeye/monitors.yml` and ship
like any other infrastructure change ([change management](change-management.md)).

## Monitored tables

| Table | Checks |
| --- | --- |
| `lakehouse.silver.orders` | freshness under 26 hours, row count autothreshold (medium), `order_id` 0 percent null, 0 duplicates |
| `lakehouse.gold.daily_revenue` | freshness under 30 hours |

The freshness thresholds match the SLAs in the [catalog](../catalog/commerce-tables.md).

## Alert routing

Alerts post to `#dp-data-quality-alerts` and page the `dp-platform-oncall` PagerDuty service.
A monitor firing on a gold table is a SEV2 ([On-call](../runbooks/oncall.md)).

## Open questions

- `lakehouse.silver.reference_codes` has no Bigeye monitor in the sources yet.
