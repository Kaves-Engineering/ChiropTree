"""Import species-level call parameters from Castro, Amado & Olalla-Tarraga (2024).

Source: "Correlated evolution between body size and echolocation in bats
(order Chiroptera)", BMC Ecology and Evolution, DOI 10.1186/s12862-024-02231-4,
Table 3 of the supplementary material (CC-BY 4.0). The paper states the
measurements were "taken from measured data in Collen (2012)", so the
reference record links castro-2024 -> collen-2012 and both share an
independence group: agreement with another source that also draws on
EchoBank is not independent corroboration.

Writes data/calls/castro-2024.csv; run data/calls/build_calls.py afterwards
to validate and rebuild the browser export.

Run:  uv run data/build_castro_calls.py
The supplementary docx is cached in data/raw/ so a re-run doesn't re-fetch it.
"""
import io
import urllib.request
from pathlib import Path

import docx

from call_import_lib import (TaxonResolver, observation_suffix, report,
                             write_review, write_rows)

HERE = Path(__file__).parent
SUPP_URL = (
    "https://static-content.springer.com/esm/"
    "art%3A10.1186%2Fs12862-024-02231-4/MediaObjects/"
    "12862_2024_2231_MOESM1_ESM.docx"
)
CACHE = HERE / "raw" / "castro_2024_supplement.docx"

REFERENCE_ID = "castro-2024"
METHOD_ID = "castro-2024-unstated"
TABLE3_HEADER = ["Suborder", "Family", "Species", "Band", "BM", "Call Dur", "PF", "Ech.T"]

# Table column -> (registry parameter, unit). Headings also resolve through the
# registry's alias index; this mapping is explicit so a silent change to the
# supplement cannot quietly re-point a column.
PARAMETERS = [
    ("peak_frequency_khz", "peak_frequency", "kHz"),
    ("bandwidth_khz", "bandwidth", "kHz"),
    ("call_duration_ms", "duration", "ms"),
    ("body_mass_g", "body_mass", "g"),
]


def fetch_supplement() -> bytes:
    if CACHE.exists():
        return CACHE.read_bytes()
    request = urllib.request.Request(SUPP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(content)
    return content


def extract_table3(docx_bytes: bytes) -> list[dict]:
    document = docx.Document(io.BytesIO(docx_bytes))
    for table in document.tables:
        header = [cell.text.strip() for cell in table.rows[0].cells]
        if header == TABLE3_HEADER:
            rows = []
            for number, row in enumerate(table.rows[1:], start=1):
                cells = [cell.text.strip() for cell in row.cells]
                record = dict(zip(
                    ["suborder", "family", "species", "bandwidth_khz", "body_mass_g",
                     "call_duration_ms", "peak_frequency_khz", "emission_type"],
                    cells,
                ))
                record["_row"] = number
                rows.append(record)
            return rows
    raise RuntimeError("Table 3 (species-level echolocation database) not found in supplement")


# Values kept but flagged, because the table's own figure is doubtful. Keyed by
# (verbatim name, parameter). The value stays: A4 says a source's number is not
# deleted because we doubt it, only marked so it loses to a better measurement.
QUALITY_OVERRIDES = {
    ("Triaenops persicus", "peak_frequency"): (
        "suspect",
        "Castro gives 39.82 kHz for Triaenops persicus, but the primary source it republishes "
        "(Collen 2012, Appendix F) lists T. persicus at 83.00 kHz and gives 39.82 for a different "
        "species, T. rufus (now Triaenops menamena). 83 kHz is what published Malagasy Triaenops "
        "call at, so this row appears to carry the right number under the wrong name. The value is "
        "kept and flagged rather than deleted; the correctly attributed measurements are imported "
        "from Collen."),
}


def main() -> None:
    resolver = TaxonResolver()
    rows = extract_table3(fetch_supplement())

    out = []
    species_seen = set()
    for record in rows:
        matches, method, split_note = resolver.resolve_many(record["species"])
        if not matches:
            continue
        for species in matches:
            species_seen.add(species["id"])

            # Context shared by every value from this row. Castro's table states no
            # call phase, no recording condition and no method, and those absences
            # are recorded rather than assumed: they are what puts these entries at
            # density 'minimal'.
            # A source can list two names that the current taxonomy has since lumped
            # into one species (Castro has both Hypsugo ariel and H. bodenheimeri).
            # Those are two separate measurements of two populations and must not
            # collapse into one observation, so the id carries the printed epithet
            # whenever it differs from the accepted name.
            accepted = species["sciName"].replace("_", " ")
            suffix = observation_suffix(record["species"], species)
            context = {
                "observation_id": f"castro2024-{species['id']}{suffix}",
                "mdd_id": species["id"],
                "verbatim_taxon_name": record["species"],
                "taxon_match_method": method,
                "notes": " ".join(filter(None, [
                    split_note,
                    ("Printed in the source as a separate species; the current "
                     f"taxonomy treats it as {accepted}." if suffix else ""),
                ])),
                "reference_id": REFERENCE_ID,
                "locator": f"Table 3, row {record['_row']}",
                "method_id": METHOD_ID,
                "call_phase": "unspecified",
                "quality_flag": "taxon_uncertain" if split_note else "ok",
            }

            emission = record["emission_type"].strip().lower()
            if emission not in ("oral", "nasal"):
                resolver.unresolved.append(
                    (record["species"], f"unexpected emission value {record['emission_type']!r}"))
                continue
            out.append({**context, "parameter": "emission", "statistic": "single",
                        "value": emission, "verbatim_value": record["emission_type"]})

            for column, parameter, unit in PARAMETERS:
                printed = record[column].strip()
                if not printed:
                    continue
                flag, note = QUALITY_OVERRIDES.get((record["species"], parameter), (None, None))
                row = {**context, "parameter": parameter, "statistic": "single",
                       "value": printed, "unit": unit, "verbatim_value": printed}
                if flag:
                    row["quality_flag"] = flag
                    row["notes"] = note
                out.append(row)

    path = write_rows(REFERENCE_ID, out)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(out), len(species_seen), resolver)
    print(f"  -> {path.relative_to(HERE.parent)}")
    if review:
        print(f"  -> {review.relative_to(HERE.parent)} (needs a human decision)")


if __name__ == "__main__":
    main()
