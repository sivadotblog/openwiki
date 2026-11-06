"""Model-free retrieval over the wiki: BM25 over page sections.

Used by the CLI (`dpwiki search`, `dpwiki read`), the `ask` agent, and the MCP server.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .wiki import Wiki

_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$", re.MULTILINE)  # H1 belongs to the lead section
STOP = set(
    "a an and are as at be by can do does for from has have how i in is it my of on or our that the"
    " this to we what when where which who why with".split()
)


def slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"\s", "-", s)  # GitHub-style anchors keep underscores


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOP and len(t) > 1]


@dataclass
class Section:
    page: str
    page_title: str
    anchor: str
    heading: str
    text: str


def sections(wiki: Wiki) -> list[Section]:
    out: list[Section] = []
    for page in wiki.pages():
        pg = wiki.read(page)
        if pg is None:
            continue
        title = pg.meta.get("title", page)
        desc = pg.meta.get("description", "")
        tags = " ".join(pg.meta.get("tags") or [])
        body = pg.body
        marks = list(_HEADING_RE.finditer(body))
        if not marks:
            out.append(Section(page, title, "", title, f"{desc}\n{tags}\n{body}"))
            continue
        lead = body[: marks[0].start()].strip()
        if lead or desc:
            out.append(Section(page, title, "", title, f"{desc}\n{tags}\n{lead}"))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
            heading = m.group(2)
            out.append(Section(page, title, slug(heading), heading, body[m.start() : end].strip()))
    return out


@dataclass
class Hit:
    page: str
    anchor: str
    title: str
    heading: str
    score: float
    snippet: str


def search(wiki: Wiki, query: str, limit: int = 8) -> list[Hit]:
    secs = sections(wiki)
    if not secs:
        return []
    docs = [tokens(f"{s.page_title} {s.heading} {s.heading} {s.text}") for s in secs]
    n = len(docs)
    avgdl = sum(len(d) for d in docs) / n
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    q = tokens(query)
    k1, b = 1.4, 0.75
    hits = []
    for s, d in zip(secs, docs, strict=True):
        tf = Counter(d)
        score = 0.0
        for t in q:
            if t not in tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avgdl))
        if score > 0:
            hits.append(Hit(s.page, s.anchor, s.page_title, s.heading, round(score, 3), _snippet(s.text, q)))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]


def _snippet(text: str, q: list[str], width: int = 220) -> str:
    flat = re.sub(r"\s+", " ", text)
    low = flat.lower()
    pos = min((low.find(t) for t in q if low.find(t) >= 0), default=0)
    start = max(0, pos - 60)
    return ("..." if start else "") + flat[start : start + width] + ("..." if start + width < len(flat) else "")


def read_section(wiki: Wiki, page: str, anchor: str | None = None) -> str | None:
    pg = wiki.read(page)
    if pg is None:
        return None
    if not anchor:
        return pg.body
    for s in sections(wiki):
        if s.page == page and s.anchor == anchor:
            return s.text
    return None
