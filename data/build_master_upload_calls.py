"""Import measurements from the consolidated upload archive (files4.zip).

The archive's `MASTER_call_records.csv` merges the 43 batch worksheets that the
earlier per-batch importer read one at a time, so this supersedes
``import_echolocation_upload.py`` for every source they share.

What it will not do:

- It will not overwrite a CSV built from the primary source. Five references
  (Webala, Taylor-Boyd, Bakwo Fils, Pennay/Law/Reinhold and Seibert) plus the
  South Asia review were transcribed by hand with real locators -- "Table 2,
  Doryrhina camerunensis, Kakamega forest, hand-held female" -- against a cached
  and hashed PDF. The master's locator is a worksheet record id. Replacing the
  first with the second would be a downgrade, so those rows are written to a
  review file for a human merge instead.
- It will not invent a citation. Eleven sources whose provenance the archive
  itself flags as unresolved are refused; see `UNRESOLVED_CITATION`.

Run: ``uv run data/build_master_upload_calls.py``.
"""
import csv
import hashlib
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from call_import_lib import TaxonResolver, write_rows
from master_upload_lib import (CONTEXT, METHODS, TRAITS, UNRESOLVED_CITATION,
                               admits, reference_for)

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "data" / "echolocation" / "files4.zip"
CALLS = ROOT / "data" / "calls"
REVIEW = CALLS / "unresolved" / "master-upload-deferred.json"

# References whose CSV is built from the primary source and must not be
# replaced by worksheet-level rows. Their master rows go to the review file.
CURATED_ELSEWHERE = {
    "srinivasulu-2025-southasia", "webala-2019", "taylor-boyd-2025",
    "bakwo-fils-2018", "pennay-law-reinhold-2004-nsw", "seibert-2015",
}

UNITS = {
    "peak_frequency": "kHz", "characteristic_frequency": "kHz",
    "start_frequency": "kHz", "end_frequency": "kHz", "min_frequency": "kHz",
    "max_frequency": "kHz", "bandwidth": "kHz", "knee_frequency": "kHz",
    "cf_frequency": "kHz", "resting_frequency": "kHz",
    "total_slope": "kHz/ms", "duration": "ms", "inter_pulse_interval": "ms",
    "duty_cycle": "percent", "detection_distance": "m",
    "beam_half_angle": "degrees", "harmonic_emphasis": "count",
    "signal_type": "",
}


def signal_type(printed: str) -> str | None:
    folded = printed.strip().lower()
    if "click" in folded:
        return "broadband_click"
    if "cf-fm" in folded or "cf/fm" in folded:
        return "CF-FM"
    if "fm-qcf" in folded or "fm/qcf" in folded:
        return "FM-QCF"
    if "qcf" in folded:
        return "QCF"
    if folded.startswith("fm") or "fm " in folded or folded == "fm":
        return "FM"
    if folded in {"cf", "constant frequency"}:
        return "CF"
    return None


def batch_key(row) -> tuple:
    """Join key between a master row and the batch worksheet it came from."""
    return ((row.get("sci_name") or "").strip().lower(),
            (row.get("trait") or "").strip(),
            (row.get("value") or "").strip(),
            (row.get("value_min") or "").strip(),
            (row.get("unit") or "").strip())


def phase(printed: str) -> str:
    """Only the registry's own call phases are accepted.

    One batch records 'release' in this column, which is a recording context and
    not a phase; the context is already carried by recording_condition, so it
    must not be smuggled in here as though it described the call.
    """
    value = (printed or "").strip().lower()
    return value if value in {"search", "approach", "terminal_buzz", "social",
                              "distress"} else "unspecified"


def number(value: str) -> str:
    value = (value or "").strip().replace(",", ".")
    try:
        return f"{float(value):g}"
    except ValueError:
        return ""


def statistic_of(row) -> tuple[str, str, str]:
    """Return (statistic, dispersion_type, dispersion_value) for one master row.

    The archive uses `dispersion_type` for two different things: a real SD or SE
    with a number beside it, and a printed interval such as "53-60" that is not
    a dispersion at all. Only the first becomes a dispersion here; the interval
    is preserved in the verbatim value instead of being parsed into one.
    """
    kind = (row["dispersion_type"] or "").strip()
    disp = number(row["dispersion_value"])
    if row["value_type"] == "range":
        return "range", "", ""
    if kind == "SD" and disp:
        return "mean", "sd", disp
    if kind == "SE" and disp:
        return "mean", "se", disp
    if kind == "median_and_range":
        return "median", "", ""
    if kind in {"SD_interval", "SD_from_mean_interval", "range"}:
        # A mean whose spread the source printed as an interval.
        return "mean", "", ""
    # A single per-species value whose statistic the source never names.
    return "species_summary", "", ""


def verbatim_of(row) -> str:
    parts = [p for p in (row["value"], row["value_min"] and row["value_max"]
                         and f"{row['value_min']}-{row['value_max']}") if p]
    printed = " ".join(parts)
    disp = (row["dispersion_value"] or "").strip()
    if disp and not number(disp):
        printed = f"{printed} ({disp})".strip()
    elif disp:
        printed = f"{printed} +/- {disp}".strip()
    return printed


def main() -> None:
    archive_hash = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    with zipfile.ZipFile(ARCHIVE) as z:
        def table(name):
            with z.open(name) as raw:
                return list(csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")))
        master = table("MASTER_call_records.csv")
        sources = {r["source_key"]: r for r in table("MASTER_sources.csv")}
        # The consolidation dropped call_phase and locality, which seven of the
        # original batch worksheets still carry, and it reassigned record ids, so
        # the two cannot be joined on id. Match on the value itself instead:
        # species, trait, value and lower bound together identify a row closely
        # enough, and a wrong match could only move a phase between two rows that
        # report the same number for the same trait in the same species.
        batch_extra = {}
        for name in z.namelist():
            if not name.endswith("_records.csv"):
                continue
            for row in table(name):
                if not (row.get("call_phase") or row.get("locality")
                        or row.get("call_type_variant")):
                    continue
                batch_extra.setdefault(batch_key(row), row)

    resolver = TaxonResolver()
    output = defaultdict(list)
    deferred, refused, unresolved_taxa = defaultdict(list), defaultdict(int), []
    skipped = defaultdict(int)

    for row in master:
        good, why = admits(row, sources)
        if not good:
            skipped[why] += 1
            continue
        key = row["source_key"]
        if key in UNRESOLVED_CITATION:
            refused[key] += 1
            continue
        reference_id = reference_for(key)
        if reference_id is None:
            skipped["no_reference_mapping"] += 1
            continue

        parameter = TRAITS[row["trait"]]
        value, low, high = (number(row["value"]), number(row["value_min"]),
                            number(row["value_max"]))
        if parameter == "signal_type":
            coded = signal_type(row["value"])
            if not coded:
                skipped["signal_type_unrecognised"] += 1
                continue
            value, low, high = coded, "", ""
            stat, disp_type, disp = "single", "", ""
        else:
            stat, disp_type, disp = statistic_of(row)
            if stat == "range":
                if not (low and high):
                    skipped["range_without_bounds"] += 1
                    continue
                value = ""
            elif not value:
                skipped["no_value"] += 1
                continue

        species, method = resolver.resolve(row["binomial_for_join"])
        if species is None:
            unresolved_taxa.append((row["binomial_for_join"], row["record_id"]))
            continue

        harmonic = (row["harmonic_n"] or "").strip()
        # A named signal type within a phase; the consolidation dropped it, so it
        # comes back from the batch worksheet alongside the call phase.
        variant = (batch_extra.get(batch_key(row), {}).get("call_type_variant") or "").strip()
        record = {
            "observation_id": "mst-" + hashlib.sha1(
                "|".join((reference_id, row["record_id"], row["binomial_for_join"],
                          row["context_class"], harmonic, variant)).encode()).hexdigest()[:14],
            "mdd_id": species["id"],
            "verbatim_taxon_name": row["sci_name"] or row["binomial_for_join"],
            "taxon_match_method": method,
            "reference_id": reference_id,
            "locator": f"supplied worksheet record {row['record_id']} ({row['region_batch']})",
            "method_id": METHODS.get(reference_id, ""),
            "call_phase": phase(batch_extra.get(batch_key(row), {}).get("call_phase", "")),
            "call_variant": variant, "variant_label": variant, "signal_direction": "",
            "recording_condition": CONTEXT.get(row["context_class"], "unspecified"),
            "habitat_class": "",
            "country": row["country_region"],
            "locality": (batch_extra.get(batch_key(row), {}).get("locality") or "").strip(),
            "date_or_season": "",
            "n_individuals": number(row["n_individuals"]),
            "n_calls": number(row["n_calls"]),
            "parameter": parameter, "statistic": stat,
            "value": value, "value_min": low if stat == "range" else "",
            "value_max": high if stat == "range" else "",
            "unit": UNITS[parameter],
            "dispersion_type": disp_type, "dispersion_value": disp,
            "harmonic": harmonic if harmonic.isdigit() else "",
            "verbatim_value": verbatim_of(row) or value,
            "quality_flag": "ok" if (disp_type or parameter == "signal_type")
                            else "definition_unstated",
            "notes": (f"Imported from MASTER_call_records.csv record {row['record_id']}; "
                      f"upload archive sha256 {archive_hash}. "
                      + (row["notes"] or "").strip()),
        }
        if reference_id in CURATED_ELSEWHERE:
            deferred[reference_id].append(record)
            continue
        output[reference_id].append(record)

    for reference_id, rows in sorted(output.items()):
        rows.sort(key=lambda r: (r["mdd_id"], r["observation_id"], r["parameter"]))
        write_rows(reference_id, rows)

    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    REVIEW.write_text(json.dumps({
        "why": "These master rows belong to references whose CSV is transcribed from "
               "the primary source with real locators. Merging them needs a human to "
               "supply the locator, so they are held here rather than overwriting "
               "better provenance.",
        "archive_sha256": archive_hash,
        "deferred_rows": {k: len(v) for k, v in sorted(deferred.items())},
        "refused_unresolved_citation": {k: {"rows": n, "why": UNRESOLVED_CITATION[k]}
                                        for k, n in sorted(refused.items())},
        "unresolved_taxa": sorted({name for name, _ in unresolved_taxa}),
        "rows": {k: v for k, v in sorted(deferred.items())},
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    written = sum(len(v) for v in output.values())
    print(f"master upload: wrote {written} rows across {len(output)} references")
    print(f"  deferred to curated importers: {sum(len(v) for v in deferred.values())} rows "
          f"in {len(deferred)} references")
    print(f"  refused, citation unresolved: {sum(refused.values())} rows in {len(refused)} sources")
    print(f"  taxa unresolved: {len({n for n, _ in unresolved_taxa})} names, {len(unresolved_taxa)} rows")
    for why, n in sorted(skipped.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  skipped {why}: {n}")


if __name__ == "__main__":
    main()
