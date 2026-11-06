# Data platform on-call

The rotation is `dp-platform-oncall` in PagerDuty. Shifts are one week, Monday 10:00 ET
to the next Monday 10:00 ET, with a primary and a secondary.

## Severity

- SEV1: a tier-1 pipeline (tag `tier-1`) misses its SLA, or a production warehouse is down.
  Page primary immediately. Secondary joins after 15 minutes without acknowledgement.
- SEV2: a tier-2 pipeline fails, or a data quality monitor fires on a gold table.
  Respond within 4 business hours.
- SEV3: everything else. Handle in the weekly triage.

## Handoff

Post a handoff note in #dp-oncall every Monday with open incidents, silenced monitors,
and any pending backfills.
