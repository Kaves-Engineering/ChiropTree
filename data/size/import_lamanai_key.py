"""Import the forearm ranges of A Field Key to Bats of Lamanai, Belize, V.6
(Clare & Simmons 2026).

The key prints one forearm range ("F.A.=61-69") per species caught or
expected at Lamanai, Belize, measured "from top of wrist to end of elbow with
wing folded" (p. 1). They are identification ranges for live bats at the net,
not means, so every row is statistic 'range_only' with range_type 'field_key'.
The value column holds the range's midpoint, only so the card has a place to
put its marker. build_size.py never lets a range-only row into a median
alongside real means, and when a species has nothing else the card shows the
range, not the midpoint.

Names are the key's own (it already uses current Central American names, see
its "Prior Taxonomy" page 22), resolved against MDD like every other source.
Where the key qualifies an entry, the qualification is kept as a note.
Carollia tibia lengths (p. 6) are not imported; only forearm is.

The PDF was supplied directly by the project owner, who vouches for it; it is
not openly published, so only the factual ranges are recorded here,
transcribed by hand from the page images. To pin it, save it as
data/raw/size/lamanai/Lamanai Bat Field Key 6.0.pdf and put its SHA-256 in
PDF_SHA256; the importer then refuses any other copy.

Run: uv run data/size/import_lamanai_key.py
"""
from size_lib import RAW, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "lamanai-key-2026"
PDF = RAW / "lamanai" / "Lamanai Bat Field Key 6.0.pdf"
PDF_SHA256 = "c2dda06a24b92c5039fcbb705bff4588aa3780c0102c1591c8fdd089ba2e41e9"

# (name as printed, page, low, high, note). low == high is a single printed value.
FOREARM = [
    ("Desmodus rotundus", 2, 53, 65, ""),
    ("Artibeus jamaicensis", 3, 55, 67, ""),
    ("Artibeus intermedius", 3, 61, 69, "The key notes that forearm separates A. intermedius from A. lituratus most of the time, but some individuals fall in the zone of overlap."),
    ("Artibeus lituratus", 3, 68, 78, ""),
    ("Dermanura phaeotis", 4, 35, 40, ""),
    ("Dermanura watsoni", 4, 35, 41, "The key says all Dermanura caught at Lamanai so far appear to be D. phaeotis."),
    ("Vampyressa thyone", 4, 29, 34, ""),
    ("Uroderma convexum", 5, 40, 44, ""),
    ("Platyrrhinus helleri", 5, 37, 41, ""),
    ("Carollia perspicillata", 6, 41, 45, ""),
    ("Carollia sowelli", 6, 37, 42, ""),
    ("Lampronycteris brachyotis", 7, 40, 42, ""),
    ("Sturnira parvidens", 7, 37, 42, ""),
    ("Glossophaga mutica", 9, 33, 38, ""),
    ("Glossophaga commissarisi", 9, 32, 35, ""),
    ("Chrotopterus auritus", 10, 77, 83, ""),
    ("Vampyrum spectrum", 10, 101, 110, ""),
    ("Gardnernycteris keenani", 11, 46, 55, ""),
    ("Phyllostomus discolor", 11, 60, 68, ""),
    ("Mimon cozumelae", 12, 53, 61, ""),
    ("Trachops coffini", 12, 57, 65, ""),
    ("Lophostoma evote", 13, 47, 54, ""),
    ("Lophostoma nicaraguae", 13, 32, 36, ""),
    ("Micronycteris schmidtorum", 13, 34, 38, ""),
    ("Micronycteris microtis", 13, 32, 37, ""),
    ("Mormoops megalophylla", 14, 51, 57, ""),
    ("Pteronotus mesoamericanus", 14, 55, 63, ""),
    ("Pteronotus psilotis", 14, 42, 49, ""),
    ("Pteronotus gymnonotus", 14, 49, 56, ""),
    ("Pteronotus fulvus", 14, 42, 49, ""),
    ("Myotis elegans", 15, 32, 34, ""),
    ("Myotis pilosatibialis", 15, 32, 39, ""),
    ("Rhogeessa aenea", 15, 26, 31, "The key notes there may be two Rhogeessa species at Lamanai."),
    ("Neoeptesicus furinalis", 17, 37, 41, ""),
    ("Bauerus dubiaquercus", 17, 49, 56, ""),
    ("Lasiurus ega", 17, 43, 47, ""),
    ("Lasiurus frantzi", 17, 40, 40, "The key prints a single value, F.A.=40."),
    ("Saccopteryx bilineata", 18, 44, 48, ""),
    ("Rhynchonycteris naso", 18, 36, 40, ""),
    ("Molossus nigricans", 19, 47, 54, ""),
    ("Molossus alvarezi", 19, 45, 52, ""),
    ("Eumops auripendulus", 19, 57, 63, ""),
    ("Eumops nanus", 19, 37, 49, ""),
    ("Peropteryx kappleri", 20, 45, 52, ""),
    ("Diclidurus albus", 20, 63, 69, ""),
    ("Centurio senex", 20, 41, 45, ""),
    ("Chiroderma villosum", 20, 41, 51, ""),
    ("Natalus mexicanus", 21, 36, 39, ""),
    ("Noctilio leporinus", 21, 82, 89, ""),
]


def main() -> None:
    if PDF_SHA256:
        check_raw({str(PDF): PDF_SHA256})
    resolver = SizeResolver()
    # two spellings, each checked against MDD v2.5 and its range for Belize:
    resolver.add_manual({
        # MDD spells the genus Gardnerycteris; G. keenani is the Central
        # American species split from G. crenulata, recorded in Belize
        "Gardnernycteris keenani": "1004970",
        # MDD spells the epithet frantzii; split from L. blossevillii, recorded in Belize
        "Lasiurus frantzi": "1005582",
    })
    rows = []
    for printed, page, low, high, note in FOREARM:
        species, method = resolver.resolve(printed)
        if not species:
            continue
        single = low == high
        row = base_row(REFERENCE_ID, species, printed, method, f"p. {page}")
        row.update(observation_id=f"lamanai-{species['id']}", trait="forearm_length", basis="measured",
                   statistic="single" if single else "range_only",
                   value=number((low + high) / 2),
                   value_min="" if single else number(low), value_max="" if single else number(high),
                   range_type="" if single else "field_key", sex="pooled", area="Lamanai, Belize",
                   data_year="2026", verbatim_value=f"F.A.={low}" if single else f"F.A.={low}-{high}",
                   notes=note)
        rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
