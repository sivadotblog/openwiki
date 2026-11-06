"""Catalog connector: table metadata from a lakehouse or warehouse.

Reads a JSON export shaped like:

    {"exported_at": "...", "platform": "databricks-unity-catalog",
     "tables": [{"catalog": "...", "schema": "...", "name": "...", "owner": "...",
                 "comment": "...", "columns": [{"name": "...", "type": "...", "comment": "..."}],
                 "tags": {...}, "upstream": ["..."], "freshness_sla_hours": 24}]}

Produce the export with a scheduled job (Unity Catalog REST API, Snowflake
information_schema, or a Bigeye export). Keeping the connector file-based means the
agent never holds warehouse credentials.

URIs look like catalog://<source-id>/<catalog>.<schema>.<table>
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .base import Connector, SourceItem


def _canon(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, indent=2)


class CatalogConnector(Connector):
    scheme = "catalog"

    def __init__(self, source_id: str, path: Path):
        self.id = source_id
        self.path = path

    def _tables(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        out = {}
        for t in data.get("tables", []):
            fq = f"{t['catalog']}.{t['schema']}.{t['name']}"
            out[fq] = t
        return out

    def scan(self) -> list[SourceItem]:
        items = []
        for fq, t in sorted(self._tables().items()):
            text = _canon(t)
            items.append(
                SourceItem(
                    uri=self.uri(fq),
                    title=fq,
                    version="table-v1:sha256:" + hashlib.sha256(text.encode()).hexdigest(),
                    kind="table",
                    size=len(text),
                )
            )
        return items

    def read(self, key: str, start: int | None = None, end: int | None = None) -> str | None:
        t = self._tables().get(key)
        return None if t is None else _canon(t)

    def version(self, key: str, fragment: str | None, prior: str | None) -> str | None:
        text = self.read(key)
        if text is None:
            return None
        return "table-v1:sha256:" + hashlib.sha256(text.encode()).hexdigest()
