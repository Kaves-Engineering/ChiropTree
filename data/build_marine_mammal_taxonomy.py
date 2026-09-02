"""Filter the MDD species CSV to marine mammals and emit a compact JSON for the lookup page.

"Marine mammal" is not a taxonomic rank -- it's a polyphyletic, ecological
grouping of three independent lineages that separately returned to the sea:

  1. Cetacea (whales, dolphins, porpoises -- infraorders Mysticeti and
     Odontoceti). MDD v2.5 files these as suborder Cetacea within order
     Artiodactyla (the current "Cetartiodactyla" placement -- cetaceans nest
     among the even-toed ungulates), not as an order of their own.
  2. Order Sirenia (manatees, dugongs), full order.
  3. The pinniped families of order Carnivora: Otariidae (eared seals/sea
     lions), Phocidae (true seals), Odobenidae (walrus).

Unlike Chiroptera, there is no single ancestor exclusive to this group -- a
whale, a dugong and a walrus each independently evolved from separate
terrestrial carnivoran/ungulate stock. This script keeps that distinction
visible: every row carries the MDD `order` (and `family`, for the Carnivora
rows) it actually belongs to, and `_meta.lineages` records the three-part
composition and how each was selected, so nothing downstream has to guess
"which clade is this" from the family name alone.

Source: Mammal Diversity Database v2.5 (Zenodo doi:10.5281/zenodo.21654811).
Reuses the same raw CSV as build_taxonomy.py (data/raw/MDD_v2.5_6904species.csv);
downloads it on first run if it isn't already present locally.

To pick up a newer MDD release: find the current Zenodo record at
https://doi.org/10.5281/zenodo.4139722 (concept DOI, always resolves to latest),
update SOURCE_URL/SOURCE_DOI below (keep in sync with build_taxonomy.py), delete
data/raw/, and re-run this script.
"""
import csv
import json
import urllib.request
from pathlib import Path

SOURCE_DOI = "10.5281/zenodo.21654811"
SOURCE_URL = "https://zenodo.org/api/records/21654811/files/MDD_v2.5_6904species.csv/content"

RAW = Path(__file__).parent / "raw" / "MDD_v2.5_6904species.csv"
OUT = Path(__file__).parent / "marine_mammal_taxonomy.json"

PINNIPED_FAMILIES = {"Otariidae", "Phocidae", "Odobenidae"}


def ensure_raw_csv():
    if RAW.exists():
        return
    RAW.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading MDD release CSV from {SOURCE_URL} ...")
    urllib.request.urlretrieve(SOURCE_URL, RAW)

FIELDS = [
    "id", "sciName", "phylosort", "mainCommonName", "otherCommonNames",
    "order", "suborder", "infraorder", "superfamily", "family", "subfamily",
    "tribe", "genus", "subgenus", "specificEpithet",
    "authoritySpeciesAuthor", "authoritySpeciesYear",
    "countryDistribution", "continentDistribution", "biogeographicRealm",
    "iucnStatus", "extinct", "MSW3_sciName",
]


def lineage_of(row):
    # MDD v2.5 files whales/dolphins/porpoises as suborder Cetacea within
    # order Artiodactyla (the current "Cetartiodactyla" placement, cetaceans
    # nested among even-toed ungulates) rather than as their own order --
    # check suborder, not order, for this one.
    if row["suborder"] == "Cetacea":
        return "Cetacea"
    if row["order"] == "Sirenia":
        return "Sirenia"
    if row["order"] == "Carnivora" and row["family"] in PINNIPED_FAMILIES:
        return "Pinnipedia"
    return None


def main():
    ensure_raw_csv()
    with RAW.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        marine = []
        for row in reader:
            lineage = lineage_of(row)
            if lineage is None:
                continue
            rec = {k: row[k] for k in FIELDS}
            rec["lineage"] = lineage
            marine.append(rec)

    marine.sort(key=lambda r: float(r["phylosort"]))

    families = sorted({m["family"] for m in marine})
    genera = sorted({m["genus"] for m in marine})

    counts = {}
    for lineage in ("Cetacea", "Sirenia", "Pinnipedia"):
        members = [m for m in marine if m["lineage"] == lineage]
        counts[lineage] = {
            "speciesCount": len(members),
            "familyCount": len({m["family"] for m in members}),
            "genusCount": len({m["genus"] for m in members}),
        }

    payload = {
        "_meta": {
            "source": "Mammal Diversity Database v2.5",
            "sourceDoi": SOURCE_DOI,
            "sourceUrl": "https://www.mammaldiversity.org",
            "speciesCount": len(marine),
            "familyCount": len(families),
            "genusCount": len(genera),
            "lineages": {
                "Cetacea": "Suborder Cetacea within order Artiodactyla in MDD's "
                           "current placement (whales, dolphins, porpoises) -- "
                           "not a taxonomic order of its own here, but treated "
                           "as one of the three marine lineages regardless.",
                "Sirenia": "Full order Sirenia (manatees, dugong).",
                "Pinnipedia": "Otariidae, Phocidae and Odobenidae within order "
                              "Carnivora -- not a taxonomic order of their own.",
            },
            "counts": counts,
            "note": (
                "Marine mammals are not a clade: Cetacea, Sirenia and the "
                "pinniped families of Carnivora are three independently "
                "aquatic lineages grouped here ecologically, not by descent. "
                "See _meta.lineages / _meta.counts and the `lineage` field on "
                "every species record."
            ),
        },
        "families": families,
        "species": marine,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(marine)} marine mammal species across {len(families)} families to {OUT}")
    for lineage, c in counts.items():
        print(f"  {lineage}: {c['speciesCount']} species, {c['familyCount']} families, {c['genusCount']} genera")


if __name__ == "__main__":
    main()
