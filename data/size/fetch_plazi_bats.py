"""Fetch every bat species treatment Plazi holds outside HMW 9 and the MSW
checklists, for import_plazi_literature.py.

Plazi's SPARQL endpoint (https://qlever.ld.plazi.org/sparql, documented in
github.com/plazi/qlever-plazi and rebuilt nightly) lists every treatment
whose taxon concept is in the order Chiroptera, with the DOI of the article
it was published in: 8,387 treatments from 339 publications in November
2026. Two groups are left out:

- the 1,419 HMW 9 accounts, which fetch_hmw.py / import_hmw.py already read;
- the Mammal Species of the World checklists (1982, 1993, 2005), which are
  name lists with no measurements.

What remains are the treatments of journal articles (species descriptions,
revisions, regional inventories) and older monographs. Treatments of genera
and higher taxa are skipped by title. Each treatment's XML goes to the
gitignored cache data/raw/size/plazi/ (shared with fetch_hmw.py), and the
tracked manifest data/size/plazi-literature-sources.json records, per docId,
the title, article DOI, authors, year, the article's title and the sha256
that import_plazi_literature.py pins.

Run:  uv run data/size/fetch_plazi_bats.py   (a re-run fetches only what is missing)
"""
import csv
import hashlib
import io
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fetch_hmw import CACHE, WORKERS, cached, header

HERE = Path(__file__).parent
DATA = HERE.parent
MANIFEST = HERE / "plazi-literature-sources.json"
HMW_MANIFEST = HERE / "hmw-2019-sources.json"
SPARQL = "https://qlever.ld.plazi.org/sparql"
QUERY = """
PREFIX dwc: <http://rs.tdwg.org/dwc/terms/>
PREFIX trt: <http://plazi.org/vocab/treatment#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT DISTINCT ?t ?pub ?title WHERE {
  ?t a trt:Treatment ; trt:definesTaxonConcept|trt:augmentsTaxonConcept ?c .
  ?c dwc:order "Chiroptera" .
  OPTIONAL { ?t trt:publishedIn ?pub }
  OPTIONAL { ?t dc:title ?title }
}"""
# name checklists without measurements
CHECKLISTS = {
    "10.5281/zenodo.7316519": "Mammal Species of the World, 3rd edition (2005)",
    "10.5281/zenodo.7352990": "Mammal Species of the World (1982)",
    "10.5281/zenodo.7353060": "Mammal Species of the World, 2nd edition (1993)",
}


def inventory() -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(_post()), delimiter="\t"))
    out = {}
    for row in rows:
        doc = row["?t"].strip("<>").rsplit("/", 1)[-1]
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", row["?pub"].strip("<>"))
        title = row["?title"].strip('"')
        out[doc] = {"doc": doc, "doi": urllib.parse.unquote(doi), "title": title}
    return list(out.values())


def _post() -> str:
    request = urllib.request.Request(
        SPARQL, data=urllib.parse.urlencode({"query": QUERY}).encode(),
        headers={"Accept": "text/tab-separated-values",
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read().decode("utf-8")


def is_species(title: str) -> bool:
    words = re.sub(r"\([^)]*\)", " ", title).split()
    return len(words) >= 2 and words[0][:1].isupper() and words[1][:1].islower() and words[1].isalpha()


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    hmw = set(json.loads(HMW_MANIFEST.read_text(encoding="utf-8")))
    treatments = inventory()
    print(f"SPARQL: {len(treatments)} bat treatments")
    wanted = [t for t in treatments
              if t["doc"] not in hmw and t["doi"] not in CHECKLISTS and is_species(t["title"])]
    print(f"  {len(wanted)} species treatments outside HMW 9 and the MSW checklists")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    todo = [t for t in wanted if t["doc"] not in manifest or not (CACHE / f"{t['doc']}.xml").exists()]
    print(f"  {len(todo)} to fetch")
    failed = []

    def fetch(t):
        try:
            return t, cached(t["doc"])
        except Exception as error:  # noqa: BLE001 - one bad document must not stop the run
            failed.append((t["doc"], str(error)))
            return t, None

    with ThreadPoolExecutor(WORKERS) as pool:
        for i, (t, path) in enumerate(pool.map(fetch, todo), start=1):
            if path is None:
                continue
            meta = header(path)
            if "zenodo" in t["doi"] and meta.get("masterDocId") and _is_hmw(meta):
                continue
            manifest[t["doc"]] = {
                "title": t["title"], "doi": t["doi"],
                "authors": meta.get("docAuthor", ""), "year": meta.get("docDate", ""),
                "article": meta.get("masterDocTitle", ""), "source": meta.get("docSource", ""),
                "page": meta.get("pageNumber", ""),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            if i % 100 == 0:
                print(f"  {i}/{len(todo)}")
                _write(manifest)
    _write(manifest)
    print(f"manifest: {len(manifest)} treatments in {MANIFEST.relative_to(DATA.parent)}")
    if failed:
        print(f"  {len(failed)} failed (re-run to retry): {failed[:3]}")


def _is_hmw(meta: dict) -> bool:
    return "Handbook of the Mammals of the World" in meta.get("docSource", "") + meta.get("masterDocTitle", "")


def _write(manifest: dict) -> None:
    MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")


if __name__ == "__main__":
    main()
