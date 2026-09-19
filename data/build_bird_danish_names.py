# /// script
# requires-python = ">=3.12"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Danish names for every bird species, from DOF's "Navne på alverdens fugle".

Run:  uv run data/build_bird_danish_names.py

The mammal pages get their Danish names from GBIF vernacular records, which is
the best there is for mammals and still leaves most bats unnamed. Birds are far
better served. Dansk Ornitologisk Forening's name group (Navnegruppen) gives a
Danish name to every species on the IOC World Bird List, plus most
subspecies, and publishes it as a spreadsheet:

  Navne på alverdens fugle. Systematiske, danske, engelske og tyske navne.
  DOF & Landsorganisationen Danske Fugleforeninger, ved M. Behnke-Pedersen,
  S. Rønnest, J. Møller Hansen & J. Fjeldså. Based on IOC 12.1 (2022).

The list follows IOC 12.1, the page follows AviList v2025b, and the two do not
split species identically. Names are matched in order of confidence, and each
record says which method matched it:

  exact      same binomial
  ssp        AviList treats as a species what IOC 12.1 kept as a subspecies:
             the DOF subspecies name (same genus, same epithet) is used
  english    the English name matches one of AviList's three English names
             (catches genus moves, e.g. a species AviList files in a new genus)

Species that none of these reach are left out rather than given a guessed
name -- the same rule the mammal pages follow.
"""
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

import openpyxl

HERE = Path(__file__).parent
SOURCE_URL = ("https://www.dof.dk/images/grupper/navne/dokumenter/"
              "Navne_pa_alverdens_fugle._Systematiske_danske_engelske_og_tyske_navne.xlsx")
RAW = HERE / "raw" / "dof_navne_alverdens_fugle.xlsx"
TAXONOMY = HERE / "bird_taxonomy.json"
OUT = HERE / "bird_danish_names.json"
SOURCE = "DOF Navnegruppen, Navne på alverdens fugle (IOC 12.1)"


def ensure_raw() -> Path:
    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {SOURCE_URL} ...")
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "chiroptree-data/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            RAW.write_bytes(response.read())
    return RAW


def clean(value) -> str:
    # the sheet marks extinct taxa with a dagger that arrives as U+FFFD
    text = str(value or "").replace("�", "").replace("†", "")
    return re.sub(r"\s+", " ", text).strip()


def english_key(name: str) -> str:
    name = unicodedata.normalize("NFKD", name.lower())
    name = "".join(c for c in name if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", name)


def read_dof(path: Path):
    """-> ({binomial: (danish, english)}, {trinomial: danish})."""
    sheet = openpyxl.load_workbook(path, read_only=True)["12.1 final"]
    species, subspecies = {}, {}
    for row in sheet.iter_rows(min_row=2, values_only=True):
        short, full, danish, english = (row[1], row[2], row[3], row[5])
        full, danish = clean(full), clean(danish)
        if not full or not danish or not short:
            continue
        words = full.split(" ")
        if str(short).startswith(" ") and len(words) == 3:
            subspecies[full] = danish
        elif len(words) == 2 and words[0][:1].isupper() and words[1].islower():
            species[full] = (danish, clean(english))
    return species, subspecies


def main():
    dof_species, dof_ssp = read_dof(ensure_raw())
    by_english = {}
    for binomial, (danish, english) in dof_species.items():
        if english:
            by_english.setdefault(english_key(english), []).append((binomial, danish))

    tax = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    out, methods = {}, {"exact": 0, "ssp": 0, "english": 0}
    for record in tax["species"]:
        binomial = record["sciName"].replace("_", " ")
        genus, epithet = record["genus"], record["specificEpithet"]
        hit = None
        if binomial in dof_species:
            hit = ("exact", binomial, dof_species[binomial][0])
        else:
            ssp = [(t, d) for t, d in dof_ssp.items()
                   if t.startswith(genus + " ") and t.endswith(" " + epithet)]
            if len(ssp) == 1:
                hit = ("ssp", ssp[0][0], ssp[0][1])
            else:
                english = [record.get("mainCommonName", "")] + record.get("otherCommonNames", "").split("|")
                candidates = {c for e in english if e for c in by_english.get(english_key(e), [])}
                if len(candidates) == 1:
                    matched, danish = candidates.pop()
                    hit = ("english", matched, danish)
        if not hit:
            continue
        method, matched, danish = hit
        methods[method] += 1
        out[record["id"]] = {
            "name": danish,
            "allNames": [danish],
            "source": SOURCE,
            "matchMethod": method,
            "matchedName": matched,
        }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    total = len(tax["species"])
    print(f"Wrote {len(out)} of {total} species ({len(out) / total:.1%}) to {OUT}: {methods}")


if __name__ == "__main__":
    main()
