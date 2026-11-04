"""Import forearm length and weight of individual bats from the SONOZOTZ
call library metadata (MacSwiney González et al. 2020), summarised per species.

2,323 recorded bats of 69 species from Mexico, 2016-2019, each weighed and
measured at capture. Only adults identified with 90% certainty or more are
used, and pregnant females are left out of body mass. The range is the
central 95% with 20 or more bats, else the minimum and maximum.

Fetch (CC0, Dryad doi:10.5061/dryad.95x69p8g6); the importer reads the copy
already cached for the call work at data/Fetch/raw/sonozotz/:
    curl -L -o sonozotz.zip "https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.95x69p8g6/download"

Run: uv run --with openpyxl --with pandas data/size/import_sonozotz.py
"""
from collections import defaultdict

import pandas as pd

from size_lib import DATA, SizeResolver, base_row, check_raw, report, summarise, write_review, write_rows

REFERENCE_ID = "sonozotz-2020"
TABLE = DATA / "Fetch" / "raw" / "sonozotz" / "Metadata_Sonozotz.xlsx"
FILES = {str(TABLE): "5c0c5e4015aa12441fb4127e96b27e2fa4e999c2f0ae2bff137184a443b89265"}
MIN_CERTAINTY = 90


def main() -> None:
    check_raw(FILES)
    table = pd.read_excel(TABLE)
    table = table[(table["Age"] == "Adult") & (table["ID Certainty  "] >= MIN_CERTAINTY)]
    values = defaultdict(lambda: {"forearm_length": [], "body_mass": []})
    for _, record in table.iterrows():
        name = f"{record['Genus']} {record['Species']}" if len(str(record["Species"]).split()) == 1 else record["Species"]
        forearm = pd.to_numeric(record["Forearm length (mm)"], errors="coerce")
        weight = pd.to_numeric(record["Weight (gr)"], errors="coerce")
        if forearm == forearm and forearm > 0:
            values[name]["forearm_length"].append(float(forearm))
        if weight == weight and weight > 0 and record["Reproductive status"] != "Pregnant":
            values[name]["body_mass"].append(float(weight))
    resolver = SizeResolver()
    rows = []
    for printed, traits in sorted(values.items()):
        species, method = resolver.resolve(printed)
        if not species:
            continue
        for trait, measured in traits.items():
            if not measured:
                continue
            row = base_row(REFERENCE_ID, species, printed, method,
                           "Metadata_Sonozotz.xlsx, adults, ID certainty >= 90%"
                           + (", not pregnant" if trait == "body_mass" else ""))
            row.update(observation_id=f"sonozotz-{species['id']}-{printed.replace(' ', '_')}", trait=trait,
                       basis="measured", sex="pooled", area="Mexico", data_year="2019",
                       **summarise(measured))
            rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
