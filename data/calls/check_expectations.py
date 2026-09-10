"""Check measured values against family and species expectations.

Two expectation files sit alongside the measurement CSVs:

- family_call_defaults.csv  — one row per family
- expected_ranges.csv       — species-level entries migrated from the retired
                              echolocation_reference.json genusExamples

Both are inference from standard comparative reviews, not measurements. They
are never displayed as data and never enter the export. Their job is to catch
import errors: a measured value falling well outside its family's expected
range is usually a transcription slip, a harmonic confusion, or a taxon
mismatch, and is worth a human look.

The check only ever warns. An expectation is a weaker claim than a measurement,
so a conflict means "look at this", not "the measurement is wrong" — sometimes
the expectation is the thing that is wrong.

Run:  uv run data/calls/check_expectations.py
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE.parent
FAMILY_DEFAULTS = HERE / "family_call_defaults.csv"
EXPECTED_RANGES = HERE / "expected_ranges.csv"
EXPORT = HERE / "exports" / "calls.json"
REPORT = HERE / "checks" / "out-of-range.md"

# A value must miss the expected range by more than this fraction of the range
# before it is reported, so that boundary cases do not drown the real signal.
TOLERANCE = 0.10


def load_expectations() -> tuple[dict, dict]:
    families, species = {}, {}
    if FAMILY_DEFAULTS.exists():
        for row in csv.DictReader(FAMILY_DEFAULTS.open(encoding="utf-8")):
            families[row["family"]] = (
                float(row["peak_freq_kHz_low"]), float(row["peak_freq_kHz_high"]),
                row.get("freq_range_confidence", ""))
    if EXPECTED_RANGES.exists():
        for row in csv.DictReader(EXPECTED_RANGES.open(encoding="utf-8")):
            species[row["taxon"]] = (
                float(row["peak_freq_kHz_low"]), float(row["peak_freq_kHz_high"]),
                row.get("confidence", ""))
    return families, species


# A single printed value ("45 kHz") is a nominal centre, not bounds, so it is
# given a proportional band instead of being treated as a zero-width range.
NOMINAL_BAND = 0.15


def harmonic_explains(value: float, harmonic, low: float, high: float) -> str:
    """Return the harmonic that would put this value in range, if one would.

    A family's expected peak-frequency band is drawn from whichever harmonic the
    comparative literature usually reports -- for most families the dominant one.
    A value this project stores against the fundamental is then out of band by
    construction, not by error. If rescaling to another harmonic lands inside the
    band, the mismatch is arithmetic rather than suspect, and saying so is more
    useful than a warning the reader has to re-derive every time.
    """
    if not harmonic:
        return ""
    stated = int(harmonic)
    for other in (1, 2, 3, 4):
        if other != stated and not outside(value * other / stated, low, high):
            return f"h{other}"
    return ""


def outside(value: float, low: float, high: float) -> bool:
    if high == low:
        slack = low * NOMINAL_BAND
    else:
        slack = max((high - low) * TOLERANCE, 0.5)
    return value < low - slack or value > high + slack


def main() -> None:
    taxonomy = json.loads((DATA / "chiroptera_taxonomy.json").read_text(encoding="utf-8"))
    info = {s["id"]: (s.get("family"), s["sciName"].replace("_", " "))
            for s in taxonomy["species"]}
    export = json.loads(EXPORT.read_text(encoding="utf-8"))
    families, species = load_expectations()

    findings = []
    checked = 0
    for mdd_id, record in export["species"].items():
        family, name = info.get(mdd_id, (None, mdd_id))
        for variant in record.get("variants", []):
            for fact in variant["facts"]:
                if fact["parameter"] != "peak_frequency" or fact.get("value_num") is None:
                    continue
                value = fact["value_num"]
                checked += 1
                for scope, expectation in (("species", species.get(name)),
                                           ("family", families.get(family))):
                    if not expectation:
                        continue
                    low, high, confidence = expectation
                    if outside(value, low, high):
                        harmonic = fact.get("harmonic")
                        findings.append({
                            "name": name, "family": family, "value": value,
                            "low": low, "high": high, "scope": scope,
                            "confidence": confidence, "citation": fact["citation"],
                            "harmonic": harmonic,
                            "explained_by": harmonic_explains(value, harmonic, low, high),
                        })
                        break  # species expectation is the tighter claim; report once

    findings.sort(key=lambda f: -abs(f["value"] - (f["low"] + f["high"]) / 2))
    explained = [f for f in findings if f["explained_by"]]
    findings = [f for f in findings if not f["explained_by"]]

    def harmonic_note(f) -> str:
        return f" [on h{f['harmonic']}]" if f.get("harmonic") else ""

    print(f"Checked {checked} peak-frequency values against "
          f"{len(families)} family and {len(species)} species expectations")
    if explained:
        print(f"  {len(explained)} value(s) outside expectation only because of the "
              f"harmonic they were measured on:")
        for f in explained:
            print(f"    {f['name']:30} {f['value']:7.1f} kHz on h{f['harmonic']} "
                  f"vs {f['scope']} {f['low']:.0f}-{f['high']:.0f}; "
                  f"in range as {f['explained_by']}  ({f['citation']})")
    if not findings:
        print("  nothing outside expectation")
        if REPORT.exists():
            REPORT.unlink()
        return

    print(f"  {len(findings)} value(s) outside expectation:")
    for f in findings:
        print(f"    {f['name']:30} {f['value']:7.1f} kHz{harmonic_note(f)}  vs {f['scope']} "
              f"{f['low']:.0f}-{f['high']:.0f} [{f['confidence']}]  ({f['citation']})")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Measured values outside expectation",
        "",
        "Generated by `data/calls/check_expectations.py`. Expectations are inference",
        "from comparative reviews, not measurements, so a row here means *look at",
        "this*, not *the measurement is wrong*. Either side can be the error.",
        "",
        f"{len(findings)} of {checked} peak-frequency values are outside their",
        f"expected range by more than {TOLERANCE:.0%} of the range width.",
        "",
        "| Species | Family | Measured | Harmonic | Expected | Scope | Confidence | Source |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    lines += [
        f"| {f['name']} | {f['family']} | {f['value']:.1f} kHz | "
        f"{('h' + f['harmonic']) if f.get('harmonic') else 'unstated'} | "
        f"{f['low']:.0f}–{f['high']:.0f} kHz | {f['scope']} | {f['confidence']} | {f['citation']} |"
        for f in findings
    ]
    if explained:
        lines += [
            "",
            "## Explained by the harmonic measured",
            "",
            "These sit outside the expected band only because the value is stored against",
            "a harmonic other than the one the band describes. Rescaling puts each back in",
            "range, so they are arithmetic, not anomalies.",
            "",
            "| Species | Family | Measured | Harmonic | Expected | In range as | Source |",
            "|---|---|---:|---|---|---|---|",
        ]
        lines += [
            f"| {f['name']} | {f['family']} | {f['value']:.1f} kHz | h{f['harmonic']} | "
            f"{f['low']:.0f}–{f['high']:.0f} kHz | {f['explained_by']} | {f['citation']} |"
            for f in explained
        ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  -> {REPORT.relative_to(DATA.parent)}")


if __name__ == "__main__":
    main()
