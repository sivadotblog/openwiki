"""Connector contract.

A connector turns one configured source (a repo folder, a doc folder, a catalog export)
into addressable items. Every item has a stable URI and a content-derived version.
The agent never touches the filesystem or network directly: it reads sources only
through connectors, so reads stay inside the configured roots.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceItem:
    uri: str  # e.g. src://platform-infra/terraform/databricks.tf
    title: str  # short human label
    version: str  # content-derived token; changes iff content changes
    kind: str  # file | table | doc
    size: int = 0


class Connector(ABC):
    id: str
    scheme: str

    @abstractmethod
    def scan(self) -> list[SourceItem]:
        """List every item this source currently exposes."""

    @abstractmethod
    def read(self, key: str, start: int | None = None, end: int | None = None) -> str | None:
        """Return text for an item key (the URI part after scheme://id/). None if missing."""

    @abstractmethod
    def version(self, key: str, fragment: str | None, prior: str | None) -> str | None:
        """Current version for an item (optionally a #Lx-Ly fragment). None if unresolved."""

    def uri(self, key: str) -> str:
        return f"{self.scheme}://{self.id}/{key}"
