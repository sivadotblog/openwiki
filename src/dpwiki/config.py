"""Load wiki.toml into typed settings."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SourceConfig:
    id: str
    kind: str
    path: Path
    include: list[str] = field(default_factory=lambda: ["**/*"])
    exclude: list[str] = field(default_factory=list)


@dataclass
class ModelConfig:
    provider: str = "anthropic"
    id: str = "claude-sonnet-5-5"
    max_page_turns: int = 12
    max_pages_per_run: int = 25


@dataclass
class Settings:
    root: Path
    title: str
    wiki_dir: Path
    instructions_path: Path
    sections: list[str]
    model: ModelConfig
    sources: list[SourceConfig]

    @property
    def claims_dir(self) -> Path:
        return self.wiki_dir / ".claims"

    @property
    def state_path(self) -> Path:
        return self.wiki_dir / ".state.json"

    @property
    def run_path(self) -> Path:
        return self.wiki_dir / ".run.json"

    def instructions(self) -> str:
        if self.instructions_path.exists():
            return self.instructions_path.read_text(encoding="utf-8")
        return ""


def find_config(start: Path | None = None) -> Path:
    env = os.environ.get("DPWIKI_CONFIG")
    if env:
        return Path(env).resolve()
    cur = (start or Path.cwd()).resolve()
    for d in [cur, *cur.parents]:
        cand = d / "wiki.toml"
        if cand.exists():
            return cand
    raise FileNotFoundError("wiki.toml not found in this directory or any parent")


def load_settings(config_path: Path | None = None) -> Settings:
    path = config_path or find_config()
    root = path.parent.resolve()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    wiki = data.get("wiki", {})
    model = data.get("model", {})

    # Environment overrides make CI configuration easy.
    model_cfg = ModelConfig(
        provider=os.environ.get("DPWIKI_PROVIDER", model.get("provider", "anthropic")),
        id=os.environ.get("DPWIKI_MODEL", model.get("id", "claude-sonnet-5-5")),
        max_page_turns=int(model.get("max_page_turns", 12)),
        max_pages_per_run=int(model.get("max_pages_per_run", 25)),
    )

    sources = []
    seen: set[str] = set()
    for s in data.get("sources", []):
        sid = s["id"]
        if sid in seen:
            raise ValueError(f"duplicate source id: {sid}")
        if not sid.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"source id must be alphanumeric with - or _: {sid}")
        seen.add(sid)
        sources.append(
            SourceConfig(
                id=sid,
                kind=s["kind"],
                path=(root / s["path"]).resolve(),
                include=list(s.get("include", ["**/*"])),
                exclude=list(s.get("exclude", [])),
            )
        )

    wiki_dir = (root / wiki.get("dir", "wiki")).resolve()
    return Settings(
        root=root,
        title=wiki.get("title", "Team Wiki"),
        wiki_dir=wiki_dir,
        instructions_path=(root / wiki.get("instructions", "wiki/INSTRUCTIONS.md")).resolve(),
        sections=list(wiki.get("sections", [])),
        model=model_cfg,
        sources=sources,
    )
