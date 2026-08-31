"""Fetch per-species literature citations from batnames.org and emit a compact JSON.

Source: Bats of the World Database (Simmons, N.B. and A.L. Cirranello,
American Museum of Natural History) — https://batnames.org. Each species page
there carries a curated "References" list (the papers behind its description,
synonymy, and taxonomic placement); many species also inherit a genus-level
reference list (e.g. the paper that erected the genus). This script fetches
both per species, using the current MDD binomial as the primary lookup key and
falling back to the MSW3-era name for species batnames.org still files under
an older genus.

The site has no bulk export or API, so this scrapes each species page
individually (~1,500 requests) with a polite delay between requests. It's
resumable: progress is cached in data/raw/batnames_scrape_cache.json (gitignored)
so a re-run only fetches species missing from the cache.

Re-run after regenerating chiroptera_taxonomy.json from a new MDD release, or
periodically to pick up new batnames.org citations (they say they update
biannually, April/October).
"""
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote_plus

TAXONOMY = Path(__file__).parent / "chiroptera_taxonomy.json"
CACHE = Path(__file__).parent / "raw" / "batnames_scrape_cache.json"
OUT = Path(__file__).parent / "batnames_references.json"

BASE = "https://batnames.org/species/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
DELAY = 0.4  # seconds between requests — polite pacing, site has no robots.txt limit stated
TIMEOUT = 20

FAILURE_RE = re.compile(r"class='failure'")
BIB_RE = re.compile(r"<div class='bibentry' id='(species|genus)'><p>(.*?)</p></div>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r"<a\s+href=(['\"])(.*?)\1[^>]*>\s*Read (?:article|chapter|book)\.?\s*</a>", re.I | re.S)
TRAILING_READ_RE = re.compile(r"\s*Read (?:article|chapter|book)\.?\s*$", re.I)


def fetch(url, retries=3):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries - 1:
                print(f"  ! giving up on {url}: {e}", file=sys.stderr)
                return None
            time.sleep(1.5 * (attempt + 1))


def parse_bibentry(frag):
    m = HREF_RE.search(frag)
    url = None
    if m:
        href = html.unescape(m.group(2)).strip()
        if href.startswith("http"):
            url = href
    text = TAG_RE.sub("", frag)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = TRAILING_READ_RE.sub("", text).strip()
    return {"citation": text, "url": url}


def fetch_refs(binomial):
    """Returns (matched: bool, species_refs: list, genus_refs: list) for one binomial."""
    url = BASE + quote_plus(binomial)
    body = fetch(url)
    if body is None:
        return None, [], []
    if FAILURE_RE.search(body):
        return False, [], []
    species_refs, genus_refs = [], []
    for kind, frag in BIB_RE.findall(body):
        ref = parse_bibentry(frag)
        if not ref["citation"]:
            continue
        (species_refs if kind == "species" else genus_refs).append(ref)
    return True, species_refs, genus_refs


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def main():
    tax = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    species = tax["species"]
    cache = load_cache()

    total = len(species)
    for i, sp in enumerate(species, 1):
        sci = sp["sciName"]
        if sci in cache:
            continue
        primary = sci.replace("_", " ")
        matched, srefs, grefs = fetch_refs(primary)
        matched_as = primary
        if not matched:
            time.sleep(DELAY)
            msw3 = sp.get("MSW3_sciName", "").replace("_", " ")
            if msw3 and msw3 != primary:
                matched, srefs, grefs = fetch_refs(msw3)
                matched_as = msw3
        cache[sci] = {
            "genus": sp["genus"],
            "matched": bool(matched),
            "matchedAs": matched_as if matched else None,
            "speciesRefs": srefs,
            "genusRefs": grefs,
        }
        if i % 25 == 0 or i == total:
            print(f"  {i}/{total} ({sci})")
            save_cache(cache)
        time.sleep(DELAY)

    save_cache(cache)

    species_refs = {}
    genus_refs = {}
    unresolved = []
    for sci, rec in cache.items():
        if not rec["matched"]:
            unresolved.append(sci)
            continue
        if rec["speciesRefs"]:
            species_refs[sci] = rec["speciesRefs"]
        if rec["genusRefs"] and rec["genus"] not in genus_refs:
            genus_refs[rec["genus"]] = rec["genusRefs"]

    payload = {
        "_meta": {
            "source": "Bats of the World Database (batnames.org)",
            "sourceUrl": "https://batnames.org",
            "citation": "Simmons, N.B. and A.L. Cirranello. Bat Species of the World: "
                        "A taxonomic and geographic database.",
            "speciesTotal": total,
            "speciesMatched": total - len(unresolved),
            "speciesWithOwnRefs": len(species_refs),
            "genusWithRefs": len(genus_refs),
            "unresolvedCount": len(unresolved),
            "unresolved": sorted(unresolved),
        },
        "speciesRefs": species_refs,
        "genusRefs": genus_refs,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote references for {len(species_refs)} species + {len(genus_refs)} genera "
          f"({len(unresolved)} unresolved) to {OUT}")


if __name__ == "__main__":
    main()
