"""dpwiki command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from . import frontmatter as fm
from .claims import ClaimsStore, check
from .config import load_settings
from .finalize import finalize, snapshot
from .search import read_section, search
from .sources import Registry
from .state import diff_sources, load_json
from .wiki import Wiki


def _settings(args):
    return load_settings(Path(args.config) if args.config else None)


def cmd_sources(args) -> int:
    s = _settings(args)
    for item in Registry.from_settings(s).scan():
        print(f"{item.uri}\t{item.kind}\t{item.version[:28]}")
    return 0


def cmd_status(args) -> int:
    """Model-free health check. Exit 1 when the wiki needs an update or has errors."""
    s = _settings(args)
    reg, wiki, store = Registry.from_settings(s), Wiki(s.wiki_dir), ClaimsStore(s.claims_dir)
    items = reg.scan()
    diff = diff_sources(load_json(s.state_path).get("sources", {}), items)
    problems = 0
    print(f"{len(wiki.pages())} pages, {len(items)} source items")
    print(f"sources since last run: {diff.summary()}")
    for page in wiki.pages():
        issues = fm.validate(wiki.read(page))
        if issues:
            problems += 1
            print(f"  invalid frontmatter {page}: {'; '.join(issues)}")
    total = clean = 0
    for page in store.pages():
        st = check(store.load(page), reg)
        total += len(st.clean) + len(st.stale) + len(st.unresolved)
        clean += len(st.clean)
        if st.needs_attention:
            problems += 1
            print(f"  {page}: {len(st.stale)} stale, {len(st.unresolved)} unresolved claims")
    print(f"claims: {clean}/{total} clean")
    from .finalize import check_links

    for page, target in check_links(wiki):
        problems += 1
        print(f"  broken link in {page}: {target}")
    stale = problems > 0 or not diff.empty
    if args.json:
        print(json.dumps({"problems": problems, "source_changes": not diff.empty}))
    return 1 if (stale and args.strict) else 0


def cmd_finalize(args) -> int:
    s = _settings(args)
    wiki, store, reg = Wiki(s.wiki_dir), ClaimsStore(s.claims_dir), Registry.from_settings(s)
    snap_file = load_json(s.run_path).get("snapshot")
    rep = finalize(wiki, store, reg, snap_file or snapshot(wiki), title=s.title)
    print(
        f"repaired={len(rep.repaired)} generated={len(rep.generated)} indexes={len(rep.indexes)} "
        f"broken_links={len(rep.broken_links)}"
    )
    for p, t in rep.broken_links:
        print(f"  broken link in {p}: {t}")
    return 0


def _run(args, init: bool) -> int:
    from .agent import run
    from .agent.llm import make_llm

    s = _settings(args)
    if args.model:
        s.model.id = args.model
    try:
        llm = make_llm(s.model)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    res = run(s, llm, init=init, force=args.force)
    rep = res.report
    if rep:
        print(
            f"\ndone: {len(res.completed)} pages written, {len(res.failed)} failed, "
            f"{len(rep.verified)} verified, {len(rep.broken_links)} broken links"
        )
        for p, t in rep.broken_links:
            print(f"  broken link in {p}: {t}")
        for p, a in rep.attention.items():
            print(f"  still needs attention: {p} {a}")
    return 1 if res.failed else 0


def cmd_search(args) -> int:
    s = _settings(args)
    for h in search(Wiki(s.wiki_dir), " ".join(args.query), limit=args.limit):
        print(f"{h.page}#{h.anchor}  {h.title} > {h.heading}  ({h.score})\n    {h.snippet}")
    return 0


def cmd_read(args) -> int:
    s = _settings(args)
    page, _, anchor = args.ref.partition("#")
    text = read_section(Wiki(s.wiki_dir), page, anchor or None)
    if text is None:
        print(f"not found: {args.ref}", file=sys.stderr)
        return 1
    print(text)
    return 0


def cmd_ask(args) -> int:
    from .agent import ask
    from .agent.llm import make_llm

    s = _settings(args)
    try:
        llm = make_llm(s.model)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(ask(s, llm, " ".join(args.question), log=lambda m: None))
    return 0


def cmd_mcp(args) -> int:
    from .mcp_server import serve

    serve(_settings(args))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dpwiki", description="Agent-maintained data platform team wiki")
    p.add_argument("--config", help="path to wiki.toml (default: search upward from cwd)")
    p.add_argument("--version", action="version", version=f"dpwiki {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="build the wiki from all sources (uses the model)")
    sp.add_argument("--model")
    sp.add_argument("--force", action="store_true", help="ignore a saved partial run")
    sp.set_defaults(fn=lambda a: _run(a, True))

    sp = sub.add_parser("update", help="update pages affected by source changes (uses the model)")
    sp.add_argument("--model")
    sp.add_argument("--force", action="store_true", help="plan even if nothing changed")
    sp.set_defaults(fn=lambda a: _run(a, False))

    sp = sub.add_parser("status", help="model-free check: source drift, stale claims, links")
    sp.add_argument("--strict", action="store_true", help="exit 1 if anything needs attention")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_status)

    sp = sub.add_parser("finalize", help="re-run deterministic passes (indexes, provenance, links)")
    sp.set_defaults(fn=cmd_finalize)

    sp = sub.add_parser("sources", help="list source items and versions")
    sp.set_defaults(fn=cmd_sources)

    sp = sub.add_parser("search", help="search the wiki (model-free)")
    sp.add_argument("query", nargs="+")
    sp.add_argument("--limit", type=int, default=8)
    sp.set_defaults(fn=cmd_search)

    sp = sub.add_parser("read", help="read a page or page#section")
    sp.add_argument("ref")
    sp.set_defaults(fn=cmd_read)

    sp = sub.add_parser("ask", help="answer a question from the wiki (uses the model)")
    sp.add_argument("question", nargs="+")
    sp.set_defaults(fn=cmd_ask)

    sp = sub.add_parser("mcp", help="serve wiki search/read over MCP (stdio) for Claude Code and others")
    sp.set_defaults(fn=cmd_mcp)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
