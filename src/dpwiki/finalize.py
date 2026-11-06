"""Deterministic post-authoring passes.

These run after the agent writes pages, in a fixed order, so the committed wiki
is consistent no matter what the agent did:

1. repair frontmatter that fails validation
2. drop claim sidecars for deleted pages
3. sync each page's `sources` field from its claim evidence
4. stamp `generated` only on pages whose body actually changed
5. stamp `verified` on pages whose claims were all checked clean this run
6. regenerate index.md in every directory
7. report broken internal links
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import PurePosixPath

from . import PRODUCER
from . import frontmatter as fm
from .claims import ClaimsStore, check
from .sources import Registry
from .wiki import Wiki

INDEX_START = "<!-- dpwiki:index:start -->"
INDEX_END = "<!-- dpwiki:index:end -->"
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class FinalizeReport:
    repaired: list[str] = field(default_factory=list)
    generated: list[str] = field(default_factory=list)
    verified: list[str] = field(default_factory=list)
    indexes: list[str] = field(default_factory=list)
    broken_links: list[tuple[str, str]] = field(default_factory=list)
    dropped_sidecars: list[str] = field(default_factory=list)
    attention: dict[str, dict] = field(default_factory=dict)


def snapshot(wiki: Wiki) -> dict[str, dict]:
    """Record body hashes and prior provenance before the agent runs."""
    snap = {}
    for page in wiki.pages():
        pg = wiki.read(page)
        if pg is None:
            continue
        snap[page] = {"hash": pg.body_hash, "generated": pg.meta.get("generated")}
    return snap


def _strip_fragment(uri: str) -> str:
    return uri.split("#", 1)[0]


def finalize(
    wiki: Wiki,
    store: ClaimsStore,
    registry: Registry,
    snap: dict[str, dict],
    *,
    touched: set[str] | None = None,
    title: str = "Wiki",
    producer: str = PRODUCER,
) -> FinalizeReport:
    rep = FinalizeReport()
    ts = now_iso()
    pages = wiki.pages()
    touched = touched or set()

    # 2. orphaned sidecars
    for sc in store.pages():
        if sc not in pages:
            store.delete(sc)
            rep.dropped_sidecars.append(sc)

    for page in pages:
        pg = wiki.read(page)
        assert pg is not None
        changed = False

        # 1. repair
        if fm.validate(pg):
            pg = fm.repair(pg, PurePosixPath(page).stem.replace("-", " ").title())
            rep.repaired.append(page)
            changed = True

        # 3. sources from claims
        pc = store.load(page)
        resources = sorted({_strip_fragment(e.resource) for c in pc.claims for e in c.evidence})
        new_sources = [{"resource": r} for r in resources]
        if new_sources != (pg.meta.get("sources") or []):
            if new_sources:
                pg.meta["sources"] = new_sources
            else:
                pg.meta.pop("sources", None)
            changed = True

        # 4. generated provenance follows real body changes only
        prior = snap.get(page)
        if prior is None or prior["hash"] != pg.body_hash:
            pg.meta["generated"] = {"by": producer, "at": ts}
            rep.generated.append(page)
            changed = True
        elif pg.meta.get("generated") != prior.get("generated"):
            if prior.get("generated"):
                pg.meta["generated"] = prior["generated"]
            else:
                pg.meta.pop("generated", None)
            changed = True

        # 5. verification
        st = check(pc, registry)
        if st.needs_attention:
            rep.attention[page] = {"stale": st.stale, "unresolved": st.unresolved}
        elif page in touched and pc.claims:
            pg.meta["verified"] = {"by": producer, "at": ts}
            pc.verified = pg.meta["verified"]
            rep.verified.append(page)
            changed = True

        if pc.claims:
            pc.page_hash = pg.body_hash
            store.save(pc)

        if changed:
            wiki.write_raw(page, fm.render(pg))

    # 6. indexes
    rep.indexes = sync_indexes(wiki, title)

    # 7. links
    rep.broken_links = check_links(wiki)
    return rep


def _dir_listing(wiki: Wiki, d: str) -> tuple[list[tuple[str, str, str]], list[str]]:
    pages, subdirs = [], set()
    for page in wiki.pages():
        pp = PurePosixPath(page)
        parent = "" if str(pp.parent) == "." else str(pp.parent)
        if parent == d:
            pg = wiki.read(page)
            m = pg.meta if pg else {}
            pages.append((pp.name, m.get("title") or pp.stem, m.get("description", "")))
        elif (parent + "/").startswith(d + "/" if d else ""):
            rest = parent[len(d) + 1 :] if d else parent
            subdirs.add(rest.split("/")[0])
    return sorted(pages, key=lambda x: x[1].lower()), sorted(subdirs)


def sync_indexes(wiki: Wiki, title: str) -> list[str]:
    dirs = {""}
    for page in wiki.pages():
        parts = PurePosixPath(page).parts[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add("/".join(parts[:i]))
    written = []
    for d in sorted(dirs):
        pages, subdirs = _dir_listing(wiki, d)
        lines = [INDEX_START, ""]
        if subdirs:
            lines.append("## Sections\n")
            for s in subdirs:
                lines.append(f"- [{s.replace('-', ' ').title()}]({s}/index.md)")
            lines.append("")
        if pages:
            lines.append("## Pages\n")
            for name, t, desc in pages:
                lines.append(f"- [{t}]({name})" + (f": {desc}" if desc else ""))
            lines.append("")
        lines.append(INDEX_END)
        block = "\n".join(lines)

        index_page = f"{d}/index.md" if d else "index.md"
        p = wiki.check_path(index_page)
        heading = title if not d else d.split("/")[-1].replace("-", " ").title()
        if p.exists():
            text = p.read_text(encoding="utf-8")
            if INDEX_START in text and INDEX_END in text:
                pre = text.split(INDEX_START)[0]
                post = text.split(INDEX_END, 1)[1]
                new = pre + block + post
            else:
                new = text.rstrip() + "\n\n" + block + "\n"
        else:
            new = f"---\ntype: index\ntitle: {heading}\n---\n\n# {heading}\n\n{block}\n"
        if not p.exists() or p.read_text(encoding="utf-8") != new:
            wiki.write_raw(index_page, new)
            written.append(index_page)
    return written


def check_links(wiki: Wiki) -> list[tuple[str, str]]:
    broken = []
    for page in wiki.pages(include_index=True):
        pg = wiki.read(page)
        if pg is None:
            continue
        base = PurePosixPath(page).parent
        for target in _LINK_RE.findall(pg.body):
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            path = target.split("#", 1)[0]
            if not path.endswith(".md"):
                continue
            parts: list[str] = []
            for part in (base / path).parts:
                if part == "..":
                    if parts:
                        parts.pop()
                elif part != ".":
                    parts.append(part)
            resolved = "/".join(parts)
            try:
                ok = wiki.check_path(resolved).is_file()
            except ValueError:
                ok = False
            if not ok:
                broken.append((page, target))
    return broken
