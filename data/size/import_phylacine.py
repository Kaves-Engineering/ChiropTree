"""Import body mass from PHYLACINE 1.2.1 (Faurby et al. 2018, 2020).

Mass.Method says how each value was obtained. "Reported" is a measurement
from the source in Mass.Source (mostly Smith et al. 2003, MOM, or a field
guide). Every other method is an estimate: scaled isometrically from
forearm, skull, mandible or bone size of a relative, borrowed from a relative
of similar size, or imputed. The method is copied onto the row word for word.

Fetch (CC0, GitHub MegaPast2Future/PHYLACINE_1.2 at commit
2fb87f0b994ee82daa6691931f15971535322a2e), into data/raw/size/phylacine/:
    curl -L -o Trait_data.csv https://raw.githubusercontent.com/MegaPast2Future/PHYLACINE_1.2/2fb87f0b994ee82daa6691931f15971535322a2e/Data/Traits/Trait_data.csv

Run: uv run data/size/import_phylacine.py
"""
import csv

from size_lib import RAW, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "phylacine-2018"
TABLE = "phylacine/Trait_data.csv"
FILES = {TABLE: "ab035a8fab3d18673dea1d4a56f741e3ea9f8ba460461c7a1e738621ca315ec7"}


def upstream(source: str) -> str:
    if source.startswith("Smith, F. A., et al. 2003. Body mass of late Quaternary mammals"):
        return "mom-2003"
    return source[:160]


def main() -> None:
    check_raw(FILES)
    with (RAW / TABLE).open(encoding="utf-8") as handle:
        table = [r for r in csv.DictReader(handle) if r["Order.1.2"] == "Chiroptera"]
    resolver = SizeResolver()
    rows = []
    for record in table:
        value = number(record["Mass.g"])
        if not value:
            continue
        printed = record["Binomial.1.2"].replace("_", " ")
        species, method = resolver.resolve(printed)
        if not species:
            continue
        how = record["Mass.Method"].strip()
        measured = how == "Reported"
        row = base_row(REFERENCE_ID, species, printed, method, "Data/Traits/Trait_data.csv / Mass.g")
        row.update(observation_id=f"phylacine-{species['id']}-{printed.replace(' ', '_')}",
                   trait="body_mass", basis="measured" if measured else "estimated",
                   estimate_method="" if measured else f"PHYLACINE: {how}",
                   statistic="single", value=value, sex="pooled", data_year="2020",
                   verbatim_value=record["Mass.g"], upstream_source=upstream(record["Mass.Source"]) if measured else "")
        rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
