# Deterministic feature status index (experiment)

Goal: keep a list of Databricks features and their release status (Beta, Public Preview,
GA) current without a model deciding the status. Tested on Lakebase.

Output: `index/lakebase-features.yaml` (the index) and `index/lakebase-review.yaml`
(items a human must settle). Built by `tools/feature_index.py`, run by
`.github/workflows/feature-index.yml` daily. Two runs on the same inputs produce
byte-identical files.

## What we learned about the sources

| Source | What it is good for | What it is not good for |
| --- | --- | --- |
| RSS feed `learn.microsoft.com/en-us/azure/databricks/feed.xml` | Trigger. About 1,470 items. Each item has `guid` (the release note URL plus anchor), title, date, categories, and an HTML description with docs links. | Identity. One item per announcement, so Beta and GA of the same feature are different items. It also includes "what's coming" items. |
| Product release notes page (`release-notes/lakebase/`) | History. One H2 per change, a bold date, and links to the feature docs page. | Current status. It only says what changed on that date. |
| The feature's docs page | Current status. Preview pages open with a banner like "This feature is in [Beta](../release-notes/release-types)", and often name the Previews toggle. | Dates. |
| Learn search index (MCP search) | Quick lookups | Truth. It lagged the live page. Lakebase Provisioned still showed a Public Preview banner in search but not on the live page. |

## Rules (all fixed, no model)

1. **Identity = docs page path.** Section anchors are hints only. The Beta notes for snapshots linked `#create-snapshot` and `#snapshot-schedules`, and the live page now uses `#create-a-snapshot` and `#create-a-backup-schedule`.
2. **Status = the page banner.** The banner word links to the release types page, so it can be found exactly. Learn page chrome headings (`ms--*`) are skipped.
3. **No banner is not proof of GA.** It means "not marked as preview". The index says `ga` only if a GA release note also exists. Otherwise `unmarked`, sent to review. Retired features (Lakebase Provisioned) and context links (an Observability overview page linked from a Beta note) land here.
4. **Partial banners are `mixed`.** For example "Some operations remain in Beta" on the API guide.
5. **Release note titles are a cross-check only.** Fixed regexes: "(Beta)", "in Beta", "Public Preview", "generally available", "is now GA", "(GA)". No match means not a status change (regions, compliance, versions).
6. **A GA note on a page covers that page's sections.** This handles the merged snapshots and backup schedule GA.
7. **Disagreements are written to review, never guessed.** `info` when the docs are ahead of the notes, `needs-review` when the docs are behind or unclear.

## Lakebase results (2026-11-06)

20 features: 9 GA, 3 Beta, 2 Public Preview, 1 mixed, 5 unmarked. 6 items need review.

Verified transitions: Lakebase on Azure (Beta 2026-02-04, GA 2026-03-02), Lakebase Search
(Beta 2026-06-16, GA 2026-09-18), snapshots API (Beta 2026-09-15) and backup schedule API
(Beta 2026-09-22), both GA 2026-10-26 in one note.

## Limits

- A release note can link several pages, and some are context, not the feature. They show up as `unmarked`.
- Renames are only visible through the Previews toggle name on the page, for example "previously named Lakebase Advanced Postgres Telemetry".
- Azure docs only. AWS and GCP docs have their own pages and could differ by cloud.
- Workspace truth (which previews are on in your workspace) is not in public docs. It is visible in the workspace Previews page.

## How this feeds OpenWiki

Commit the index to the repo. A wiki page about Databricks feature status cites lines in
`index/lakebase-features.yaml`. When the daily job changes one feature's block, only the
claims citing those lines go stale, so only that page is revisited by the next update.
