"""Import adult forearm length and body mass from COMBINE (Soria et al. 2021).

COMBINE ships two tables with the same rows: trait_data_reported.csv holds
only values some source reported, and trait_data_imputed.csv fills the gaps by
phylogenetic imputation. trait_data_sources.csv names, cell by cell, where
each reported value came from. So each value here is one of:

- measured, with the upstream database COMBINE took it from (Amniote,
  PanTHERIA, PHYLACINE, ...), so build_size.py never counts it as a second
  independent source alongside that database;
- estimated, "split from X": COMBINE gave a newly split species the value of
  the species it was split from;
- estimated, imputed: present only in the imputed table.

Fetch (CC BY 4.0, figshare 10.6084/m9.figshare.13028255.v4), into
data/raw/size/combine/:
    curl -L -o trait_data_reported.csv https://ndownloader.figshare.com/files/27703263
    curl -L -o trait_data_imputed.csv  https://ndownloader.figshare.com/files/27703266
    curl -L -o trait_data_sources.csv  https://ndownloader.figshare.com/files/27703260

Run: uv run data/size/import_combine.py
"""
import csv

from size_lib import RAW, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "combine-2021"
FILES = {
    "combine/trait_data_reported.csv": "14ace2dff03b71c20dc923a9eb293aaadc29934e21c6f11fa30d1b70e5abab92",
    "combine/trait_data_imputed.csv": "b576cfd9f12b1441eb564bbf7acb65f06e676108aa0651aed9594585e7ff65f9",
    "combine/trait_data_sources.csv": "f0d8ba1e42fabed49ffd0d4e61a577c3bfee0a787b9886c5891f8707112a1200",
}
TRAITS = {"adult_forearm_length_mm": "forearm_length", "adult_mass_g": "body_mass"}
# COMBINE's names for the databases it drew on -> this project's reference ids
UPSTREAM = {
    "Amniotes": "amniote-2015",
    "PanTHERIA": "pantheria-2009",
    "PHYLACINE": "phylacine-2018",
    "Smith et al. (2003) (EltonTraits)": "mom-2003",
    "EltonTraits": "eltontraits-2014",
}


def key(row: dict) -> str:
    """The row's name. IUCN's, unless IUCN does not recognise the species (then PHYLACINE's)."""
    iucn = row["iucn2020_binomial"]
    return row["phylacine_binomial"] if iucn in ("", "NA", "Not recognised") else iucn


def read(name: str) -> dict[str, dict]:
    with (RAW / "combine" / name).open(encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["order"] == "Chiroptera"]
    table = {key(r): r for r in rows}
    if len(table) != len(rows):
        raise SystemExit(f"{name}: two rows share a name; the three tables can no longer be joined by name")
    return table


def main() -> None:
    check_raw(FILES)
    reported, imputed, sources = read("trait_data_reported.csv"), read("trait_data_imputed.csv"), read("trait_data_sources.csv")
    resolver = SizeResolver()
    rows = []
    for binomial, rep in reported.items():
        species, method = resolver.resolve(binomial)
        if not species and rep["phylacine_binomial"] not in ("", "NA", binomial):
            resolver.unresolved.pop()
            species, method = resolver.resolve(rep["phylacine_binomial"])
        if not species:
            continue
        for column, trait in TRAITS.items():
            value = number(rep.get(column))
            source = (sources[binomial].get(column) or "").strip()
            row = base_row(REFERENCE_ID, species, binomial, method, f"trait_data_reported.csv / {column}")
            if value and source.startswith("split from"):
                row.update(basis="estimated", upstream_source="",
                           estimate_method=f"COMBINE gave this species the value of {source[11:]}, the species it was split from")
            elif value:
                row.update(basis="measured", estimate_method="", upstream_source=UPSTREAM.get(source, source))
            else:
                value = number(imputed.get(binomial, {}).get(column))
                if not value:
                    continue
                row.update(basis="estimated", upstream_source="", locator=f"trait_data_imputed.csv / {column}",
                           estimate_method="COMBINE phylogenetic imputation (Soria et al. 2021)")
            row.update(observation_id=f"combine-{species['id']}-{binomial.replace(' ', '_')}", trait=trait,
                       statistic="mean", value=value, sex="pooled", data_year="2021",
                       verbatim_value=rep.get(column) if row["basis"] == "measured" else imputed[binomial][column])
            rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
