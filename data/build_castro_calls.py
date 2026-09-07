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

from call_import_lib import TaxonResolver, report, write_review, write_rows

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


def main() -> None:
    resolver = TaxonResolver()
    rows = extract_table3(fetch_supplement())

    out = []
    species_seen = set()
    for record in rows:
        species, method = resolver.resolve(record["species"])
        if species is None:
            continue
        species_seen.add(species["id"])

        # Context shared by every value from this row. Castro's table states no
        # call phase, no recording condition and no method, and those absences
        # are recorded rather than assumed: they are what puts these entries at
        # density 'minimal'.
        context = {
            "observation_id": f"castro2024-{species['id']}",
            "mdd_id": species["id"],
            "verbatim_taxon_name": record["species"],
            "taxon_match_method": method,
            "reference_id": REFERENCE_ID,
            "locator": f"Table 3, row {record['_row']}",
            "method_id": METHOD_ID,
            "call_phase": "unspecified",
            "quality_flag": "ok",
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
            out.append({**context, "parameter": parameter, "statistic": "single",
                        "value": printed, "unit": unit, "verbatim_value": printed})

    path = write_rows(REFERENCE_ID, out)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(out), len(species_seen), resolver)
    print(f"  -> {path.relative_to(HERE.parent)}")
    if review:
        print(f"  -> {review.relative_to(HERE.parent)} (needs a human decision)")


if __name__ == "__main__":
    main()
