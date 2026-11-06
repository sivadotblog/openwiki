import shutil
from pathlib import Path

import pytest

from dpwiki.config import load_settings

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway copy of the sample wiki and sources."""
    dst = tmp_path / "repo"
    dst.mkdir()
    shutil.copy(ROOT / "wiki.toml", dst / "wiki.toml")
    shutil.copytree(ROOT / "sources", dst / "sources")
    shutil.copytree(ROOT / "wiki", dst / "wiki")
    return dst


@pytest.fixture
def settings(repo: Path):
    return load_settings(repo / "wiki.toml")
