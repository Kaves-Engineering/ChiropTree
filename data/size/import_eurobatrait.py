"""Import forearm length and body mass from EuroBaTrait 1.0 (Froidevaux et al. 2023).

The morphology table gives, per population and study, a mean with SD and n.
Only rows of type "mean" are taken. EuroBaTrait's own summary rows ("mean of
means", "mean of min and max") are derived from those, so importing them
would count the same bats twice. Each row keeps the study it came from as its
upstream source and the area it was measured in.

Fetch (CC BY 4.0, figshare 10.6084/m9.figshare.21777161.v2), into
data/raw/eurobatrait-1.0/ (where the call importer keeps its tables):
    curl -L -o 03_morphology.csv https://ndownloader.figshare.com/files/39765382

Run: uv run data/size/import_eurobatrait.py
"""
import csv
import re

from size_lib import DATA, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "eurobatrait-2023"
TABLE = DATA / "raw" / "eurobatrait-1.0" / "03_morphology.csv"
FILES = {str(TABLE): "dfadfbccfbfd2753908e28e9db230dd61fe60d00634d58a018a4dcae91f76920"}
TRAITS = {"ForearmLength": "forearm_length", "BodyMass": "body_mass"}


def main() -> None:
    check_raw(FILES)
    with TABLE.open(encoding="utf-8-sig") as handle:
        table = list(csv.DictReader(handle))
    resolver = SizeResolver()
    rows = []
    for index, record in enumerate(table, start=2):  # line number in the file
        trait = TRAITS.get(record["verbatimTraitName"])
        if not trait or record["verbatimTraitValueType"] != "mean":
            continue
        value = number(record["verbatimTraitValue"])
        if not value:
            continue
        printed = record["verbatimScientificName"].replace("_", " ")
        species, method = resolver.resolve(printed)
        if not species:
            continue
        details = [record[k] for k in ("AdditionalInfo1", "AdditionalInfo2", "AdditionalInfo3") if record[k]]
        sex = "female" if "Female" in details else "male" if "Male" in details else "pooled"
        row = base_row(REFERENCE_ID, species, printed, method, f"03_morphology.csv line {index}")
        row.update(observation_id=f"eurobatrait-{species['id']}-L{index}", trait=trait, basis="measured",
                   statistic="mean", value=value, sd=number(record["verbatimTraitValueSD"]),
                   n=number(record["verbatimN1"]), sex=sex, area=re.sub(r"(?<=[a-z])(?=[A-Z])", " ", record["Area"].replace("_", " ")),
                   upstream_source=(record["FullReference"] or record["ShortReference"])[:200],
                   verbatim_value=record["verbatimTraitValue"],
                   notes="; ".join(d.replace("_", " ") for d in details))
        rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
