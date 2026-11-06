"""Read-only MCP server so coding agents (Claude Code, Cursor, Copilot) can use the wiki.

Tools are local and model-free. Register with Claude Code:

    claude mcp add dpwiki -- dpwiki --config /path/to/wiki.toml mcp
"""

from __future__ import annotations

from .claims import ClaimsStore, check
from .config import Settings
from .search import read_section, search
from .sources import Registry
from .wiki import Wiki


def serve(settings: Settings) -> None:
    try:  # mcp >= 2
        from mcp.server.mcpserver import MCPServer as Server
    except ImportError:
        try:  # mcp 1.x
            from mcp.server.fastmcp import FastMCP as Server
        except ImportError as e:  # pragma: no cover
            raise SystemExit("install the mcp extra: pip install 'dpwiki[mcp]'") from e

    wiki = Wiki(settings.wiki_dir)
    mcp = Server(
        "dpwiki",
        instructions=(
            f"Search and read '{settings.title}'. Use wiki_search for concrete questions about the "
            "data platform (Databricks, Snowflake, Airflow, Prefect, Bigeye, runbooks, datasets), then "
            "wiki_read the best sections. Stop once you have grounded the answer."
        ),
    )

    @mcp.tool()
    def wiki_search(query: str, limit: int = 8) -> list[dict]:
        """Ranked search over wiki sections. Returns page, anchor, heading, score, snippet."""
        return [h.__dict__ for h in search(wiki, query, limit=limit)]

    @mcp.tool()
    def wiki_read(page: str, anchor: str = "") -> str:
        """Read a full page, or one section when anchor is given."""
        text = read_section(wiki, page, anchor or None)
        return text if text is not None else f"not found: {page}#{anchor}"

    @mcp.tool()
    def wiki_list() -> list[dict]:
        """List all pages with type, title, and description."""
        return wiki.catalog()

    @mcp.tool()
    def wiki_freshness(page: str) -> dict:
        """Whether a page's claims still match their sources (clean/stale/unresolved counts)."""
        st = check(ClaimsStore(settings.claims_dir).load(page), Registry.from_settings(settings))
        pg = wiki.read(page)
        return {
            "page": page,
            "clean": len(st.clean),
            "stale": len(st.stale),
            "unresolved": len(st.unresolved),
            "verified": (pg.meta.get("verified") if pg else None),
        }

    mcp.run()
