# OpenWiki for Data Platforms (dpwiki)

A prototype of an agent-maintained knowledge base for a data platform team.

An agent reads the team's platform repos, pipeline code, runbooks, and catalog exports,
and writes a linked Markdown wiki. Every important fact on a page is stored as a claim
tied to a specific version of a source. When a source changes, dpwiki knows which claims
went stale and which pages need an update. The agent then fixes only those pages and a
scheduled job opens a pull request for the team to review.

The design follows [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki).
This version is a small Python rewrite focused on one use case: a team wiki for data
platforms (Databricks, Snowflake, Airflow, Prefect, Bigeye).

## What is in this repo

| Path | What it is |
| --- | --- |
| `wiki/` | The generated team wiki. Browse it on GitHub. |
| `wiki/INSTRUCTIONS.md` | The charter. Humans own it. The agent reads it every run. |
| `wiki/.claims/` | Claim sidecars, one JSON file per page. Written only by dpwiki. |
| `sources/` | Sample sources: Terraform, DAGs, Prefect flows, runbooks, a Unity Catalog export. |
| `wiki.toml` | Which sources to read, which sections the wiki has, which model to use. |
| `src/dpwiki/` | The engine. |
| `docs/architecture.md` | How it works, with diagrams. |

The sample sources are made up. Replace them with your real repos and exports.

## How it works

1. **Preflight** (no model). Scan every source and compare content versions to the last run.
   Re-check every claim. A claim is clean, stale (source changed), or unresolved (source gone).
2. **Plan** (model). Given the changes and the stale pages, decide which pages to create,
   update, or delete.
3. **Page jobs** (model, one page at a time). The agent reads sources through bounded tools,
   writes the page, and submits claim decisions: add, confirm, revise, retract. dpwiki
   rejects claims whose evidence does not resolve. Progress is saved after each page, so an
   interrupted run resumes.
4. **Finalize** (no model). Repair frontmatter, sync each page's `sources` from its claims,
   stamp `generated` only when a page body actually changed, stamp `verified` when all claims
   are clean, rebuild every `index.md`, and report broken links.

If nothing changed, `dpwiki update` exits without calling the model.

## Quick start

Python 3.11 or newer.

```sh
pip install -e ".[mcp,dev]"

dpwiki status                    # model-free health check
dpwiki search snowflake credits  # model-free search
dpwiki read runbooks/oncall.md#severity
```

To let the agent write and update pages:

```sh
export ANTHROPIC_API_KEY=...     # or set provider = "bedrock" in wiki.toml and use AWS credentials
dpwiki update                    # update pages affected by source changes
dpwiki init --force              # rebuild from all sources
dpwiki ask "who do I page when orders_ingest misses its SLA?"
```

Try the drift loop on the sample data:

```sh
sed -i 's/auto_suspend        = 120/auto_suspend        = 300/' \
  sources/repos/platform-infra/terraform/snowflake/warehouses.tf
dpwiki status        # shows platforms/snowflake.md has 1 stale claim
dpwiki update        # agent revises that page only
```

## Browse it

The wiki is published to GitHub Pages at https://sivadotblog.github.io/openwiki/ using
OpenWiki's native visualizer: an interactive page graph next to a Markdown reader.
`.github/workflows/pages.yml` runs `npx openwiki visualize wiki --export _site` on every
push that changes `wiki/`. To view it locally:

```sh
npx openwiki visualize wiki --port 4400
```

## Use it from Claude Code

The MCP server is read-only and does not call a model.

```sh
claude mcp add dpwiki -- dpwiki --config /path/to/openwiki/wiki.toml mcp
```

Tools: `wiki_search`, `wiki_read`, `wiki_list`, `wiki_freshness`.

## Connect real sources

Edit `wiki.toml`. Two connector kinds exist today.

- `filesystem`: any checked-out repo or docs folder, with include and exclude globs.
  Evidence URIs look like `src://<source-id>/path/to/file.py#L10-L20`.
- `catalog`: a JSON export of table metadata (Unity Catalog, Snowflake information_schema,
  or a Bigeye export). Evidence URIs look like `catalog://<source-id>/catalog.schema.table`.

In CI, check out the platform repos next to this one and point `filesystem` sources at them.
Produce the catalog export with a scheduled job that has read-only catalog access, so the
wiki agent never holds warehouse credentials. A new connector is one class in
`src/dpwiki/sources/` with `scan`, `read`, and `version`.

## Scheduled updates

`.github/workflows/wiki-update.yml` runs `dpwiki update` daily and opens a pull request
named `wiki: update`. It needs the `ANTHROPIC_API_KEY` secret and the repository variable
`DPWIKI_ENABLE_SCHEDULED_UPDATE=true`. Manual runs work from the Actions tab.
`.github/workflows/ci.yml` runs tests and `dpwiki status --strict` on every pull request.

## Safety

- The agent reads sources only through connectors. Reads cannot leave the configured roots.
- The agent writes only kebab-case pages under `wiki/`. It cannot write `index.md`,
  `INSTRUCTIONS.md`, claim sidecars, or run state.
- Source text is treated as untrusted data. Prompts tell the model not to follow
  instructions found in sources and not to copy secrets or personal data.
- Every change lands as a pull request, so a human reviews it before it becomes the wiki.

## Differences from langchain-ai/openwiki

| OpenWiki | This prototype |
| --- | --- |
| TypeScript, Deep Agents, many model providers | Python, Anthropic SDK (direct or Bedrock) |
| Code mode for one repo, personal mode for connectors | One team mode that grounds claims in repos and catalog exports |
| Claims only for repository evidence | Claims for files and catalog tables |
| Coding agent integrations drive generation over MCP | MCP is read-only retrieval; generation runs from the CLI or CI |
| Interactive graph visualizer | Reused as is: `openwiki visualize` publishes this wiki to GitHub Pages |

## Status

Prototype. 14 tests cover claims, drift detection, line relocation, containment, the
finalizer, search, and a full scripted update run. The sample wiki in `wiki/` was produced
by `scripts/seed_wiki.py`, which drives the real lifecycle with a scripted model so the
repo works without an API key. Run `dpwiki init --force` with a key to have the model
write it instead.

## License

MIT
