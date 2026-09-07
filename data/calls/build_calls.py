"""Build the browser export from per-source measurement CSVs.

Reads every data/calls/<reference_id>.csv, validates each row against the
parameter registry and the reference/method records, groups rows into
observations, and writes a display view the species card can render.

Species that have not yet been migrated to the structured format are passed
through from the legacy call_measurements.json unchanged, so the export always
covers everything the page covered before.

Run:  uv run data/calls/build_calls.py
"""
import csv
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from parameter_registry import Registry

HERE = Path(__file__).parent
DATA = HERE.parent
TAXONOMY = DATA / "chiroptera_taxonomy.json"
LEGACY = DATA / "call_measurements.json"
REFERENCES = HERE / "references.json"
OUT = HERE / "exports" / "calls.json"

# Two values of the same parameter are treated as disagreeing when their spread
# exceeds this fraction of their mean. Only ever a flag, never a filter.
DIVERGENCE_TOLERANCE = 0.15


class BuildError(Exception):
    pass


def short_label(reference_id: str, reference: dict) -> str:
    """'Seibert A-M, Koblitz JC, ... (2015) ...' -> 'Seibert et al. 2015'."""
    if reference.get("label"):
        return reference["label"]
    match = re.match(r"\s*([A-Z][A-Za-z'\-]+).*?\((\d{4})\)", reference.get("citation", ""))
    if match:
        surname, year = match.groups()
        return f"{surname} et al. {year}"
    return reference_id


def load_rows() -> list[dict]:
    rows = []
    for path in sorted(HERE.glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            for line_no, row in enumerate(csv.DictReader(handle), start=2):
                row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
                row["_source_file"] = path.name
                row["_line"] = line_no
                rows.append(row)
    return rows


def validate(rows, registry, refs, methods, taxonomy_ids) -> list[str]:
    problems = []
    statistics = set(registry.raw["statistics"])
    quality_flags = set(registry.raw["quality_flags"])

    for row in rows:
        where = f"{row['_source_file']}:{row['_line']}"
        parameter = row["parameter"]

        if parameter not in registry.parameters:
            problems.append(f"{where}: unknown parameter {parameter!r}")
            continue
        param = registry.get(parameter)

        if row["reference_id"] not in refs:
            problems.append(f"{where}: unknown reference {row['reference_id']!r}")
        if not row.get("locator"):
            problems.append(f"{where}: no locator - every value needs a place in its source")
        if row.get("method_id") and row["method_id"] not in methods:
            problems.append(f"{where}: unknown method {row['method_id']!r}")
        if row["mdd_id"] not in taxonomy_ids:
            problems.append(f"{where}: mdd_id {row['mdd_id']!r} is not in the current taxonomy")
        if row["statistic"] not in statistics:
            problems.append(f"{where}: unknown statistic {row['statistic']!r}")
        if row.get("quality_flag") and row["quality_flag"] not in quality_flags:
            problems.append(f"{where}: unknown quality_flag {row['quality_flag']!r}")

        if param["value_type"] == "numeric":
            if row["statistic"] == "range":
                if not (row["value_min"] and row["value_max"]):
                    problems.append(f"{where}: statistic 'range' needs value_min and value_max")
                    continue
                for bound in (row["value_min"], row["value_max"]):
                    problems += [f"{where}: {p}" for p in
                                 registry.validate(parameter, bound, row["unit"])]
            else:
                if not row["value"]:
                    problems.append(f"{where}: numeric parameter needs a value")
                    continue
                problems += [f"{where}: {p}" for p in
                             registry.validate(parameter, row["value"], row["unit"])]
                if row["value"] and row["verbatim_value"]:
                    # A2: the stored number must still be findable in what the source printed.
                    printed = row["verbatim_value"].replace("–", "-").replace("−", "-")
                    if not re.search(rf"(?<![\d.]){re.escape(row['value'].rstrip('0').rstrip('.'))}",
                                     printed.replace(",", "")):
                        problems.append(
                            f"{where}: value {row['value']!r} does not appear in "
                            f"verbatim_value {row['verbatim_value']!r}"
                        )
        else:
            problems += [f"{where}: {p}" for p in registry.validate(parameter, row["value"])]

    return problems


def comparability_key(row, registry, methods) -> str:
    """Values only compete when the method makes them the same quantity."""
    param = registry.get(row["parameter"])
    fields = param.get("comparability_fields")
    if not fields:
        return ""
    method = methods.get(row.get("method_id"), {})
    return "; ".join(f"{f}={method.get(f)}" for f in fields)


def basis_text(key: str) -> str:
    """'source_level_reference_distance_m=0.1; source_level_type=peak_equivalent'
    -> 'peak-equivalent at 0.1 m'."""
    if not key:
        return ""
    parts = dict(p.split("=", 1) for p in key.split("; "))
    distance = parts.get("source_level_reference_distance_m")
    kind = parts.get("source_level_type", "").replace("_", "-")
    if distance in (None, "None"):
        return f"{kind}, reference distance unstated" if kind else ""
    return f"{kind} at {distance} m".strip()


def format_value(row, registry) -> str:
    param = registry.get(row["parameter"])
    if param["value_type"] != "numeric":
        return row["value"]
    unit = param["unit"].replace("count_per_s", "/s").replace("dB_SPL", "dB")
    if row["statistic"] == "range":
        return f"{row['value_min']}–{row['value_max']} {unit}"
    text = f"{row['value']} {unit}"
    if row.get("dispersion_value"):
        text = f"{row['value']} ± {row['dispersion_value']} {unit}"
    if row["statistic"] in {"median", "approximate"}:
        text = ("~" if row["statistic"] == "approximate" else "median ") + text
    return text


def rank(row, refs) -> tuple:
    """Selection rule from the design doc, best first."""
    year = int(re.search(r"(\d{4})", row["reference_id"]).group(1)) if re.search(r"\d{4}", row["reference_id"]) else 0
    return (
        0 if row.get("quality_flag", "ok") in ("", "ok") else 1,
        0 if row.get("recording_condition") == "free_flying_wild" else 1,
        -int(row["n_calls"]) if row.get("n_calls") else 0,
        -year,
    )


def build_species(rows, registry, refs, methods) -> dict:
    observations = defaultdict(list)
    for row in rows:
        observations[row["observation_id"]].append(row)

    variants = defaultdict(list)
    for obs_rows in observations.values():
        variants[obs_rows[0].get("call_variant") or "default"].extend(obs_rows)

    variant_views = []
    for variant_id, vrows in sorted(variants.items()):
        labelled = next((r["variant_label"] for r in vrows if r.get("variant_label")), variant_id)
        by_param = defaultdict(list)
        for row in vrows:
            by_param[(row["parameter"], comparability_key(row, registry, methods))].append(row)

        facts = []
        for (parameter, ckey), prows in by_param.items():
            param = registry.get(parameter)
            prows.sort(key=lambda r: rank(r, refs))
            best = prows[0]

            numeric = []
            if param["value_type"] == "numeric":
                for r in prows:
                    if r["value"]:
                        numeric.append(float(r["value"]))
                    elif r["value_min"] and r["value_max"]:
                        # A range still carries a central tendency worth comparing.
                        numeric.append((float(r["value_min"]) + float(r["value_max"])) / 2)
            agreement = "single_source"
            if len(numeric) > 1:
                spread = (max(numeric) - min(numeric)) / (sum(numeric) / len(numeric))
                groups = {refs[r["reference_id"]].get("independence_group") for r in prows}
                if spread > DIVERGENCE_TOLERANCE:
                    agreement = "divergent" if len(groups) > 1 else "divergent_within_group"
                else:
                    agreement = "corroborated" if len(groups) > 1 else "consistent_within_group"

            facts.append({
                "parameter": parameter,
                "label": param["label"],
                "group": param["group"],
                "status": param["status"],
                "display": format_value(best, registry),
                "statistic": best["statistic"],
                "basis": basis_text(ckey),
                "n_calls": best.get("n_calls") or None,
                "quality_flag": best.get("quality_flag") or "ok",
                "ambiguity": param.get("ambiguity"),
                "citation": best["reference_id"],
                "agreement": agreement,
                "alternatives": [{
                    "display": format_value(r, registry),
                    "basis": basis_text(comparability_key(r, registry, methods)),
                    "citation": r["reference_id"],
                    "quality_flag": r.get("quality_flag") or "ok",
                    "note": r.get("notes") or "",
                } for r in prows[1:]],
                "note": best.get("notes") or "",
            })

        order = {"signal_structure": 0, "spectral": 1, "temporal": 2,
                 "amplitude": 3, "beam": 4, "auditory": 5, "covariate": 6}
        facts.sort(key=lambda f: (order.get(f["group"], 9), f["label"]))

        lookup = {f["parameter"]: f for f in facts}
        variant_views.append({
            "id": variant_id,
            "label": labelled,
            "signal_type": lookup.get("signal_type", {}).get("display"),
            "emission": lookup.get("emission", {}).get("display"),
            "direction": next((r["signal_direction"] for r in vrows if r.get("signal_direction")), None),
            "facts": [f for f in facts if f["parameter"] not in {"signal_type", "emission"}],
        })

    citations = sorted({r["reference_id"] for r in rows})
    groups = {refs[c].get("independence_group") for c in citations}
    return {
        "format": "structured",
        "evidence_scope": "species_measurement",
        "headline": headline(variant_views),
        "variants": variant_views,
        "n_observations": len(observations),
        "n_sources": len(citations),
        "n_independent_groups": len(groups),
        "citations": citations,
    }


def headline(variants) -> str:
    """Generated from stored measurements only - never hand-written (A6)."""
    parts = []
    for variant in variants:
        lookup = {f["parameter"]: f["display"] for f in variant["facts"]}
        bits = []
        if "peak_frequency" in lookup:
            bits.append(f"peaks at {lookup['peak_frequency']}")
        if "duration" in lookup:
            bits.append(f"over {lookup['duration']}")
        route = variant.get("emission")
        label = variant["label"].split(" (")[0]
        descriptor = f"{label}"
        if route:
            descriptor += f" ({route}{', ' + variant['direction'] if variant.get('direction') else ''})"
        parts.append(f"{descriptor} {' '.join(bits)}".strip())
    if len(parts) > 1:
        return f"Alternates {len(parts)} search-call types — " + "; ".join(parts) + "."
    return (parts[0] + ".") if parts else ""


def main() -> None:
    registry = Registry()
    problems = registry.check()
    if problems:
        raise BuildError("parameter registry is invalid: " + "; ".join(problems))

    ref_file = json.loads(REFERENCES.read_text(encoding="utf-8"))
    refs, methods = ref_file["references"], ref_file["methods"]
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    taxonomy_ids = {s["id"] for s in taxonomy["species"]}

    rows = load_rows()
    issues = validate(rows, registry, refs, methods, taxonomy_ids)
    if issues:
        for issue in issues:
            print(f"  ! {issue}")
        raise BuildError(f"{len(issues)} validation problem(s); nothing written")

    by_species = defaultdict(list)
    for row in rows:
        by_species[row["mdd_id"]].append(row)

    legacy = json.loads(LEGACY.read_text(encoding="utf-8"))
    export_refs = {rid: {"label": short_label(rid, r), "url": r.get("url", "")}
                   for rid, r in refs.items()}
    for rid, r in legacy["references"].items():
        export_refs.setdefault(rid, r)

    species = {}
    for mdd_id, entry in legacy["species"].items():
        species[mdd_id] = {"format": "legacy", **entry}
    for mdd_id, srows in by_species.items():
        species[mdd_id] = build_species(srows, registry, refs, methods)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "version": 2,
        "generated_on": date.today().isoformat(),
        "references": export_refs,
        "species": species,
    }, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")

    structured = sum(1 for s in species.values() if s["format"] == "structured")
    total = len(taxonomy["species"])
    print(f"Validated {len(rows)} measurement rows from {len({r['_source_file'] for r in rows})} source file(s)")
    print(f"Wrote {OUT.relative_to(DATA.parent)}")
    print(f"  {structured} species structured, {len(species) - structured} legacy, "
          f"{total - len(species)} with no call data ({len(species) / total:.1%} coverage)")


if __name__ == "__main__":
    main()
