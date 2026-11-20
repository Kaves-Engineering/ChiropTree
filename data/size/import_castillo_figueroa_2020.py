"""Import the forearm lengths of Castillo-Figueroa (2020), Ecological
morphology of Neotropical bat wing structures, Zoological Studies 59: 60.

Table 1 gives, for 97 species, the mean and SD of forearm length (FL) and of
three digit lengths, measured with a digital caliper by one person on 1,512
dry adult voucher specimens in the mammal collection of the Museo Javeriano
de Historia Natural (MPUJ-MAMM), Bogotá, Colombia. The paper does not give
localities; the collection is mainly Colombian. Sexes are pooled. Where n = 1
the table prints a single value with no SD, imported as a 'single' row.
Forearms of dry study skins can run slightly shorter than those of fresh bats.

Values were read from the PDF's text layer by row and checked against the
page images (Table 1, pp. 4-6); the PDF's layout text interleaves the columns,
so each row was confirmed by eye.

Rows not imported (see EXCLUDED): one row is copied from the row above it;
two single specimens disagree with the species' other records in a way
that points to a mix-up with a congener; and two names stand for species
that do not occur in the Neotropics, so the specimens behind them cannot be
assigned to an MDD species.

Names are as printed (the author followed ITIS 2020) and resolved against MDD
v2.5. Pteronotus parnellii is parked by the resolver as a split name.

The PDF is the journal's open copy (https://doi.org/10.6620/ZS.2020.59-60),
downloaded by the project owner. Save it as
data/raw/size/literature/castillo-figueroa-2020.pdf; the importer refuses any
other copy.

Run: uv run data/size/import_castillo_figueroa_2020.py
"""
from size_lib import RAW, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "castillo-figueroa-2020"
PDF = RAW / "literature" / "castillo-figueroa-2020.pdf"
PDF_SHA256 = "0c05905de058a4a6451b776afe564fabd776f25d4786664681565beabc38a76b"
AREA = "MPUJ-MAMM collection, Bogotá (mainly Colombia)"

# (name as printed, page, n, FL mean, FL SD); SD None where n = 1.
TABLE_1 = [
    ("Cormura brevirostris", 4, 1, 44.58, None),
    ("Peropteryx kappleri", 4, 2, 46.72, 0.95),
    ("Rhynchonycteris naso", 4, 1, 36.02, None),
    ("Saccopteryx bilineata", 4, 6, 47.11, 1.67),
    ("Saccopteryx leptura", 4, 12, 37.29, 2.31),
    ("Cynomops planirostris", 4, 4, 32.77, 0.52),
    ("Molossops temminckii", 5, 5, 30.56, 0.95),
    ("Molossus molossus", 5, 14, 38.89, 2.51),
    ("Molossus pretiosus", 5, 1, 43.56, None),
    ("Molossus rufus", 5, 5, 49.88, 0.43),
    ("Tadarida brasiliensis", 5, 1, 42.25, None),
    ("Mormoops megalophylla", 5, 12, 53.37, 1.13),
    ("Pteronotus parnellii", 5, 4, 60.23, 1.47),
    ("Natalus tumidirostris", 5, 9, 39.54, 0.89),
    ("Noctilio albiventris", 5, 6, 59.68, 1.79),
    ("Noctilio leporinus", 5, 2, 84.32, 1.25),
    ("Carollia brevicauda", 5, 72, 39.47, 1.77),
    ("Carollia castanea", 5, 56, 36.31, 1.44),
    ("Carollia perspicillata", 5, 243, 41.90, 1.78),
    ("Rhinophylla fischerae", 5, 3, 31.20, 1.32),
    ("Rhinophylla pumilio", 5, 2, 30.68, 0.19),
    ("Desmodus rotundus", 5, 43, 59.60, 3.00),
    ("Anoura cadenai", 5, 1, 35.23, None),
    ("Anoura geoffroyi", 5, 27, 42.60, 1.91),
    ("Anoura latidens", 5, 3, 42.31, 1.19),
    ("Anoura luismanueli", 5, 11, 35.5, 2.26),
    ("Choeroniscus godmani", 5, 4, 32.10, 1.46),
    ("Glossophaga longirostris", 5, 1, 37.42, None),
    ("Glossophaga soricina", 5, 85, 35.03, 1.15),
    ("Hsunycteris cadenai", 5, 1, 32.33, None),
    ("Hsunycteris thomasi", 5, 1, 35.42, None),
    ("Micronycteris hirsuta", 5, 1, 42.17, None),
    ("Micronycteris megalotis", 5, 4, 34.26, 1.29),
    ("Micronycteris microtis", 5, 2, 34.36, 0.30),
    ("Micronycteris schmidtorum", 5, 2, 34.82, 0.68),
    ("Chrotopterus auritus", 5, 1, 82.23, None),
    ("Gardnerycteris crenulatum", 5, 7, 48.93, None),
    ("Lophostoma brasiliense", 5, 1, 34.53, None),
    ("Lophostoma silvicolum", 5, 13, 52.22, 2.84),
    ("Phylloderma stenops", 5, 1, 76.29, None),
    ("Phyllostomus discolor", 5, 23, 62.23, 2.36),
    ("Phyllostomus elongatus", 5, 1, 60.71, None),
    ("Phyllostomus hastatus", 5, 13, 88.52, 2.14),
    ("Tonatia saurophila", 5, 1, 59.22, None),
    ("Trachops cirrhosus", 5, 6, 60.24, 1.84),
    ("Artibeus anderseni", 5, 7, 38.52, 2.45),
    ("Artibeus bogotensis", 5, 5, 42.09, 1.36),
    ("Artibeus cinereus", 5, 3, 41.71, 1.88),
    ("Artibeus concolor", 6, 1, 47.41, None),
    ("Artibeus glaucus", 6, 56, 41.45, 1.59),
    ("Artibeus gnomus", 6, 1, 38.52, None),
    ("Artibeus jamaicensis", 6, 34, 61.47, 3.73),
    ("Artibeus lituratus", 6, 197, 68.38, 2.92),
    ("Artibeus phaeotis", 6, 44, 37.81, 1.59),
    ("Artibeus planirostris", 6, 58, 60.80, 2.83),
    ("Artibeus rava", 6, 12, 38.76, 1.06),
    ("Chiroderma salvini", 6, 4, 51.11, 2.34),
    ("Mesophylla macconnelli", 6, 2, 31.93, 0.07),
    ("Platyrrhinus angustirostris", 6, 3, 37.27, 1.61),
    ("Platyrrhinus dorsalis", 6, 15, 45.94, 3.26),
    ("Platyrrhinus helleri", 6, 42, 38.66, 2.08),
    ("Platyrrhinus infuscus", 6, 1, 54.14, None),
    ("Platyrrhinus lineatus", 6, 5, 44.16, 1.35),
    ("Platyrrhinus umbratus", 6, 4, 45.75, 0.68),
    ("Platyrrhinus vittatus", 6, 6, 60.97, 1.45),
    ("Sphaeronycteris toxophyllum", 6, 1, 40.95, None),
    ("Sturnira aratathomasi", 6, 3, 57.26, 1.78),
    ("Sturnira bidens", 6, 7, 41.25, 1.11),
    ("Sturnira bogotensis", 6, 27, 43.31, 1.86),
    ("Sturnira erythromos", 6, 25, 40.42, 1.59),
    ("Sturnira lilium", 6, 65, 41.18, 1.45),
    ("Sturnira ludovici", 6, 8, 47.40, 1.98),
    ("Sturnira luisi", 6, 1, 41.21, None),
    ("Sturnira oporaphilum", 6, 9, 43.94, 1.07),
    ("Uroderma bilobatum", 6, 56, 41.38, 1.71),
    ("Uroderma magnirostrum", 6, 16, 42.32, 1.41),
    ("Vampyressa thyone", 6, 5, 31.62, 1.09),
    ("Vampyriscus nymphaea", 6, 3, 37.91, 2.01),
    ("Thyroptera tricolor", 6, 1, 38.74, None),
    ("Thyroptera lavali", 6, 1, 36.17, None),
    ("Eptesicus andinus", 6, 1, 46.49, None),
    ("Eptesicus furinalis", 6, 1, 37.01, None),
    ("Eptesicus brasiliensis", 6, 2, 42.31, 1.78),
    ("Histiotus montanus", 6, 3, 48.80, 1.30),
    ("Lasiurus blossevillii", 6, 3, 38.26, 1.07),
    ("Lasiurus ega", 6, 2, 46.66, 0.19),
    ("Myotis albescens", 6, 2, 35.03, 1.40),
    ("Myotis keaysi", 6, 9, 41.46, 0.77),
    ("Myotis nigricans", 6, 25, 33.92, 2.47),
    ("Myotis oxyotus", 6, 6, 41.03, 0.77),
    ("Myotis riparius", 6, 1, 32.21, None),
    ("Rhogeessa io", 6, 5, 28.64, 1.48),
]

# Rows of Table 1 deliberately left out: (name as printed, page, printed FL, reason)
EXCLUDED = [
    ("Saccopteryx gymnura", 4, "38.44 (n = 1)",
     "One specimen, 38.4 mm: well above the species' other record (34 mm, PanTHERIA) and in the range of "
     "S. leptura (39.2 mm in Velazco et al. 2021), so probably a misidentified S. leptura."),
    ("Rhinophylla alethina", 5, "29.94 (n = 1)",
     "One specimen, 29.9 mm against 35.5 mm in PanTHERIA; the row carries R. pumilio's acronym (Rhpu), so "
     "the specimen or the row is probably mixed up with R. pumilio."),
    ("Enchisthenes hartii", 6, "51.11 ± 1.88 (n = 6)",
     "Its four means (FL, LD3, LD4, LD5) repeat the Chiroderma salvini row above it, with only the SDs and n "
     "changed, so the row was copied; 51 mm is far above the species (39.3 mm in Velazco et al. 2021)."),
    ("Lasiurus seminolus", 6, "36.18 (n = 1)",
     "L. seminolus lives in the south-eastern United States; a Colombian specimen under this name cannot be "
     "assigned to an MDD species."),
    ("Myotis keenii", 6, "34.92 (n = 1)",
     "M. keenii lives in north-western North America; a Neotropical specimen under this name cannot be "
     "assigned to an MDD species."),
]

NOTES = {
    "Gardnerycteris crenulatum": "Printed with n = 7 but no SD.",
    "Chiroderma salvini": "The next row (Enchisthenes hartii) repeats these means and is not imported.",
    "Artibeus lituratus": "The table's LD3 for this row equals its FL (68.38), a copying slip in the digit "
                          "column; the forearm is in line with other sources.",
}


def main() -> None:
    check_raw({str(PDF): PDF_SHA256})
    resolver = SizeResolver()
    rows = []
    for printed, page, n, mean, sd in TABLE_1:
        species, method = resolver.resolve(printed)
        if not species:
            continue
        single = n == 1
        row = base_row(REFERENCE_ID, species, printed, method, f"Table 1, p. {page}, FL")
        row.update(observation_id=f"{REFERENCE_ID}-{species['id']}", trait="forearm_length", basis="measured",
                   statistic="single" if single else "mean", value=number(mean),
                   sd="" if sd is None else number(sd), n=str(n), sex="pooled", area=AREA, data_year="2020",
                   verbatim_value=f"{mean}" if sd is None else f"{mean} ± {sd}",
                   notes=NOTES.get(printed, ""))
        rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)
    print(f"  {len(EXCLUDED)} rows left out on purpose: {', '.join(e[0] for e in EXCLUDED)}")


if __name__ == "__main__":
    main()
