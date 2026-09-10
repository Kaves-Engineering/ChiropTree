"""Import the supplied South Asia review table into the call schema.

The input is ``data/echolocation/files2.zip`` supplied with this project.  It
contains ``southasia_call_records.csv``, an extraction of Supplementary
Material 3 of Srinivasulu et al. (2025).  The archive SHA-256 is checked before
reading so the generated CSV is reproducible from the supplied source bytes.

Run: ``uv run data/build_srinivasulu_2025_southasia_calls.py``.
"""
import csv
import hashlib
import io
import zipfile
from pathlib import Path

from call_import_lib import TaxonResolver, report, write_review, write_rows

REFERENCE_ID = "srinivasulu-2025-southasia"
ARCHIVE = Path(__file__).parent / "echolocation" / "files2.zip"
ARCHIVE_SHA256 = "a38d7d07114bc95f0946027b78aa36ed4d5bd7100c7b654fd38bc6aa8181740c"

PARAMETERS = {
    "maximum_frequency_kHz": ("max_frequency", "kHz"),
    "minimum_frequency_kHz": ("min_frequency", "kHz"),
    "fmaxE_kHz": ("peak_frequency", "kHz"),
    "call_duration_ms": ("duration", "ms"),
}
CONDITIONS = {
    "Release-Open": ("hand_release", "open"),
    "Release-Cluttered": ("hand_release", "clutter"),
    "Flight-Open": ("free_flying_wild", "open"),
    "Flight-Cluttered": ("free_flying_wild", "clutter"),
    # The review's label is explicitly hand-held.  Do not relabel it as flight.
    "Hand-held": ("hand_release", ""),
}


def method_id(detector: str) -> str:
    return "srinivasulu-2025-southasia-" + "".join(
        char.lower() if char.isalnum() else "-" for char in detector
    ).strip("-")


def main() -> None:
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    if digest != ARCHIVE_SHA256:
        raise RuntimeError(f"Unexpected source archive SHA-256: {digest}")

    with zipfile.ZipFile(ARCHIVE) as source:
        table = source.read("southasia_call_records.csv").decode("utf-8-sig")
    records = csv.DictReader(io.StringIO(table))

    resolver = TaxonResolver()
    rows = []
    species_seen = set()
    for record in records:
        parameter, unit = PARAMETERS[record["trait"]]
        species, match_method = resolver.resolve(record["sci_name"])
        if species is None:
            continue
        species_seen.add(species["id"])
        condition, habitat = CONDITIONS[record["recording_condition"]]
        note = (
            f"Review Supplementary Material 3 attributes this observation to "
            f"{record['source']}. "
        )
        if parameter == "peak_frequency":
            note += "The table labels this FmaxE (frequency of maximum energy)."
        else:
            note += f"The table labels this {record['trait']}."
        rows.append({
            "observation_id": f"srinivasulu2025-{record['obs_id']}",
            "mdd_id": species["id"],
            "verbatim_taxon_name": record["sci_name"],
            "taxon_match_method": match_method,
            "reference_id": REFERENCE_ID,
            "locator": f"Supplementary Material 3, observation {record['obs_id']}",
            "method_id": method_id(record["detector"]),
            "call_phase": "unspecified",
            "recording_condition": condition,
            "habitat_class": habitat,
            "country": record["country"],
            "locality": record["region"],
            "n_calls": record["n_pulses"],
            "parameter": parameter,
            # The review table gives one point per observation but does not
            # state whether it is a mean, median, or exemplar.
            "statistic": "species_summary",
            "value": record["value"],
            "unit": unit,
            "verbatim_value": record["value"],
            "quality_flag": "definition_unstated",
            "notes": note,
        })

    path = write_rows(REFERENCE_ID, rows)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(rows), len(species_seen), resolver)
    print(f"  -> {path}")
    if review:
        print(f"  -> {review} (needs a human decision)")


if __name__ == "__main__":
    main()
