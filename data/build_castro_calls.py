"""Merge species-level call parameters from Castro, Amado & Olalla-Tarraga (2024)
into call_measurements.json.

Source: "Correlated evolution between body size and echolocation in bats
(order Chiroptera)", BMC Ecology and Evolution, DOI 10.1186/s12862-024-02231-4,
Table 3 of the supplementary material (CC-BY 4.0). The paper states the
measurements were "taken from measured data in Collen (2012)"; Castro et al.
is cited here because it is the peer-reviewed, openly licensed republication
with a species-level table we can read and check reproducibly.

See call_import_lib.py for the shared skip/report policy this and other
build_<source>_calls.py scripts follow.

Run:  uv run data/build_castro_calls.py
The supplementary docx is cached in data/raw/ so a re-run doesn't re-fetch it.
"""
import io
import urllib.request
from pathlib import Path

import docx

from call_import_lib import load_species_by_name, load_store, merge_species, norm, report, save_store

HERE = Path(__file__).parent
SUPP_URL = (
    "https://static-content.springer.com/esm/"
    "art%3A10.1186%2Fs12862-024-02231-4/MediaObjects/"
    "12862_2024_2231_MOESM1_ESM.docx"
)
CACHE = HERE / "raw" / "castro_2024_supplement.docx"

REFERENCE_ID = "castro-2024"
REFERENCE = {
    "url": "https://doi.org/10.1186/s12862-024-02231-4",
    "label": "Castro, Amado & Olalla-Tarraga 2024, table 3 (data from Collen 2012)",
}

TABLE3_HEADER = ["Suborder", "Family", "Species", "Band", "BM", "Call Dur", "PF", "Ech.T"]


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
            for row in table.rows[1:]:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(dict(zip(
                    ["suborder", "family", "species", "bandwidth_khz", "body_mass_g",
                     "call_duration_ms", "peak_frequency_khz", "emission_type"],
                    cells,
                )))
            return rows
    raise RuntimeError("Table 3 (species-level echolocation database) not found in supplement")


def main() -> None:
    by_name = load_species_by_name()
    store = load_store()
    rows = extract_table3(fetch_supplement())

    unmatched = []
    entries = []
    for row in rows:
        species = by_name.get(norm(row["species"]))
        if not species:
            unmatched.append(row["species"])
            continue
        emission = "oral" if row["emission_type"].strip().lower() == "oral" else "nasal"
        entries.append((species["id"], {
            "summary": (
                f"Peak frequency ~{row['peak_frequency_khz']} kHz, "
                f"bandwidth {row['bandwidth_khz']} kHz, "
                f"duration {row['call_duration_ms']} ms ({emission} emission)."
            ),
            "context": f"Comparative database entry; body mass {row['body_mass_g']} g.",
        }))

    summary = merge_species(store, REFERENCE_ID, REFERENCE, entries)
    save_store(store)
    report(summary, unmatched)


if __name__ == "__main__":
    main()
