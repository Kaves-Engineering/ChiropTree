"""Supplement MDD's countryDistribution with GBIF occurrence-record evidence.

Mirrors data/build_country_distribution.py exactly, just pointed at the
marine mammal taxonomy. Asks GBIF's occurrence index, country by country,
which countries hold real specimen or observation records for each marine
mammal species, and writes any country *not already in MDD's list* to
data/marine_mammal_gbif_country_supplement.json.

This is additive only: MDD's own countries are never removed or overridden,
and nothing here touches marine_mammal_taxonomy.json (so re-running
build_marine_mammal_taxonomy.py against a new MDD release does not wipe this
file). Canonicalises country names against data/marine_world_map.json -- the
map this page actually draws -- not the bat pages' world_map.json: a name is
only worth adding if the map can resolve it to a shape or dot, and the two
maps differ (Antarctica, and the sub-Antarctic aliases). Merged into
countryDistribution
client-side at page load -- see luMergeCountrySupplement in
marine-mammal-lookup.html and marine-mammal-tree.html.

A country only counts as evidence if it has at least MIN_RECORDS non-fossil,
non-captive occurrence records with occurrenceStatus=PRESENT -- single
records are usually vagrants, strandings far outside the normal range, or
misidentifications.

Run:  uv run data/build_marine_mammal_country_distribution.py
~140 species is far fewer than the ~1,500 bats, so this should take a
couple of minutes rather than 10-20. Safe to re-run: results are cached in
data/raw/marine_mammal_gbif_country_cache.json so an interrupted run
resumes cheaply.
"""
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).parent
TAXONOMY = HERE / "marine_mammal_taxonomy.json"
WORLD_MAP = HERE / "marine_world_map.json"
CACHE = HERE / "raw" / "marine_mammal_gbif_country_cache.json"
OUT = HERE / "marine_mammal_gbif_country_supplement.json"

MATCH_URL = "https://api.gbif.org/v1/species/match?name={}&strict=true"
OCC_URL = (
    "https://api.gbif.org/v1/occurrence/search?taxonKey={}&facet=country"
    "&facetLimit=300&limit=0&occurrenceStatus=PRESENT"
    "&basisOfRecord=PRESERVED_SPECIMEN&basisOfRecord=HUMAN_OBSERVATION"
    "&basisOfRecord=MATERIAL_SAMPLE&basisOfRecord=MACHINE_OBSERVATION"
)
COUNTRY_ENUM_URL = "https://api.gbif.org/v1/enumeration/country"

MIN_RECORDS = 3
WORKERS = 8


def fetch_json(url, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "treeofbatlife-lookup/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            if attempt == retries - 1:
                return None
            time.sleep(1.5 * (attempt + 1))


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def build_canonical_names(tax, wmap_index):
    """iso3 -> the spelling MDD itself already uses for that country, so
    supplemented countries read the same way as MDD's own entries."""
    canonical = {}
    for s in tax["species"]:
        for raw in (s.get("countryDistribution") or "").split("|"):
            name = raw.strip().rstrip("?").strip()
            if not name:
                continue
            key = wmap_index.get(norm(name))
            if key and key not in canonical:
                canonical[key] = name
    return canonical


def load_iso2_to_iso3():
    rows = fetch_json(COUNTRY_ENUM_URL) or []
    return {r["iso2"]: (r["iso3"], r["title"]) for r in rows if r.get("iso2") and r.get("iso3")}


def usage_key_for(sci_name_space, fallback_name_space=None):
    match = fetch_json(MATCH_URL.format(urllib.parse.quote(sci_name_space)))
    if (not match or "usageKey" not in match) and fallback_name_space:
        match = fetch_json(MATCH_URL.format(urllib.parse.quote(fallback_name_space)))
    if not match or "usageKey" not in match:
        return None
    return match["usageKey"]


def country_counts_for(usage_key):
    """{iso2: record_count} for a taxon key, PRESENT + non-fossil/non-captive only."""
    data = fetch_json(OCC_URL.format(usage_key))
    if not data:
        return {}
    out = {}
    for facet in data.get("facets", []):
        if facet.get("field") != "COUNTRY":
            continue
        for c in facet.get("counts", []):
            out[c["name"]] = c["count"]
    return out


def process_species(s, fallback):
    sci_space = s["sciName"].replace("_", " ")
    key = usage_key_for(sci_space, fallback)
    if not key:
        return s["sciName"], None
    return s["sciName"], country_counts_for(key)


def main():
    tax = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    wmap = json.loads(WORLD_MAP.read_text(encoding="utf-8"))
    iso2_to_iso3 = load_iso2_to_iso3()
    canonical = build_canonical_names(tax, wmap["index"])

    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"resuming from cache: {len(cache)} species already fetched")

    species = tax["species"]
    todo = [s for s in species if s["sciName"] not in cache]
    print(f"{len(todo)} of {len(species)} species need fetching")

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {}
        for s in todo:
            msw3 = s.get("MSW3_sciName") or ""
            fallback = msw3.replace("_", " ") if msw3 and msw3 != "NA" else None
            futures[pool.submit(process_species, s, fallback)] = s["sciName"]
        for fut in as_completed(futures):
            sci = futures[fut]
            try:
                _, counts = fut.result()
            except Exception:  # noqa: BLE001
                counts = None
            if counts is not None:
                cache[sci] = counts
            done += 1
            if done % 20 == 0:
                print(f"{done}/{len(todo)} fetched")
                CACHE.parent.mkdir(parents=True, exist_ok=True)
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    supplement = {s["sciName"]: previous[s["sciName"]] for s in species if s["sciName"] in previous}
    unmatched_countries = set()
    for s in species:
        sci = s["sciName"]
        if sci not in cache:
            continue
        counts = cache[sci]
        existing = {norm(n.strip().rstrip("?")) for n in (s.get("countryDistribution") or "").split("|") if n.strip()}
        added = []
        for iso2, count in counts.items():
            if count < MIN_RECORDS:
                continue
            iso3_title = iso2_to_iso3.get(iso2)
            if not iso3_title:
                continue
            iso3, title = iso3_title
            name = canonical.get(iso3)
            if not name:
                # country MDD never uses anywhere; fall back to GBIF's title
                # only if the world map can actually resolve it to a shape
                if norm(title) in wmap["index"]:
                    name = title
                else:
                    unmatched_countries.add(f"{title} ({iso3})")
                    continue
            if norm(name) in existing:
                continue
            added.append(name)
        if added:
            supplement[sci] = sorted(added)
        else:
            supplement.pop(sci, None)

    OUT.write_text(json.dumps(supplement, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    total_added = sum(len(v) for v in supplement.values())
    print(f"Done: {len(supplement)} species gained countries, {total_added} country entries added. Wrote {OUT}")
    if unmatched_countries:
        print(f"{len(unmatched_countries)} GBIF countries could not be placed on the map (skipped):")
        for c in sorted(unmatched_countries):
            print(f"   {c}")


if __name__ == "__main__":
    main()
