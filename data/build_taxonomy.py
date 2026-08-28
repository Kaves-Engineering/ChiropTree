"""Filter the MDD species CSV to Chiroptera and emit a compact JSON for the lookup page.

Source: Mammal Diversity Database v2.5 (Zenodo doi:10.5281/zenodo.21654811).
Downloads the raw release CSV on first run if it isn't already present locally.

To pick up a newer MDD release: find the current Zenodo record at
https://doi.org/10.5281/zenodo.4139722 (concept DOI, always resolves to latest),
update SOURCE_URL/SOURCE_DOI below to the new record's CSV file, delete
data/raw/, and re-run this script.
"""
import csv
import json
import urllib.request
from pathlib import Path

SOURCE_DOI = "10.5281/zenodo.21654811"
SOURCE_URL = "https://zenodo.org/api/records/21654811/files/MDD_v2.5_6904species.csv/content"

RAW = Path(__file__).parent / "raw" / "MDD_v2.5_6904species.csv"
OUT = Path(__file__).parent / "chiroptera_taxonomy.json"


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
    "iucnStatus", "extinct",
]

def main():
    ensure_raw_csv()
    with RAW.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        bats = [
            {k: row[k] for k in FIELDS}
            for row in reader
            if row["order"] == "Chiroptera"
        ]

    bats.sort(key=lambda r: float(r["phylosort"]))

    families = sorted({b["family"] for b in bats})
    genera = sorted({b["genus"] for b in bats})

    payload = {
        "_meta": {
            "source": "Mammal Diversity Database v2.5",
            "sourceDoi": SOURCE_DOI,
            "sourceUrl": "https://www.mammaldiversity.org",
            "speciesCount": len(bats),
            "familyCount": len(families),
            "genusCount": len(genera),
        },
        "families": families,
        "species": bats,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(bats)} Chiroptera species across {len(families)} families to {OUT}")

if __name__ == "__main__":
    main()
