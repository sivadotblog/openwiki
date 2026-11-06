import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import feature_index as fi  # noqa: E402

# Real headings from the Lakebase release notes page.
CASES = {
    "Lakebase snapshots and backup schedule APIs are generally available": "ga",
    "Lakebase now available in five additional Azure regions": None,
    "Lakebase Insights moves to per-project settings, with on-demand runs (Beta)": "beta",
    "Lakebase Search supports Chinese, Japanese, and Korean full-text search": None,
    "Inbound Private Link for Lakebase Postgres connections is now generally available on Azure": "ga",
    "Lakebase observability telemetry in system tables (Beta)": "beta",
    "Lakebase backup schedule API (Beta)": "beta",
    "Lakebase Search is generally available": "ga",
    "Lakebase snapshots API (Beta)": "beta",
    "Lakebase now provides a service level agreement (SLA)": None,
    "Lakebase Postgres APIs are now generally available": "ga",
    "Lakebase Change Data Feed (CDF) is now in Public Preview": "public-preview",
    "Lakebase is now generally available on Azure": "ga",
    "Lakebase now available on Azure (Beta)": "beta",
    "Lakebase Search adds vector, keyword, and hybrid search to Postgres (Beta)": "beta",
    "Databricks CLI is now GA": "ga",
    "Omnigent coding agent meta-harness is now in Beta": "beta",
    "Databricks Runtime 19 and Databricks Runtime 19 for Machine Learning are in Beta": "beta",
    "New `INSERT REPLACE` commands (GA)": "ga",
}


def test_title_rules():
    for title, want in CASES.items():
        assert fi.classify_title(title) == want, title


def test_doc_key():
    base = "https://learn.microsoft.com/en-us/azure/databricks/release-notes/lakebase/"
    assert fi.doc_key("../../oltp/projects/snapshots#create-snapshot", base) == "oltp/projects/snapshots#create-snapshot"
    assert fi.doc_key("/azure/databricks/oltp/projects/snapshots", base) == "oltp/projects/snapshots"
    assert fi.doc_key("../release-types", base) is None
    assert fi.doc_key("https://www.databricks.com/blog/x", base) is None


PAGE = """<html><body><main>
<h1>Detect issues with Insights</h1>
<div class="IMPORTANT"><p>Important</p><p>This feature is in <a href="../../release-notes/release-types">Beta</a>.
To use it, a workspace admin must turn on <strong>Lakebase Insights</strong> from the <strong>Previews</strong> page.</p></div>
<h2 id="prereqs">Prerequisites</h2><p>text</p>
</main></body></html>"""

GA_PAGE = """<html><body><main><h1>Snapshots</h1><p>Intro</p>
<h2 id="create-snapshot">Create a snapshot</h2><p>steps</p>
<h2 id="snapshot-schedules">Create a backup schedule</h2><p>steps</p></main></body></html>"""

SECTION_PAGE = """<html><body><main><h1>Thing</h1><p>Intro</p>
<h2 id="old">Old part</h2><p>stable</p>
<h2 id="new">New part</h2><div><p>This feature is in <a href="/azure/databricks/release-notes/release-types">Public Preview</a>.</p></div>
</main></body></html>"""


def test_banners(monkeypatch=None):
    fi._cache.update({
        fi.BASE + "oltp/projects/observability-ai-insights": PAGE,
        fi.BASE + "oltp/projects/snapshots": GA_PAGE,
        fi.BASE + "x/thing": SECTION_PAGE,
    })
    b = fi.page_banner("oltp/projects/observability-ai-insights")
    assert (b.status, b.scope, b.preview_name, b.page_title) == ("beta", "page", "Lakebase Insights", "Detect issues with Insights")
    assert fi.page_banner("oltp/projects/snapshots#create-snapshot").status == "ga"
    assert fi.page_banner("oltp/projects/snapshots#gone") is None
    assert fi.page_banner("x/thing#new").status == "public-preview"
    assert fi.page_banner("x/thing#old").status == "ga"


if __name__ == "__main__":
    test_title_rules(); test_doc_key(); test_banners()
    print("ok")
