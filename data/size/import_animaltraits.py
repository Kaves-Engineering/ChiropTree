"""Import bat body masses from AnimalTraits (Herberstein et al. 2022).

AnimalTraits collects body mass alongside metabolic rate or brain size, each
row from one published study and usually from a few individuals (often one,
for the brain-size studies). Every row is kept as its own measurement, with
the study it came from as the upstream source. The table stores mass in kg;
the study's own figure, in its own unit, is kept as the verbatim value.

Fetch (CC0, Zenodo doi:10.5281/zenodo.6468938, v1.0.7), into
data/raw/size/animaltraits/:
    curl -L -o observations.csv https://zenodo.org/api/records/6468938/files/observations.csv/content

Run: uv run data/size/import_animaltraits.py
"""
import csv

from size_lib import RAW, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "animaltraits-2022"
TABLE = "animaltraits/observations.csv"
FILES = {TABLE: "151a77e6e9d6c27878e7c94321b3d686b81088d4845c0a510fcdb0d3a45fb44d"}
TO_GRAMS = {"kg": 1000.0, "g": 1.0}


def grams(value: str, unit: str) -> str:
    return number(float(value) * TO_GRAMS[unit]) if number(value) else ""


def main() -> None:
    check_raw(FILES)
    with (RAW / TABLE).open(encoding="utf-8") as handle:
        table = [r for r in csv.DictReader(handle) if r["order"] == "Chiroptera"]
    resolver = SizeResolver()
    rows = []
    for index, record in enumerate(table):
        unit = record["body mass - units"]
        value = grams(record["body mass"], unit)
        if not value:
            continue
        printed = record["species"]
        species, method = resolver.resolve(printed)
        if not species:
            continue
        low, high = grams(record["body mass - minimum"], unit), grams(record["body mass - maximum"], unit)
        sex = {"female": "female", "male": "male"}.get(record["sex"].lower(), "pooled")
        row = base_row(REFERENCE_ID, species, printed, method, f"observations.csv, {record['inTextReference']}")
        row.update(observation_id=f"animaltraits-{species['id']}-{index}", trait="body_mass", basis="measured",
                   statistic="mean", value=value, value_min=low, value_max=high,
                   range_type="min_max" if low and high else "", n=number(record["sampleSizeValue"]),
                   sex=sex, data_year=record["publicationYear"], upstream_source=record["fullReference"][:200],
                   verbatim_value=f"{record['original body mass']} {record['original body mass - units']}".strip())
        rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
