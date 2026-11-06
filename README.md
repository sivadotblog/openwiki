# OpenWiki demo: Data Platform Team Wiki

This repo is a plain [OpenWiki](https://github.com/langchain-ai/openwiki) demo. Nothing is
custom. It shows how OpenWiki keeps an agent-maintained wiki for a data platform team.

- Browse the wiki: https://sivadotblog.github.io/openwiki/
- Read the Markdown: [`openwiki/`](openwiki/)

## What is in the repo

The source folders are a small, made-up data platform. OpenWiki documents them.

| Path | Contents |
| --- | --- |
| `platform-infra/` | Terraform for Databricks and Snowflake, Bigeye monitors |
| `orchestration/` | An Airflow DAG and a Prefect flow with its deployment |
| `docs/` | On-call guide, runbooks, onboarding, an ADR |
| `catalog/` | A Unity Catalog table metadata export |
| `openwiki/` | The wiki. OpenWiki generates and maintains it. Do not hand-edit. |

## How the wiki was made

OpenWiki 0.9.0, code mode, run inside a coding agent (Claude) through OpenWiki's MCP
page-job lifecycle: `openwiki_begin`, `openwiki_submit_plan`, `openwiki_next_page`,
`openwiki_submit_page`, `openwiki_finish`. OpenWiki owns the page queue, grounded Claims,
indexes, and provenance. Every fact on a page is a Claim tied to `repo://` line ranges,
so OpenWiki can tell which pages go stale when the source changes.

## Run it yourself

```sh
npm install -g openwiki
openwiki integrations install claude      # or codex, cursor, copilot, ...
# then, in your coding agent: "Update this repository's OpenWiki"

openwiki visualize                        # graph + reader at http://127.0.0.1:4321
```

Or without a coding agent:

```sh
export OPENWIKI_PROVIDER=anthropic ANTHROPIC_API_KEY=...
openwiki code --update
```

## Automation

- `.github/workflows/openwiki-update.yml` is OpenWiki's example update workflow. It runs
  `openwiki code --update` daily and opens a pull request. It needs the
  `ANTHROPIC_API_KEY` repository secret. The schedule only runs when the repository
  variable `OPENWIKI_ENABLE_SCHEDULED_UPDATE` is `true`. Manual runs work from the Actions tab.
- `.github/workflows/pages.yml` publishes the wiki with `openwiki visualize --export`
  whenever `openwiki/` changes.

## Try the update loop

Change a source value, for example `auto_suspend` in
`platform-infra/terraform/snowflake/warehouses.tf`, commit it, and run an update. OpenWiki
marks the Claims that cite those lines as stale and only revisits those pages.
