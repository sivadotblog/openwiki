"""Deterministic feature status index for Azure Databricks, built from public docs.

Sources, in order of authority:
  1. The feature's own docs page. Preview pages carry a banner that links to the
     release types page, e.g. "This feature is in [Beta](../release-notes/release-types)".
     No banner means GA. This is the source of truth for the current status.
  2. Release note entries (the product release notes page and the RSS feed). They tell
     us WHEN something changed and WHICH docs pages to recheck. Their titles are only
     used as a cross-check against the page banner.

Identity: a feature is a docs page path, plus a section anchor when the release note
links one (e.g. oltp/projects/snapshots#create-snapshot). Feed GUIDs are per
announcement, so they are never used as feature IDs.

Output is sorted and contains no run timestamps, so the same inputs always produce
byte-identical files. Disagreements are written to a review list instead of guessed.

Usage:
  python tools/feature_index.py --product lakebase --out index/
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import yaml

BASE = "https://learn.microsoft.com/en-us/azure/databricks/"
FEED = "https://learn.microsoft.com/en-us/azure/databricks/feed.xml"
PRODUCTS = {
    "lakebase": {
        "release_notes": BASE + "release-notes/lakebase/",
        "feed_match": re.compile(r"\blakebase\b", re.I),
    }
}
UA = "feature-index/0.1 (+https://github.com/sivadotblog/openwiki)"
SKIP_PATHS = ("release-notes/", "admin/workspace-settings/manage-previews")

# Release types, from release-notes/release-types.
STATUS_WORDS = {
    "private preview": "private-preview",
    "beta": "beta",
    "experimental": "experimental",
    "public preview": "public-preview",
}

RANK = {"private-preview": 0, "experimental": 1, "beta": 1, "public-preview": 2, "mixed": 2, "ga": 3}

# Title rules. Order matters: the first match wins. Each rule is a fixed regex.
TITLE_RULES = [
    (re.compile(r"\bgenerally available\b|\bis now ga\b|\(ga\)", re.I), "ga"),
    (re.compile(r"\bpublic preview\b", re.I), "public-preview"),
    (re.compile(r"\bprivate preview\b", re.I), "private-preview"),
    (re.compile(r"\(beta\)|\bin beta\b|\bnow in beta\b|\bare in beta\b|\bis in beta\b", re.I), "beta"),
    (re.compile(r"\bexperimental\b", re.I), "experimental"),
]


def classify_title(title: str) -> str | None:
    for rx, status in TITLE_RULES:
        if rx.search(title):
            return status
    return None


# ---------------------------------------------------------------- fetching


_cache: dict[str, str] = {}


def fetch(url: str) -> str:
    if url in _cache:
        return _cache[url]
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read().decode("utf-8", "replace")
                _cache[url] = text
                return text
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last}")


def doc_key(href: str, base_url: str) -> str | None:
    """Normalize a link to 'path[#anchor]' relative to the Azure Databricks docs root."""
    u = urlparse(urljoin(base_url, href))
    if u.netloc and u.netloc != "learn.microsoft.com":
        return None
    path = re.sub(r"^/[a-z]{2}-[a-z]{2}/", "/", u.path)
    if not path.startswith("/azure/databricks/"):
        return None
    rel = path[len("/azure/databricks/"):].strip("/")
    if not rel or rel.startswith(SKIP_PATHS) or "_static" in rel:
        return None
    return rel + (f"#{u.fragment}" if u.fragment else "")


# ---------------------------------------------------------------- HTML parsing


class Doc(HTMLParser):
    """Flatten <main> into a token stream of headings, links, strong text and text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tokens: list[tuple] = []  # ("h", level, id, text) | ("a", href, text) | ("t", text) | ("strong", text)
        self.in_main = 0
        self._h: list | None = None
        self._a: list | None = None
        self._strong: list | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "main":
            self.in_main += 1
        if not self.in_main:
            return
        if tag in ("h1", "h2", "h3", "h4") and not (a.get("id") or "").startswith("ms--"):
            # ms--* headings are Learn page chrome ("In this article"), not content.
            self._h = [int(tag[1]), a.get("id") or "", []]
        elif tag == "a" and a.get("href"):
            self._a = [a["href"], []]
        elif tag == "strong":
            self._strong = []

    def handle_endtag(self, tag):
        if tag == "main":
            self.in_main -= 1
        if not self.in_main:
            return
        if tag in ("h1", "h2", "h3", "h4") and self._h:
            self.tokens.append(("h", self._h[0], self._h[1], " ".join("".join(self._h[2]).split())))
            self._h = None
        elif tag == "a" and self._a:
            self.tokens.append(("a", self._a[0], " ".join("".join(self._a[1]).split())))
            self._a = None
        elif tag == "strong" and self._strong is not None:
            self.tokens.append(("strong", " ".join("".join(self._strong).split())))
            self._strong = None

    def handle_data(self, data):
        if not self.in_main:
            return
        for buf in (self._h and self._h[2], self._a and self._a[1], self._strong):
            if buf is not None and buf is not False:
                buf.append(data)
        if self._h is None and self._a is None and data.strip():
            self.tokens.append(("t", data))


def parse(html: str) -> list[tuple]:
    p = Doc()
    p.feed(html)
    return p.tokens


@dataclass
class Entry:
    source: str  # url#anchor of the release note entry
    title: str
    date: str  # ISO date
    title_status: str | None
    keys: list[str] = field(default_factory=list)


MONTHS = {m: i for i, m in enumerate(
    "january february march april may june july august september october november december".split(), 1)}
DATE_RE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})$")


def iso(text: str) -> str | None:
    m = DATE_RE.match(text.strip())
    if not m:
        return None
    return f"{int(m[3]):04d}-{MONTHS[m[1].lower()]:02d}-{int(m[2]):02d}"


def release_note_entries(url: str) -> list[Entry]:
    """Each H2 on a product release notes page is one entry: title, bold date, links."""
    tokens = parse(fetch(url))
    entries: list[Entry] = []
    cur: Entry | None = None
    for tok in tokens:
        if tok[0] == "h" and tok[1] == 2:
            cur = Entry(source=f"{url}#{tok[2]}", title=tok[3], date="", title_status=classify_title(tok[3]))
            entries.append(cur)
        elif cur is None:
            continue
        elif tok[0] == "strong" and not cur.date and iso(tok[1]):
            cur.date = iso(tok[1])
        elif tok[0] == "a":
            k = doc_key(tok[1], url)
            if k and k not in cur.keys:
                cur.keys.append(k)
    return entries


def feed_entries(match: re.Pattern) -> list[Entry]:
    root = ET.fromstring(fetch(FEED))
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        desc = item.findtext("description") or ""
        if not match.search(title):
            continue  # a passing mention in the description is not a product change
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link).strip()
        pub = (item.findtext("pubDate") or "").strip()
        try:
            date = time.strftime("%Y-%m-%d", time.strptime(pub[:16], "%a, %d %b %Y"))
        except ValueError:
            date = ""
        keys = []
        for href in re.findall(r'href="([^"]+)"', unescape(desc)):
            k = doc_key(href, link or BASE)
            if k and k not in keys:
                keys.append(k)
        out.append(Entry(source=guid, title=title, date=date, title_status=classify_title(title), keys=keys))
    return out


# ---------------------------------------------------------------- page banners


@dataclass
class Banner:
    status: str  # banner status, or "none" when the page has no preview banner
    scope: str  # page | section
    preview_name: str | None
    page_title: str
    anchor_missing: bool = False


def page_banner(key: str) -> Banner | None:
    """Status the docs page itself declares for a page or one of its sections."""
    path, _, anchor = key.partition("#")
    try:
        tokens = parse(fetch(BASE + path))
    except RuntimeError:
        return None
    title = next((t[3] for t in tokens if t[0] == "h" and t[1] == 1), path)

    def banner_in(span: list[tuple]) -> tuple[str, str | None] | None:
        for i, t in enumerate(span):
            if t[0] == "a" and "release-types" in t[1]:
                word = t[2].lower()
                lead = " ".join(u[1] for u in span[max(0, i - 3):i] if u[0] == "t").lower()
                if word in STATUS_WORDS and re.search(r"\bsome\b|\bcertain\b|\bparts?\b", lead):
                    return "mixed", None  # e.g. "Some operations remain in Beta"
                if word in STATUS_WORDS:
                    # The preview toggle name is the first bold text after the link, if any.
                    name = None
                    for u in span[i + 1:i + 12]:
                        if u[0] == "h":
                            break
                        if u[0] == "strong" and u[1] and u[1].lower() != "previews":
                            name = u[1]
                            break
                    return STATUS_WORDS[word], name
        return None

    # Page-level banner: between H1 and the first H2.
    first_h2 = next((i for i, t in enumerate(tokens) if t[0] == "h" and t[1] == 2), len(tokens))
    page = banner_in(tokens[:first_h2])
    if anchor:
        start = next((i for i, t in enumerate(tokens) if t[0] == "h" and t[2] == anchor), None)
        if start is None:
            # Docs renamed the section. Anchors are hints, the page is the identity.
            if page:
                return Banner(page[0], "page", page[1], title, anchor_missing=True)
            return Banner("none", "page", None, title, anchor_missing=True)
        level = tokens[start][1]
        end = next((i for i in range(start + 1, len(tokens))
                    if tokens[i][0] == "h" and tokens[i][1] <= level), len(tokens))
        sect = banner_in(tokens[start + 1:end])
        if sect:
            return Banner(sect[0], "section", sect[1], title)
    if page:
        return Banner(page[0], "page", page[1], title)
    return Banner("none", "page" if not anchor else "section", None, title)


# ---------------------------------------------------------------- build


def build(product: str) -> tuple[dict, list[dict]]:
    cfg = PRODUCTS[product]
    entries = release_note_entries(cfg["release_notes"])
    feed = feed_entries(cfg["feed_match"])
    seen_titles = {e.title.lower() for e in entries}
    # Feed items not yet on the release notes page (new) are still processed.
    entries += [e for e in feed if e.title.lower() not in seen_titles]

    features: dict[str, dict] = {}
    review: list[dict] = []
    for e in sorted(entries, key=lambda x: (x.date, x.source)):
        if not e.title_status:
            continue  # regions, compliance, versions: not a status change
        if not e.keys:
            review.append({"reason": "status entry with no docs link", "entry": e.source, "title": e.title})
            continue
        for k in e.keys:
            f = features.setdefault(k, {"history": []})
            f["history"].append({"date": e.date, "status": e.title_status, "title": e.title, "source": e.source})

    # A GA entry that links a page without an anchor also covers that page's sections.
    for k in list(features):
        if "#" in k:
            continue
        for sk in features:
            if sk.startswith(k + "#"):
                ga = [h for h in features[k]["history"] if h["status"] == "ga"]
                for h in ga:
                    if h not in features[sk]["history"]:
                        features[sk]["history"].append({**h, "via": k})
                features[sk]["history"].sort(key=lambda h: (h["date"], h["source"]))

    for k, f in sorted(features.items()):
        b = page_banner(k)
        latest = f["history"][-1]["status"]
        if b is None:
            f["status"] = "unresolved"
            review.append({"reason": "docs page or section not found", "feature": k})
            continue
        # No banner only proves "not marked as preview". Call it GA only when a GA note exists,
        # because retired or merged features also lose their banner.
        has_ga_note = any(h["status"] == "ga" for h in f["history"])
        if b.status == "none":
            status, source = ("ga", f"no-{b.scope}-banner+ga-release-note") if has_ga_note else ("unmarked", f"no-{b.scope}-banner")
        else:
            status, source = b.status, f"docs-{b.scope}-banner"
        f.update(title=b.page_title, status=status, status_source=source)
        if b.preview_name:
            f["preview_toggle"] = b.preview_name
        f["latest_release_note_status"] = latest
        if b.anchor_missing:
            f["anchor_missing"] = True
            review.append({"reason": "section anchor no longer on page; used page banner",
                           "feature": k, "action": "info"})
        if status == "unmarked":
            review.append({"reason": "no preview banner and no GA release note: GA, retired, or a context link",
                           "feature": k, "release_note": latest, "release_note_title": f["history"][-1]["title"],
                           "action": "needs-review"})
        elif status == "mixed":
            review.append({"reason": "page says only some parts are in preview",
                           "feature": k, "release_note": latest, "action": "needs-review"})
        elif latest != status:
            ahead = RANK[status] > RANK[latest]
            review.append({
                "reason": "docs ahead of release notes" if ahead else "docs behind release notes",
                "feature": k, "docs": status, "release_note": latest,
                "release_note_title": f["history"][-1]["title"],
                "action": "info" if ahead else "needs-review",
            })
    ordered = {k: {kk: f[kk] for kk in ("title", "status", "status_source", "preview_toggle", "anchor_missing",
                                         "latest_release_note_status", "history") if kk in f}
               for k, f in sorted(features.items())}
    return ordered, review


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", default="lakebase", choices=sorted(PRODUCTS))
    ap.add_argument("--out", default="index")
    args = ap.parse_args()
    features, review = build(args.product)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    dump = lambda d: yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=120)  # noqa: E731
    (out / f"{args.product}-features.yaml").write_text(
        f"# Generated by tools/feature_index.py from public Azure Databricks docs. Do not hand-edit.\n"
        f"# status comes from each docs page banner; history comes from release notes.\n"
        + dump({"product": args.product, "features": features}), encoding="utf-8")
    (out / f"{args.product}-review.yaml").write_text(
        "# Items the rules could not settle. A human resolves these.\n" + dump({"review": review}),
        encoding="utf-8")
    counts: dict[str, int] = {}
    for f in features.values():
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    actions: dict[str, int] = {}
    for r in review:
        actions[r.get("action", "needs-review")] = actions.get(r.get("action", "needs-review"), 0) + 1
    print(json.dumps({"features": len(features), "by_status": dict(sorted(counts.items())),
                      "review": dict(sorted(actions.items()))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
