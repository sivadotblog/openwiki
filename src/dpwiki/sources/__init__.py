"""Connector registry and URI resolution."""

from __future__ import annotations

import re

from ..config import Settings
from .base import Connector, SourceItem
from .catalog import CatalogConnector
from .filesystem import FilesystemConnector

__all__ = ["Connector", "SourceItem", "Registry", "parse_uri"]

_URI_RE = re.compile(r"^(?P<scheme>[a-z]+)://(?P<sid>[A-Za-z0-9_-]+)/(?P<key>[^#]+)(?P<frag>#L\d+(?:-L\d+)?)?$")


def parse_uri(uri: str) -> tuple[str, str, str, str | None]:
    m = _URI_RE.match(uri.strip())
    if not m:
        raise ValueError(
            f"invalid evidence URI '{uri}'. Use scheme://source-id/key, "
            "e.g. src://platform-infra/terraform/main.tf#L10-L20"
        )
    return m["scheme"], m["sid"], m["key"], m["frag"]


class Registry:
    def __init__(self, connectors: list[Connector]):
        self.by_id = {c.id: c for c in connectors}

    @classmethod
    def from_settings(cls, settings: Settings) -> Registry:
        conns: list[Connector] = []
        for s in settings.sources:
            if s.kind == "filesystem":
                conns.append(FilesystemConnector(s.id, s.path, s.include, s.exclude))
            elif s.kind == "catalog":
                conns.append(CatalogConnector(s.id, s.path))
            else:
                raise ValueError(f"unknown source kind '{s.kind}' for source '{s.id}'")
        return cls(conns)

    def _conn(self, uri: str) -> tuple[Connector, str, str | None]:
        scheme, sid, key, frag = parse_uri(uri)
        c = self.by_id.get(sid)
        if c is None or c.scheme != scheme:
            raise ValueError(f"unknown source in URI: {uri}")
        return c, key, frag

    def scan(self) -> list[SourceItem]:
        out: list[SourceItem] = []
        for c in self.by_id.values():
            out.extend(c.scan())
        return out

    def read(self, uri: str) -> str | None:
        c, key, frag = self._conn(uri)
        if frag:
            from .filesystem import parse_fragment

            s, e = parse_fragment(frag)
            return c.read(key, s, e)
        return c.read(key)

    def version(self, uri: str, prior: str | None = None) -> str | None:
        c, key, frag = self._conn(uri)
        return c.version(key, frag, prior)
