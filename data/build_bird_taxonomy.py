# /// script
# requires-python = ">=3.12"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Build data/bird_taxonomy.json from AviList, the unified global bird checklist.

Run:  uv run data/build_bird_taxonomy.py

The bat and marine mammal pages are built from the Mammal Diversity Database.
Birds are not mammals, so this page needs a different backbone. It uses
AviList v2025b (doi:10.2173/avilist.v2025b, CC BY 4.0). AviList is the checklist
that merged Clements/eBird and BirdLife/HBW into one global list in 2025, and
the IOC World Bird List is converging on it. It is the nearest thing birds have
to what MDD is for mammals.

The output deliberately keeps MDD's record shape (id, sciName as
Genus_species, mainCommonName, order, family, genus, specificEpithet,
iucnStatus, extinct, countryDistribution, ...) so every line of the master
page's lookup, card and map code reads it unchanged. Fields MDD has and
AviList does not (subfamily, tribe, realm, continents) are simply absent.
Fields AviList adds are carried under their own names:

  range     AviList's range text. Where the species row has none, the
            subspecies ranges are joined instead ("ssp: range; ...").
  ebird     Cornell Lab species code (eBird / Birds of the World URLs).
  avibase   Avibase ID.

The id is the eBird code where there is one (all but ~13 species), which is
stable across checklist versions in a way AviList's row sequence is not.

AviList has no country column. Countries come from GBIF occurrence records,
built separately by build_bird_country_distribution.py into
bird_gbif_countries.json. If that file exists, this script merges it into
countryDistribution. The pipeline is therefore:

  uv run data/build_bird_taxonomy.py              # names first
  uv run data/build_bird_country_distribution.py  # needs those names
  uv run data/build_bird_taxonomy.py              # merge the countries in
"""
import hashlib
import json
import re
import urllib.request
from pathlib import Path

import openpyxl

HERE = Path(__file__).parent
SOURCE_VERSION = "v2025b"
SOURCE_DOI = "10.2173/avilist.v2025b"
SOURCE_URL = "https://www.avilist.org/wp-content/uploads/2026/06/AviList-v2025b-10Jun2026-extended.xlsx"
RAW = HERE / "raw" / "AviList-v2025b-extended.xlsx"
COUNTRIES = HERE / "bird_gbif_countries.json"
OUT = HERE / "bird_taxonomy.json"

# AviList spells out extinction in free text; MDD's field is a 0/1 flag. Only
# the definite cases count here -- "possibly extinct" species stay extant, and
# their IUCN category (CR) carries the doubt.
EXTINCT = {"Extinct", "(extinct)"}


def ensure_raw() -> Path:
    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading AviList {SOURCE_VERSION} from {SOURCE_URL} ...")
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "chiroptree-data/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            RAW.write_bytes(response.read())
    return RAW


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip() if value is not None else ""


def iucn(value: str) -> str:
    # "CR (PE)" / "CR (PEW)" -- possibly extinct (in the wild) -- are still CR
    # to the page, which styles status by a bare category code
    code = clean(value).split(" ")[0]
    return code or "NE"


def read_rows(path: Path) -> list[dict]:
    workbook = openpyxl.load_workbook(path, read_only=True)
    sheet = workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    header = next(rows)
    return [dict(zip(header, row)) for row in rows]


def main():
    raw = ensure_raw()
    checksum = hashlib.sha256(raw.read_bytes()).hexdigest()
    countries = json.loads(COUNTRIES.read_text(encoding="utf-8")) if COUNTRIES.exists() else {}

    species, current, ssp_ranges = [], None, []
    family_names = {}

    def close_species():
        if current is not None and not current.get("range") and ssp_ranges:
            current["range"] = "; ".join(ssp_ranges)

    for row in read_rows(raw):
        rank = row.get("Taxon_rank")
        if rank == "subspecies":
            if current is not None and clean(row.get("Range")):
                epithet = clean(row["Scientific_name"]).split(" ")[-1]
                ssp_ranges.append(f"{epithet}: {clean(row['Range'])}")
            continue
        if rank != "species":
            continue
        close_species()
        ssp_ranges = []
        family_names.setdefault(clean(row["Family"]), clean(row["Family_English_name"]))
        name = clean(row["Scientific_name"])
        genus, epithet = name.split(" ", 1)
        english = clean(row["English_name_AviList"])
        others = []
        for column in ("English_name_Clements_v2025", "English_name_BirdLife_v10"):
            other = clean(row.get(column))
            if other and other != english and other not in others:
                others.append(other)
        code = clean(row.get("Species_code_Cornell_Lab"))
        record = {
            "id": code or f"avilist-{row['Sequence']}",
            "sciName": f"{genus}_{epithet}",
            "mainCommonName": english,
            "otherCommonNames": "|".join(others),
            "order": clean(row["Order"]),
            "family": clean(row["Family"]),
            "genus": genus,
            "specificEpithet": epithet,
            "authoritySpeciesAuthor": clean(row["Authority"]),
            "iucnStatus": iucn(row.get("IUCN_Red_List_Category")),
            # absent reads as "No" on the card, same as MDD's "0"
            "extinct": "1" if clean(row.get("Extinct_or_possibly_extinct")) in EXTINCT else "",
            "range": clean(row.get("Range")),
            "ebird": code,
            "avibase": clean(row.get("AvibaseID")),
        }
        found = countries.get(record["sciName"])
        if found:
            record["countryDistribution"] = "|".join(found)
        # empty fields cost bytes eleven thousand times over
        current = {k: v for k, v in record.items() if v}
        species.append(current)
    close_species()

    ids = [s["id"] for s in species]
    names = [s["sciName"] for s in species]
    assert len(ids) == len(set(ids)), "duplicate species id"
    assert len(names) == len(set(names)), "duplicate scientific name"

    payload = {
        "_meta": {
            "source": f"AviList {SOURCE_VERSION}",
            "sourceDoi": SOURCE_DOI,
            "sourceUrl": "https://www.avilist.org",
            "sourceChecksum": checksum,
            "license": "CC BY 4.0",
            "citation": f"AviList Core Team. 2025. AviList: The Global Avian Checklist, {SOURCE_VERSION}. https://doi.org/{SOURCE_DOI}",
            "speciesCount": len(species),
            "familyCount": len({s["family"] for s in species}),
            "genusCount": len({s["genus"] for s in species}),
            "orderCount": len({s["order"] for s in species}),
            "countrySource": "GBIF occurrence records, filtered for vagrancy -- see build_bird_country_distribution.py" if countries else None,
        },
        "families": sorted({s["family"] for s in species}),
        "familyNames": family_names,
        "species": species,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    with_countries = sum(1 for s in species if s.get("countryDistribution"))
    print(f"Wrote {len(species)} species, {payload['_meta']['genusCount']} genera, "
          f"{payload['_meta']['familyCount']} families, {payload['_meta']['orderCount']} orders "
          f"to {OUT} ({OUT.stat().st_size / 1024:.0f} KB); {with_countries} with countries")


if __name__ == "__main__":
    main()
