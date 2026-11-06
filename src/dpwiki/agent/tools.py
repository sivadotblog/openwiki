"""Tool definitions and handlers the agent can call.

Every handler is bounded: sources are read only through the connector registry and
pages are written only through the Wiki store. Claim sidecars are never exposed for
direct writes; the agent proposes decisions and dpwiki applies them.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .. import frontmatter as fm
from ..claims import ClaimsStore, apply_decisions, check
from ..search import read_section, search
from ..sources import Registry
from ..wiki import Wiki, WikiPathError

MAX_READ_CHARS = 30_000


def _schema(name: str, description: str, props: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "input_schema": {"type": "object", "properties": props, "required": required},
    }


S = {"type": "string"}
LIST_S = {"type": "array", "items": {"type": "string"}}

LIST_SOURCES = _schema(
    "list_sources",
    "List source items (files, docs, catalog tables) with their URIs. Optional prefix filter, "
    "e.g. 'src://orchestration/dags/'.",
    {"prefix": S},
    [],
)
READ_SOURCE = _schema(
    "read_source",
    "Read a source item by URI. File text comes back with line numbers so you can cite #Lx-Ly ranges.",
    {"uri": S},
    ["uri"],
)
GREP_SOURCES = _schema(
    "grep_sources",
    "Case-insensitive search for a literal string or regex across all sources. Returns URI#Lnn hits.",
    {"pattern": S},
    ["pattern"],
)
READ_PAGE = _schema(
    "read_page",
    "Read a wiki page (path relative to the wiki root). Optional anchor reads one section.",
    {"path": S, "anchor": S},
    ["path"],
)
SEARCH_WIKI = _schema("search_wiki", "Ranked search over wiki sections.", {"query": S}, ["query"])
GET_PAGE_CLAIMS = _schema(
    "get_page_claims",
    "Show the claims recorded for a page and whether each is clean, stale, or unresolved.",
    {"path": S},
    ["path"],
)
SUBMIT_PAGE = _schema(
    "submit_page",
    "Write the page and its claim decisions. Returns ok or a list of errors to fix.",
    {
        "path": S,
        "type": {"type": "string", "enum": sorted(fm.PAGE_TYPES - {"index"})},
        "title": S,
        "description": {"type": "string", "description": "One sentence used in indexes and search."},
        "tags": LIST_S,
        "owner": {"type": "string", "description": "Owning team or rotation, if known."},
        "status": {"type": "string", "enum": sorted(fm.STATUSES)},
        "body": {"type": "string", "description": "Markdown body starting with '# Title'."},
        "claims": {
            "type": "object",
            "properties": {
                "add": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"statement": S, "evidence": LIST_S},
                        "required": ["statement", "evidence"],
                    },
                },
                "confirm": LIST_S,
                "revise": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"id": S, "statement": S, "evidence": LIST_S},
                        "required": ["id", "statement"],
                    },
                },
                "retract": LIST_S,
            },
        },
    },
    ["path", "type", "title", "description", "body"],
)
DELETE_PAGE = _schema(
    "delete_page", "Delete a page that no longer has a reason to exist.", {"path": S, "reason": S}, ["path", "reason"]
)
SUBMIT_PLAN = _schema(
    "submit_plan",
    "Submit the page plan for this run.",
    {
        "summary": S,
        "jobs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": S,
                    "action": {"type": "string", "enum": ["create", "update", "delete"]},
                    "title": S,
                    "type": {"type": "string", "enum": sorted(fm.PAGE_TYPES - {"index"})},
                    "purpose": S,
                    "sources": LIST_S,
                },
                "required": ["path", "action", "title", "purpose"],
            },
        },
    },
    ["jobs"],
)


@dataclass
class ToolContext:
    wiki: Wiki
    store: ClaimsStore
    registry: Registry
    job_path: str | None = None
    done: bool = False
    touched: set[str] = field(default_factory=set)
    log: Callable[[str], None] = print


def _numbered(text: str) -> str:
    lines = text.splitlines()
    w = len(str(len(lines)))
    return "\n".join(f"{i + 1:>{w}} | {line}" for i, line in enumerate(lines))


def handle(ctx: ToolContext, name: str, args: dict[str, Any]) -> str:
    try:
        return _HANDLERS[name](ctx, args)
    except KeyError as e:
        if name not in _HANDLERS:
            return f"error: unknown tool {name}"
        return f"error: missing argument {e}"
    except (ValueError, WikiPathError) as e:
        return f"error: {e}"


def _list_sources(ctx: ToolContext, a: dict) -> str:
    prefix = a.get("prefix") or ""
    items = [i for i in ctx.registry.scan() if i.uri.startswith(prefix)]
    rows = [f"{i.uri}  ({i.kind}, {i.size} chars)" for i in items[:500]]
    more = f"\n... {len(items) - 500} more" if len(items) > 500 else ""
    return "\n".join(rows) + more if rows else "no sources match"


def _read_source(ctx: ToolContext, a: dict) -> str:
    uri = a["uri"]
    text = ctx.registry.read(uri.split("#")[0])
    if text is None:
        return f"error: source not found: {uri}"
    body = _numbered(text) if uri.startswith("src://") else text
    if len(body) > MAX_READ_CHARS:
        body = body[:MAX_READ_CHARS] + "\n... [truncated]"
    return f'<source uri="{uri}">\n{body}\n</source>'


def _grep_sources(ctx: ToolContext, a: dict) -> str:
    try:
        rx = re.compile(a["pattern"], re.IGNORECASE)
    except re.error:
        rx = re.compile(re.escape(a["pattern"]), re.IGNORECASE)
    hits = []
    for item in ctx.registry.scan():
        text = ctx.registry.read(item.uri) or ""
        for n, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                hits.append(f"{item.uri}#L{n}: {line.strip()[:160]}")
                if len(hits) >= 80:
                    return "\n".join(hits) + "\n... [more hits truncated]"
    return "\n".join(hits) or "no matches"


def _read_page(ctx: ToolContext, a: dict) -> str:
    text = read_section(ctx.wiki, a["path"], a.get("anchor"))
    if text is None:
        return f"page or section not found: {a['path']}"
    pg = ctx.wiki.read(a["path"])
    head = json.dumps({k: pg.meta.get(k) for k in ("type", "title", "description", "tags", "owner", "status")})
    return f"{head}\n\n{text}"


def _search_wiki(ctx: ToolContext, a: dict) -> str:
    hits = search(ctx.wiki, a["query"])
    if not hits:
        return "no results"
    return "\n".join(f"{h.page}#{h.anchor}  [{h.title} > {h.heading}]  score={h.score}\n    {h.snippet}" for h in hits)


def _get_page_claims(ctx: ToolContext, a: dict) -> str:
    ctx.wiki.check_path(a["path"])
    pc = ctx.store.load(a["path"])
    if not pc.claims:
        return "no claims recorded for this page"
    st = check(pc, ctx.registry)
    status = {cid: "clean" for cid in st.clean}
    status.update({cid: "stale" for cid in st.stale})
    status.update({cid: "unresolved" for cid in st.unresolved})
    return "\n".join(
        f"{c.id} [{status[c.id]}] {c.statement}\n    evidence: {', '.join(e.resource for e in c.evidence)}"
        for c in pc.claims
    )


def _submit_page(ctx: ToolContext, a: dict) -> str:
    path = a["path"]
    if ctx.job_path and path != ctx.job_path:
        return f"error: this job writes {ctx.job_path}, not {path}"
    ctx.wiki.check_path(path, for_write=True)
    body = (a.get("body") or "").strip()
    errors = []
    if not body.startswith("# "):
        errors.append("body must start with '# <title>'")
    meta = {k: a[k] for k in ("type", "title", "description", "tags", "owner", "status") if a.get(k)}
    existing = ctx.wiki.read(path)
    if existing:  # keep code-owned fields; finalize reconciles them
        for k in fm.CODE_FIELDS:
            if k in existing.meta:
                meta[k] = existing.meta[k]
    page = fm.Page(meta=meta, body="\n" + body + "\n")
    errors += fm.validate(page)

    pc = ctx.store.load(path)
    decisions = a.get("claims") or {}
    new_pc, claim_errors = apply_decisions(pc, ctx.registry, decisions)
    errors += claim_errors
    if not new_pc.claims:
        errors.append("a page needs at least one claim with evidence")
    if errors:
        return "error: page not written. Fix and resubmit:\n- " + "\n- ".join(errors)

    ctx.wiki.write(path, page)
    ctx.store.save(new_pc)
    ctx.touched.add(path)
    ctx.done = True
    ctx.log(f"  wrote {path} ({len(new_pc.claims)} claims)")
    return f"ok: wrote {path} with {len(new_pc.claims)} claims"


def _delete_page(ctx: ToolContext, a: dict) -> str:
    path = a["path"]
    if ctx.job_path and path != ctx.job_path:
        return f"error: this job is for {ctx.job_path}"
    ctx.wiki.delete(path)
    ctx.store.delete(path)
    ctx.done = True
    ctx.log(f"  deleted {path}: {a.get('reason', '')}")
    return f"ok: deleted {path}"


_HANDLERS = {
    "list_sources": _list_sources,
    "read_source": _read_source,
    "grep_sources": _grep_sources,
    "read_page": _read_page,
    "search_wiki": _search_wiki,
    "get_page_claims": _get_page_claims,
    "submit_page": _submit_page,
    "delete_page": _delete_page,
}

WRITER_TOOLS = [
    LIST_SOURCES,
    READ_SOURCE,
    GREP_SOURCES,
    READ_PAGE,
    SEARCH_WIKI,
    GET_PAGE_CLAIMS,
    SUBMIT_PAGE,
    DELETE_PAGE,
]
ASK_TOOLS = [SEARCH_WIKI, READ_PAGE]
