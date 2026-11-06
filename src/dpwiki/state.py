"""Run state: the source manifest from the last run, and resumable page-job progress."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .sources import SourceItem


@dataclass
class SourceDiff:
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.added or self.changed or self.removed)

    def summary(self) -> str:
        return f"{len(self.added)} added, {len(self.changed)} changed, {len(self.removed)} removed"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def diff_sources(prev: dict[str, str], current: list[SourceItem]) -> SourceDiff:
    cur = {i.uri: i.version for i in current}
    d = SourceDiff()
    for uri, v in sorted(cur.items()):
        if uri not in prev:
            d.added.append(uri)
        elif prev[uri] != v:
            d.changed.append(uri)
    d.removed = sorted(set(prev) - set(cur))
    return d
