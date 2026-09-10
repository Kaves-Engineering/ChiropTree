"""Report named species still lacking a structured call measurement by region.

This deliberately reports only regions for which a named species roster
exists.  Central America and Denmark are not turned into fake complete lists:
their worksheets contain measurements, but no full regional checklist.
Mexico's list is explicitly a Sonozotz library cohort, not a Mexican national
fauna.

Rosters come from two places: the supplied upload archive, and `calls/rosters/`
for lists derived from published checklists fetched separately (see
`data/Fetch/FETCH_RESULTS_2026-09-09.md`).

Run: uv run data/report_regional_call_gaps.py
"""
import csv
import io
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "data" / "echolocation" / "files.zip"
TAXONOMY = ROOT / "data" / "chiroptera_taxonomy.json"
CALLS = ROOT / "data" / "calls" / "exports" / "calls.json"
ROSTER_DIR = ROOT / "data" / "calls" / "rosters"
FAMILY_DEFAULTS = ROOT / "data" / "calls" / "family_call_defaults.csv"
GENUS_DEFAULTS = ROOT / "data" / "calls" / "genus_call_defaults.csv"
OUT = ROOT / "data" / "calls" / "regional_missing_species.csv"
SUMMARY = ROOT / "data" / "calls" / "regional_coverage_summary.csv"

# (region, roster_scope, filename, source) where source is "archive" or "file".
ROSTERS = [
    ("Brazil", "national checklist (2024 audit; 186 species)", "southamerica_amazon_brazil_coverage_audit.csv", "archive"),
    ("Ecuador", "national checklist (Tirira 2018.1 audit; 171 species)", "ecuador_coverage_audit.csv", "archive"),
    ("Peru", "national checklist supplied with the Peru batch", "peru_bats_full_list.csv", "archive"),
    ("Europe", "47-species investigated cohort; not a continent-wide checklist", "europe_species.csv", "archive"),
    ("North America", "45-species United States/Canada cohort; reconstructed, not authoritative", "northamerica_species.csv", "archive"),
    ("Mexico", "69-species Sonozotz recording-library cohort; not a national checklist", "mexico_sonozotz_species.csv", "archive"),
    ("Colombia", "national checklist (Mamiferos de Colombia v1.14, SiB/GBIF; 222 species)",
     "colombia_bats.csv", "file"),
    ("Sub-Saharan Africa", "African Bat Database V2 (Monadjem et al. 2024); 292 confirmed "
     "binomials, 20 'cf.' records excluded", "africa_bats.csv", "file"),
    ("Vietnam", "90-species ChiroVox recording cohort (Gyorossy et al. 2024 Table S1); "
     "not a national checklist", "vietnam_bats.csv", "file"),
    ("Indonesia", "51-species GBIF recording cohort (MZB, Bukit Barisan Selatan and West "
     "Java call datasets); not a national checklist", "indonesia_bats.csv", "file"),
    ("Malaysia", "45-species GBIF recording cohort (Penang, Langkawi and HNHM Asian Bat "
     "Database); not a national checklist", "malaysia_bats.csv", "file"),
    ("Taiwan", "17-species GBIF reference-call cohort; not a national checklist",
     "taiwan_bats.csv", "file"),
]


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("_", " ").strip()).lower()


def non_echolocating_families():
    """Families positively asserted to lack laryngeal echolocation, and the genera
    within them that are nonetheless known click-echolocators (Rousettus).

    Design-doc A5: "no laryngeal echolocation" is a sourced claim, not missing
    data, and must not be counted as a coverage gap.
    """
    families, exceptions = set(), set()
    with FAMILY_DEFAULTS.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("laryngeal_echolocation") or "").strip().lower() == "no":
                families.add(row["family"].strip().lower())
    with GENUS_DEFAULTS.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("echolocation_mode", "").strip() == "non_laryngeal_clicks":
                exceptions.add(row["genus"].strip().lower())
    return families, exceptions


def rows(archive, filename, source):
    if source == "file":
        with (ROSTER_DIR / filename).open(encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)
        return
    with archive.open(filename) as handle:
        yield from csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8-sig", newline=""))


def main():
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))["species"]
    mdd = {norm(species["sciName"]): species for species in taxonomy}
    calls = json.loads(CALLS.read_text(encoding="utf-8"))["species"]
    no_echo_families, click_genera = non_echolocating_families()
    missing, summary = [], []
    with zipfile.ZipFile(ARCHIVE) as archive:
        for region, scope, filename, source in ROSTERS:
            roster = []
            for row in rows(archive, filename, source):
                name = (row.get("sci_name") or "").strip()
                if name:
                    roster.append((name, row.get("family", "")))
            # A worksheet may mention a species more than once; a roster may not.
            roster = list(dict.fromkeys(roster))
            measured = unresolved = not_applicable = 0
            for name, family in roster:
                taxon = mdd.get(norm(name))
                if taxon and calls.get(taxon["id"], {}).get("format") == "structured":
                    measured += 1
                    continue
                # A5: a sourced "does not echolocate" claim is not a coverage gap.
                if (family.strip().lower() in no_echo_families
                        and name.split()[0].strip().lower() not in click_genera):
                    not_applicable += 1
                    status = "no_laryngeal_echolocation"
                else:
                    status = "taxonomy_unresolved" if taxon is None else "no_structured_measurement"
                unresolved += status == "taxonomy_unresolved"
                missing.append({"region": region, "roster_scope": scope, "family": family,
                                "sci_name_as_rostered": name,
                                "mdd_id": taxon["id"] if taxon else "",
                                "status": status,
                                "source_roster": filename})
            summary.append({"region": region, "roster_scope": scope, "source_roster": filename,
                            "named_species": len(roster), "with_structured_measurement": measured,
                            "no_laryngeal_echolocation": not_applicable,
                            "still_missing": len(roster) - measured - not_applicable,
                            "taxonomy_unresolved": unresolved})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(missing[0]))
        writer.writeheader(); writer.writerows(missing)
    with SUMMARY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader(); writer.writerows(summary)
    print(f"Wrote {len(missing)} named gaps across {len(ROSTERS)} supplied rosters.")


if __name__ == "__main__":
    main()
