"""Import forearm length and body mass of individual bats from ATLANTIC MAMMAL
TRAITS (Gonçalves et al. 2018), summarised per species.

23,010 bats of 98 species captured in the Atlantic Forest of Brazil, Argentina
and Paraguay, 1940-2017. Only adults are used, and pregnant females are left
out of body mass. Each species gets one row per trait with the mean, SD, n and
a range: the central 95% of the individuals when there are 20 or more, else
the minimum and maximum.

The data paper's supplement is on Wiley (blocked to scripted download); the
same table, unchanged, ships as an .rda in the MIT-licensed atlanticr package.
The data paper itself states there are no copyright restrictions. Its strings
are MacRoman-encoded, so they are read with that encoding forced. Fetch into
data/raw/size/atlantic/:
    curl -L -o atlantic_mammal_traits.rda https://raw.githubusercontent.com/mauriciovancine/atlanticr/main/data/atlantic_mammal_traits.rda

Run: uv run --with rdata --with pandas data/size/import_atlantic.py
"""
from collections import defaultdict

import rdata

from size_lib import RAW, SizeResolver, base_row, check_raw, report, summarise, write_review, write_rows

REFERENCE_ID = "atlantic-traits-2018"
TABLE = "atlantic/atlantic_mammal_traits.rda"
FILES = {TABLE: "c7d03c6fe4025ef75f05bf34fa4a7a4bde3792ee92d5195c58f506b1bc879226"}


def main() -> None:
    check_raw(FILES)
    parsed = rdata.parser.parse_file(RAW / TABLE)
    table = rdata.conversion.convert(parsed, default_encoding="mac_roman",
                                     force_default_encoding=True)["atlantic_mammal_traits"]
    bats = table[(table["order"] == "Chiroptera") & (table["age"] == "adult")]
    values = defaultdict(lambda: {"forearm_length": [], "body_mass": []})
    for record in bats.itertuples(index=False):
        name = str(record.binomial)
        if record.forearm == record.forearm and record.forearm > 0:  # NaN-safe
            values[name]["forearm_length"].append(float(record.forearm))
        if record.body_mass == record.body_mass and record.body_mass > 0 and str(record.reproductive_stage) != "pregnant":
            values[name]["body_mass"].append(float(record.body_mass))
    resolver = SizeResolver()
    # the source drops the final i of the epithet; MDD v2.5 lists the one
    # species as Lonchophylla peracchii D. Dias, Esbérard & Moratelli
    resolver.add_manual({"Lonchophylla peracchi": "1004940"})
    rows = []
    for printed, traits in sorted(values.items()):
        species, method = resolver.resolve(printed)
        if not species:
            continue
        for trait, measured in traits.items():
            if not measured:
                continue
            row = base_row(REFERENCE_ID, species, printed, method,
                           "ATLANTIC_TR_all_data.csv, adults" + (", not pregnant" if trait == "body_mass" else ""))
            row.update(observation_id=f"atlantic-{species['id']}-{printed.replace(' ', '_')}", trait=trait,
                       basis="measured", sex="pooled", area="Atlantic Forest (BR, AR, PY)", data_year="2017",
                       **summarise(measured))
            rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
