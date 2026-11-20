"""Import the forearm lengths measured in Mammalian Diversity and Matses
Ethnomammalogy in Amazonian Peru, Part 4: Bats (Velazco, Voss, Fleck &
Simmons 2021, Bulletin of the American Museum of Natural History 451).

The monograph inventories the bats of the Yavarí-Ucayali interfluve (Loreto,
NE Peru). For most species it prints a table of external and craniodental
measurements of its own voucher specimens, by sex: "F" is forearm length,
"distance from the elbow (tip of the olecranon process) to the distal end of
the wrist (including the carpals) when the wing is partially or fully folded"
(p. 10). Each cell is one of:

- "46.3 (45.0-49.0) 7": mean, observed range and sample size -> a mean row;
- "36.7, 37.0": every specimen when there are two or three -> a mean row whose
  range is the smallest and largest of them;
- a column headed by one catalogue number ("MUSA 15288 ♂") -> a single row.

Every value below was transcribed by hand from the 49 measurement tables
(tables 1-64; the others are roost, name-elicitation and fauna tables),
read from page images because the PDF's text layer scrambles the columns.
Sexes are kept apart as printed.

Names are the monograph's own and resolved against MDD v2.5 like every other
source; hand-checked mappings are listed in MANUAL with their reason.

The PDF is BioOne's copy, downloaded by the project owner (BioOne's terms
limit use to personal, educational, non-commercial purposes). Only the
factual measurements are recorded here. Save it as
data/raw/size/literature/velazco-2021-matses-bats.pdf; the importer refuses
any other copy.

Run: uv run data/size/import_velazco_2021_matses.py
"""
import re

from size_lib import RAW, SizeResolver, base_row, check_raw, number, report, write_review, write_rows

REFERENCE_ID = "velazco-2021-matses"
PDF = RAW / "literature" / "velazco-2021-matses-bats.pdf"
PDF_SHA256 = "8470f277bd3f64259e52f3ca6b2c56b495cd0a95d2bbf2cf76d83c327bc8d651"
AREA = "Yavarí-Ucayali interfluve, Loreto, Peru"

# Names as printed that need a hand-checked MDD species, with the reason.
MANUAL: dict[str, tuple[str, str]] = {}

# (table, page, name as printed, sex, column heading, F cell as printed, note)
# Sex: male/female from the column heading; a catalogue-number column carries
# the specimen's sex symbol.
F = [
    (1, 12, "Cormura brevirostris", "male", "Males", "46.3 (45.0–49.0) 7", ""),
    (1, 12, "Cormura brevirostris", "female", "Females", "47.3 (44.0–49.0) 15", ""),
    (1, 12, "Cyttarops alecto", "male", "MUSA 15288", "44.4", ""),
    (1, 12, "Diclidurus isabella", "female", "MUSM 37068", "58.8", ""),
    (3, 16, "Peropteryx kappleri", "male", "Males", "49.6 (48.0–50.5) 4", ""),
    (3, 16, "Peropteryx kappleri", "female", "Females", "51.8 (47.0–54.0) 5", ""),
    (5, 19, "Peropteryx leucoptera", "male", "Males", "45.3 (45.0–46.0) 3", ""),
    (5, 19, "Peropteryx pallidoptera", "male", "Males", "42.0 (39.0–46.0) 3", ""),
    (5, 19, "Peropteryx pallidoptera", "female", "Females", "41.9 (41.0–43.0) 12", ""),
    (7, 21, "Rhynchonycteris naso", "male", "Males", "36.2 (34.0–37.5) 14", ""),
    (7, 21, "Rhynchonycteris naso", "female", "Females", "38.4 (34.7–40.8) 6", ""),
    (8, 25, "Saccopteryx bilineata", "male", "Males", "47.5 (46.0–50.0) 13", ""),
    (8, 25, "Saccopteryx bilineata", "female", "Females", "49.6 (47.0–55.0) 12", ""),
    (8, 25, "Saccopteryx canescens", "pooled", "S. canescens", "36.0 (34.5–37.1) 4", "Sexes not separated."),
    (10, 27, "Saccopteryx leptura", "male", "Males", "38.6 (38.0–40.0) 7", ""),
    (10, 27, "Saccopteryx leptura", "female", "Females", "39.8 (38.0–42.0) 15", ""),
    (12, 29, "Noctilio albiventris", "male", "Males", "70.0 (68.0–71.0) 6", ""),
    (12, 29, "Noctilio albiventris", "female", "FMNH 89013, MUSM 15241, MUSM 15243", "68.0, 68.0, 70.0", "Three females, each printed in its own column."),
    (14, 31, "Noctilio leporinus", "male", "Males", "84.2 (80.0–87.1) 6", ""),
    (14, 31, "Noctilio leporinus", "female", "Females", "83.8 (76.0–87.0) 9", ""),
    (15, 33, "Carollia benkeithi", "male", "Males", "35.0 (34.0–36.0) 12", ""),
    (15, 33, "Carollia benkeithi", "female", "Females", "34.7 (34.0–35.0) 7", ""),
    (16, 35, "Carollia brevicauda", "male", "Males", "37.8 (36.0–39.0) 13", ""),
    (16, 35, "Carollia brevicauda", "female", "Females", "37.5 (36.0–39.0) 14", ""),
    (18, 37, "Carollia perspicillata", "male", "Males", "41.5 (39.0–44.0) 31", ""),
    (18, 37, "Carollia perspicillata", "female", "Females", "42.0 (40.0–44.6) 30", ""),
    (20, 40, "Desmodus rotundus", "male", "AMNH 278473, MUSM 21145", "58.0, 60.0", "Two males, each printed in its own column."),
    (20, 40, "Desmodus rotundus", "female", "Females", "62.7 (60.0–66.0) 6", ""),
    (21, 43, "Anoura caudifer", "female", "Females", "36.7, 37.0", ""),
    (21, 43, "Choeroniscus minor", "male", "Males", "35.0, –", "Two males; the forearm of one is not printed."),
    (21, 43, "Choeroniscus minor", "female", "Females", "34.7 (34–35) 6", ""),
    (22, 45, "Glossophaga bakeri", "male", "Males", "35.0 (34.3–36.0) 5", ""),
    (22, 45, "Glossophaga bakeri", "female", "Females", "37.4, 35.8", ""),
    (22, 45, "Glossophaga soricina", "male", "Males", "34.4 (34.0–35.5) 14", ""),
    (22, 45, "Glossophaga soricina", "female", "Females", "35.5 (34.0–37.6) 13", ""),
    (23, 49, "Glyphonycteris daviesi", "male", "AMNH 273180", "56.0", ""),
    (23, 49, "Glyphonycteris daviesi", "female", "Females", "55.0 (50.0–58.0) 3", ""),
    (23, 49, "Glyphonycteris sylvestris", "male", "MUSM 15202", "39.0", ""),
    (23, 49, "Trinycteris nicefori", "male", "Males", "38.0 (36.7–39.0) 8", ""),
    (23, 49, "Trinycteris nicefori", "female", "MUSM 13213", "41", ""),
    (24, 53, "Hsunycteris dashe", "female", "Females", "36.0, 35.0", "The type series is from this region."),
    (24, 53, "Hsunycteris pattoni", "male", "Males", "32.1 (31.0–34.0) 15", ""),
    (24, 53, "Hsunycteris pattoni", "female", "Females", "32.7 (31.0–34.0) 11", ""),
    (24, 53, "Hsunycteris thomasi", "male", "Males", "31.0 (30.4–32.0) 4", ""),
    (24, 53, "Hsunycteris thomasi", "female", "Females", "32.0, 33.0", ""),
    (26, 56, "Lampronycteris brachyotis", "male", "Males", "39.8 (37.0–42.0) 5", ""),
    (26, 56, "Lampronycteris brachyotis", "female", "MUSM 15203", "44.0", ""),
    (27, 58, "Micronycteris brosseti", "male", "Males", "31.9 (31.6–32.0) 3", ""),
    (27, 58, "Micronycteris brosseti", "female", "FMNH 89100", "32.8", ""),
    (27, 58, "Micronycteris matses", "male", "Males", "38.0 (38.0–38.0) 3", ""),
    (27, 58, "Micronycteris matses", "female", "Females", "38.8 (38.0–40.0) 5", ""),
    (28, 61, "Micronycteris megalotis", "male", "Males", "33.9 (33.0–35.0) 5", ""),
    (28, 61, "Micronycteris megalotis", "female", "Females", "36.0, 34.5", ""),
    (28, 61, "Micronycteris microtis", "male", "Males", "34.6 (33.0–36.0) 15", ""),
    (28, 61, "Micronycteris microtis", "female", "Females", "35.5 (34.0–37.0) 11", ""),
    (30, 64, "Micronycteris minuta", "male", "Males", "35.0, 35.9", ""),
    (30, 64, "Micronycteris minuta", "female", "Females", "36.0 (36.0–36.0) 3", ""),
    (30, 64, "Micronycteris hirsuta", "male", "AMNH 273153", "46.0", ""),
    (30, 64, "Micronycteris hirsuta", "female", "Females", "45.0 (44.0–46.0) 4", ""),
    (31, 68, "Chrotopterus auritus", "male", "Males", "80.0 (78.0–81.0) 3", ""),
    (31, 68, "Gardnerycteris crenulata", "male", "Males", "48.0 (45.3–50.0) 10", ""),
    (31, 68, "Gardnerycteris crenulata", "female", "Females", "48.5 (43.0–51.0) 11", ""),
    (32, 72, "Lophostoma brasiliense", "male", "Males", "35.1 (34.0–37.0) 7", ""),
    (32, 72, "Lophostoma brasiliense", "female", "Females", "34.9 (34.0–35.8) 6", ""),
    (32, 72, "Lophostoma carrikeri", "male", "Males", "46.2, 45.6", ""),
    (32, 72, "Lophostoma silvicolum", "male", "Males", "55.9 (55.0–56.2) 6", ""),
    (32, 72, "Lophostoma silvicolum", "female", "Females", "54.4 (50.6–59.0) 16", ""),
    (33, 76, "Macrophyllum macrophyllum", "male", "Males", "37.0, 35.0", ""),
    (33, 76, "Phylloderma stenops", "male", "Males", "73.4 (72.0–75.0) 3", ""),
    (33, 76, "Phyllostomus discolor", "male", "Males", "62.5, 61.3", ""),
    (33, 76, "Phyllostomus discolor", "female", "Females", "61.9 (59.4–64.2) 4", ""),
    (34, 80, "Phyllostomus elongatus", "male", "Males", "65.6 (63.0–69.0) 11", ""),
    (34, 80, "Phyllostomus elongatus", "female", "Females", "65.4 (64.0–68.0) 12", ""),
    (34, 80, "Phyllostomus hastatus", "male", "Males", "86.0 (81.0–90.0) 12", ""),
    (34, 80, "Phyllostomus hastatus", "female", "Females", "84.6 (83.0–86.0) 7", ""),
    (36, 82, "Tonatia maresi", "male", "Males", "55.0, 58.0", ""),
    (36, 82, "Tonatia maresi", "female", "Females", "57.4 (56.0–59.0) 6", ""),
    (36, 82, "Trachops cirrhosus", "male", "Males", "58.9 (55.0–62.0) 11", ""),
    (36, 82, "Trachops cirrhosus", "female", "Females", "63.3 (61.0–66.0) 7", ""),
    (37, 88, "Rhinophylla fischerae", "male", "Males", "31.0 (30.0–32.0) 4", ""),
    (37, 88, "Rhinophylla fischerae", "female", "Females", "31.3 (31.0–32.0) 6", ""),
    (37, 88, "Rhinophylla pumilio", "male", "Males", "33.7 (32.4–35.0) 13", ""),
    (37, 88, "Rhinophylla pumilio", "female", "Females", "34.8 (33.0–36.0) 15", ""),
    (38, 93, "Artibeus concolor", "male", "Males", "47.7 (46.3–50.4) 4", ""),
    (38, 93, "Artibeus concolor", "female", "Females", "52.0, 49.0", ""),
    (38, 93, "Artibeus lituratus", "male", "Males", "70.5 (67.5–73.0) 6", ""),
    (38, 93, "Artibeus lituratus", "female", "Females", "71.8 (67.0–75.0) 6", ""),
    (39, 94, "Artibeus obscurus", "male", "Males", "60.1 (57.0–64.0) 13", ""),
    (39, 94, "Artibeus obscurus", "female", "Females", "60.2 (58.0–63.0) 6", ""),
    (39, 94, "Artibeus planirostris", "male", "Males", "67.3 (62.0–71.0) 8", ""),
    (39, 94, "Artibeus planirostris", "female", "Females", "68.3 (65.9–70.3) 7", ""),
    (40, 98, "Artibeus anderseni", "male", "Males", "35.2 (33.0–37.0) 31", ""),
    (40, 98, "Artibeus anderseni", "female", "Females", "35.7 (34.0–37.0) 12", ""),
    (40, 98, "Artibeus bogotensis", "female", "MUSM 1320", "37.0", ""),
    (40, 98, "Artibeus cinereus", "male", "Males", "36.0 (34.2–39.0) 9", ""),
    (40, 98, "Artibeus cinereus", "female", "Females", "36.3 (35.5–38.4) 8", ""),
    (42, 100, "Artibeus glaucus", "male", "Males", "39.0, 39.0", ""),
    (42, 100, "Artibeus glaucus", "female", "Females", "39.2 (38.0–40.5) 3", ""),
    (42, 100, "Artibeus gnomus", "male", "Males", "38.6 (37.0–41.0) 9", ""),
    (42, 100, "Artibeus gnomus", "female", "Females", "37.7 (36.0–40.0) 8", ""),
    (43, 104, "Chiroderma trinitatum", "male", "Males", "39.5 (38.0–40.7) 6", ""),
    (43, 104, "Chiroderma trinitatum", "female", "Females", "41.1 (41.0–41.2) 3", ""),
    (43, 104, "Chiroderma villosum", "male", "Males", "45.9 (44.8–47.0) 4", ""),
    (43, 104, "Chiroderma villosum", "female", "Females", "47.6 (46.0–50.0) 4", ""),
    (44, 106, "Enchisthenes hartii", "male", "MUSM 6966", "39.3", ""),
    (44, 106, "Mesophylla macconnelli", "male", "Males", "30.3 (28.0–32.0) 20", ""),
    (44, 106, "Mesophylla macconnelli", "female", "Females", "31.5 (30.0–33.0) 20", ""),
    (46, 110, "Platyrrhinus angustirostris", "male", "Males", "39.0, 39.5", ""),
    (46, 110, "Platyrrhinus brachycephalus", "male", "Males", "38.0 (37.2–39.0) 6", ""),
    (46, 110, "Platyrrhinus brachycephalus", "female", "Females", "37.0, 37.3", ""),
    (46, 110, "Platyrrhinus fusciventris", "female", "Females", "37.0 (36.1–37.9) 3", ""),
    (47, 111, "Platyrrhinus incarum", "male", "MUSM 13241", "35.0", ""),
    (47, 111, "Platyrrhinus incarum", "female", "Females", "37.1 (36.0–39.0) 5", ""),
    (47, 111, "Platyrrhinus infuscus", "male", "MUSM 15289", "56.0", ""),
    (47, 111, "Platyrrhinus infuscus", "female", "Females", "57.2 (56.0–59.0) 6", ""),
    (47, 111, "Sphaeronycteris toxophyllum", "male", "MUSM 32955", "39.0", ""),
    (48, 113, "Sturnira giannae", "male", "Males", "44.3 (44.0–45.0) 3", ""),
    (48, 113, "Sturnira giannae", "female", "Females", "44.8 (44.6–45.0) 3", ""),
    (49, 114, "Sturnira magna", "male", "Males", "58.0 (57.0–59.0) 3", ""),
    (49, 114, "Sturnira magna", "female", "Females", "58.6 (57.0–61.0) 5", ""),
    (49, 114, "Sturnira tildae", "male", "MUSM 5923", "47.8", ""),
    (49, 114, "Sturnira tildae", "female", "Females", "49.0 (47.1–50.0) 3", ""),
    (50, 117, "Uroderma bilobatum", "male", "Males", "42.2 (40.0–43.4) 11", ""),
    (50, 117, "Uroderma bilobatum", "female", "Females", "42.1 (37.0–45.0) 13", ""),
    (50, 117, "Uroderma magnirostrum", "male", "MUSM 4362", "41.5", ""),
    (50, 117, "Uroderma magnirostrum", "female", "Females", "43.6, 44.8", ""),
    (51, 120, "Vampyressa thyone", "male", "Males", "30.4 (29.0–32.0) 9", ""),
    (51, 120, "Vampyressa thyone", "female", "Females", "30.6 (29.5–32.0) 17", ""),
    (51, 120, "Vampyrodes caraccioli", "male", "MUSA 15124", "52.4", ""),
    (52, 122, "Vampyriscus bidens", "male", "Males", "35.0, 35.5", ""),
    (52, 122, "Vampyriscus bidens", "female", "FMNH 87075", "35.5", ""),
    (52, 122, "Vampyriscus brocki", "male", "Males", "32.3 (31.0–33.0) 3", ""),
    (52, 122, "Vampyriscus brocki", "female", "Females", "32.7 (31.7–34.5) 12", ""),
    (53, 124, "Furipterus horrens", "male", "Males", "35.2 (33.0–38.0) 9", ""),
    (53, 124, "Furipterus horrens", "female", "Females", "38.0, 37.0", ""),
    (55, 127, "Thyroptera discifera", "male", "MUSM 5546", "33.4", ""),
    (55, 127, "Thyroptera wynneae", "male", "AMNH 278486", "33.0", ""),
    (56, 129, "Thyroptera lavali", "male", "FMNH 89118, MUSM 5944", "39.0, 39.0", "Two males, each printed in its own column."),
    (56, 129, "Thyroptera lavali", "female", "FMNH 89119, 89120, 89121", "41.0, 40.0, 40.0", "Three females, each printed in its own column."),
    (57, 130, "Thyroptera tricolor", "male", "Males", "37.1 (35.4–40.0) 9", ""),
    (57, 130, "Thyroptera tricolor", "female", "Females", "36.8 (35.0–38.0) 9", ""),
    (59, 132, "Eptesicus brasiliensis", "male", "MUSM 13201", "43.0", ""),
    (59, 132, "Eptesicus brasiliensis", "female", "Females", "44.6, 44.4, 43.0", ""),
    (59, 132, "Eptesicus furinalis", "male", "ROM 122089", "41.0", ""),
    (59, 132, "Eptesicus furinalis", "female", "ROM 122178", "41.0", ""),
    (60, 137, "Myotis albescens", "male", "Males", "(33.0) 3", "Printed as '(33.0) 3' with no mean; read as three males that all measured 33.0 mm."),
    (60, 137, "Myotis albescens", "female", "Females", "35.0", "One female."),
    (60, 137, "Myotis nigricans", "male", "Males", "34.1, 34.3", ""),
    (60, 137, "Myotis nigricans", "female", "Females", "34.3, 35.1", ""),
    (61, 139, "Myotis riparius", "male", "Males", "36.3 (33.0–38.0) 9", ""),
    (61, 139, "Myotis riparius", "female", "Females", "36.3 (35.0–37.0) 9", ""),
    (62, 142, "Cynomops planirostris", "male", "AMNH 278460", "33.0", ""),
    (62, 142, "Eumops hansae", "male", "Males", "37.6, 38.8", ""),
    (62, 142, "Eumops hansae", "female", "MUSA 15144", "37.2", ""),
    (62, 142, "Molossops neglectus", "male", "Males", "39.0, 38.2", ""),
    (62, 142, "Molossops neglectus", "female", "MUSM 6972", "37.3", ""),
    (63, 145, "Molossus coibensis", "male", "ROM 122130", "38.0", ""),
    (63, 145, "Molossus coibensis", "female", "Females", "36.0 (35.0–37.0) 5", ""),
    (63, 145, "Molossus molossus", "male", "Males", "41.4 (40.0–42.2) 10", ""),
    (63, 145, "Molossus molossus", "female", "Females", "41.2 (40.0–43.0) 11", ""),
    (64, 148, "Molossus rufus", "male", "Males", "53.6 (51.0–55.0) 7", ""),
    (64, 148, "Molossus rufus", "female", "Females", "52.5 (51.0–54.0) 4", ""),
    (64, 148, "Promops centralis", "male", "MUSM 6974", "51.7", ""),
    (64, 148, "Promops centralis", "female", "MUSM 5604", "49.6", ""),
]

SUMMARY = re.compile(r"^(?P<mean>[\d.]+) \((?P<low>[\d.]+)–(?P<high>[\d.]+)\) (?P<n>\d+)$")


def parse(cell: str) -> dict:
    """One printed F cell as size-row fields."""
    match = SUMMARY.match(cell)
    if match:
        return {"statistic": "mean", "value": number(match["mean"]), "value_min": number(match["low"]),
                "value_max": number(match["high"]), "range_type": "min_max", "n": match["n"]}
    if cell == "(33.0) 3":
        return {"statistic": "mean", "value": "33", "n": "3"}
    values = [float(v) for v in cell.split(", ") if v != "–"]
    if len(values) == 1:
        return {"statistic": "single", "value": number(values[0]), "n": "1"}
    return {"statistic": "mean", "value": number(sum(values) / len(values)),
            "value_min": number(min(values)), "value_max": number(max(values)),
            "range_type": "min_max", "n": str(len(values))}


def main() -> None:
    check_raw({str(PDF): PDF_SHA256})
    resolver = SizeResolver()
    resolver.add_manual({name: mdd_id for name, (mdd_id, _) in MANUAL.items()})
    rows = []
    seen: dict[str, int] = {}
    for table, page, printed, sex, column, cell, note in F:
        species, method = resolver.resolve(printed)
        if not species:
            continue
        seen[species["id"]] = seen.get(species["id"], 0) + 1
        reason = MANUAL.get(printed, ("", ""))[1]
        row = base_row(REFERENCE_ID, species, printed, method, f"Table {table}, p. {page}, F, {column}")
        row.update(parse(cell))
        row.update(observation_id=f"{REFERENCE_ID}-{species['id']}-{seen[species['id']]}",
                   trait="forearm_length", basis="measured", sex=sex, area=AREA, data_year="2021",
                   verbatim_value=cell, notes=" ".join(t for t in (note, reason) if t))
        rows.append(row)
    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, rows, resolver)


if __name__ == "__main__":
    main()
