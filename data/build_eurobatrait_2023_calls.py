"""Import EuroBaTrait 1.0 acoustic-signature observations.

The four CC-BY tables used here are cached at ``data/raw/eurobatrait-1.0``.
Their expected SHA-256 digests are checked before reading, so the generated
measurement CSV is reproducible from the exact Figshare v2 source files.

Run: ``uv run data/build_eurobatrait_2023_calls.py``.
"""
import csv
import hashlib
from pathlib import Path

from call_import_lib import TaxonResolver, report, write_review, write_rows
from calls.parameter_registry import Registry


REFERENCE_ID = "eurobatrait-2023"
RAW = Path(__file__).parent / "raw" / "eurobatrait-1.0"
SOURCES = {
    "04_acoustic_signature.csv": "22381fc194772a55190d463278dee95707d7d3ca5e84a60e980c8c7bd18f3604",
    "Taxon.csv": "d2789d8e8775c7693282b45f7832d54475054d9d596cab37464b505e91d9db68",
    "Trait_description.csv": "a990aa682fc9d417181368ed6a23eb24847d79640c573de9e71293bde9c6e2e7",
    "Trait_references.csv": "64ac4fdad22c069e71c3b5a9589fa093163e9346f8dea0b8e9b1adedd6afe98e",
}

# The values resolve through the shared parameter registry.  The strings at
# right are registered aliases; keeping the source-heading translation here
# makes the one context-dependent exception (buzz peak) explicit.
TRAIT_HEADINGS = {
    "CallBandwidth": "bandwidth",
    "CallDuration": "call duration",
    "CallEndFrequency": "end frequency",
    "InterpulseInterval": "inter-pulse interval",
    "CallMaxFrequency": "max frequency",
    "CallMinFrequency": "min frequency",
    "CallPeakFrequency": "peak frequency",
    "CallSlope": "slope",
    "CallStartFrequency": "start frequency",
    "buzzDuration": "buzz duration",
    "buzzPeakFrequency": "peak frequency",
    "CallType": "call type",
}

# CallMidFrequency is an energy frequency at the temporal midpoint, not a
# knee, characteristic, or peak frequency. rateBuzz is an activity metric,
# not a pulse or buzz measurement. Neither is silently coerced into a current
# parameter; their exclusions are reported after each import.
EXCLUDED_TRAITS = {"CallMidFrequency", "rateBuzz"}

# EuroBaTrait uses former Eptesicus combinations for three taxa now accepted
# in MDD as Cnephaeus. These are one-to-one genus recombinations, not splits.
MANUAL_TAXA = {
    "Eptesicus anatolicus": "1005511",
    "Eptesicus isabellinus": "1005524",
}


def source_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def condition(printed: str) -> str:
    """Map only unambiguous source contexts to the controlled vocabulary."""
    if printed == "hand-release":
        return "hand_release"
    if printed in {"free-flight", "leaving roost"}:
        return "free_flying_wild"
    return "unspecified"


def clean(value: str | None) -> str:
    return "" if value in {None, "", "NA"} else value


def main() -> None:
    for filename, expected in SOURCES.items():
        actual = source_digest(RAW / filename)
        if actual != expected:
            raise RuntimeError(f"Unexpected SHA-256 for {filename}: {actual}")

    registry = Registry()
    resolver = TaxonResolver()
    resolver.add_manual(MANUAL_TAXA)
    rows, species_seen, excluded = [], set(), set()

    with (RAW / "04_acoustic_signature.csv").open(encoding="utf-8-sig", newline="") as handle:
        records = csv.DictReader(handle)
        for line_number, record in enumerate(records, start=2):
            trait = record["verbatimTraitName"]
            if trait in EXCLUDED_TRAITS:
                excluded.add(trait)
                continue
            heading = TRAIT_HEADINGS.get(trait)
            if heading is None:
                raise RuntimeError(f"Unmapped EuroBaTrait trait: {trait}")
            parameter = registry.resolve(heading)
            if parameter is None:
                raise RuntimeError(f"Registry has no parameter alias for {trait} ({heading!r})")

            printed_name = record["verbatimScientificName"].replace("_", " ")
            species, match_method = resolver.resolve(printed_name)
            if species is None:
                continue
            species_seen.add(species["id"])

            is_buzz = trait in {"buzzDuration", "buzzPeakFrequency"}
            is_type = trait == "CallType"
            source_type = clean(record["verbatimTraitValueType"])
            statistic = "single" if is_type else "mean"
            quality = "definition_unstated" if source_type != "mean of means" else "derived"
            value = record["verbatimTraitValue"]
            if is_type:
                value = {"FM/QCF": "FM-QCF", "CF+FM": "CF-FM"}.get(value, value)
                quality = "definition_unstated"

            notes = (
                f"EuroBaTrait source: {record['ShortReference']}. "
                f"Original citation as retained by EuroBaTrait: {record['FullReference']} "
                f"Printed recording context: {clean(record['verbatimTraitMethod']) or 'NA'}."
            )
            extras = [clean(record[field]) for field in ("AdditionalInfo1", "AdditionalInfo2", "AdditionalInfo3")]
            if any(extras):
                notes += " Additional source information: " + "; ".join(x for x in extras if x) + "."
            if source_type == "mean of means":
                notes += " The database labels this a mean of means; it is retained as a derived mean."
            if trait == "CallSlope":
                notes += " The database reports the signed slope; negative values indicate descending sweeps."
            if trait == "buzzDuration":
                notes += " EuroBaTrait defines this as feeding-buzz duration including its pre-buzz phase."

            n_unit = clean(record["verbatimN1Unit"])
            rows.append({
                "observation_id": f"eurobatrait2023-{line_number}",
                "mdd_id": species["id"],
                "verbatim_taxon_name": printed_name,
                "taxon_match_method": match_method,
                "reference_id": REFERENCE_ID,
                "locator": f"04_acoustic_signature.csv, line {line_number}",
                "method_id": "eurobatrait-2023-compiled",
                "call_phase": "terminal_buzz" if is_buzz else "unspecified",
                "recording_condition": condition(clean(record["verbatimTraitMethod"])),
                "country": clean(record["Area"]),
                "n_calls": clean(record["verbatimN1"]) if n_unit == "call" else "",
                "parameter": parameter,
                "statistic": statistic,
                "value": value,
                "unit": "" if is_type else record["verbatimTraitUnit"],
                "dispersion_type": "sd" if clean(record["verbatimTraitValueSD"]) else "",
                "dispersion_value": clean(record["verbatimTraitValueSD"]),
                "verbatim_value": record["verbatimTraitValue"],
                "quality_flag": quality,
                "notes": notes,
            })

    path = write_rows(REFERENCE_ID, rows)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(rows), len(species_seen), resolver)
    print(f"  excluded without coercion: {', '.join(sorted(excluded))}")
    print(f"  -> {path}")
    if review:
        print(f"  -> {review} (needs a human decision)")


if __name__ == "__main__":
    main()
