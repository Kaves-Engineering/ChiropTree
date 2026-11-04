"""Import adult body mass of bats from AnAge, Build 15 (Tacutu et al. 2018).

AnAge is a longevity database; its "Adult weight (g)" column is a compiled
adult mass. Its "Data quality" column grades the longevity record, not the
weight, so it is not used here.

Fetch (CC BY 3.0, Human Ageing Genomic Resources), then unzip into
data/raw/size/anage/:
    curl -L -o anage_dataset.zip https://genomics.senescence.info/species/dataset.zip

Run: uv run data/size/import_anage.py
"""
import csv

from size_lib import RAW, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "anage-2023"
TABLE = "anage/anage_data.txt"
FILES = {TABLE: "98867969fbd4d0bed6bab415c2715bb19079dbd7f92bdc26e5961856aa1c1519"}


def main() -> None:
    check_raw(FILES)
    with (RAW / TABLE).open(encoding="latin-1") as handle:
        table = [r for r in csv.DictReader(handle, delimiter="\t") if r["Order"] == "Chiroptera"]
    resolver = SizeResolver()
    rows = []
    for record in table:
        value = number(record["Adult weight (g)"])
        if not value:
            continue
        printed = f"{record['Genus']} {record['Species']}"
        species, method = resolver.resolve(printed)
        if not species:
            continue
        row = base_row(REFERENCE_ID, species, printed, method, f"anage_data.txt / Adult weight (g), HAGRID {record['HAGRID']}")
        row.update(observation_id=f"anage-{species['id']}-{printed.replace(' ', '_')}", trait="body_mass",
                   basis="measured", statistic="single", value=value, sex="pooled", data_year="2023",
                   verbatim_value=record["Adult weight (g)"])
        rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
