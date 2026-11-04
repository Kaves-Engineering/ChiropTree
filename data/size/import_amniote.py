"""Import body mass from the Amniote life-history database (Myhrvold et al. 2015).

adult_body_mass_g is pooled; female_body_mass_g and male_body_mass_g are kept
as their own rows, which gives a few species a sex-specific spread. The
companion reference table names the source of each cell. A cell taken
straight from PanTHERIA (Jones et al. 2009) is marked as that upstream, so it
is not counted as independent of PanTHERIA itself.

Fetch (CC0, figshare 10.6084/m9.figshare.c.3308127.v1), then unzip into
data/raw/size/amniote/:
    curl -L -o ECOL_96_269.zip https://ndownloader.figshare.com/files/8067269

Run: uv run data/size/import_amniote.py
"""
import csv

from size_lib import RAW, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "amniote-2015"
TABLE = "amniote/Data_Files/Amniote_Database_Aug_2015.csv"
REFS = "amniote/Data_Files/Amniote_Database_References_Aug_2015.csv"
FILES = {
    TABLE: "ae16377ebe8a172949c2b8c200a50c5d0c7fc04d34bd3c9704635da4a4d51f53",
    REFS: "dd07f835d9f928fe25015ba090f414ed52b7e881c7ae88e3d700cf1264817352",
}
COLUMNS = {"adult_body_mass_g": "pooled", "female_body_mass_g": "female", "male_body_mass_g": "male"}


def upstream(reference: str) -> str:
    reference = reference.strip()
    if reference.startswith("Jones, K., Bielby, J., Cardillo, M. et al., 2009") and ";" not in reference:
        return "pantheria-2009"
    return "" if reference == "-999" else reference[:160]


def read(rel: str) -> list[dict]:
    with (RAW / rel).open(encoding="latin-1") as handle:
        return [r for r in csv.DictReader(handle) if r["order"] == "Chiroptera"]


def main() -> None:
    check_raw(FILES)
    table = read(TABLE)
    refs = {(r["genus"], r["species"]): r for r in read(REFS)}
    resolver = SizeResolver()
    rows = []
    for record in table:
        printed = f"{record['genus']} {record['species']}"
        cells = [(c, s) for c, s in COLUMNS.items() if number(record[c])]
        if not cells:
            continue
        species, method = resolver.resolve(printed)
        if not species:
            continue
        cited = refs.get((record["genus"], record["species"]), {})
        for column, sex in cells:
            row = base_row(REFERENCE_ID, species, printed, method, f"Amniote_Database_Aug_2015.csv / {column}")
            row.update(observation_id=f"amniote-{species['id']}-{printed.replace(' ', '_')}-{sex}",
                       trait="body_mass", basis="measured", statistic="mean", value=number(record[column]),
                       sex=sex, data_year="2015", verbatim_value=record[column],
                       upstream_source=upstream(cited.get(column, "")))
            rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
