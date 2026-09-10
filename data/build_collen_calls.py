"""Import Appendix F of Collen (2012), the primary source behind Castro (2024).

Source: Collen A (2012) "The evolution of echolocation in bats: a comparative
approach", PhD thesis, University College London. Open access at UCL Discovery,
eprint 1370574. Appendix F ("Species list: Analyses", pp. 337-392) is the full
species x parameter table drawn from the EchoBank call consortium.

Why the primary source rather than the republication: Castro's Table 3 carries
five parameters for 329 rows; this appendix carries ten for 918 rows, including
the minimum and maximum frequency bounds that make a species card useful.

Three things this importer has to get right.

1. Only some rows are measured. The appendix mixes measured, assumed and
   imputed values, and marks them by typeface rather than in a column: roman is
   measured, italic is imputed, bold is assumed (call type only). Only roman
   values are imported. Reading the typeface needs a font-aware PDF parser,
   which is why this module uses PyMuPDF rather than plain text extraction. The
   roman counts it finds reproduce the per-parameter "Measured" sample sizes
   printed at the head of the appendix, which is the check that the typeface
   rule is being applied correctly.

2. Characteristic frequency is deliberately NOT imported. Table 2.8 defines it
   as "the frequency measure with the lowest variance for each species out of
   maximum frequency, minimum frequency, and peak frequency" -- so it is a copy
   of one of the three columns we already import, chosen per species, not an
   independent measurement. Importing it would create a second value identical
   to an existing one and manufacture false corroboration. It is also not the
   Analook characteristic frequency that this project's registry defines, so it
   must not go into that parameter either.

3. The values are per-species representatives whose underlying statistic the
   thesis does not state, so they are stored with statistic=species_summary
   rather than mean.

Run:  uv run data/build_collen_calls.py
The thesis PDF is cached in data/raw/ so a re-run doesn't re-fetch it.
"""
import re
import urllib.request
from pathlib import Path

import pymupdf

from call_import_lib import (TaxonResolver, observation_suffix, report,
                             write_review, write_rows)

HERE = Path(__file__).parent
PDF_URL = ("https://discovery.ucl.ac.uk/1370574/4/"
           "Redacted%20version%20of%20whole%20thesis%20final%20copy%20with%20no%20cartoon%20121112.pdf")
CACHE = HERE / "raw" / "collen_2012_thesis.pdf"

REFERENCE_ID = "collen-2012"
METHOD_ID = "collen-2012-sonobat"

# Appendix F, printed pp. 337-392; PyMuPDF pages are 0-based, so index = printed - 1.
FIRST_PAGE, LAST_PAGE = 336, 391

# Left x of each column, measured from the rendered pages. Values sit within a
# few points of these anchors and are assigned to the nearest one.
COLUMNS = [
    (305, "call_shape_class", None),
    (340, "bandwidth", "kHz"),
    (380, "body_mass", "g"),
    (423, "duration", "ms"),
    (460, None, None),            # characteristic frequency - see module docstring
    (505, "dominant_slope", "kHz/msec"),
    (543, "max_frequency", "kHz"),
    (585, "min_frequency", "kHz"),
    (625, "peak_frequency", "kHz"),
    (668, "total_slope", "kHz/msec"),
]
X_TOLERANCE = 12
ROW_TOLERANCE = 4

# Only these call-shape classes translate to the registry's signal_type without
# interpretation, because the class definitions say exactly that.
SIGNAL_TYPE_FROM_CLASS = {"1": "none", "2": "broadband_click"}

# Values kept but flagged, keyed by (verbatim name, parameter).
QUALITY_OVERRIDES = {
    ("Triaenops rufus", "peak_frequency"): (
        "harmonic_ambiguous",
        "39.82 kHz is roughly half what published Malagasy Triaenops call at (males of this "
        "species about 82 kHz, females about 93), and 39.82 x 2 = 79.6 falls in that band. This "
        "looks like the fundamental reported where the dominant second harmonic is the usual "
        "measure for a high-duty-cycle trident bat. Flagged, not corrected."),
}


def fetch_thesis() -> Path:
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(PDF_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            CACHE.write_bytes(response.read())
    return CACHE


def extract_rows(pdf: Path) -> list[dict]:
    """One dict per appendix line: family, species, and measured values only."""
    document = pymupdf.open(pdf)
    rows = []
    for index in range(FIRST_PAGE, LAST_PAGE + 1):
        spans = []
        for block in document[index].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        spans.append((span["bbox"][1], span["bbox"][0], span["font"], text))
        spans.sort()

        lines = []
        for top, left, font, text in spans:
            if lines and abs(lines[-1][0] - top) <= ROW_TOLERANCE:
                lines[-1][1].append((left, font, text))
            else:
                lines.append((top, [(left, font, text)]))

        for _, cells in lines:
            family = next((t for x, f, t in cells if x < 150 and t[:1].isupper()
                           and t.endswith("dae")), None)
            # A few rows print the binomial with an underscore
            # ("Rousettus_aegyptiacus"), so accept either separator.
            species = next((t.replace("_", " ") for x, f, t in cells
                            if 150 <= x < 300 and "Italic" in f
                            and (" " in t or "_" in t)), None)
            if not family or not species:
                continue
            record = {"family": family, "species": species, "values": {}}
            for x, font, text in cells:
                if not re.fullmatch(r"-?\d+(\.\d+)?", text):
                    continue
                anchor = min(COLUMNS, key=lambda c: abs(c[0] - x))
                if abs(anchor[0] - x) > X_TOLERANCE or anchor[1] is None:
                    continue
                # Roman is measured; italic is imputed and bold is assumed.
                if "Italic" in font or "Bold" in font:
                    continue
                record["values"][anchor[1]] = (text, anchor[2])
            if record["values"]:
                rows.append(record)
    return rows


def main() -> None:
    resolver = TaxonResolver()
    table = extract_rows(fetch_thesis())
    print(f"Parsed {len(table)} appendix lines carrying at least one measured value")

    out = []
    species_seen = set()
    for record in table:
        matches, method, split_note = resolver.resolve_many(record["species"])
        if not matches:
            continue
        for species in matches:
            species_seen.add(species["id"])
            suffix = observation_suffix(record["species"], species)
            context = {
                "observation_id": f"collen2012-{species['id']}{suffix}",
                "mdd_id": species["id"],
                "verbatim_taxon_name": record["species"],
                "taxon_match_method": method,
                "reference_id": REFERENCE_ID,
                "locator": "Appendix F, pp. 337-392",
                "method_id": METHOD_ID,
                "call_phase": "unspecified",
                "quality_flag": "taxon_uncertain" if split_note else "ok",
                "notes": " ".join(filter(None, [
                    split_note,
                    ("Printed in the source as a separate species; the current taxonomy "
                     f"treats it as {species['sciName'].replace('_', ' ')}." if suffix else ""),
                ])),
            }
            for parameter, (printed, unit) in sorted(record["values"].items()):
                if parameter == "call_shape_class":
                    code = printed.split(".")[0]
                    out.append({**context, "parameter": "call_shape_class",
                                "statistic": "single", "value": code, "verbatim_value": printed})
                    if code in SIGNAL_TYPE_FROM_CLASS:
                        out.append({**context, "parameter": "signal_type", "statistic": "single",
                                    "value": SIGNAL_TYPE_FROM_CLASS[code], "verbatim_value": printed,
                                    "notes": "Read from Collen's call-shape class, whose definition "
                                             "states this directly."})
                    continue
                flag, note = QUALITY_OVERRIDES.get((record["species"], parameter), (None, None))
                row = {**context, "parameter": parameter, "statistic": "species_summary",
                       "value": printed, "unit": unit, "verbatim_value": printed}
                if flag:
                    row["quality_flag"], row["notes"] = flag, note
                out.append(row)

    path = write_rows(REFERENCE_ID, out)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(out), len(species_seen), resolver)
    print(f"  -> {path.relative_to(HERE.parent)}")
    if review:
        print(f"  -> {review.relative_to(HERE.parent)} (needs a human decision)")


if __name__ == "__main__":
    main()
