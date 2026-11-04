"""Import body mass from EltonTraits 1.0 (Wilman et al. 2014).

BodyMass-SpecLevel says how each value was obtained, per the data paper's
metadata: 1 = species-level data (measured; the source is usually Smith et al.
2003's MOM database or PanTHERIA, named in BodyMass-Source), 0 = a genus or
family average (estimated), 2 = phylogenetically imputed by Jetz & Freckleton
(estimated).

Fetch (CC0, figshare 10.6084/m9.figshare.c.3306933.v1), into
data/raw/size/eltontraits/:
    curl -L -o MamFuncDat.txt https://ndownloader.figshare.com/files/5631084

Run: uv run data/size/import_eltontraits.py
"""
import csv

from size_lib import RAW, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "eltontraits-2014"
TABLE = "eltontraits/MamFuncDat.txt"
FILES = {TABLE: "51acbe6215b3c1f742463ff3fb37ef607150c052e0f7a9dc0d97fcaca61d3f76"}
# MamFuncDatSources.txt reference ids -> this project's reference ids
UPSTREAM = {"Ref_117": "mom-2003", "Ref_58": "pantheria-2009"}
ESTIMATES = {
    "0": "EltonTraits used a genus or family average (BodyMass-SpecLevel 0)",
    "2": "EltonTraits used a phylogenetic imputation by Jetz & Freckleton (BodyMass-SpecLevel 2)",
}
# EltonTraits has no order column; its families, in its own spelling
BAT_FAMILIES = {
    "Craseonycteridae", "Emballonuridae", "Furipteridae", "Hipposideridae", "Megadermatidae",
    "Molossidae", "Mormoopidae", "Mystacinidae", "Myzopodidae", "Natalidae", "Noctilionidae",
    "Nycteridae", "Phyllostomidae", "Pteropodidae", "Rhinolophidae", "Rhinopomatidae",
    "Thyropteridae", "Vespertilionidae", "Miniopteridae", "Cistugidae", "Rhinonycteridae",
}


def main() -> None:
    check_raw(FILES)
    with (RAW / TABLE).open(encoding="latin-1") as handle:
        table = [r for r in csv.DictReader(handle, delimiter="\t") if r["MSWFamilyLatin"] in BAT_FAMILIES]
    resolver = SizeResolver()
    rows = []
    for record in table:
        printed = record["Scientific"]
        value = number(record["BodyMass-Value"])
        if not value:
            continue
        species, method = resolver.resolve(printed)
        if not species:
            continue
        level = record["BodyMass-SpecLevel"]
        source = record["BodyMass-Source"].strip()
        row = base_row(REFERENCE_ID, species, printed, method, f"MamFuncDat.txt / BodyMass-Value ({source})")
        row.update(observation_id=f"eltontraits-{species['id']}-{printed.replace(' ', '_')}",
                   trait="body_mass", basis="measured" if level == "1" else "estimated",
                   estimate_method=ESTIMATES.get(level, ""), statistic="single", value=value,
                   sex="pooled", data_year="2014", verbatim_value=record["BodyMass-Value"],
                   upstream_source=UPSTREAM.get(source, source) if level == "1" else "")
        rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
