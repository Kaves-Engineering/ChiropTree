"""Fetch Danish vernacular names for every marine mammal species from GBIF.

Mirrors data/build_danish_names.py exactly, just pointed at the marine
mammal taxonomy instead of the Chiroptera one. GBIF aggregates vernacular
names from many taxonomic checklists/sources; we query by scientific name,
then pull any Danish-language ("dan") vernacular name attached to the
matched taxon. Species with no Danish name recorded anywhere in GBIF's
sources are simply omitted from the output -- we do not invent names.

Denmark has real, if occasional, records of several marine mammals in this
set (harbour porpoise, several seal species, occasional whale strandings),
so unlike bats this is not expected to come back nearly empty.
"""
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TAXONOMY = Path(__file__).parent / "marine_mammal_taxonomy.json"
OUT = Path(__file__).parent / "marine_mammal_danish_names.json"

MATCH_URL = "https://api.gbif.org/v1/species/match?name={}&strict=true"
VERNACULAR_URL = "https://api.gbif.org/v1/species/{}/vernacularNames?limit=200"

PREFERRED_SOURCE = "National Checklist of all species occurring in Denmark"


def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "treeofbatlife-lookup/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            if attempt == retries - 1:
                return None
            time.sleep(1.5 * (attempt + 1))


def danish_name_for(sci_name_space, fallback_name_space=None):
    match = fetch_json(MATCH_URL.format(urllib.parse.quote(sci_name_space)))
    if (not match or "usageKey" not in match) and fallback_name_space:
        # MDD's current genus placement is sometimes ahead of GBIF's backbone;
        # retry with the MSW3-era name, which GBIF's taxonomy generally does
        # recognise (same rationale as the bat script).
        match = fetch_json(MATCH_URL.format(urllib.parse.quote(fallback_name_space)))
    if not match or "usageKey" not in match:
        return None
    vern = fetch_json(VERNACULAR_URL.format(match["usageKey"]))
    if not vern:
        return None
    dan = [v for v in vern.get("results", []) if v.get("language") == "dan"]
    if not dan:
        return None
    # Prefer the official Danish national checklist source; else first seen.
    preferred = [v for v in dan if v.get("source") == PREFERRED_SOURCE or v.get("country") == "DK"]
    pick = preferred[0] if preferred else dan[0]
    all_names = sorted({v["vernacularName"] for v in dan})
    return {
        "name": pick["vernacularName"],
        "source": pick.get("source", "GBIF"),
        "allNames": all_names,
        "gbifKey": match["usageKey"],
        "matchedName": match.get("scientificName", sci_name_space),
    }


def main():
    tax = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    species = tax["species"]
    results = {}
    done = 0
    total = len(species)

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {}
        for s in species:
            msw3 = s.get("MSW3_sciName") or ""
            fallback = msw3.replace("_", " ") if msw3 and msw3 != "NA" else None
            fut = pool.submit(danish_name_for, s["sciName"].replace("_", " "), fallback)
            futures[fut] = s
        for fut in as_completed(futures):
            species = futures[fut]
            done += 1
            try:
                res = fut.result()
            except Exception:  # noqa: BLE001
                res = None
            if res:
                results[species["id"]] = {
                    **res,
                    "mddId": species["id"],
                    "matchMethod": "accepted-name-or-msw3-fallback",
                }
            if done % 50 == 0:
                print(f"{done}/{total} checked, {len(results)} Danish names found so far")

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"Done: {len(results)} of {total} species have a Danish name. Wrote {OUT}")


if __name__ == "__main__":
    main()
