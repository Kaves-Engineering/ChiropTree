"""Fetch the tables that bat treatments cite, for import_plazi_tables.py.

Plazi keeps a treatment's tables outside its XML: the treatment only carries a
<tableCitation tableUuid=...> with the caption. table.plazi.org/id/<uuid>
serves the table itself as XML (MODS header, then an HTML-like <table> whose
taxon names are tagged like the treatment text). The same tables are deposited
in Zenodo's Biodiversity Literature Repository (community "biosyslit"), each
with its own record; that record is what a reader is linked to.

This script reads the treatment XML that fetch_plazi_bats.py cached (journal
articles and monographs; not HMW 9, not the MSW checklists), collects every
cited table, caches its XML in data/raw/size/plazi-tables/<uuid>.xml, looks
up its Zenodo record and writes the tracked manifest
data/size/plazi-tables-sources.json: per table uuid, the caption, the article
(DOI, authors, year, title, taken from a citing treatment in
plazi-literature-sources.json), the citing treatments, the Zenodo record URL
(empty when none is found) and the sha256 import_plazi_tables.py pins.

Run:  uv run data/size/fetch_plazi_tables.py   (a re-run fetches only what is missing)
"""
import hashlib
import html
import json
import re
import time
import urllib.parse
from pathlib import Path

from fetch_hmw import CACHE, get

HERE = Path(__file__).parent
DATA = HERE.parent
TREATMENTS = HERE / "plazi-literature-sources.json"
MANIFEST = HERE / "plazi-tables-sources.json"
TABLES = DATA / "raw" / "size" / "plazi-tables"
TABLE_URL = "http://table.plazi.org/id/{}"
ZENODO_SEARCH = "https://zenodo.org/api/records?q={}&size=5"


def cited_tables(treatments: dict) -> dict:
    """uuid -> {caption, citing treatments, article metadata} for every cited table."""
    out = {}
    for doc, meta in sorted(treatments.items()):
        path = CACHE / f"{doc}.xml"
        if not path.exists():
            continue
        xml = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"<tableCitation\b([^>]*)>", xml):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(1)))
            uuid = attrs.get("tableUuid")
            if not uuid:
                continue
            entry = out.setdefault(uuid, {
                "caption": re.sub(r"\s+", " ", html.unescape(attrs.get("captionText", ""))).strip(),
                "label": attrs.get("captionStart", ""),
                "doi": meta["doi"], "authors": meta.get("authors", ""), "year": meta.get("year", ""),
                "article": meta.get("article", ""), "treatments": [],
            })
            if doc not in entry["treatments"]:
                entry["treatments"].append(doc)
    return out


def zenodo_record(uuid: str) -> str:
    """The BLR record whose alternate identifier is this table, or ''."""
    query = urllib.parse.quote(f'"{uuid}"')
    hits = json.loads(get(ZENODO_SEARCH.format(query)))["hits"]["hits"]
    for hit in hits:
        alternates = [a.get("identifier", "") for a in hit["metadata"].get("alternate_identifiers", [])]
        if any(uuid in a for a in alternates):
            return hit["links"]["self_html"]
    return ""


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    treatments = json.loads(TREATMENTS.read_text(encoding="utf-8"))
    tables = cited_tables(treatments)
    print(f"{len(tables)} tables cited by {sum(len(t['treatments']) for t in tables.values())} treatment citations")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    failed = []
    for i, (uuid, entry) in enumerate(sorted(tables.items()), start=1):
        path = TABLES / f"{uuid}.xml"
        old = manifest.get(uuid, {})
        try:
            if not path.exists():
                path.write_bytes(get(TABLE_URL.format(uuid)))
                time.sleep(0.5)
            zenodo = old["zenodo"] if "zenodo" in old else zenodo_record(uuid)
        except Exception as error:  # noqa: BLE001 - one bad table must not stop the run
            failed.append((uuid, str(error)))
            continue
        manifest[uuid] = {**entry, "zenodo": zenodo, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if i % 25 == 0:
            print(f"  {i}/{len(tables)}")
            _write(manifest)
    _write(manifest)
    linked = sum(1 for t in manifest.values() if t["zenodo"])
    print(f"manifest: {len(manifest)} tables ({linked} with a Zenodo record) in {MANIFEST.relative_to(DATA.parent)}")
    if failed:
        print(f"  {len(failed)} failed (re-run to retry): {failed[:3]}")


def _write(manifest: dict) -> None:
    MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")


if __name__ == "__main__":
    main()
