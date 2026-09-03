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
import json
from pathlib import Path

from taxonomy_store import build_database, export_taxonomy

OUT = Path(__file__).parent / "marine_mammal_taxonomy.json"

PINNIPED_FAMILIES = {"Otariidae", "Phocidae", "Odobenidae"}


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
    def include(row):
        return lineage_of(row) is not None

    def add_lineage(row):
        row["lineage"] = lineage_of(row)

    payload = export_taxonomy(build_database(), OUT, include, add_lineage)
    marine = payload["species"]

    counts = {}
    for lineage in ("Cetacea", "Sirenia", "Pinnipedia"):
        members = [m for m in marine if m["lineage"] == lineage]
        counts[lineage] = {
            "speciesCount": len(members),
            "familyCount": len({m["family"] for m in members}),
            "genusCount": len({m["genus"] for m in members}),
        }

    payload["_meta"].update(
        {
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
        }
    )

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"Wrote {len(marine)} marine mammal species across "
        f"{payload['_meta']['familyCount']} families to {OUT}"
    )
    for lineage, c in counts.items():
        print(f"  {lineage}: {c['speciesCount']} species, {c['familyCount']} families, {c['genusCount']} genera")


if __name__ == "__main__":
    main()
