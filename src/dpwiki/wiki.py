"""Wiki page store with path containment.

Pages are Markdown files under the wiki directory. Reserved paths:
  .claims/   claim sidecars (dpwiki owned)
  .state.json, .run.json   run state (dpwiki owned)
  index.md   generated per directory
  INSTRUCTIONS.md   human-owned charter for the agent
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from . import frontmatter as fm

RESERVED_NAMES = {"index.md", "INSTRUCTIONS.md", "log.md"}
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*\.md$")


class WikiPathError(ValueError):
    pass


class Wiki:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def check_path(self, page: str, *, for_write: bool = False) -> Path:
        pp = PurePosixPath(page)
        if pp.is_absolute() or ".." in pp.parts or any(p.startswith(".") for p in pp.parts):
            raise WikiPathError(f"invalid page path: {page}")
        if for_write:
            if pp.name in RESERVED_NAMES:
                raise WikiPathError(f"{pp.name} is maintained by dpwiki or humans, not the agent")
            if not _SLUG_RE.match(page):
                raise WikiPathError(
                    f"page path must be lowercase kebab-case ending in .md, e.g. runbooks/airflow-backfill.md (got {page})"
                )
        p = (self.root / page).resolve()
        if not p.is_relative_to(self.root):
            raise WikiPathError(f"page path escapes wiki: {page}")
        return p

    def exists(self, page: str) -> bool:
        return self.check_path(page).is_file()

    def read(self, page: str) -> fm.Page | None:
        p = self.check_path(page)
        if not p.is_file():
            return None
        return fm.parse(p.read_text(encoding="utf-8"))

    def write(self, page: str, pg: fm.Page) -> None:
        p = self.check_path(page, for_write=True)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(fm.render(pg), encoding="utf-8")

    def write_raw(self, page: str, text: str) -> None:
        """For dpwiki-owned files such as index.md."""
        p = self.check_path(page)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def delete(self, page: str) -> None:
        self.check_path(page, for_write=True).unlink(missing_ok=True)

    def pages(self, *, include_index: bool = False) -> list[str]:
        out = []
        for p in sorted(self.root.rglob("*.md")):
            rel = p.relative_to(self.root).as_posix()
            if any(part.startswith(".") for part in PurePosixPath(rel).parts):
                continue
            name = PurePosixPath(rel).name
            if name in RESERVED_NAMES and not (include_index and name == "index.md"):
                continue
            out.append(rel)
        return out

    def catalog(self) -> list[dict]:
        """Compact listing for prompts: path, type, title, description."""
        rows = []
        for page in self.pages():
            pg = self.read(page)
            m = pg.meta if pg else {}
            rows.append(
                {
                    "path": page,
                    "type": m.get("type", ""),
                    "title": m.get("title", ""),
                    "description": m.get("description", ""),
                }
            )
        return rows
