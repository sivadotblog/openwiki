"""Grounded claims.

A claim is one atomic, checkable statement on a wiki page, backed by evidence
resources from configured sources. Each evidence record stores the content
version that was observed when the claim was written. On every run, dpwiki
re-resolves evidence without calling a model:

* clean      every evidence resource resolves to the recorded version
* stale      everything resolves but at least one version changed
* unresolved at least one resource no longer exists

Stale and unresolved claims tell the agent exactly which pages need attention,
so an update run can skip pages whose sources did not change.

Claim state lives in JSON sidecars under wiki/.claims/, mirroring page paths.
Only dpwiki writes them. The agent proposes add/confirm/revise/retract decisions.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .sources import Registry, parse_uri

SCHEMA = 1


@dataclass
class Evidence:
    resource: str
    version: str


@dataclass
class Claim:
    id: str
    statement: str
    evidence: list[Evidence] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> Claim:
        return cls(
            id=d["id"],
            statement=d["statement"],
            evidence=[Evidence(**e) for e in d.get("evidence", [])],
        )


@dataclass
class PageClaims:
    page: str
    page_hash: str = ""
    claims: list[Claim] = field(default_factory=list)
    verified: dict | None = None

    def to_json(self) -> str:
        d = {
            "schema": SCHEMA,
            "page": self.page,
            "page_hash": self.page_hash,
            "claims": [asdict(c) for c in self.claims],
        }
        if self.verified:
            d["verified"] = self.verified
        return json.dumps(d, indent=2, sort_keys=False) + "\n"


@dataclass
class ClaimStatus:
    clean: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    @property
    def needs_attention(self) -> bool:
        return bool(self.stale or self.unresolved)


def claim_id(page: str, statement: str) -> str:
    h = hashlib.sha256(f"{page}\n{statement.strip()}".encode()).hexdigest()[:12]
    return f"c-{h}"


class ClaimsStore:
    def __init__(self, claims_dir: Path):
        self.dir = claims_dir

    def _path(self, page: str) -> Path:
        p = (self.dir / page).with_suffix(".json")
        if not p.resolve().is_relative_to(self.dir.resolve()):
            raise ValueError(f"page path escapes claims dir: {page}")
        return p

    def load(self, page: str) -> PageClaims:
        p = self._path(page)
        if not p.exists():
            return PageClaims(page=page)
        d = json.loads(p.read_text(encoding="utf-8"))
        return PageClaims(
            page=d["page"],
            page_hash=d.get("page_hash", ""),
            claims=[Claim.from_dict(c) for c in d.get("claims", [])],
            verified=d.get("verified"),
        )

    def save(self, pc: PageClaims) -> None:
        p = self._path(pc.page)
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(pc.to_json())
            os.replace(tmp, p)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def delete(self, page: str) -> None:
        self._path(page).unlink(missing_ok=True)

    def pages(self) -> list[str]:
        if not self.dir.exists():
            return []
        return sorted(p.relative_to(self.dir).with_suffix(".md").as_posix() for p in self.dir.rglob("*.json"))


def check(pc: PageClaims, registry: Registry) -> ClaimStatus:
    st = ClaimStatus()
    for c in pc.claims:
        state = "clean"
        for ev in c.evidence:
            try:
                cur = registry.version(ev.resource, ev.version)
            except ValueError:
                cur = None
            if cur is None:
                state = "unresolved"
                break
            if cur != ev.version:
                state = "stale"
        getattr(st, state).append(c.id)
    return st


def resolve_evidence(registry: Registry, uris: list[str]) -> list[Evidence]:
    """Turn agent-proposed URIs into versioned evidence. Raises on bad or missing URIs."""
    if not uris:
        raise ValueError("a claim needs at least one evidence URI")
    out = []
    for u in uris:
        parse_uri(u)
        v = registry.version(u)
        if v is None:
            raise ValueError(f"evidence does not resolve: {u}")
        out.append(Evidence(resource=u, version=v))
    return out


def apply_decisions(pc: PageClaims, registry: Registry, decisions: dict) -> tuple[PageClaims, list[str]]:
    """Apply sparse claim decisions from the agent.

    decisions = {
      "add":     [{"statement": str, "evidence": [uri, ...]}],
      "confirm": [claim_id, ...],                 # still true; re-pin versions
      "revise":  [{"id": str, "statement": str, "evidence": [uri, ...]}],
      "retract": [claim_id, ...],
    }
    Claims not mentioned are kept as they are.
    Returns the new PageClaims and a list of errors (bad ids, bad evidence).
    """
    errors: list[str] = []
    by_id = {c.id: c for c in pc.claims}

    for cid in decisions.get("retract", []) or []:
        if by_id.pop(cid, None) is None:
            errors.append(f"retract: unknown claim id {cid}")

    for cid in decisions.get("confirm", []) or []:
        c = by_id.get(cid)
        if c is None:
            errors.append(f"confirm: unknown claim id {cid}")
            continue
        try:
            c.evidence = resolve_evidence(registry, [e.resource for e in c.evidence])
        except ValueError as e:
            errors.append(f"confirm {cid}: {e}")

    for r in decisions.get("revise", []) or []:
        cid = r.get("id")
        if cid not in by_id:
            errors.append(f"revise: unknown claim id {cid}")
            continue
        try:
            ev = resolve_evidence(registry, r.get("evidence") or [e.resource for e in by_id[cid].evidence])
        except ValueError as e:
            errors.append(f"revise {cid}: {e}")
            continue
        by_id.pop(cid)
        new = Claim(id=claim_id(pc.page, r["statement"]), statement=r["statement"], evidence=ev)
        by_id[new.id] = new

    for a in decisions.get("add", []) or []:
        stmt = (a.get("statement") or "").strip()
        if not stmt:
            errors.append("add: empty statement")
            continue
        try:
            ev = resolve_evidence(registry, a.get("evidence") or [])
        except ValueError as e:
            errors.append(f"add '{stmt[:60]}': {e}")
            continue
        c = Claim(id=claim_id(pc.page, stmt), statement=stmt, evidence=ev)
        by_id[c.id] = c

    return PageClaims(page=pc.page, page_hash=pc.page_hash, claims=list(by_id.values()), verified=pc.verified), errors
