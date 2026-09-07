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
from collections import Counter, defaultdict
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
    """Citation -> author-year label, using the convention readers expect.

    One author 'Collen 2012'; two 'Schnitzler & Kalko 2001'; three or more
    'Seibert et al. 2015'. Calling a two-author paper 'et al.' is simply wrong,
    and these labels are what the card shows.
    """
    if reference.get("label"):
        return reference["label"]
    citation = reference.get("citation", "")
    match = re.match(r"\s*(.+?)\s*\((\d{4})\)", citation)
    if not match:
        return reference_id
    authors_text, year = match.groups()

    def is_surname(word: str) -> bool:
        # Unicode-aware: "Flückiger" and "Mohl" are both surnames.
        return (len(word) > 1 and word[:1].isupper()
                and all(c.isalpha() or c in "'-" for c in word))

    # "Schnitzler H-U, Kalko EKV" -> ["Schnitzler", "Kalko"]. A nobiliary
    # particle ("von Helversen") still names an author, so scan the whole part
    # rather than only its first word.
    surnames = []
    for part in authors_text.split(","):
        words = part.strip().split()
        surname = next((w for w in words if is_surname(w)), None)
        if surname:
            surnames.append(surname)
    if not surnames:
        return reference_id
    # A citation already written "Foley NM et al." names more authors than it lists.
    if "et al" in authors_text.lower() or len(surnames) > 2:
        return f"{surnames[0]} et al. {year}"
    if len(surnames) == 2:
        return f"{surnames[0]} & {surnames[1]} {year}"
    return f"{surnames[0]} {year}"


def load_rows(reference_ids: set[str]) -> tuple[list[dict], list[str]]:
    """Load the measurement CSVs, which are the ones named after a reference.

    Only a file whose stem is a known reference_id is a measurement source, so
    other CSVs in this directory (family-level defaults, working notes) are
    skipped and named rather than parsed as measurements and crashing the build.
    """
    rows, skipped = [], []
    for path in sorted(HERE.glob("*.csv")):
        if path.stem not in reference_ids:
            skipped.append(path.name)
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = {"parameter", "reference_id", "mdd_id"} - set(reader.fieldnames or [])
            if missing:
                raise BuildError(
                    f"{path.name} is named after a reference but is missing "
                    f"required column(s): {', '.join(sorted(missing))}"
                )
            for line_no, row in enumerate(reader, start=2):
                row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
                row["_source_file"] = path.name
                row["_line"] = line_no
                rows.append(row)
    return rows, skipped


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
                    # A2: the stored number must still be findable in what the
                    # source printed. Compared numerically, not textually, so
                    # that a source printing European decimal commas ("4,3")
                    # still validates against a stored 4.3.
                    printed = row["verbatim_value"].replace("–", "-").replace("−", "-")
                    printed = re.sub(r"(?<=\d),(?=\d)", ".", printed)
                    printed_numbers = [float(n) for n in
                                       re.findall(r"\d+(?:\.\d+)?", printed)]
                    if not any(abs(n - float(row["value"])) < 1e-9 for n in printed_numbers):
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
    has_named = any(key != "default" for key in variants)

    variant_views = []
    # Named call types first; anything unattributed to one comes last.
    for variant_id, vrows in sorted(variants.items(), key=lambda kv: (kv[0] == "default", kv[0])):
        labelled = next((r["variant_label"] for r in vrows if r.get("variant_label")), None)
        if not labelled:
            phases = {r.get("call_phase") for r in vrows} - {"", "unspecified", None}
            if variant_id == "default" and has_named:
                # A whole-species aggregate is not a third call type: a
                # comparative table that never distinguished the alternating
                # signals must not be displayed as though it had.
                labelled = "Not attributed to a call type"
            elif phases:
                labelled = f"{sorted(phases)[0].replace('_', ' ').capitalize()} call"
            else:
                labelled = "Call, phase unspecified"
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
                "value_num": numeric[0] if numeric else None,
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
            "overview": overview(lookup),
            "is_named": variant_id != "default",
            "facts": [f for f in facts if f["parameter"] not in {"signal_type", "emission"}],
        })

    reference_order = index_references(variant_views)

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
        "reference_order": reference_order,
        "density": density(rows, methods, len(groups)),
    }


FAMILY_DEFAULTS = HERE / "family_call_defaults.csv"
FAMILY_REFERENCES = HERE / "family_references.json"

# A family range this many times wider than its low bound tells a reader almost
# nothing about an individual species, and the card says so outright.
UNINFORMATIVE_SPAN = 3.0


GENUS_DEFAULTS = HERE / "genus_call_defaults.csv"


def inference_row(row: dict, scope: str, references: dict) -> dict:
    """Shape one family or genus row into the record the card renders."""
    low, high = float(row["peak_freq_kHz_low"]), float(row["peak_freq_kHz_high"])
    mode = row.get("echolocation_mode") or (
        "laryngeal" if row.get("laryngeal_echolocation", "").lower() == "yes" else "none")
    cited = [r for r in (row.get("reference_ids") or "").split(";") if r and r != "none"]

    warnings = []
    # The "does not echolocate" case is stated in the card's opening sentence,
    # so repeating it as a warning is noise.
    if mode == "non_laryngeal_clicks":
        warnings.append("Clicks are broadband, so a peak-frequency range describes "
                        "them poorly and is not comparable with a laryngeal call.")
    if mode != "none":
        if high / low >= UNINFORMATIVE_SPAN:
            warnings.append(f"This {scope}'s range spans {high / low:.0f}x, so it does not "
                            "usefully constrain any individual species.")
        if not cited:
            warnings.append(f"No identifiable published source for this {scope}'s range.")
        if row.get("freq_range_confidence") == "poorly_constrained":
            warnings.append(f"The {scope} range itself is poorly constrained.")

    return {
        "scope": scope,
        "taxon": row.get("family") if scope == "family" else row.get("genus"),
        "mode": mode,
        "show_range": mode != "none",
        "low": low,
        "high": high,
        "confidence": row.get("freq_range_confidence", ""),
        # A taxon that does not echolocate has no emission route and no duty
        # cycle. The family row carries Rousettus's values, which must not be
        # shown on a Pteropus card.
        "emission": row.get("emission_route", "") if mode != "none" else "",
        "duty_cycle": (row.get("duty_cycle_class", "")
                       if mode != "none"
                       and row.get("propagate_duty_cycle", "yes") == "yes"
                       and row.get("duty_cycle_class") != "not_applicable" else ""),
        "structure": row.get("call_structure", ""),
        "documentation": row.get("family_documentation_status", ""),
        "reason": row.get("notes", ""),
        "warnings": warnings,
        "verified": bool(row.get("verified_by")),
        "citations": [{
            "id": r,
            "label": short_label(r, references.get(r, {})),
            "citation": references.get(r, {}).get("citation", r),
            "url": references.get(r, {}).get("url"),
            "doi_verified": references.get(r, {}).get("doi_verified", False),
        } for r in cited],
    }


MIN_CONGENERS = 3


def derive_genus_expectations(species: dict, taxonomy: list) -> dict:
    """Genus expectations computed from the congeners we have actually measured.

    A family default is often useless for an individual species: Vespertilionidae
    spans 16x, and a Kerivoula sits at the top of it. The species we have already
    measured are a much tighter and — unlike a review consensus — a fully sourced
    guide, because every contributing value carries its own citation.

    This is an observed spread, not a prediction interval: an unmeasured species
    can fall outside it, and the card says so.
    """
    genus_of = {s["id"]: s.get("genus") for s in taxonomy}
    observed = defaultdict(list)
    for mdd_id, record in species.items():
        genus = genus_of.get(mdd_id)
        if not genus or record.get("format") != "structured":
            continue
        for variant in record.get("variants", []):
            for fact in variant["facts"]:
                if fact["parameter"] == "peak_frequency" and fact.get("value_num") is not None:
                    observed[genus].append((fact["value_num"], fact["citation"]))
                    break
            else:
                continue
            break

    derived = {}
    for genus, entries in observed.items():
        if len(entries) < MIN_CONGENERS:
            continue
        values = [v for v, _ in entries]
        sources = sorted({c for _, c in entries})
        low, high = min(values), max(values)
        warnings = [
            f"Observed across the {len(values)} measured species of {genus} in this "
            "dataset. It is the spread of what has been measured, not a prediction: "
            "an unmeasured species can fall outside it."
        ]
        if high / low >= UNINFORMATIVE_SPAN:
            warnings.append(f"Even within {genus} the measured spread is {high / low:.0f}x, "
                            "so it constrains an individual species only loosely.")
        derived[genus] = {
            "scope": "genus", "taxon": genus, "mode": "laryngeal", "derived": True,
            "show_range": True, "low": round(low, 1), "high": round(high, 1),
            "n_species": len(values),
            "confidence": "measured_congeners", "emission": "", "duty_cycle": "",
            "structure": "", "documentation": "",
            "reason": (f"No published genus-level range was used. These bounds are the lowest "
                       f"and highest peak frequencies measured across {len(values)} species of "
                       f"{genus} already in this dataset."),
            "warnings": warnings, "verified": False,
            "citations": [{"id": s, "label": s, "citation": s, "url": None,
                           "doi_verified": True} for s in sources],
        }
    return derived


def build_genus_inference() -> dict:
    """Genus-level expectations, which override the family where they exist.

    A family default is often too broad to say anything (Vespertilionidae spans
    16x). A genus default can be far tighter, and in Pteropodidae it carries a
    qualitative distinction the family cannot: Rousettus echolocates with tongue
    clicks while the other 45 genera do not echolocate at all.
    """
    if not GENUS_DEFAULTS.exists():
        return {}
    references = json.loads(FAMILY_REFERENCES.read_text(encoding="utf-8"))["references"]
    return {row["genus"]: inference_row(row, "genus", references)
            for row in csv.DictReader(GENUS_DEFAULTS.open(encoding="utf-8"))}


def build_family_inference() -> dict:
    """Family-level expectations, used where no genus-level row exists.

    Inference from comparative reviews, not measurement, and labelled as such
    everywhere it appears. Every entry carries the stated reason the taxon is
    expected to fall in that range, the sources behind it, and warnings
    generated from the data rather than written by hand.
    """
    if not FAMILY_DEFAULTS.exists():
        return {}
    references = json.loads(FAMILY_REFERENCES.read_text(encoding="utf-8"))["references"]
    return {row["family"]: inference_row(row, "family", references)
            for row in csv.DictReader(FAMILY_DEFAULTS.open(encoding="utf-8"))}


def is_stated(value) -> bool:
    """Method fields record ignorance explicitly, so 'unstated in abstract' and
    friends count as absent rather than as a recorded value."""
    if value in (None, "", "NA"):
        return False
    return "unstated" not in str(value).lower()


def density(rows, methods, n_groups: int) -> dict:
    """How much evidence stands behind a card.

    A Castro-style comparative row and the barbastellus workup are both
    'species measurements', but one is five bare numbers and the other is
    27 rows with dispersion, sample sizes and method. Without a marker the
    thin card looks like the rich card is broken. The level is derived from
    named components, and the components travel with it, so the card can say
    exactly what is missing rather than showing a mystery score.
    """
    parameters = {r["parameter"] for r in rows}
    has_phase = any(r.get("call_phase") and r["call_phase"] != "unspecified" for r in rows)
    has_condition = any(r.get("recording_condition") for r in rows)
    has_sample_size = any(r.get("n_calls") or r.get("n_individuals") for r in rows)
    has_dispersion = any(r.get("dispersion_value") for r in rows)

    method_ids = {r.get("method_id") for r in rows if r.get("method_id")}
    stated = sum(1 for mid in method_ids
                 for key, value in methods.get(mid, {}).items()
                 if key not in ("reference_id", "notes") and is_stated(value))
    has_method = stated > 0

    context = has_phase and has_condition
    if len(parameters) >= 6 and has_dispersion and has_sample_size and context \
            and (has_method or n_groups > 1):
        level = "rich"
    elif len(parameters) >= 4 and (has_dispersion or has_sample_size) and context:
        level = "detailed"
    elif len(parameters) >= 3 and context:
        level = "basic"
    else:
        level = "minimal"

    have, missing = [], []
    (have if has_phase else missing).append("call phase")
    (have if has_condition else missing).append("recording condition")
    (have if has_sample_size else missing).append("sample size")
    (have if has_dispersion else missing).append("dispersion")
    (have if has_method else missing).append("recording method")
    (have if n_groups > 1 else missing).append("independent corroboration")

    return {
        "level": level,
        "rank": ["minimal", "basic", "detailed", "rich"].index(level) + 1,
        "parameters": len(parameters),
        "have": have,
        "missing": missing,
    }


def overview(lookup: dict) -> dict:
    """The collapsed one-line summary: frequency span and peak.

    Span prefers explicit min/max frequency; where a source only reports the
    endpoints of a sweep those are used instead, and derived_from says so, so
    the card never implies a measurement that was not made.
    """
    explicit = [p for p in ("min_frequency", "max_frequency") if p in lookup]
    endpoints = [p for p in ("end_frequency", "start_frequency") if p in lookup]
    used = explicit if len(explicit) == 2 else (endpoints if len(endpoints) == 2 else explicit + endpoints)
    values = [lookup[p]["value_num"] for p in used if lookup[p].get("value_num") is not None]

    result = {"low": None, "high": None, "peak": None, "derived_from": None}
    if len(values) >= 2:
        result["low"], result["high"] = min(values), max(values)
        result["derived_from"] = ("min/max frequency" if used == explicit
                                  else "sweep start and end frequency")
    peak = lookup.get("peak_frequency") or lookup.get("characteristic_frequency")
    if peak and peak.get("value_num") is not None:
        result["peak"] = peak["value_num"]
        result["peak_label"] = peak["label"]
    return result


def index_references(variants) -> None:
    """Number the citations in order of first appearance, so the card can carry
    a superscript marker per value and one reference list underneath."""
    order: list[str] = []

    def index_of(citation: str) -> int:
        if citation not in order:
            order.append(citation)
        return order.index(citation) + 1

    for variant in variants:
        for fact in variant["facts"]:
            fact["ref_index"] = index_of(fact["citation"])
            for alternative in fact.get("alternatives", []):
                alternative["ref_index"] = index_of(alternative["citation"])
    return order


def headline(variants) -> str:
    """One orienting sentence, generated from stored values only (A6).

    Deliberately carries no numbers: the collapsed variant rows already show
    frequency span and peak, so repeating them here is duplication rather than
    orientation.
    """
    if not variants:
        return ""
    # Only distinguished call types count towards alternation; a species-level
    # aggregate row is not one of them.
    named = [v for v in variants if v.get("is_named")]
    if len(named) > 1:
        # Each variant row shows its own route and direction; what the rows
        # cannot show is the contrast between them, so that is the headline.
        routes = {v.get("emission") for v in named if v.get("emission")}
        directions = {v.get("direction") for v in named if v.get("direction")}
        contrasts = []
        if len(routes) > 1:
            contrasts.append("different routes")
        if len(directions) > 1:
            contrasts.append("different directions")
        tail = f", emitted through {' and aimed in '.join(contrasts)}" if contrasts else ""
        return f"Alternates {len(named)} search-call types{tail}."
    routes = {"oral": "emitted through the mouth",
              "nasal": "emitted through the nose",
              "tongue_click": "produced with the tongue"}
    only = variants[0]
    signal = only.get("signal_type") or "Echolocation"
    route = routes.get(only.get("emission"))
    # The label already carries the phase, or says it is unspecified; do not
    # assert "search call" for a source that never said so.
    subject = only["label"][0].lower() + only["label"][1:]
    return f"{signal} {subject}{f', {route}' if route else ''}."


def main() -> None:
    registry = Registry()
    problems = registry.check()
    if problems:
        raise BuildError("parameter registry is invalid: " + "; ".join(problems))

    ref_file = json.loads(REFERENCES.read_text(encoding="utf-8"))
    refs, methods = ref_file["references"], ref_file["methods"]
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    taxonomy_ids = {s["id"] for s in taxonomy["species"]}

    rows, skipped = load_rows(set(refs))
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
        # A prose summary carries no phase, sample size, dispersion or method,
        # so it is minimal by construction until it is migrated.
        species[mdd_id] = {"format": "legacy", **entry, "density": {
            "level": "minimal", "rank": 1, "parameters": None,
            "have": [], "missing": ["structured measurements"],
        }}

    shadowed = []
    for mdd_id, srows in by_species.items():
        record = build_species(srows, registry, refs, methods)
        # A4: importing a broad source must not silently delete a narrower one.
        # Where a legacy entry cites a reference the structured rows do not, it
        # is carried through visibly and listed for migration rather than lost.
        previous = species.get(mdd_id)
        if previous and previous["format"] == "legacy" \
                and previous.get("reference") not in record["citations"]:
            record["unmigrated"] = {
                "summary": previous.get("summary"),
                "context": previous.get("context"),
                "reference": previous.get("reference"),
            }
            shadowed.append((mdd_id, previous.get("reference")))
        species[mdd_id] = record

    # Family inference is emitted once, keyed by family, and the page applies it
    # to species with no measurement. Keeping it out of the per-species records
    # keeps it structurally impossible to mistake for a measurement, and keeps
    # the export from growing by 1,190 copies of the same paragraph.
    inference = build_family_inference()
    # Hand-written genus rows win over derived ones: they carry qualitative
    # facts (Rousettus clicks) that measured congeners cannot supply.
    genus_inference = derive_genus_expectations(species, taxonomy["species"])
    for entry in genus_inference.values():
        # Derived entries cite the measurement sources by id; give them the same
        # author-year labels the measurement cards use.
        for citation in entry["citations"]:
            reference = refs.get(citation["id"]) or legacy["references"].get(citation["id"], {})
            citation["label"] = short_label(citation["id"], reference)
            citation["citation"] = reference.get("citation", citation["id"])
            citation["url"] = reference.get("url")
    genus_inference.update(build_genus_inference())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "version": 3,
        "generated_on": date.today().isoformat(),
        "references": export_refs,
        "familyInference": inference,
        "genusInference": genus_inference,
        "species": species,
    }, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")

    structured = sum(1 for s in species.values() if s["format"] == "structured")
    total = len(taxonomy["species"])
    levels = Counter(s["density"]["level"] for s in species.values())
    print(f"Validated {len(rows)} measurement rows from {len({r['_source_file'] for r in rows})} source file(s)")
    print(f"Wrote {OUT.relative_to(DATA.parent)}")
    print(f"  {structured} species structured, {len(species) - structured} legacy, "
          f"{total - len(species)} with no call data ({len(species) / total:.1%} coverage)")
    print("  density: " + ", ".join(f"{levels[k]} {k}" for k in
                                    ("rich", "detailed", "basic", "minimal") if levels[k]))
    if skipped:
        print(f"  not measurement sources, skipped: {', '.join(skipped)}")
    unsourced = [f for f, i in inference.items() if not i["citations"]]
    if genus_inference:
        derived = sorted(g for g, i in genus_inference.items() if i.get("derived"))
        curated = sorted(g for g, i in genus_inference.items() if not i.get("derived"))
        print(f"  genus inference: {len(derived)} derived from measured congeners"
              + (f", curated for {', '.join(curated)}" if curated else ""))
    print(f"  family inference for {len(inference)} families"
          + (f"; {len(unsourced)} cite no source ({', '.join(sorted(unsourced))})" if unsourced else ""))
    if shadowed:
        by_reference = Counter(reference for _, reference in shadowed)
        print(f"  {len(shadowed)} legacy entries kept alongside structured data, "
              f"awaiting migration: "
              + ", ".join(f"{n}x {ref}" for ref, n in sorted(by_reference.items())))


if __name__ == "__main__":
    main()
