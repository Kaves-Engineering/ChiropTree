"""Country lists for every bird species, from GBIF occurrence records.

Run:  uv run data/build_bird_country_distribution.py
Then: uv run data/build_bird_taxonomy.py   (merges the result in)

MDD gives the mammal pages a curated country checklist, and GBIF only
supplements it. AviList has no country column at all, so for birds GBIF is
the whole source. The page labels it that way ("Countries (GBIF records)").

Bird occurrence data is dominated by eBird, and eBird records every twitched
rarity hundreds of times: one Siberian Rubythroat in the Netherlands is 2,000
records. The flat 3-record floor the mammal scripts use would paint half of
Europe for any vagrant. A country is therefore kept only when:

  count >= MIN_RECORDS, and either
  count / (all bird records in that country)  >= MIN_COUNTRY_SHARE
      -- the species is a real part of that country's avifauna, measured
         against how heavily the country is birded, so Chad (30k records)
         and the US (1.1bn) are judged on the same scale; or
  count / (all records of the species)        >= MIN_SPECIES_SHARE
      -- a sizeable part of the species' own records are there, which keeps
         range-restricted species in big, heavily birded countries (Kirtland's
         Warbler in Canada, 6% of its records but 8e-6 of Canada's).

Checked by hand against Kirtland's Warbler, Florida Scrub-Jay, Heermann's
Gull, Siberian Rubythroat, Yellow-rumped Warbler, Common Ostrich, Emperor
Penguin, Common Crane and Collared Flycatcher. Vagrants in heavily birded
countries drop out; regular wintering and breeding countries stay. It is still
occurrence evidence, not a checklist: established introductions are included
(House Sparrow in the Americas), and a small, lightly birded country can keep a
rare visitor. The page says "GBIF records" for exactly this reason.

Names are the spellings MDD already uses for each country (read from the MDD
CSV the mammal pages are built from), so the three pages name places the same
way. The map is marine_world_map.json -- the one that draws Antarctica, which
the penguins need.

Takes 1.5-2 hours for ~11,000 species, one request at a time. Per-species results are cached in
data/raw/bird_gbif_country_cache.json, so an interrupted run resumes cheaply
and re-tuning the thresholds needs no network at all.
"""
import csv
import json
import sys
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).parent
TAXONOMY = HERE / "bird_taxonomy.json"
WORLD_MAP = HERE / "marine_world_map.json"
MDD_CSV = HERE / "raw" / "MDD_v2.5_6904species.csv"
CACHE = HERE / "raw" / "bird_gbif_country_cache.json"
OUT = HERE / "bird_gbif_countries.json"

FILTERS = (
    "&occurrenceStatus=PRESENT"
    "&basisOfRecord=PRESERVED_SPECIMEN&basisOfRecord=HUMAN_OBSERVATION"
    "&basisOfRecord=MATERIAL_SAMPLE&basisOfRecord=MACHINE_OBSERVATION"
)
MATCH_URL = "https://api.gbif.org/v1/species/match?strict=true&name={}"
OCC_URL = "https://api.gbif.org/v1/occurrence/search?taxonKey={}&facet=country&facetLimit=300&limit=0" + FILTERS
COUNTRY_ENUM_URL = "https://api.gbif.org/v1/enumeration/country"
AVES = 212

MIN_RECORDS = 5
MIN_COUNTRY_SHARE = 5e-5
MIN_SPECIES_SHARE = 0.05
# GBIF rate-limits per client (HTTP 429, no Retry-After). Parallel workers
# only trip the limit and then sit in back-off, so the fetch runs one request
# at a time and backs off hard when told to.
WORKERS = 1
PACE = 0.5            # seconds between requests: stays under the limit
THROTTLE_BACKOFF = 30


def fetch_json(url, retries=5):
    for attempt in range(retries):
        try:
            time.sleep(PACE)
            req = urllib.request.Request(url, headers={"User-Agent": "chiroptree-data/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as error:  # noqa: BLE001
            if attempt == retries - 1:
                return None
            if getattr(error, "code", None) == 429:
                print(f"GBIF rate limit; waiting {THROTTLE_BACKOFF * (attempt + 1)}s", flush=True)
                time.sleep(THROTTLE_BACKOFF * (attempt + 1))
            else:
                time.sleep(2 * (attempt + 1))


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def facet(data):
    for f in (data or {}).get("facets", []):
        if f.get("field") == "COUNTRY":
            return {c["name"]: c["count"] for c in f.get("counts", [])}
    return {}


def canonical_names(index):
    """map key -> the spelling MDD uses for it, so all three pages agree."""
    canonical = {}
    if not MDD_CSV.exists():
        return canonical
    with MDD_CSV.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            for raw in row["countryDistribution"].split("|"):
                name = raw.strip().rstrip("?").strip()
                key = index.get(norm(name)) if name and name != "NA" else None
                if key and key not in canonical:
                    canonical[key] = name
    return canonical


def fetch_species(sci):
    match = fetch_json(MATCH_URL.format(urllib.parse.quote(sci.replace("_", " "))))
    if match is None:
        return None                                   # network trouble: retry next run
    if match.get("rank") != "SPECIES" or "usageKey" not in match:
        return {"key": None, "counts": {}}            # GBIF does not know the name
    counts = fetch_json(OCC_URL.format(match["usageKey"]))
    if counts is None:
        return None
    return {"key": match["usageKey"], "counts": facet(counts)}


def main():
    tax = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    index = json.loads(WORLD_MAP.read_text(encoding="utf-8"))["index"]
    canonical = canonical_names(index)
    # --no-fetch rebuilds the output from the cache alone: for re-tuning the
    # thresholds, or for publishing what is cached while GBIF is throttling
    offline = "--no-fetch" in sys.argv
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    if "_enum" not in cache:
        cache["_enum"] = fetch_json(COUNTRY_ENUM_URL) or []
    enum = {r["iso2"]: r for r in cache["_enum"] if r.get("iso2")}
    if "_aves" not in cache:
        cache["_aves"] = facet(fetch_json(OCC_URL.format(AVES)))
    country_totals = cache["_aves"]

    names = [s["sciName"] for s in tax["species"]]
    todo = [] if offline else [n for n in names if n not in cache]
    print(f"{len(todo)} of {len(names)} species need fetching", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_species, n): n for n in todo}
        for fut in as_completed(futures):
            result = fut.result()
            if result is not None:
                cache[futures[fut]] = result
            done += 1
            if done % 250 == 0 or done == len(todo):
                print(f"{done}/{len(todo)} fetched", flush=True)
                CACHE.parent.mkdir(parents=True, exist_ok=True)
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    out, unplaced, unmatched, unfetched, dropped = {}, {}, 0, 0, 0
    for sci in names:
        entry = cache.get(sci)
        if not entry:
            unfetched += 1
            continue
        if entry["key"] is None:
            unmatched += 1
            continue
        counts = entry["counts"]
        total = sum(counts.values()) or 1
        kept = []
        for iso2, n in counts.items():
            if n < MIN_RECORDS:
                continue
            if n / country_totals.get(iso2, n) < MIN_COUNTRY_SHARE and n / total < MIN_SPECIES_SHARE:
                dropped += 1
                continue
            country = enum.get(iso2)
            if not country:
                continue                               # ZZ = high seas / unknown
            key = index.get(country["iso3"].lower()) or index.get(norm(country["title"]))
            if not key:
                unplaced[country["title"]] = unplaced.get(country["title"], 0) + 1
                continue
            name = canonical.get(key) or country["title"]
            if norm(name) not in index:
                unplaced[country["title"]] = unplaced.get(country["title"], 0) + 1
                continue
            if name not in kept:
                kept.append(name)
        if kept:
            out[sci] = sorted(kept)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    print(f"Wrote {OUT}: {len(out)} of {len(names)} species have countries; "
          f"{unmatched} names GBIF does not recognise; {unfetched} not fetched yet; "
          f"{dropped} country records dropped as vagrancy")
    if unplaced:
        print("Countries GBIF names that the map cannot place (skipped):")
        for title, n in sorted(unplaced.items(), key=lambda x: -x[1]):
            print(f"   {title}: {n} species")


if __name__ == "__main__":
    main()
