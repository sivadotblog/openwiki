"""Filesystem connector: local repo checkouts and documentation folders.

URIs look like src://<source-id>/<relative/path>[#L10-L42].
Whole-file versions hash the file. Line-range versions hash the selected lines and
can relocate the same text if edits above it moved it, so moving code does not
mark a claim stale. Only a real content change does.
"""

from __future__ import annotations

import fnmatch
import hashlib
from pathlib import Path, PurePosixPath

from .base import Connector, SourceItem

MAX_BYTES = 400_000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "target", "dist"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _match(rel: str, patterns: list[str]) -> bool:
    for p in patterns:
        if fnmatch.fnmatch(rel, p):
            return True
        if p.startswith("**/") and fnmatch.fnmatch(rel, p[3:]):  # root-level files
            return True
    return False


class FilesystemConnector(Connector):
    scheme = "src"

    def __init__(self, source_id: str, root: Path, include: list[str], exclude: list[str]):
        self.id = source_id
        self.root = root.resolve()
        self.include = include or ["**/*"]
        self.exclude = exclude

    # -- containment -------------------------------------------------------
    def _path(self, key: str) -> Path | None:
        pp = PurePosixPath(key)
        if pp.is_absolute() or ".." in pp.parts or any(p in SKIP_DIRS for p in pp.parts):
            return None
        p = self.root / key
        if p.is_symlink():
            return None
        p = p.resolve()
        if not p.is_relative_to(self.root) or not p.is_file():
            return None
        return p

    def _text(self, key: str) -> str | None:
        p = self._path(key)
        if p is None or p.stat().st_size > MAX_BYTES:
            return None
        try:
            return p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None

    # -- contract ----------------------------------------------------------
    def scan(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        if not self.root.exists():
            return items
        for p in sorted(self.root.rglob("*")):
            if not p.is_file() or p.is_symlink():
                continue
            rel = p.relative_to(self.root).as_posix()
            if any(part in SKIP_DIRS for part in PurePosixPath(rel).parts):
                continue
            if not _match(rel, self.include) or _match(rel, self.exclude):
                continue
            text = self._text(rel)
            if text is None:
                continue
            items.append(
                SourceItem(
                    uri=self.uri(rel),
                    title=rel,
                    version=f"file-v1:sha256:{_sha(text)}",
                    kind="doc" if rel.endswith(".md") else "file",
                    size=len(text),
                )
            )
        return items

    def read(self, key: str, start: int | None = None, end: int | None = None) -> str | None:
        text = self._text(key)
        if text is None:
            return None
        if start is None:
            return text
        lines = text.splitlines()
        return "\n".join(lines[start - 1 : (end or start)])

    def version(self, key: str, fragment: str | None, prior: str | None) -> str | None:
        text = self._text(key)
        if text is None:
            return None
        if not fragment:
            return f"file-v1:sha256:{_sha(text)}"
        start, end = parse_fragment(fragment)
        lines = text.splitlines()
        n = end - start + 1
        # 1. If the prior selected text still exists somewhere in the file (moved or not),
        #    the claim's evidence did not change.
        if prior and prior.startswith("lines-v1:"):
            _, plen, _, phash = prior.split(":", 3)
            plen = int(plen)
            hits = [i for i in range(0, max(0, len(lines) - plen + 1)) if _sha("\n".join(lines[i : i + plen])) == phash]
            if len(hits) >= 1:
                return prior
        # 2. Otherwise version whatever is at the hinted span now.
        if start > len(lines):
            return None
        sel = "\n".join(lines[start - 1 : end])
        return f"lines-v1:{n}:sha256:{_sha(sel)}"


def parse_fragment(fragment: str) -> tuple[int, int]:
    f = fragment.lstrip("#")
    if not f.startswith("L"):
        raise ValueError(f"bad line fragment: {fragment}")
    parts = f.split("-")
    start = int(parts[0][1:])
    end = int(parts[1][1:]) if len(parts) > 1 else start
    if start < 1 or end < start:
        raise ValueError(f"bad line range: {fragment}")
    return start, end
