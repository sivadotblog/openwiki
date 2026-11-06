"""End-to-end lifecycle with a scripted model: drift -> plan -> revise -> finalize."""

from dpwiki import frontmatter as fm
from dpwiki.agent.runner import ask, preflight, run
from dpwiki.agent.scripted import ScriptedLLM
from dpwiki.claims import ClaimsStore, check
from dpwiki.sources import Registry
from dpwiki.wiki import Wiki


def quiet(_):
    pass


def test_up_to_date_run_skips_model(settings):
    llm = ScriptedLLM({"jobs": []}, {})
    res = run(settings, llm, log=quiet)
    assert res.skipped and llm.calls == []


def test_update_after_source_change(settings):
    tf = settings.root / "sources/repos/platform-infra/terraform/snowflake/warehouses.tf"
    tf.write_text(tf.read_text().replace("auto_suspend        = 120", "auto_suspend        = 300"))

    reg, store, wiki = Registry.from_settings(settings), ClaimsStore(settings.claims_dir), Wiki(settings.wiki_dir)
    pf = preflight(settings, reg, wiki, store)
    tf_uri = "src://platform-infra/terraform/snowflake/warehouses.tf"
    assert pf["diff"].changed == [tf_uri]
    assert "platforms/snowflake.md" in pf["attention"]
    stale_id = pf["attention"]["platforms/snowflake.md"]["stale"][0]

    old = wiki.read("platforms/snowflake.md")
    lines = tf.read_text().splitlines()
    s = next(i for i, ln in enumerate(lines, 1) if 'resource "snowflake_warehouse" "transform_wh"' in ln)
    e = next(i for i, ln in enumerate(lines, 1) if 'scaling_policy      = "STANDARD"' in ln)
    plan = {
        "summary": "TRANSFORM_WH auto-suspend changed",
        "jobs": [
            {
                "path": "platforms/snowflake.md",
                "action": "update",
                "title": "Snowflake",
                "purpose": "fix auto-suspend",
                "sources": [tf_uri],
            }
        ],
    }
    page = {
        **{k: old.meta[k] for k in ("type", "title", "description", "tags", "owner", "status")},
        "body": old.body.replace("| 120 s |", "| 300 s |"),
        "claims": {
            "revise": [
                {
                    "id": stale_id,
                    "statement": "TRANSFORM_WH is size LARGE, auto-suspends after 300 seconds, and scales from 1 to 3 clusters with the STANDARD policy.",
                    "evidence": [f"{tf_uri}#L{s}-L{e}"],
                }
            ]
        },
    }
    before = {p: wiki.read(p).meta.get("generated") for p in wiki.pages()}
    res = run(settings, ScriptedLLM(plan, {"platforms/snowflake.md": page}), log=quiet)

    assert res.completed == ["platforms/snowflake.md"] and not res.failed
    assert res.report.attention == {}
    assert not check(store.load("platforms/snowflake.md"), reg).needs_attention
    after = wiki.read("platforms/snowflake.md")
    assert "300 s" in after.body and fm.validate(after) == []
    assert after.meta["generated"] != before["platforms/snowflake.md"]
    # untouched pages keep their provenance
    assert wiki.read("runbooks/oncall.md").meta["generated"] == before["runbooks/oncall.md"]
    assert not settings.run_path.exists()
    # next run has nothing to do
    assert run(settings, ScriptedLLM({"jobs": []}, {}), log=quiet).skipped


def test_rejected_page_is_not_written(settings):
    from dpwiki.agent import tools

    ctx = tools.ToolContext(
        Wiki(settings.wiki_dir),
        ClaimsStore(settings.claims_dir),
        Registry.from_settings(settings),
        job_path="runbooks/new.md",
        log=quiet,
    )
    out = tools.handle(
        ctx,
        "submit_page",
        {
            "path": "runbooks/new.md",
            "type": "runbook",
            "title": "New",
            "description": "d",
            "body": "# New\n",
            "claims": {"add": [{"statement": "x", "evidence": ["src://team-docs/nope.md"]}]},
        },
    )
    assert out.startswith("error") and not (settings.wiki_dir / "runbooks/new.md").exists()


def test_read_source_numbers_lines(settings):
    from dpwiki.agent import tools

    ctx = tools.ToolContext(
        Wiki(settings.wiki_dir), ClaimsStore(settings.claims_dir), Registry.from_settings(settings), log=quiet
    )
    out = tools.handle(ctx, "read_source", {"uri": "src://team-docs/oncall.md"})
    assert " 1 | # Data platform on-call" in out


def test_ask_uses_wiki_tools(settings):
    llm = ScriptedLLM({}, {}, answer="Page dp-platform-oncall. See runbooks/oncall.md#severity")
    out = ask(settings, llm, "who do I page for a SEV1", log=quiet)
    assert "runbooks/oncall.md" in out
    assert llm.calls[0]["tools"] == ["search_wiki", "read_page"]
