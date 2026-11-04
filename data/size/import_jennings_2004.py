"""Import Table 2 of Jennings et al. (2004): mass and forearm of West Indian bats.

300 adult, non-gravid bats of 14 taxa caught on Puerto Rico, Dominica and St.
Vincent, 1994-1996, given as mean ± SD (p. 81). Two taxa are split by sex
because the paper found sexual dimorphism in mass. The sex symbols are lost in
the PDF's text layer; the paper's own text (p. 77) says Monophyllus plethodon
luciae males are heavier, and Artibeus jamaicensis schwartzi females are
heavier, which fixes which row is which.

Taxa resolve through the same hand-checked trinomial table the Table 1 call
importer uses (data/build_jennings_2004_calls.py), so both tables of the
paper always land on the same species.

Run: uv run data/size/import_jennings_2004.py
"""
from size_lib import DATA, SizeResolver, base_row, check_raw, report, write_rows

from build_jennings_2004_calls import RAW, RAW_SHA256, TAXA  # data/ is on the path via size_lib

REFERENCE_ID = "jennings-2004"

# Transcribed from Table 2 (p. 81): taxon, sex, n, mass mean, SD, forearm mean, SD
TABLE_2 = [
    ("M. blainvillii", "pooled", 18, "9.4", "0.8", "47.3", "3.2"),
    ("P. davyi davyi", "pooled", 7, "9.9", "0.8", "48.3", "1.5"),
    ("P. parnellii portoricensis", "pooled", 6, "11.3", "2.5", "51.0", "0.9"),
    ("P. quadridens fuliginosus", "pooled", 16, "5.7", "0.7", "38.6", "1.1"),
    ("B. cavernarum intermedia", "pooled", 10, "46.0", "3.9", "66.3", "1.7"),
    ("E. bombifrons bombifrons", "pooled", 17, "16.3", "2.6", "48.2", "1.7"),
    ("G. longirostris rostrata", "pooled", 51, "11.9", "1.1", "38.5", "1.0"),
    ("M. plethodon luciae", "male", 8, "16.7", "1.1", "42.3", "0.6"),
    ("M. plethodon luciae", "female", 21, "14.6", "0.9", "41.8", "1.1"),
    ("A. jamaicensis jamaicensis", "pooled", 17, "45.5", "4.9", "61.6", "2.2"),
    ("A. jamaicensis schwartzi", "male", 52, "57.8", "6.5", "66.2", "1.6"),
    ("A. jamaicensis schwartzi", "female", 43, "62.6", "7.5", "66.5", "1.9"),
    ("S. rufum darioi", "pooled", 4, "24.3", "3.4", "49.0", "0.8"),
    ("S. lilium angeli", "pooled", 11, "21.1", "0.9", "44.3", "0.6"),
    ("S. lilium paulsoni", "pooled", 11, "19.4", "2.7", "42.7", "3.1"),
    ("N. stramineus stramineus", "pooled", 8, "6.3", "0.8", "41.3", "3.5"),
]
assert sum(row[2] for row in TABLE_2) == 300, "Table 2 covers 300 bats"


def main() -> None:
    check_raw({str(RAW): RAW_SHA256})
    resolver = SizeResolver()
    rows = []
    for printed, sex, n, mass, mass_sd, forearm, forearm_sd in TABLE_2:
        mdd_id, islands, why = TAXA[printed]
        species = resolver.by_id[mdd_id]
        resolver.matched_manual += 1
        for trait, value, sd in (("body_mass", mass, mass_sd), ("forearm_length", forearm, forearm_sd)):
            row = base_row(REFERENCE_ID, species, printed, "manual", "Table 2, p. 81")
            row.update(observation_id=f"jennings2004-{mdd_id}-{sex}", trait=trait, basis="measured",
                       statistic="mean", value=value, sd=sd, n=str(n), sex=sex,
                       area=", ".join(islands), data_year="1996", verbatim_value=f"{value} ± {sd}",
                       notes=why)
            rows.append(row)
    write_rows(REFERENCE_ID, rows)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
