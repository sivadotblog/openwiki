"""Page frontmatter: parse, validate, render.

Pages follow a small subset of the Open Knowledge Format (OKF) used by OpenWiki:

    ---
    type: runbook                # required
    title: Snowflake warehouse saturation
    description: One line summary used in indexes and search.
    tags: [snowflake, oncall]
    owner: platform-oncall       # team or person accountable for the page
    status: stable               # draft | stable | deprecated
    sources: [...]               # code-owned: evidence resources behind the page
    generated: {by, at}          # code-owned: last run that changed the body
    verified: {by, at}           # code-owned: last run that confirmed the claims
    ---

Authors (human or agent) own type, title, description, tags, owner, status.
dpwiki owns sources, generated, verified and rewrites them deterministically.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import yaml

PAGE_TYPES = {
    "concept",
    "platform",
    "runbook",
    "workflow",
    "dataset",
    "onboarding",
    "decision",
    "reference",
    "index",
}
STATUSES = {"draft", "stable", "deprecated"}
AUTHOR_FIELDS = ["type", "title", "description", "tags", "owner", "status"]
CODE_FIELDS = ["sources", "generated", "verified"]
FIELD_ORDER = AUTHOR_FIELDS + CODE_FIELDS

_FM_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


@dataclass
class Page:
    meta: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def body_hash(self) -> str:
        return "sha256:" + hashlib.sha256(self.body.encode("utf-8")).hexdigest()


def parse(text: str) -> Page:
    m = _FM_RE.match(text)
    if not m:
        return Page(meta={}, body=text)
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return Page(meta=meta, body=text[m.end() :])


def render(page: Page) -> str:
    ordered: dict[str, Any] = {}
    for k in FIELD_ORDER:
        if k in page.meta and page.meta[k] not in (None, "", []):
            ordered[k] = page.meta[k]
    for k, v in page.meta.items():  # keep unknown producer extensions
        if k not in ordered and v not in (None, "", []):
            ordered[k] = v
    fm = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=100).strip()
    body = page.body if page.body.startswith("\n") else "\n" + page.body
    return f"---\n{fm}\n---\n{body.rstrip()}\n"


def _is_iso(ts: Any) -> bool:
    if isinstance(ts, datetime):
        return ts.tzinfo is not None
    if not isinstance(ts, str):
        return False
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _check_event(name: str, ev: Any, issues: list[str]) -> None:
    if not isinstance(ev, dict) or not isinstance(ev.get("by"), str) or not ev["by"]:
        issues.append(f"{name} must be a mapping with a non-empty 'by'")
    elif "at" in ev and not _is_iso(ev["at"]):
        issues.append(f"{name}.at must be an ISO 8601 timestamp with a UTC offset")


def validate(page: Page) -> list[str]:
    """Return a list of human-readable issues. Empty list means valid."""
    m = page.meta
    issues: list[str] = []
    if not m:
        return ["missing frontmatter"]
    t = m.get("type")
    if not isinstance(t, str) or not t:
        issues.append("missing type")
    elif t not in PAGE_TYPES:
        issues.append(f"unknown type '{t}' (expected one of {sorted(PAGE_TYPES)})")
    for k in ("title", "description", "owner"):
        if k in m and (not isinstance(m[k], str) or not m[k].strip()):
            issues.append(f"{k} must be a non-empty string")
    if "tags" in m and (not isinstance(m["tags"], list) or not all(isinstance(x, str) and x for x in m["tags"])):
        issues.append("tags must be a list of non-empty strings")
    if "status" in m and m["status"] not in STATUSES:
        issues.append(f"status must be one of {sorted(STATUSES)}")
    if "sources" in m:
        if not isinstance(m["sources"], list) or not all(
            isinstance(s, dict) and isinstance(s.get("resource"), str) for s in m["sources"]
        ):
            issues.append("sources must be a list of mappings with 'resource'")
    for ev in ("generated", "verified"):
        if ev in m:
            _check_event(ev, m[ev], issues)
    return issues


def repair(page: Page, fallback_title: str) -> Page:
    """Conservative repair: drop invalid code-owned fields, fill a missing type/title."""
    meta = dict(page.meta)
    if not isinstance(meta.get("type"), str) or meta.get("type") not in PAGE_TYPES:
        meta["type"] = "reference"
    if not isinstance(meta.get("title"), str) or not meta["title"].strip():
        h1 = re.search(r"^# (.+)$", page.body, re.MULTILINE)
        meta["title"] = h1.group(1).strip() if h1 else fallback_title
    for k in ("generated", "verified"):
        issues: list[str] = []
        if k in meta:
            _check_event(k, meta[k], issues)
            if issues:
                meta.pop(k)
    if "status" in meta and meta["status"] not in STATUSES:
        meta.pop("status")
    if "tags" in meta and not isinstance(meta["tags"], list):
        meta.pop("tags")
    return Page(meta=meta, body=page.body)
