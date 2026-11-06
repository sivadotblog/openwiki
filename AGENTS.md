# Agent guide

This repo is dpwiki, a Python prototype of an agent-maintained team wiki for a data platform.

## Answering questions about the data platform

Use the wiki before reading sources. Run `dpwiki search <terms>` then `dpwiki read <page>#<anchor>`,
or use the `dpwiki` MCP tools if they are connected. Pages live in `wiki/`.

## Changing the wiki

- Do not hand-edit files in `wiki/.claims/`, `wiki/.state.json`, or the generated block of any `index.md`.
- To change wiki content, change the sources or `wiki/INSTRUCTIONS.md`, then run `dpwiki update`.
- Small manual fixes to a page body are fine. Run `dpwiki finalize` afterwards.

## Changing the code

- Engine code is in `src/dpwiki/`. Tests are in `tests/`.
- Run `pytest -q` and `ruff check src tests scripts` before committing.
- If you change the sample sources or the seed pages, run `python scripts/seed_wiki.py` and commit the result.
