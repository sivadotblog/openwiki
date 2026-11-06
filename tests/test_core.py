import pytest

from dpwiki import frontmatter as fm
from dpwiki.claims import ClaimsStore, apply_decisions, check
from dpwiki.finalize import check_links
from dpwiki.search import read_section, search
from dpwiki.sources import Registry, parse_uri
from dpwiki.wiki import Wiki, WikiPathError


def test_seed_wiki_is_clean(settings):
    reg, store, wiki = Registry.from_settings(settings), ClaimsStore(settings.claims_dir), Wiki(settings.wiki_dir)
    assert len(wiki.pages()) >= 10
    for page in wiki.pages():
        assert fm.validate(wiki.read(page)) == [], page
        st = check(store.load(page), reg)
        assert st.clean and not st.needs_attention, page
    assert check_links(wiki) == []


def test_edit_makes_claim_stale(settings):
    reg, store = Registry.from_settings(settings), ClaimsStore(settings.claims_dir)
    tf = settings.root / "sources/repos/platform-infra/terraform/snowflake/warehouses.tf"
    tf.write_text(tf.read_text().replace("auto_suspend        = 120", "auto_suspend        = 300"))
    st = check(store.load("platforms/snowflake.md"), reg)
    assert len(st.stale) == 1
    # unrelated pages stay clean
    assert not check(store.load("orchestration/airflow.md"), reg).needs_attention


def test_moving_lines_does_not_make_claims_stale(settings):
    reg, store = Registry.from_settings(settings), ClaimsStore(settings.claims_dir)
    dag = settings.root / "sources/repos/orchestration/airflow/dags/orders_ingest.py"
    dag.write_text("# new header comment\n# another\n" + dag.read_text())
    st = check(store.load("orchestration/airflow.md"), reg)
    assert not st.needs_attention


def test_deleted_source_makes_claims_unresolved(settings):
    reg, store = Registry.from_settings(settings), ClaimsStore(settings.claims_dir)
    (settings.root / "sources/docs/runbooks/airflow-backfill.md").unlink()
    st = check(store.load("runbooks/airflow-backfill.md"), reg)
    assert len(st.unresolved) == 4


def test_catalog_change_is_detected(settings):
    reg, store = Registry.from_settings(settings), ClaimsStore(settings.claims_dir)
    p = settings.root / "sources/catalog/unity_catalog_export.json"
    p.write_text(p.read_text().replace('"freshness_sla_hours": 30', '"freshness_sla_hours": 36'))
    st = check(store.load("catalog/commerce-tables.md"), reg)
    assert len(st.stale) == 2  # both daily_revenue claims


def test_claim_decisions(settings):
    reg, store = Registry.from_settings(settings), ClaimsStore(settings.claims_dir)
    pc = store.load("runbooks/oncall.md")
    first = pc.claims[0].id
    new, errors = apply_decisions(
        pc,
        reg,
        {
            "retract": [first],
            "add": [
                {"statement": "ok", "evidence": ["src://team-docs/oncall.md#L1-L1"]},
                {"statement": "bad", "evidence": ["src://team-docs/missing.md"]},
                {"statement": "escape", "evidence": ["src://team-docs/../../wiki.toml"]},
            ],
            "confirm": ["c-doesnotexist"],
        },
    )
    assert first not in {c.id for c in new.claims}
    assert any(c.statement == "ok" for c in new.claims)
    assert len(errors) == 3


def test_uri_and_path_containment(settings):
    with pytest.raises(ValueError):
        parse_uri("/etc/passwd")
    reg = Registry.from_settings(settings)
    assert reg.read("src://team-docs/../../../etc/passwd") is None
    wiki = Wiki(settings.wiki_dir)
    for bad in ["../x.md", ".claims/a.md", "index.md", "Runbooks/X.md", "a/b.txt"]:
        with pytest.raises(WikiPathError):
            wiki.check_path(bad, for_write=True)


def test_frontmatter_validate_and_repair():
    pg = fm.parse("---\ntype: wat\nstatus: shiny\ngenerated: nope\n---\n# Hello\n")
    issues = fm.validate(pg)
    assert any("unknown type" in i for i in issues) and any("status" in i for i in issues)
    fixed = fm.repair(pg, "Fallback")
    assert fm.validate(fixed) == []
    assert fixed.meta["title"] == "Hello"


def test_search_and_read(settings):
    wiki = Wiki(settings.wiki_dir)
    hits = search(wiki, "who do I page for a SEV1")
    assert hits and hits[0].page == "runbooks/oncall.md"
    text = read_section(wiki, "orchestration/airflow.md", "orders_ingest")
    assert text and "05:30 UTC" in text
