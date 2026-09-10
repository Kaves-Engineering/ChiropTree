"""Import the two newly audited Colombian source tables into data/calls.

The source artefacts are cached in data/raw so each row can name their exact
SHA-256 fingerprint.  This importer deliberately excludes Pteronotus cf.
rubiginosus: the source labels it a sonotype and says Colombian acoustic data
are insufficient to separate it from the related taxa.

Run from the repository root:
    uv run data/import_colombian_literature_calls.py
"""
import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CALLS = ROOT / "data" / "calls"
RAW = ROOT / "data" / "raw"

FIELDS = [
    "observation_id", "mdd_id", "verbatim_taxon_name", "taxon_match_method",
    "reference_id", "locator", "method_id", "call_phase", "call_variant",
    "variant_label", "signal_direction", "recording_condition", "habitat_class",
    "country", "locality", "date_or_season", "n_individuals", "n_calls",
    "parameter", "statistic", "value", "value_min", "value_max", "unit",
    "dispersion_type", "dispersion_value", "verbatim_value", "quality_flag", "notes",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(**values) -> dict:
    result = {field: "" for field in FIELDS}
    result.update(values)
    return result


def mean_row(*, observation_id, mdd_id, taxon, reference_id, locator, method_id,
             phase, condition, country, locality, season, calls, parameter,
             value, unit, sd, verbatim, notes, **extra):
    return row(
        observation_id=observation_id, mdd_id=mdd_id, verbatim_taxon_name=taxon,
        taxon_match_method="exact", reference_id=reference_id, locator=locator,
        method_id=method_id, call_phase=phase, signal_direction=extra.get("direction", ""),
        recording_condition=condition, habitat_class=extra.get("habitat", ""),
        country=country, locality=locality, date_or_season=season,
        n_individuals=extra.get("individuals", ""), n_calls=calls,
        parameter=parameter, statistic="mean", value=str(value), unit=unit,
        dispersion_type="sd", dispersion_value=str(sd), verbatim_value=verbatim,
        quality_flag=extra.get("quality", "definition_unstated"), notes=notes,
    )


def main() -> None:
    yanten_raw = RAW / "yanten-2023.html"
    buitrago_raw = RAW / "buitrago-castano-2025.pdf"
    for raw_path in (yanten_raw, buitrago_raw):
        if not raw_path.is_file():
            raise SystemExit(f"Missing cached source: {raw_path}")
    yanten_hash, buitrago_hash = sha256(yanten_raw), sha256(buitrago_raw)
    if yanten_hash != "10dad00af4fd7ebdc2216aa8c67431c41d471b397ffa016727b25c3d21dfc43a":
        raise SystemExit("yanten-2023 raw-file hash changed; re-audit before importing")
    if buitrago_hash != "f3b7653bd664d10bc4a00d4c598e333ab9ee638f880ea2bc9b5db0fc49c56e25":
        raise SystemExit("buitrago-castano-2025 raw-file hash changed; re-audit before importing")

    yanten_rows = []
    common = {
        "reference_id": "yanten-2023", "locator": "Appendix 1, Vichada (Colombia) row",
        "method_id": "yanten-2023-field", "condition": "free_flying_wild",
        "country": "Colombia", "locality": "Puerto Carreño, Vichada: Reserva Forestal La Pedregoza and Caño Negro farm",
        "season": "February 2018; November 2020", "direction": "downward",
        "quality": "definition_unstated",
    }
    # Appendix order: duration, IPI, start, end, peak, maximum, minimum.
    observations = [
        ("yanten-2023-personatus-search", "1004862", "Pteronotus personatus", "search", "132", "22 sequences",
         [("duration", 6.8, "ms", 1.3, "6.8 ± 1.3"), ("inter_pulse_interval", 78.9, "ms", 26.5, "78.9 ± 26.5"),
          ("start_frequency", 77.2, "kHz", 2.0, "77.2 ± 2.0"), ("end_frequency", 66.2, "kHz", 2.0, "66.2 ± 2.0"),
          ("peak_frequency", 68.0, "kHz", 4.0, "68.0 ± 4.0"), ("max_frequency", 78.5, "kHz", 2.0, "78.5 ± 2.0"),
          ("min_frequency", 65.3, "kHz", 1.7, "65.3 ± 1.7")]),
        ("yanten-2023-personatus-approach", "1004862", "Pteronotus personatus", "approach", "117", "16 sequences",
         [("duration", 6.5, "ms", 1.5, "6.5 ± 1.5"), ("inter_pulse_interval", 56.8, "ms", 10.9, "56.8 ± 10.9"),
          ("start_frequency", 78.4, "kHz", 2.3, "78.4 ± 2.3"), ("end_frequency", 66.6, "kHz", 2.0, "66.6 ± 2.0"),
          ("peak_frequency", 68.6, "kHz", 3.3, "68.6 ± 3.3"), ("max_frequency", 79.4, "kHz", 2.2, "79.4 ± 2.2")]),
        ("yanten-2023-gymnonotus-search", "1004856", "Pteronotus gymnonotus", "search", "34", "3 sequences",
         [("duration", 7.5, "ms", 0.9, "7.5 ± 0.9"), ("inter_pulse_interval", 68.0, "ms", 3.5, "68.0 ± 3.5"),
          ("start_frequency", 57.5, "kHz", 3.2, "57.5 ± 3.2"), ("end_frequency", 49.8, "kHz", 3.1, "49.8 ± 3.1"),
          ("peak_frequency", 57.2, "kHz", 3.9, "57.2 ± 3.9"), ("max_frequency", 58.8, "kHz", 3.6, "58.8 ± 3.6"),
          ("min_frequency", 48.5, "kHz", 3.4, "48.5 ± 3.4")]),
    ]
    for observation_id, mdd_id, taxon, phase, calls, sequences, measurements in observations:
        note = (f"Manually transcribed by import_colombian_literature_calls.py from Appendix 1; "
                f"cached raw SHA-256 {yanten_hash}. n/N in the source is {calls}/{sequences}. "
                "The paper states that all values are from the second harmonic.")
        for parameter, value, unit, sd, verbatim in measurements:
            yanten_rows.append(mean_row(observation_id=observation_id, mdd_id=mdd_id, taxon=taxon,
                phase=phase, calls=calls, parameter=parameter, value=value, unit=unit, sd=sd,
                verbatim=verbatim, notes=note, **common))

    buitrago_rows = []
    note = (f"Manually transcribed by import_colombian_literature_calls.py from Table 1; cached raw SHA-256 {buitrago_hash}. "
            "N=92 calls / 6 recording sessions from one adult female (IAvH-M-11214); the paper says the result does not represent between-individual variation. "
            "Published bandwidth (21.6 ± 5.2 kHz) is retained verbatim although it does not equal the displayed max-minus-min values.")
    common_b = {
        "observation_id": "buitrago-castano-2025-ega-flight-room", "mdd_id": "1005580", "taxon": "Lasiurus ega",
        "reference_id": "buitrago-castano-2025", "locator": "Table 1, Puerto Wilches row",
        "method_id": "buitrago-castano-2025-flight-room", "phase": "search", "condition": "flight_room",
        "country": "Colombia", "locality": "Puerto Wilches, Santander (7.37316, -73.86333)",
        "season": "2022-03-27, 08:43-08:49", "calls": "92", "individuals": "1",
        "direction": "downward",
    }
    for parameter, value, unit, sd, verbatim, quality in [
        ("max_frequency", 36.97, "kHz", 2.436, "36.97 ± 2.436", "definition_unstated"),
        ("min_frequency", 30.92, "kHz", 2.85, "30.92 ± 2.85", "definition_unstated"),
        ("peak_frequency", 36.97, "kHz", 2.43, "36.97 ± 2.43", "definition_unstated"),
        ("bandwidth", 21.6, "kHz", 5.2, "21.6 ± 5.2", "suspect"),
        ("duration", 2.85, "ms", 0.5, "2.85 ± 0.5", "definition_unstated"),
        ("inter_pulse_interval", 33.73, "ms", 0.98, "33.73 ± 0.98", "definition_unstated"),
    ]:
        buitrago_rows.append(mean_row(parameter=parameter, value=value, unit=unit, sd=sd,
            verbatim=verbatim, notes=note, quality=quality, **common_b))

    for filename, rows in (("yanten-2023.csv", yanten_rows), ("buitrago-castano-2025.csv", buitrago_rows)):
        with (CALLS / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    print(f"Wrote {len(yanten_rows)} Yantén rows and {len(buitrago_rows)} Buitrago-Castaño rows.")


if __name__ == "__main__":
    main()
