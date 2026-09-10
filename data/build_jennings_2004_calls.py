"""Import Table 1 of Jennings et al. (2004), echolocation calls of West Indian bats.

Table 1 gives, for each taxon, the harmonic carrying most energy and five
variables measured on that harmonic.  Several taxa are listed twice or three
times because a different harmonic was dominant in different individuals, so
the harmonic is carried per measurement rather than per taxon.

The paper uses 2004 trinomials.  Four of its subspecies are accepted species in
MDD today, so each trinomial identifies exactly one current species -- the
authors identified to subspecies precisely because Artibeus jamaicensis
subspecies differ in size and hence in call frequency.

Run: ``uv run data/build_jennings_2004_calls.py``.
"""
import hashlib
import re
from pathlib import Path

from call_import_lib import TaxonResolver, report, write_review, write_rows

REFERENCE_ID = "jennings-2004"
METHOD_ID = "jennings-2004-release"
RAW = Path(__file__).parent / "raw" / "jennings-2004.pdf"
RAW_SHA256 = "8dab510db818880abdad4b69d33c65c4342b813f7adeb8e1d3c5302e8ceeab45"

ISO = {"Puerto Rico": "PR", "Dominica": "DM", "St. Vincent": "VC"}

# printed name -> (MDD id, islands, why the name needed a decision)
TAXA = {
    "M. blainvillii": ("1004850", ["Puerto Rico"],
                       "MDD spells the epithet blainvillei; an orthographic variant, not a different taxon"),
    "P. davyi davyi": ("1004853", ["Dominica"], ""),
    "P. parnellii portoricensis": ("1004863", ["Puerto Rico"],
                                   "P. parnellii portoricensis is now the full species Pteronotus portoricensis"),
    "P. quadridens fuliginosus": ("1004866", ["Puerto Rico"], ""),
    "B. cavernarum intermedia": ("1004883", ["Puerto Rico"], ""),
    "E. bombifrons bombifrons": ("1004885", ["Puerto Rico"], ""),
    "G. longirostris rostrata": ("1004911", ["St. Vincent"], ""),
    "M. plethodon luciae": ("1004917", ["Dominica", "St. Vincent"], ""),
    "A. jamaicensis jamaicensis": ("1005011", ["Puerto Rico", "Dominica"], ""),
    "A. jamaicensis schwartzi": ("1005018", ["St. Vincent"],
                                 "A. jamaicensis schwartzi is now the full species Artibeus schwartzi"),
    "S. rufum darioi": ("1005054", ["Puerto Rico"], ""),
    "S. lilium angeli": ("1005071", ["Dominica"],
                         "S. lilium angeli is now the full species Sturnira angeli"),
    "S. lilium paulsoni": ("1005090", ["St. Vincent"],
                           "S. lilium paulsoni is now the full species Sturnira paulsoni"),
    "N. stramineus stramineus": ("1005279", ["Dominica"], ""),
}

PARAMETERS = ["duration", "inter_pulse_interval", "peak_frequency",
              "start_frequency", "end_frequency"]
UNITS = {"duration": "ms", "inter_pulse_interval": "ms", "peak_frequency": "kHz",
         "start_frequency": "kHz", "end_frequency": "kHz"}
HARMONIC_NUMBER = {"f": "1", "h2": "2", "h3": "3", "h4": "4"}

# Transcribed verbatim from Table 1 (pp. 79-80). Each entry is
# (taxon, maximum number of harmonics, [(dominant harmonic, n bats, five printed cells)]),
# the cells in the column order of PARAMETERS.
TABLE_1 = [
    ("M. blainvillii", 4, [
        ("f", 2, ["3.2, 3.5", "24, 78", "27.2, 27.9", "35.0, 32.0", "10.0, 17.0"]),
        ("h2", 2, ["3.8, 2.0", "26.1, 27", "54.0, 54.5", "61.0, 76.0", "39.0, 40.0"]),
    ]),
    ("P. davyi davyi", 5, [
        ("f", 1, ["2.8", "15", "34.1", "38.0", "22.0"]),
        ("h2", 5, ["4.6 ± 1.5 (2.7–6.1)", "41 ± 31 (13–85)",
                   "67.0 ± 2.2 (64.7–70.0)", "70.3 ± 1.3 (69.0–72.0)",
                   "51.0 ± 4.4 (46.0–56.0)"]),
    ]),
    ("P. parnellii portoricensis", 4, [
        ("f", 1, ["14.5", "38", "31.2", "28.0", "23.0"]),
        ("h2", 9, ["22.0 ± 5.7 (15.2–32.0)", "56 ± 20 (30–99)",
                   "61.3 ± 0.8 (60.0–62.3)", "56.2 ± 3.9 (52.0–63.0)",
                   "46.8 ± 1.6 (44.0–49.0)"]),
    ]),
    ("P. quadridens fuliginosus", 3, [
        ("f", 4, ["4.8 ± 1.3 (3.6–6.2)", "109 ± 79 (34–178)",
                  "40.4 ± 0.5 (39.9–40.8)", "42.5 ± 1.3 (41.0–44.0)",
                  "30.3 ± 2.2 (28.0–33.0)"]),
        ("h2", 3, ["5.0 ± 0.6 (4.5–5.7)", "82 ± 21 (61–103)",
                   "70.7 ± 7.1 (64.8–78.6)", "82.0 ± 2.0 (80.0–84.0)",
                   "58.7 ± 2.9 (57.0–62.0)"]),
    ]),
    ("B. cavernarum intermedia", 4, [
        ("f", 2, ["4.8, 4.7", "223, 230", "33.4, 31.7", "40.0, 39.0", "17.0, 18.0"]),
        ("h2", 4, ["2.6 ± 0.5 (2.2–3.2)", "76 ± 28 (46–108)",
                   "51.4 ± 2.8 (47.9–54.8)", "66.8 ± 3.6 (64.0–72.0)",
                   "38.0 ± 2.3 (36.0–40.0)"]),
    ]),
    ("E. bombifrons bombifrons", 3, [
        ("f", 5, ["4.7 ± 1.0 (3.3–5.8)", "107 ± 51 (67–197)",
                  "37.9 ± 4.3 (31.5–42.7)", "54.2 ± 4.1 (50.0–59.0)",
                  "26.8 ± 1.9 (25.0–30.0)"]),
    ]),
    ("G. longirostris rostrata", 4, [
        ("h3", 8, ["1.6 ± 0.4 (1.2–2.3)", "48 ± 22 (22–85)",
                   "90.8 ± 9.8 (81.4–110.8)", "119.4 ± 20.2 (97.0–148.0)",
                   "72.5 ± 7.0 (64.0–82.0)"]),
    ]),
    ("M. plethodon luciae", 3, [
        ("f", 15, ["2.1 ± 1.0 (1.0–4.6)", "70 ± 45 (18–164)",
                   "42.1 ± 6.6 (32.2–52.4)", "61.5 ± 5.1 (55.0–72.0)",
                   "27.6 ± 4.2 (22.0–39.0)"]),
        ("h2", 10, ["1.3 ± 0.3 (0.9–1.6)", "51 ± 27 (17–95)",
                    "85.6 ± 7.0 (78.0–99.0)", "114.9 ± 10.7 (97.0–128.0)",
                    "58.5 ± 7.2 (44.0–68.0)"]),
    ]),
    ("A. jamaicensis jamaicensis", 5, [
        ("h2", 14, ["2.6 ± 0.8 (1.0–3.5)", "73 ± 31 (33–133)",
                    "54.7 ± 3.6 (47.3–58.2)", "72.5 ± 4.7 (64.0–83.0)",
                    "40.0 ± 2.6 (36.0–45.0)"]),
        ("h3", 6, ["1.8 ± 0.6 (1.1–2.6)", "78 ± 81 (23–237)",
                   "72.2 ± 3.6 (68.2–77.6)", "94.7 ± 6.4 (88.0–106.0)",
                   "56.7 ± 3.4 (51.0–60.0)"]),
    ]),
    ("A. jamaicensis schwartzi", 5, [
        ("h2", 3, ["2.7 ± 1.0 (1.7–3.7)", "97 ± 22 (73–116)",
                   "53.2 ± 7.0 (48.9–61.3)", "74.0 ± 3.6 (71.0–78.0)",
                   "36.7 ± 4.9 (31.0–40.0)"]),
        ("h3", 7, ["2.9 ± 0.7 (1.6–3.9)", "60 ± 57 (23–177)",
                   "65.7 ± 4.3 (59.3–73.4)", "90.3 ± 8.5 (82.0–106.0)",
                   "45.6 ± 3.4 (43.0–53.0)"]),
    ]),
    ("S. rufum darioi", 3, [
        ("f", 1, ["3.1", "76", "67.6", "95.0", "26.0"]),
    ]),
    ("S. lilium angeli", 4, [
        ("h2", 5, ["2.7 ± 0.8 (1.3–3.3)", "72 ± 23 (41–92)",
                   "73.1 ± 11.5 (55.3–85.1)", "92.8 ± 8.8 (86.0–108.0)",
                   "46.2 ± 10.3 (36.0–59.0)"]),
        ("h3", 2, ["0.9, 1.0", "16, 58", "81.2, 79.4", "108.0, 107.0", "63.0, 64.0"]),
        ("h4", 1, ["1.0", "58", "79.4", "107.0", "64.0"]),
    ]),
    ("S. lilium paulsoni", 4, [
        ("h2", 2, ["1.7, 1.1", "41, 42", "56.0, 67.8", "91.0, 75.0", "36.0, 36.0"]),
    ]),
    ("N. stramineus stramineus", 3, [
        ("f", 2, ["2.8, 2.4", "36, 35", "44.6, 41.3", "66.0, 74.0", "30.0, 36.0"]),
        ("h2", 5, ["3.1 ± 0.8 (2.1–4.3)", "32 ± 4 (28–38)",
                   "113.8 ± 5.1 (107.7–121.2)", "152.8 ± 8.2 (143.0–162.0)",
                   "79.8 ± 5.5 (73.0–86.0)"]),
    ]),
]

RELEASE_NOTE = ("Released from the hand in background-cluttered space and recorded in free "
                "flight about 10 m away; one orientation-phase call per bat.")
PAIR_NOTE = (" Two bats were recorded and the source prints both values rather than a "
             "summary, so they are stored as the observed pair.")


def numbers(text: str) -> list[float]:
    return [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]


def parse(printed: str) -> dict:
    """Turn one printed Table 1 cell into a statistic and its values.

    Three shapes appear: 'mean +/- SD (min-max)', two individual values printed
    as 'a, b' where only two bats were recorded, and a bare single value.
    """
    values = numbers(printed)
    if "±" in printed:
        return {"statistic": "mean", "value": values[0],
                "dispersion_type": "sd", "dispersion_value": values[1]}
    if "," in printed:
        # Not a summary: the source prints both bats' values side by side.
        return {"statistic": "range",
                "value_min": min(values[:2]), "value_max": max(values[:2])}
    return {"statistic": "single", "value": values[0]}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def text(parsed: dict, key: str) -> str:
    return str(parsed[key]) if key in parsed else ""


def main() -> None:
    actual = hashlib.sha256(RAW.read_bytes()).hexdigest()
    if actual != RAW_SHA256:
        raise RuntimeError(f"Unexpected SHA-256 for {RAW.name}: {actual}")

    resolver = TaxonResolver()
    resolver.add_manual({})
    rows: list[dict] = []

    for printed_taxon, max_harmonics, harmonic_rows in TABLE_1:
        mdd_id, islands, decision = TAXA[printed_taxon]
        base = {
            "mdd_id": mdd_id,
            "verbatim_taxon_name": printed_taxon,
            "taxon_match_method": "manual",
            "reference_id": REFERENCE_ID,
            "method_id": METHOD_ID,
            "call_phase": "search",
            "call_variant": "", "variant_label": "", "signal_direction": "",
            "recording_condition": "hand_release",
            "habitat_class": "edge",
            "country": "; ".join(ISO[island] for island in islands),
            "locality": "; ".join(islands),
            "date_or_season": "Jan 1994, Apr 1995, Aug and Oct 1995, Jul and Aug 1996",
            "quality_flag": "ok",
        }
        taxon_note = RELEASE_NOTE + (f" Taxonomy: {decision}." if decision else "")

        # The maximum number of harmonics describes the call, not any one
        # harmonic, so it is its own observation with the harmonic left empty.
        rows.append({**base,
                     "observation_id": f"jennings-2004-{slug(printed_taxon)}",
                     "locator": f"Table 1, pp. 79-80, {printed_taxon}",
                     "n_individuals": "", "n_calls": "",
                     "parameter": "harmonic_count", "statistic": "max",
                     "value": str(max_harmonics), "value_min": "", "value_max": "",
                     "unit": "count", "dispersion_type": "", "dispersion_value": "",
                     "harmonic": "", "verbatim_value": str(max_harmonics),
                     "notes": ("Maximum number of harmonics, the fundamental included, seen "
                               "within the 120 kHz response of the recording equipment; more "
                               "may lie above it. " + taxon_note)})

        for dominant, n_bats, cells in harmonic_rows:
            observation_id = f"jennings-2004-{slug(printed_taxon)}-{dominant}"
            for parameter, printed in zip(PARAMETERS, cells):
                parsed = parse(printed)
                rows.append({**base,
                             "observation_id": observation_id,
                             "locator": f"Table 1, pp. 79-80, {printed_taxon} ({dominant})",
                             # One call per bat was analysed, so calls == bats.
                             "n_individuals": str(n_bats), "n_calls": str(n_bats),
                             "parameter": parameter,
                             "statistic": parsed["statistic"],
                             "value": text(parsed, "value"),
                             "value_min": text(parsed, "value_min"),
                             "value_max": text(parsed, "value_max"),
                             "unit": UNITS[parameter],
                             "dispersion_type": parsed.get("dispersion_type", ""),
                             "dispersion_value": text(parsed, "dispersion_value"),
                             "harmonic": HARMONIC_NUMBER[dominant],
                             "verbatim_value": printed,
                             "notes": (f"Measured on the harmonic carrying most energy in this "
                                       f"group of bats ({dominant}). " + taxon_note
                                       + (PAIR_NOTE if parsed["statistic"] == "range" else ""))})

    write_rows(REFERENCE_ID, rows)
    write_review(REFERENCE_ID, [])
    report(REFERENCE_ID, len(rows), len({r["mdd_id"] for r in rows}), resolver)


if __name__ == "__main__":
    main()
