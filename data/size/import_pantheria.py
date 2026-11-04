"""Import adult forearm length and body mass from PanTHERIA 1.0 (Jones et al. 2009).

Uses the MSW 2005 table. 5-1 AdultBodyMass_g and 8-1 AdultForearmLen_mm are
species medians of values compiled from the literature (measured). Where
5-1 is missing, 5-5 AdultBodyMass_g_EXT may hold a mass that PanTHERIA's
metadata says was computed for bats from forearm length,
ln mass = -8.298 + 2.864 ln forearm; those are written as estimates.

Fetch (CC0, figshare 10.6084/m9.figshare.c.3301274.v1), then unzip into
data/raw/size/pantheria/:
    curl -L -o ECOL_90_184.zip https://ndownloader.figshare.com/files/5604752

Run: uv run data/size/import_pantheria.py
"""
import csv

from size_lib import RAW, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "pantheria-2009"
TABLE = "pantheria/PanTHERIA_1-0_WR05_Aug2008.txt"
FILES = {TABLE: "36e64314cae0394a966a63b949504d1975ac5c5629e05e36c1b139b3348f044a"}
EXT_METHOD = "PanTHERIA estimated it from forearm length: ln mass = -8.298 + 2.864 ln forearm (column 5-5_EXT)"


def main() -> None:
    check_raw(FILES)
    with (RAW / TABLE).open(encoding="latin-1") as handle:
        table = [r for r in csv.DictReader(handle, delimiter="\t") if r["MSW05_Order"] == "Chiroptera"]
    resolver = SizeResolver()
    rows = []
    for record in table:
        printed = record["MSW05_Binomial"]
        species, method = resolver.resolve(printed)
        if not species:
            continue
        oid = f"pantheria-{species['id']}-{printed.replace(' ', '_')}"
        cells = [
            ("forearm_length", "8-1_AdultForearmLen_mm", "measured", ""),
            ("body_mass", "5-1_AdultBodyMass_g", "measured", ""),
        ]
        if not number(record["5-1_AdultBodyMass_g"]):
            cells.append(("body_mass", "5-5_AdultBodyMass_g_EXT", "estimated", EXT_METHOD))
        for trait, column, basis, how in cells:
            value = number(record[column])
            if not value:
                continue
            row = base_row(REFERENCE_ID, species, printed, method, f"WR05 table / {column}")
            row.update(observation_id=oid, trait=trait, basis=basis, estimate_method=how,
                       statistic="median", value=value, sex="pooled", data_year="2008",
                       verbatim_value=record[column])
            rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
