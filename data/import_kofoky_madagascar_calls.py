"""Import MDD-resolved Madagascar observations from Kofoky et al. (2009)."""
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "calls" / "kofoky-2009.csv"
RAW = ROOT / "data" / "raw" / "kofoky-2009.pdf"
FIELDS = [
    "observation_id", "mdd_id", "verbatim_taxon_name", "taxon_match_method",
    "reference_id", "locator", "method_id", "call_phase", "call_variant",
    "variant_label", "signal_direction", "recording_condition", "habitat_class",
    "country", "locality", "date_or_season", "n_individuals", "n_calls",
    "parameter", "statistic", "value", "value_min", "value_max", "unit",
    "dispersion_type", "dispersion_value", "verbatim_value", "quality_flag", "notes",
]
HASH = "26436d299810e72deb211d725d4c21b501b4de56579d6d43ce17a2d6c2c85c46"
TAXA = [
    ("paremballonura-tiavato", "1004812", "Emballonura tiavato", "manual", "6", "25", [("peak_frequency", 54.2, .71), ("max_frequency", 55.6, .88), ("min_frequency", 37.2, 2.82), ("duration", 4.2, 1.13), ("inter_pulse_interval", 92.2, 29.59)]),
    ("paremballonura-atrata", "1004811", "Emballonura atrata", "manual", "2", "7", [("peak_frequency", 52.9, 1.16), ("max_frequency", 55.7, .95), ("min_frequency", 39.1, 3.07), ("duration", 2.9, .44), ("inter_pulse_interval", 82.8, 11.12)]),
    ("laephotis-malagasyensis", "1005733", "Neoromicia malagasyensis", "manual", "6", "20", [("peak_frequency", 45.7, 2.94), ("max_frequency", 79.8, 12.35), ("min_frequency", 40.5, 3.77), ("duration", 4.9, .78), ("inter_pulse_interval", 69.1, 17.57)]),
    ("scotophilus-tandrefana", "1005696", "Scotophilus tandrefana", "exact", "1", "7", [("peak_frequency", 48.2, 1.52), ("max_frequency", 91.2, 8.95), ("min_frequency", 42.9, .72), ("duration", 3.0, .30), ("inter_pulse_interval", 33.0, 10.33)]),
    ("scotophilus-marovaza", "1005690", "Scotophilus marovaza", "exact", "9", "21", [("peak_frequency", 45.9, 1.2), ("max_frequency", 68.9, 3.7), ("min_frequency", 42.9, 1.3), ("duration", 6.4, .6), ("inter_pulse_interval", 87.4, 24.4)]),
]

def main():
    if hashlib.sha256(RAW.read_bytes()).hexdigest() != HASH:
        raise SystemExit("kofoky-2009 raw hash changed; re-audit before importing")
    rows = []
    for slug, mdd_id, verbatim, match, bats, pulses, values in TAXA:
        note = ("Manually transcribed from Table 1 by import_kofoky_madagascar_calls.py; "
                f"cached raw SHA-256 {HASH}. Table reports {bats} bats / {pulses} pulses. "
                "The observation combines recording conditions, as documented by the method record.")
        for parameter, value, sd in values:
            unit = "ms" if parameter in {"duration", "inter_pulse_interval"} else "kHz"
            rows.append({field: "" for field in FIELDS} | {
                "observation_id": f"kofoky-2009-{slug}", "mdd_id": mdd_id,
                "verbatim_taxon_name": verbatim, "taxon_match_method": match,
                "reference_id": "kofoky-2009", "locator": f"Table 1, {verbatim} row",
                "method_id": "kofoky-2009-mixed", "call_phase": "unspecified",
                "recording_condition": "unspecified", "country": "Madagascar",
                "n_individuals": bats, "n_calls": pulses, "parameter": parameter,
                "statistic": "mean", "value": str(value), "unit": unit,
                "dispersion_type": "sd", "dispersion_value": str(sd),
                "verbatim_value": f"{value} ± {sd}", "quality_flag": "ok", "notes": note,
            })
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader(); writer.writerows(rows)
    print(f"Wrote {len(rows)} Kofoky rows")

if __name__ == "__main__":
    main()
