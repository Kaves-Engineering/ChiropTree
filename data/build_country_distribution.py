"""Supplement MDD's countryDistribution with GBIF occurrence-record evidence.

MDD's per-species country field is a checklist column that lags real-world
records -- e.g. it omits several long-established Danish species (northern
bat, whiskered bat, Leisler's bat, greater mouse-eared bat) that Denmark's own
national bat surveys have recorded for decades. This script asks GBIF's
occurrence index, country by country, which countries hold real observation
records for each Chiroptera species, and writes any country
*not already in MDD's list* to data/gbif_country_supplement.json. Only
observation records count -- see BASIS_OF_RECORD below for why museum
specimens are left out.

This is additive only: MDD's own countries are never removed or overridden,
and nothing here touches chiroptera_taxonomy.json (so re-running
build_taxonomy.py against a new MDD release does not wipe this file). The
supplement is merged into countryDistribution client-side, at page load, the
same way data/danish_names.json is merged in -- see the bundled() loader in
chiroptera-tree.html and index.html.

A country only counts as evidence if it has at least MIN_RECORDS observation
records with occurrenceStatus=PRESENT -- single records are usually vagrants,
escapes, or misidentifications (e.g. this threshold drops a single Mexican
record GBIF has for Eptesicus nilssonii, a boreal Palearctic species).

Run:  uv run data/build_country_distribution.py
Takes roughly 10-20 minutes for ~1,500 species (two GBIF calls each, GBIF's
public API is not key-gated but is rate-limited by fair use, hence the
worker cap and retry/backoff below). Safe to re-run: results are cached in
data/raw/gbif_country_cache.json so an interrupted run resumes cheaply (the
cache records which BASIS_OF_RECORD it was built under, and is discarded
rather than reused when that changes).
"""
import json
import math
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).parent
TAXONOMY = HERE / "chiroptera_taxonomy.json"
WORLD_MAP = HERE / "world_map.json"
CACHE = HERE / "raw" / "gbif_country_cache.json"
OUT = HERE / "gbif_country_supplement.json"

MATCH_URL = "https://api.gbif.org/v1/species/match?name={}&strict=true"
# Museum-specimen records (PRESERVED_SPECIMEN, and the tissue/DNA subsamples
# filed as MATERIAL_SAMPLE) are deliberately excluded. A specimen record's
# country is the country of the *collection* as often as the country of the
# animal, and old catalogue transcriptions carry misidentifications that no
# modern survey would repeat -- e.g. four ZOBODAT specimens place the Mexican
# Balantiopteryx io in Romanian Dobrogea, enough to clear MIN_RECORDS on its
# own. Observation records are the ones that reflect where a bat was actually
# seen, so only those count as evidence here.
BASIS_OF_RECORD = ("HUMAN_OBSERVATION", "MACHINE_OBSERVATION")
OCC_URL = (
    "https://api.gbif.org/v1/occurrence/search?taxonKey={}&facet=country"
    "&facetLimit=300&limit=0&occurrenceStatus=PRESENT"
    + "".join("&basisOfRecord=" + b for b in BASIS_OF_RECORD)
)
COUNTRY_ENUM_URL = "https://api.gbif.org/v1/enumeration/country"

MIN_RECORDS = 3
WORKERS = 8

# A record count alone cannot tell a range extension from a misidentification:
# four camera-trap records from a Colombian wild-felid survey were enough to put
# Pipistrellus pipistrellus, a Palearctic bat, in South America. So a candidate
# country also has to sit near the range MDD already asserts -- within
# MAX_RANGE_GAP_KM of the nearest country on MDD's own list, measured outline to
# outline on data/world_map.json. That keeps the cases this file exists for
# (Denmark borders Germany; Mexico borders Guatemala) and drops the ones an
# ocean away. Continent membership would not work here: MDD's continent labels
# cut Neotropical ranges in half at the Panama isthmus.
MAX_RANGE_GAP_KM = 500
# world_map.json is Robinson-projected, 800 px to 360 degrees of longitude at
# the equator. Robinson compresses east-west toward the poles, so a high-latitude
# gap comes out up to ~25% short -- the error runs toward keeping a country,
# which is the safe direction for an additive supplement.
KM_PER_PX = 40075 / 800


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


def load_cache():
    """Cached counts, but only if they were fetched under today's record
    filter -- changing BASIS_OF_RECORD makes every cached count meaningless."""
    if not CACHE.exists():
        return {}
    raw = json.loads(CACHE.read_text(encoding="utf-8"))
    if raw.get("basisOfRecord") != list(BASIS_OF_RECORD):
        print("cache was built under a different record filter; refetching from scratch")
        return {}
    return raw.get("species", {})


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps({"basisOfRecord": list(BASIS_OF_RECORD), "species": cache}, ensure_ascii=False),
        encoding="utf-8",
    )


def build_geometry(wmap):
    """map key -> (outline points, bounding box), in projected px.

    Countries drawn as a single dot (small islands) and the 27 microstates the
    map carries no coordinates for at all are handled by their callers, not
    here -- a country with no geometry is never rejected for being far away."""
    geom = {}
    for key, path in wmap["shapes"].items():
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path)]
        pts = list(zip(nums[0::2], nums[1::2]))
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        geom[key] = (pts, (min(xs), min(ys), max(xs), max(ys)))
    for key, (x, y) in wmap["dots"].items():
        geom.setdefault(key, ([(x, y)], (x, y, x, y)))
    return geom


def bbox_gap(a, b):
    """Distance between two bounding boxes -- a cheap lower bound on the
    distance between the outlines inside them."""
    return math.hypot(max(a[0] - b[2], b[0] - a[2], 0.0), max(a[1] - b[3], b[1] - a[3], 0.0))


def pair_gap_px(geom, a, b, memo):
    """Shortest distance between two countries' outlines. Boxes that are
    already further apart than the cutoff return that lower bound instead of
    the exact figure -- the caller only ever compares against the cutoff."""
    key = (a, b) if a < b else (b, a)
    if key in memo:
        return memo[key]
    (pts_a, box_a), (pts_b, box_b) = geom[a], geom[b]
    gap = bbox_gap(box_a, box_b)
    if gap * KM_PER_PX <= MAX_RANGE_GAP_KM:
        gap = min(math.dist(p, q) for p in pts_a for q in pts_b)
    memo[key] = gap
    return gap


def range_gap_km(geom, candidate, home, memo):
    """How far a candidate country is from the nearest country MDD already
    lists for the species, or None when that cannot be measured."""
    if candidate not in geom:
        return None
    home = [k for k in home if k in geom]
    if not home:
        return None
    return min(pair_gap_px(geom, candidate, k, memo) for k in home) * KM_PER_PX


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
    geom = build_geometry(wmap)
    gap_memo = {}

    cache = load_cache()
    # a cache we could not reuse means every previously written supplement was
    # derived under the old record filter too, so it must not be carried over
    carry_previous = bool(cache)
    if cache:
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
            if done % 50 == 0:
                print(f"{done}/{len(todo)} fetched")
                save_cache(cache)

    save_cache(cache)

    previous = json.loads(OUT.read_text(encoding="utf-8")) if (OUT.exists() and carry_previous) else {}
    supplement = {s["sciName"]: previous[s["sciName"]] for s in species if s["sciName"] in previous}
    unmatched_countries = set()
    too_far = []
    unknown_to_gbif = [s["sciName"] for s in species if s["sciName"] not in cache]
    for s in species:
        sci = s["sciName"]
        if sci not in cache:
            continue
        counts = cache[sci]
        mdd_countries = [n.strip().rstrip("?").strip() for n in (s.get("countryDistribution") or "").split("|")]
        mdd_countries = [n for n in mdd_countries if n and n != "NA"]
        existing = {norm(n) for n in mdd_countries}
        home = {k for k in (wmap["index"].get(norm(n)) for n in mdd_countries) if k}
        candidates = []
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
            candidates.append((name, wmap["index"].get(norm(name))))

        # An accepted country joins the range, so the next country can be
        # measured from it: a range that MDD stops short of is reached one
        # border at a time, each step paying the same MIN_RECORDS toll. That is
        # what carries Uroderma bilobatum from Colombia up through Panama to
        # Mexico, while nothing gets Pipistrellus pipistrellus across the
        # Atlantic -- there is no chain of record-bearing countries to cross.
        added = []
        spreading = True
        while spreading:
            spreading = False
            for entry in list(candidates):
                name, key = entry
                gap = range_gap_km(geom, key, home, gap_memo)
                if gap is not None and gap > MAX_RANGE_GAP_KM:
                    continue
                candidates.remove(entry)
                added.append(name)
                if key:
                    home.add(key)
                spreading = True
        for name, key in candidates:
            too_far.append((round(range_gap_km(geom, key, home, gap_memo)), sci, name))
        if added:
            supplement[sci] = sorted(added)
        else:
            supplement.pop(sci, None)

    OUT.write_text(json.dumps(supplement, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    total_added = sum(len(v) for v in supplement.values())
    print(f"Done: {len(supplement)} species gained countries, {total_added} country entries added. Wrote {OUT}")
    if too_far:
        too_far.sort(reverse=True)
        print(f"{len(too_far)} candidate countries dropped as too far from MDD's range, farthest first:")
        for gap, sci, name in too_far[:10]:
            print(f"   {gap:>6} km  {sci.replace('_', ' ')} -> {name}")
        if len(too_far) > 10:
            print(f"   ... and {len(too_far) - 10} more")
    if unknown_to_gbif:
        # names GBIF's backbone does not carry at all (mostly recent MDD
        # splits). They get no supplement, and are retried on every run.
        print(f"{len(unknown_to_gbif)} species have no GBIF backbone match, e.g. "
              + ", ".join(n.replace("_", " ") for n in unknown_to_gbif[:3]))
    if unmatched_countries:
        print(f"{len(unmatched_countries)} GBIF countries could not be placed on the map (skipped):")
        for c in sorted(unmatched_countries):
            print(f"   {c}")


if __name__ == "__main__":
    main()
