"""Seed the sample wiki without a model API key.

Runs the real dpwiki lifecycle (plan -> submit_page -> claim validation -> finalize)
with a ScriptedLLM that replays hand-written pages. Evidence line ranges are located
by snippet so they always point at the right lines.

    python scripts/seed_wiki.py            # from the repo root

With an API key you would run `dpwiki init` instead and let the model write the pages.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dpwiki.agent.runner import run  # noqa: E402
from dpwiki.agent.scripted import ScriptedLLM  # noqa: E402
from dpwiki.config import load_settings  # noqa: E402

SETTINGS = load_settings(ROOT / "wiki.toml")
SRC = {s.id: s.path for s in SETTINGS.sources}


def ev(uri: str, start: str, end: str | None = None) -> str:
    """Return uri#Lx-Ly for the lines containing the start (and end) snippets."""
    if uri.startswith("catalog://"):
        return uri
    sid, rel = uri[len("src://") :].split("/", 1)
    lines = (SRC[sid] / rel).read_text().splitlines()
    s = next(i for i, ln in enumerate(lines, 1) if start in ln)
    e = s if end is None else next(i for i, ln in enumerate(lines, 1) if i >= s and end in ln)
    return f"{uri}#L{s}-L{e}"


def c(statement: str, *evidence: str) -> dict:
    return {"statement": statement, "evidence": list(evidence)}


DBX = "src://platform-infra/terraform/databricks/workspace.tf"
SNOW = "src://platform-infra/terraform/snowflake/warehouses.tf"
BIGEYE = "src://platform-infra/bigeye/monitors.yml"
INFRA_README = "src://platform-infra/README.md"
DAG = "src://orchestration/airflow/dags/orders_ingest.py"
FLOW = "src://orchestration/prefect/flows/reference_data_refresh.py"
PREFECT = "src://orchestration/prefect/prefect.yaml"
ORCH_README = "src://orchestration/README.md"
ONCALL = "src://team-docs/oncall.md"
RB_SNOW = "src://team-docs/runbooks/snowflake-warehouse-saturation.md"
RB_BACKFILL = "src://team-docs/runbooks/airflow-backfill.md"
ACCESS = "src://team-docs/onboarding/access-requests.md"
ADR3 = "src://team-docs/decisions/adr-003-prefect-for-new-pipelines.md"
T_ORDERS = "catalog://lakehouse-catalog/lakehouse.silver.orders"
T_REV = "catalog://lakehouse-catalog/lakehouse.gold.daily_revenue"
T_REF = "catalog://lakehouse-catalog/lakehouse.silver.reference_codes"

PAGES: dict[str, dict] = {}

PAGES["platforms/databricks.md"] = dict(
    type="platform",
    title="Databricks",
    description="Databricks workspace, Unity Catalog metastore, cluster policies, and the BI SQL warehouse.",
    tags=["databricks", "unity-catalog", "terraform"],
    owner="dp-platform-admins",
    status="stable",
    body="""# Databricks

Databricks runs the lakehouse: Spark jobs that build bronze and silver tables, and a
serverless SQL warehouse for BI. Everything here is managed in Terraform in
`platform-infra/terraform/databricks`. See [How infrastructure changes ship](../governance/change-management.md).

## Unity Catalog

- Metastore `dp-primary-metastore` in `eastus2`, rooted in the `dpplatformlake` storage account.
- Catalog `lakehouse` holds the curated bronze, silver, and gold schemas. Owner is `dp-platform-admins`.
- Table-level ownership and SLAs are in the [catalog pages](../catalog/commerce-tables.md).

## Cluster policies

| Policy | Use | Key limits |
| --- | --- | --- |
| `jobs-standard` | Scheduled jobs | Runtime 15.x, auto-terminate fixed at 20 min, max 16 workers, D8ds_v5 or D16ds_v5 nodes |
| `interactive-small` | Notebooks | Auto-terminate up to 60 min (default 30), max 4 workers |

Both policies force the tag `cost_center = data-platform`, so all spend is attributed to the platform.

## SQL warehouse

`bi-serving` is a serverless Medium warehouse that scales from 1 to 4 clusters and stops
after 15 idle minutes.

## Who calls it

The [orders_ingest DAG](../orchestration/airflow.md#orders_ingest) triggers the
`silver_orders_merge` job through the `databricks_default` connection.
""",
    claims={
        "add": [
            c(
                "The Unity Catalog metastore is named dp-primary-metastore and is in region eastus2.",
                ev(DBX, 'resource "databricks_metastore"', "region"),
            ),
            c(
                "The lakehouse catalog is owned by dp-platform-admins.",
                ev(DBX, 'resource "databricks_catalog"', 'owner        = "dp-platform-admins"'),
            ),
            c(
                "The jobs-standard cluster policy fixes auto-termination at 20 minutes.",
                ev(DBX, '"autotermination_minutes" : { "type" : "fixed"'),
            ),
            c(
                "The jobs-standard cluster policy caps autoscaling at 16 workers.",
                ev(DBX, '"autoscale.max_workers" : { "type" : "range", "maxValue" : 16 }'),
            ),
            c(
                "The jobs-standard policy allows only Standard_D8ds_v5 and Standard_D16ds_v5 nodes.",
                ev(DBX, '"node_type_id"'),
            ),
            c(
                "The interactive-small policy allows up to 60 minutes auto-termination with a default of 30 and max 4 workers.",
                ev(
                    DBX,
                    '"autotermination_minutes" : { "type" : "range"',
                    '"autoscale.max_workers" : { "type" : "range", "maxValue" : 4 }',
                ),
            ),
            c(
                "Cluster policies force the custom tag cost_center = data-platform.",
                ev(DBX, '"custom_tags.cost_center"'),
            ),
            c(
                "The bi-serving SQL warehouse is serverless, Medium, scales 1 to 4 clusters, and auto-stops after 15 minutes.",
                ev(DBX, 'resource "databricks_sql_endpoint"', "enable_serverless_compute"),
            ),
            c(
                "orders_ingest triggers the Databricks job silver_orders_merge.",
                ev(DAG, 'job_name="silver_orders_merge"'),
            ),
        ]
    },
)

PAGES["platforms/snowflake.md"] = dict(
    type="platform",
    title="Snowflake",
    description="Snowflake warehouses TRANSFORM_WH and BI_WH, their scaling settings, and the monthly credit monitor.",
    tags=["snowflake", "warehouses", "cost"],
    owner="data-platform-eng",
    status="stable",
    body="""# Snowflake

Snowflake serves transformation loads and BI queries. Warehouses and resource monitors
are defined in `platform-infra/terraform/snowflake/warehouses.tf`.

## Warehouses

| Warehouse | Size | Clusters | Scaling | Auto-suspend | Used by |
| --- | --- | --- | --- | --- | --- |
| `TRANSFORM_WH` | LARGE | 1 to 3 | STANDARD | 120 s | dbt and Airflow loads |
| `BI_WH` | MEDIUM | 1 to 6 | ECONOMY | 60 s | dashboards and analysts |

## Cost guardrail

`TRANSFORM_WH` is attached to the resource monitor `TRANSFORM_MONTHLY`: 4000 credits per
month, notifications at 75 and 90 percent, and suspension at 100 percent. When the monitor
suspends the warehouse, every Snowflake load stops, including
[gold_daily_revenue](../orchestration/airflow.md#orders_ingest).

## Operating it

- Queueing or slow loads: follow [Snowflake warehouse saturation](../runbooks/snowflake-warehouse-saturation.md).
- Access: request `dp-snowflake-transform`. See [New engineer onboarding](../onboarding/new-engineer.md).
""",
    claims={
        "add": [
            c(
                "TRANSFORM_WH is size LARGE, auto-suspends after 120 seconds, and scales from 1 to 3 clusters with the STANDARD policy.",
                ev(SNOW, 'resource "snowflake_warehouse" "transform_wh"', 'scaling_policy      = "STANDARD"'),
            ),
            c(
                "TRANSFORM_WH is used for dbt and Airflow loads and owned by data-platform-eng.",
                ev(SNOW, 'comment             = "dbt and Airflow loads'),
            ),
            c(
                "BI_WH is size MEDIUM, auto-suspends after 60 seconds, and scales from 1 to 6 clusters with the ECONOMY policy.",
                ev(SNOW, 'resource "snowflake_warehouse" "bi_wh"', 'scaling_policy    = "ECONOMY"'),
            ),
            c("TRANSFORM_MONTHLY allows 4000 credits per month.", ev(SNOW, "credit_quota")),
            c(
                "TRANSFORM_MONTHLY notifies at 75 and 90 percent and suspends at 100 percent.",
                ev(SNOW, "notify_triggers", "suspend_trigger"),
            ),
            c(
                "TRANSFORM_WH is attached to the TRANSFORM_MONTHLY resource monitor.",
                ev(SNOW, "resource_monitor    = snowflake_resource_monitor"),
            ),
            c(
                "The dp-snowflake-transform group grants the TRANSFORMER role and TRANSFORM_WH usage.",
                ev(ACCESS, "`dp-snowflake-transform`"),
            ),
        ]
    },
)

PAGES["orchestration/airflow.md"] = dict(
    type="platform",
    title="Airflow",
    description="Airflow on dp-airflow-prod, the orders_ingest tier-1 DAG, and how Airflow relates to the Prefect migration.",
    tags=["airflow", "orchestration", "tier-1"],
    owner="data-platform-eng",
    status="stable",
    body="""# Airflow

Airflow 2 runs on the managed environment `dp-airflow-prod`. Existing tier-1 pipelines stay
here until they migrate. New pipelines go to [Prefect](prefect.md) per
[ADR-003](../governance/adr-003-prefect-for-new-pipelines.md).

Connections such as `databricks_default` and `snowflake_transform` come from the secrets
backend, never from DAG code.

## orders_ingest

Tier-1 DAG that moves orders from the landing zone to Databricks silver and then to a
Snowflake gold table.

```mermaid
flowchart LR
  L["wait_for_landing\\n/landing/orders/ds/_SUCCESS"] --> S["silver_orders\\nDatabricks job silver_orders_merge"]
  S --> G["gold_daily_revenue\\nCALL GOLD.BUILD_DAILY_REVENUE on TRANSFORM_WH"]
```

| Setting | Value |
| --- | --- |
| Schedule | `30 5 * * *` (05:30 UTC daily) |
| Owner | `data-platform-eng` |
| Retries | 3, 10 minutes apart |
| SLA | 4 hours |
| Concurrency | `max_active_runs=1`, `catchup=False` |
| Sensor | pokes every 5 minutes, times out after 3 hours, reschedule mode |

Outputs: [lakehouse.silver.orders and lakehouse.gold.daily_revenue](../catalog/commerce-tables.md).

## When it breaks

- Missed SLA on a tier-1 DAG is a SEV1. See [On-call](../runbooks/oncall.md).
- Re-running a date range: [Airflow backfill](../runbooks/airflow-backfill.md).
- Slow `gold_daily_revenue`: [Snowflake warehouse saturation](../runbooks/snowflake-warehouse-saturation.md).
""",
    claims={
        "add": [
            c(
                "Airflow DAGs run on the managed Airflow environment dp-airflow-prod.",
                ev(ORCH_README, "dp-airflow-prod"),
            ),
            c(
                "Connections databricks_default and snowflake_transform come from the secrets backend, not code.",
                ev(ORCH_README, "Connections (`databricks_default`"),
            ),
            c("orders_ingest runs daily at 05:30 UTC.", ev(DAG, 'schedule="30 5 * * *"')),
            c(
                "orders_ingest has owner data-platform-eng, 3 retries 10 minutes apart, and a 4 hour SLA.",
                ev(DAG, '"owner": "data-platform-eng"', '"sla": timedelta(hours=4)'),
            ),
            c(
                "orders_ingest runs with max_active_runs=1 and catchup disabled.",
                ev(DAG, "catchup=False", "max_active_runs=1"),
            ),
            c("orders_ingest is tagged tier-1.", ev(DAG, 'tags=["orders", "tier-1"]')),
            c(
                "The landing sensor waits for /landing/orders/{{ ds }}/_SUCCESS, pokes every 300 seconds, and times out after 3 hours in reschedule mode.",
                ev(DAG, 'filepath="/landing/orders/', 'mode="reschedule"'),
            ),
            c(
                "gold_daily_revenue calls GOLD.BUILD_DAILY_REVENUE on TRANSFORM_WH.",
                ev(DAG, 'warehouse="TRANSFORM_WH"', "BUILD_DAILY_REVENUE"),
            ),
            c(
                "Task order is wait_for_landing, then silver_orders, then gold_daily_revenue.",
                ev(DAG, "wait_for_landing >> silver_orders >> gold_daily_revenue"),
            ),
        ]
    },
)

PAGES["orchestration/prefect.md"] = dict(
    type="platform",
    title="Prefect",
    description="Prefect 3 is the default orchestrator for new pipelines; covers the dp-k8s-pool work pool and the reference-data-refresh flow.",
    tags=["prefect", "orchestration", "kubernetes"],
    owner="data-platform-eng",
    status="stable",
    body="""# Prefect

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
""",
    claims={
        "add": [
            c(
                "New pipelines use Prefect 3 flows on the dp-k8s-pool work pool.",
                ev(ADR3, "All new pipelines are written as Prefect 3 flows"),
            ),
            c(
                "The reference-data-refresh-weekly deployment runs Mondays at 06:00 America/New_York.",
                ev(PREFECT, 'cron: "0 6 * * 1"', "timezone: America/New_York"),
            ),
            c("The reference-data-refresh deployment is tagged tier-2.", ev(PREFECT, "tags: [reference-data, tier-2]")),
            c(
                "The deployment runs image prefect-flows:2026.10 with 1 CPU and 4Gi memory.",
                ev(PREFECT, "image: dpregistry", "memory_request: 4Gi"),
            ),
            c("The flow times out after 2 hours.", ev(FLOW, "timeout_seconds=2 * 60 * 60")),
            c("fetch_drop retries 4 times with exponential backoff.", ev(FLOW, "@task(retries=4")),
            c(
                "Validation rejects files whose row count drops more than 20 percent from the previous drop.",
                ev(FLOW, "Rejects files whose row count drops"),
            ),
            c(
                "publish merges into lakehouse.silver.reference_codes on (code_system, code).",
                ev(FLOW, "MERGE into lakehouse.silver.reference_codes"),
            ),
            c("dp-prefect-devs grants Prefect workspace developer access.", ev(ACCESS, "`dp-prefect-devs`")),
        ]
    },
)

PAGES["governance/adr-003-prefect-for-new-pipelines.md"] = dict(
    type="decision",
    title="ADR-003: Prefect for new pipelines",
    description="Accepted decision that new pipelines use Prefect 3 while existing Airflow DAGs migrate over time, tier-1 last.",
    tags=["adr", "prefect", "airflow"],
    status="stable",
    body="""# ADR-003: Prefect for new pipelines

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
""",
    claims={
        "add": [
            c("ADR-003 was accepted in 2025-09.", ev(ADR3, "Status: accepted")),
            c(
                "The Airflow DAG count passed 400 and peak scheduler latency reached several minutes.",
                ev(ADR3, "Airflow DAG count passed 400", "reached several minutes"),
            ),
            c(
                "Existing Airflow DAGs stay until their owning team migrates them, and tier-1 DAGs migrate last.",
                ev(ADR3, "Existing Airflow DAGs stay"),
            ),
            c(
                "Two orchestrators run in parallel for at least 2026 and on-call must know both.",
                ev(ADR3, "Two orchestrators run in parallel"),
            ),
        ]
    },
)

PAGES["governance/data-quality.md"] = dict(
    type="concept",
    title="Data quality monitoring",
    description="Bigeye monitors as code: freshness, volume, null, and duplicate checks on tier-1 tables, and where alerts go.",
    tags=["bigeye", "data-quality", "alerts"],
    owner="data-platform-eng",
    status="stable",
    body="""# Data quality monitoring

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
""",
    claims={
        "add": [
            c(
                "Bigeye checks lakehouse.silver.orders freshness with an upper bound of 26 hours.",
                ev(BIGEYE, "fq_table_name: lakehouse.silver.orders", "upper_bound: 26"),
            ),
            c(
                "Bigeye checks lakehouse.silver.orders row count with a medium-sensitivity autothreshold.",
                ev(BIGEYE, "COUNT_ROWS", "sensitivity: MEDIUM"),
            ),
            c(
                "order_id in lakehouse.silver.orders must be 0 percent null and have 0 duplicates.",
                ev(BIGEYE, "column_name: order_id", "COUNT_DUPLICATES"),
            ),
            c(
                "Bigeye checks lakehouse.gold.daily_revenue freshness with an upper bound of 30 hours.",
                ev(BIGEYE, "fq_table_name: lakehouse.gold.daily_revenue", "upper_bound: 30"),
            ),
            c(
                "Bigeye alerts go to #dp-data-quality-alerts and PagerDuty dp-platform-oncall.",
                ev(BIGEYE, "notification_channels", "pagerduty: dp-platform-oncall"),
            ),
            c(
                "A data quality monitor firing on a gold table is SEV2.",
                ev(ONCALL, "SEV2:", "data quality monitor fires on a gold table"),
            ),
        ]
    },
)

PAGES["governance/change-management.md"] = dict(
    type="workflow",
    title="How infrastructure changes ship",
    description="Terraform plan on every PR, apply from main after a dp-platform-admins approval, and where state lives.",
    tags=["terraform", "change-management"],
    owner="dp-platform-admins",
    status="stable",
    body="""# How infrastructure changes ship

`platform-infra` holds Terraform for [Databricks](../platforms/databricks.md) and
[Snowflake](../platforms/snowflake.md), and Bigeye config for [data quality](data-quality.md).

1. Open a pull request. `terraform plan` runs on every PR.
2. Get one approval from `dp-platform-admins`.
3. Merge. `terraform apply` runs from the `main` branch pipeline.

State lives in the `dp-tfstate` storage account, one state file per workspace.

Production write access is never granted to individuals, so emergency changes made by hand
(for example in the [Snowflake saturation runbook](../runbooks/snowflake-warehouse-saturation.md))
must be followed by a PR that makes them permanent or reverts them.
""",
    claims={
        "add": [
            c(
                "terraform plan runs on every PR in platform-infra.",
                ev(INFRA_README, "`terraform plan` runs on every PR"),
            ),
            c(
                "terraform apply runs from the main branch pipeline after one approval from dp-platform-admins.",
                ev(
                    INFRA_README,
                    "`terraform plan` runs on every PR",
                    "runs from the `main` branch pipeline after one approval",
                ),
            ),
            c(
                "Terraform state is stored in the dp-tfstate storage account with one state file per workspace.",
                ev(INFRA_README, "State is stored in the `dp-tfstate`"),
            ),
            c(
                "Production write access is never granted to individuals.",
                ev(ACCESS, "Production write access is never granted"),
            ),
        ]
    },
)

PAGES["runbooks/snowflake-warehouse-saturation.md"] = dict(
    type="runbook",
    title="Snowflake warehouse saturation",
    description="Steps when queries queue on TRANSFORM_WH or BI_WH: check load history, add a cluster, find heavy queries, watch the credit monitor.",
    tags=["snowflake", "runbook", "oncall"],
    owner="dp-platform-oncall",
    status="stable",
    body="""# Snowflake warehouse saturation

**Symptoms:** queries queue on `TRANSFORM_WH` or `BI_WH`, Airflow Snowflake tasks run long,
dashboard latency alerts. Warehouse settings are on the [Snowflake](../platforms/snowflake.md) page.

## Steps

1. Check queueing for the last two hours:
   ```sql
   select * from table(information_schema.warehouse_load_history(
     date_range_start=>dateadd('hour',-2,current_timestamp())))
   where warehouse_name = 'TRANSFORM_WH';
   ```
2. If `avg_queued_load` is above 1 for 15 minutes, add one cluster:
   `alter warehouse TRANSFORM_WH set max_cluster_count = 4;`
   Then open a PR in `platform-infra` to make it permanent or revert it
   ([change management](../governance/change-management.md)).
3. Find the heaviest queries in `snowflake.account_usage.query_history` and contact the owner.
4. If `TRANSFORM_MONTHLY` is above 90 percent of quota, tell `#dp-oncall` before resizing.
   At 100 percent the monitor suspends `TRANSFORM_WH`.

## Guardrail

Do not resize warehouses above LARGE without approval from the platform lead.
""",
    claims={
        "add": [
            c(
                "The saturation threshold is avg_queued_load above 1 for 15 minutes.",
                ev(RB_SNOW, "If `avg_queued_load` > 1 for 15 minutes"),
            ),
            c(
                "The mitigation is to raise max_cluster_count by one and open a platform-infra PR to make it permanent or revert it.",
                ev(RB_SNOW, "If `avg_queued_load` > 1", "platform-infra to make it permanent"),
            ),
            c(
                "Heavy queries are found in snowflake.account_usage.query_history.",
                ev(RB_SNOW, "account_usage.query_history"),
            ),
            c(
                "Above 90 percent of the resource monitor quota, on-call must tell #dp-oncall before resizing.",
                ev(RB_SNOW, "above 90 percent of quota"),
            ),
            c(
                "Resizing warehouses above LARGE requires approval from the platform lead.",
                ev(RB_SNOW, "Do not resize warehouses above LARGE"),
            ),
            c(
                "TRANSFORM_WH currently has max_cluster_count 3, so step 2 raises it to 4.",
                ev(SNOW, "max_cluster_count   = 3"),
            ),
        ]
    },
)

PAGES["runbooks/airflow-backfill.md"] = dict(
    type="runbook",
    title="Airflow backfill",
    description="How to re-run a date range for an Airflow DAG: pause, clear, batch by 7 days, watch Bigeye, unpause, announce.",
    tags=["airflow", "runbook", "backfill"],
    owner="dp-platform-oncall",
    status="stable",
    body="""# Airflow backfill

Use when a DAG missed runs or produced bad data for a range of dates.

## Steps

1. Pause the DAG in the UI so the scheduler does not compete with the backfill.
2. Clear the affected task instances, for example:
   `airflow tasks clear orders_ingest -s 2026-10-01 -e 2026-10-03 --yes`
3. For more than 7 days, run in batches of 7 days. [orders_ingest](../orchestration/airflow.md#orders_ingest)
   has `max_active_runs=1`, so runs execute one at a time.
4. Watch Bigeye freshness on the downstream tables until it is green ([data quality](../governance/data-quality.md)).
5. Unpause the DAG and post the date range in `#dp-oncall`.

Mention any backfill still running in the Monday [on-call handoff](oncall.md#handoff).
""",
    claims={
        "add": [
            c("The first backfill step is pausing the DAG in the UI.", ev(RB_BACKFILL, "Pause the DAG in the UI")),
            c(
                "Task instances are cleared with airflow tasks clear and a start and end date.",
                ev(RB_BACKFILL, "airflow tasks clear orders_ingest"),
            ),
            c("Backfills longer than 7 days run in batches of 7 days.", ev(RB_BACKFILL, "For more than 7 days")),
            c(
                "After backfilling, unpause the DAG and post the date range in #dp-oncall.",
                ev(RB_BACKFILL, "Unpause the DAG"),
            ),
            c("orders_ingest has max_active_runs=1.", ev(DAG, "max_active_runs=1")),
            c(
                "The Monday handoff note includes pending backfills.",
                ev(ONCALL, "Post a handoff note", "pending backfills"),
            ),
        ]
    },
)

PAGES["runbooks/oncall.md"] = dict(
    type="runbook",
    title="On-call",
    description="The dp-platform-oncall rotation, severity definitions, response times, and the Monday handoff.",
    tags=["oncall", "pagerduty", "severity"],
    owner="dp-platform-oncall",
    status="stable",
    body="""# On-call

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
""",
    claims={
        "add": [
            c(
                "The on-call rotation is dp-platform-oncall in PagerDuty.",
                ev(ONCALL, "The rotation is `dp-platform-oncall`"),
            ),
            c(
                "Shifts are one week from Monday 10:00 ET with a primary and a secondary.",
                ev(ONCALL, "Shifts are one week", "with a primary and a secondary"),
            ),
            c("SEV1 is a tier-1 pipeline missing its SLA or a production warehouse being down.", ev(ONCALL, "SEV1:")),
            c(
                "For SEV1 the secondary joins after 15 minutes without acknowledgement.",
                ev(ONCALL, "Secondary joins after 15 minutes"),
            ),
            c("SEV2 requires a response within 4 business hours.", ev(ONCALL, "Respond within 4 business hours")),
            c("SEV3 is handled in the weekly triage.", ev(ONCALL, "SEV3:")),
            c(
                "The weekly handoff note goes in #dp-oncall and lists open incidents, silenced monitors, and pending backfills.",
                ev(ONCALL, "Post a handoff note", "pending backfills"),
            ),
        ]
    },
)

PAGES["onboarding/new-engineer.md"] = dict(
    type="onboarding",
    title="New engineer onboarding",
    description="Access groups to request in week one, Slack channels to join, and the no-individual-prod-write rule.",
    tags=["onboarding", "access"],
    status="stable",
    body="""# New engineer onboarding

## Week one access

Request these groups in the access portal:

| Group | What it grants |
| --- | --- |
| `dp-engineers` | Databricks workspace user, `lakehouse` catalog USE, Airflow viewer |
| `dp-snowflake-transform` | Snowflake role TRANSFORMER and `TRANSFORM_WH` usage |
| `dp-prefect-devs` | Prefect workspace developer |
| `dp-platform-admins` | Terraform apply approvals. Leads only. |

Production write access is never granted to individuals. Changes ship through pipelines
([change management](../governance/change-management.md)).

## Slack

Join `#dp-platform-help`, `#dp-oncall`, and `#dp-data-quality-alerts`.

## Read next

1. [Databricks](../platforms/databricks.md) and [Snowflake](../platforms/snowflake.md)
2. [Airflow](../orchestration/airflow.md), [Prefect](../orchestration/prefect.md), and [ADR-003](../governance/adr-003-prefect-for-new-pipelines.md)
3. [On-call](../runbooks/oncall.md)
""",
    claims={
        "add": [
            c(
                "dp-engineers grants Databricks workspace user, lakehouse catalog USE, and Airflow viewer.",
                ev(ACCESS, "`dp-engineers`"),
            ),
            c(
                "dp-snowflake-transform grants the TRANSFORMER role and TRANSFORM_WH usage.",
                ev(ACCESS, "`dp-snowflake-transform`"),
            ),
            c("dp-prefect-devs grants Prefect workspace developer.", ev(ACCESS, "`dp-prefect-devs`")),
            c(
                "dp-platform-admins grants Terraform apply approvals and is for leads only.",
                ev(ACCESS, "`dp-platform-admins`"),
            ),
            c(
                "New engineers join #dp-platform-help, #dp-oncall, and #dp-data-quality-alerts.",
                ev(ACCESS, "Join Slack channels"),
            ),
        ]
    },
)

PAGES["catalog/commerce-tables.md"] = dict(
    type="dataset",
    title="Commerce and reference tables",
    description="Owners, freshness SLAs, columns, and lineage for lakehouse.silver.orders, lakehouse.gold.daily_revenue, and lakehouse.silver.reference_codes.",
    tags=["catalog", "orders", "revenue", "lineage"],
    status="stable",
    body="""# Commerce and reference tables

Table metadata comes from the Unity Catalog export.

```mermaid
flowchart LR
  raw["landing.orders_raw"] --> orders["lakehouse.silver.orders"]
  orders --> rev["lakehouse.gold.daily_revenue"]
  sftp["vendor_sftp.code_sets"] --> ref["lakehouse.silver.reference_codes"]
```

## lakehouse.silver.orders

- Owner `data-platform-eng`. Tier 1. Freshness SLA 26 hours.
- One row per order, merged daily by `silver_orders_merge` ([orders_ingest](../orchestration/airflow.md#orders_ingest)).
- Columns: `order_id` (primary key), `customer_key` (surrogate key, not PII), `order_ts` (UTC),
  `amount` (USD), `status` (placed, shipped, cancelled).

## lakehouse.gold.daily_revenue

- Owner `analytics-eng`. Tier 1. Freshness SLA 30 hours.
- Revenue by day and status. Built in Snowflake by `GOLD.BUILD_DAILY_REVENUE` and mirrored.

## lakehouse.silver.reference_codes

- Owner `data-platform-eng`. Tier 2. Freshness SLA 192 hours (8 days).
- Vendor code sets refreshed weekly by [reference-data-refresh](../orchestration/prefect.md#reference-data-refresh).
""",
    claims={
        "add": [
            c(
                "lakehouse.silver.orders is owned by data-platform-eng, is tier 1, and has a 26 hour freshness SLA.",
                T_ORDERS,
            ),
            c("lakehouse.silver.orders is merged daily by silver_orders_merge from landing.orders_raw.", T_ORDERS),
            c("customer_key in lakehouse.silver.orders is a surrogate key and not PII.", T_ORDERS),
            c(
                "lakehouse.gold.daily_revenue is owned by analytics-eng, is tier 1, and has a 30 hour freshness SLA.",
                T_REV,
            ),
            c(
                "lakehouse.gold.daily_revenue is built in Snowflake by GOLD.BUILD_DAILY_REVENUE and depends on lakehouse.silver.orders.",
                T_REV,
            ),
            c(
                "lakehouse.silver.reference_codes is tier 2 with a 192 hour freshness SLA and is refreshed weekly by reference-data-refresh.",
                T_REF,
            ),
        ]
    },
)

PLAN = {
    "summary": "Initial build: platforms, orchestration, governance, runbooks, onboarding, and catalog pages.",
    "jobs": [
        {
            "path": p,
            "action": "create",
            "title": spec["title"],
            "type": spec["type"],
            "purpose": spec["description"],
            "sources": [],
        }
        for p, spec in PAGES.items()
    ],
}


def main() -> None:
    for d in (SETTINGS.wiki_dir / ".claims",):
        if d.exists():
            import shutil

            shutil.rmtree(d)
    for p in list(SETTINGS.wiki_dir.rglob("*.md")):
        if p.name != "INSTRUCTIONS.md" and p != SETTINGS.wiki_dir / "index.md":
            p.unlink()  # keep the charter and the human-written intro on the root index
    for f in (SETTINGS.state_path, SETTINGS.run_path):
        f.unlink(missing_ok=True)
    res = run(SETTINGS, ScriptedLLM(PLAN, PAGES), init=True, force=True)
    rep = res.report
    print(
        f"completed={len(res.completed)} failed={res.failed} verified={len(rep.verified)} "
        f"broken_links={rep.broken_links} attention={rep.attention}"
    )
    if res.failed or rep.broken_links:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
