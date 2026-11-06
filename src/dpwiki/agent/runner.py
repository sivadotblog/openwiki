"""Run lifecycle: preflight -> plan -> page jobs -> finalize.

Progress is saved after every page job in wiki/.run.json, so an interrupted run
resumes where it stopped instead of starting over.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from .. import PRODUCER
from ..claims import ClaimsStore, check
from ..config import Settings
from ..finalize import FinalizeReport, finalize, now_iso, snapshot
from ..sources import Registry
from ..state import diff_sources, load_json, save_json
from ..wiki import Wiki
from . import prompts, tools
from .llm import LLM

Log = Callable[[str], None]


@dataclass
class RunResult:
    mode: str
    plan_summary: str = ""
    jobs: list[dict] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    report: FinalizeReport | None = None
    skipped: bool = False


def preflight(settings: Settings, registry: Registry, wiki: Wiki, store: ClaimsStore) -> dict:
    items = registry.scan()
    prev = load_json(settings.state_path).get("sources", {})
    diff = diff_sources(prev, items)
    attention = {}
    for page in store.pages():
        st = check(store.load(page), registry)
        if st.needs_attention:
            attention[page] = {"stale": st.stale, "unresolved": st.unresolved}
    # Pages that cite a changed or removed source also need a look, even if
    # their specific line ranges did not move.
    touched_sources = set(diff.changed) | set(diff.removed)
    cites = {}
    for page in store.pages():
        pc = store.load(page)
        hit = sorted({e.resource.split("#")[0] for c in pc.claims for e in c.evidence} & touched_sources)
        if hit:
            cites[page] = hit
    return {"items": items, "diff": diff, "attention": attention, "cites_changed": cites}


def _plan(settings: Settings, llm: LLM, wiki: Wiki, pf: dict, init: bool) -> tuple[str, list[dict]]:
    system = prompts.PLANNER.format(
        title=settings.title,
        instructions=settings.instructions() or "(none)",
        sections=", ".join(settings.sections) or "(any)",
        max_pages=settings.model.max_pages_per_run,
        safety=prompts.SAFETY,
    )
    items = pf["items"]
    manifest = "\n".join(f"{i.uri}  ({i.kind})" for i in items[:600])
    diff = pf["diff"]
    user = f"""Run mode: {"init (build the wiki from scratch)" if init else "update"}

Existing pages:
{json.dumps(wiki.catalog(), indent=1) if wiki.pages() else "(none)"}

Source manifest ({len(items)} items):
{manifest}

Source changes since last run: {diff.summary()}
added: {json.dumps(diff.added[:200])}
changed: {json.dumps(diff.changed[:200])}
removed: {json.dumps(diff.removed[:200])}

Pages with stale or unresolved claims:
{json.dumps(pf["attention"], indent=1) or "{}"}

Pages citing changed or removed sources:
{json.dumps(pf["cites_changed"], indent=1) or "{}"}

Plan the work and call submit_plan."""
    resp = llm.create(
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[tools.SUBMIT_PLAN],
        tool_choice={"type": "tool", "name": "submit_plan"},
        max_tokens=8000,
    )
    for b in resp["content"]:
        if b["type"] == "tool_use" and b["name"] == "submit_plan":
            inp = b["input"]
            jobs = inp.get("jobs", [])[: settings.model.max_pages_per_run]
            return inp.get("summary", ""), jobs
    raise RuntimeError("planner did not call submit_plan")


def _run_job(settings: Settings, llm: LLM, ctx: tools.ToolContext, job: dict, log: Log) -> bool:
    ctx.job_path = job["path"]
    ctx.done = False
    system = prompts.WRITER.format(
        title=settings.title,
        instructions=settings.instructions() or "(none)",
        job=json.dumps(job, indent=1),
        safety=prompts.SAFETY,
    )
    first = (
        f"Delete {job['path']} if it is no longer justified, otherwise update it."
        if job.get("action") == "delete"
        else f"Write {job['path']} now."
    )
    messages: list[dict] = [{"role": "user", "content": first}]
    for _ in range(settings.model.max_page_turns):
        resp = llm.create(system=system, messages=messages, tools=tools.WRITER_TOOLS, max_tokens=16000)
        messages.append({"role": "assistant", "content": resp["content"]})
        uses = [b for b in resp["content"] if b["type"] == "tool_use"]
        if not uses:
            messages.append({"role": "user", "content": "Call submit_page (or delete_page) to finish this job."})
            continue
        results = []
        for u in uses:
            out = tools.handle(ctx, u["name"], u["input"] or {})
            results.append({"type": "tool_result", "tool_use_id": u["id"], "content": out})
        messages.append({"role": "user", "content": results})
        if ctx.done:
            return True
    log(f"  gave up on {job['path']} after {settings.model.max_page_turns} turns")
    return False


def run(
    settings: Settings,
    llm: LLM,
    *,
    init: bool = False,
    force: bool = False,
    log: Log = print,
) -> RunResult:
    registry = Registry.from_settings(settings)
    wiki = Wiki(settings.wiki_dir)
    store = ClaimsStore(settings.claims_dir)
    mode = "init" if init else "update"
    result = RunResult(mode=mode)

    pf = preflight(settings, registry, wiki, store)
    log(
        f"preflight: {len(pf['items'])} source items; {pf['diff'].summary()}; "
        f"{len(pf['attention'])} pages need attention"
    )

    run_state = load_json(settings.run_path)
    if run_state.get("jobs") and not force:
        log(f"resuming run started {run_state.get('started')}")
        jobs = run_state["jobs"]
        result.plan_summary = run_state.get("summary", "")
        completed = set(run_state.get("completed", []))
        snap = run_state["snapshot"]
    else:
        if not init and pf["diff"].empty and not pf["attention"] and not force:
            log("wiki is up to date")
            result.skipped = True
            result.report = finalize(wiki, store, registry, snapshot(wiki), title=settings.title)
            return result
        snap = snapshot(wiki)
        result.plan_summary, jobs = _plan(settings, llm, wiki, pf, init)
        completed = set()
        run_state = {
            "started": now_iso(),
            "mode": mode,
            "summary": result.plan_summary,
            "jobs": jobs,
            "completed": [],
            "snapshot": snap,
        }
        save_json(settings.run_path, run_state)
        log(f"plan: {len(jobs)} jobs. {result.plan_summary}")

    result.jobs = jobs
    ctx = tools.ToolContext(wiki=wiki, store=store, registry=registry, log=log)
    for job in jobs:
        if job["path"] in completed:
            continue
        log(f"[{job.get('action', 'update')}] {job['path']}")
        try:
            ok = _run_job(settings, llm, ctx, job, log)
        except Exception as e:  # keep going; one bad page should not sink the run
            log(f"  error: {e}")
            ok = False
        if ok:
            completed.add(job["path"])
            result.completed.append(job["path"])
            run_state["completed"] = sorted(completed)
            save_json(settings.run_path, run_state)
        else:
            result.failed.append(job["path"])

    result.report = finalize(
        wiki, store, registry, snap, touched=ctx.touched | set(completed), title=settings.title, producer=PRODUCER
    )
    save_json(
        settings.state_path,
        {
            "last_run": now_iso(),
            "producer": PRODUCER,
            "sources": {i.uri: i.version for i in pf["items"]},
        },
    )
    if not result.failed:
        settings.run_path.unlink(missing_ok=True)
    return result


def ask(settings: Settings, llm: LLM, question: str, log: Log = print, max_turns: int = 8) -> str:
    wiki = Wiki(settings.wiki_dir)
    ctx = tools.ToolContext(
        wiki=wiki, store=ClaimsStore(settings.claims_dir), registry=Registry.from_settings(settings), log=log
    )
    system = prompts.ASK.format(title=settings.title, safety=prompts.SAFETY)
    messages: list[dict] = [{"role": "user", "content": question}]
    for _ in range(max_turns):
        resp = llm.create(system=system, messages=messages, tools=tools.ASK_TOOLS, max_tokens=4000)
        messages.append({"role": "assistant", "content": resp["content"]})
        uses = [b for b in resp["content"] if b["type"] == "tool_use"]
        if not uses:
            return "\n".join(b["text"] for b in resp["content"] if b["type"] == "text")
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": u["id"], "content": tools.handle(ctx, u["name"], u["input"])}
                    for u in uses
                ],
            }
        )
    return "No answer within the turn limit."
