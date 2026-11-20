"""Flag species whose forearm or body-mass headline is likely wrong.

Reads the built data/chiroptera_body_size.json (so copies are already folded
and estimates already marked) and writes a review list of species worth a
targeted literature search to data/size/unresolved/size_flags.csv.

The 30% spread flag in build_size.py is tuned for the page, and is far too
loose for forearm: within a species forearm varies by a few percent, so two
sources 15% apart (Vampyrum spectrum: 81 vs 68.8 mm) mean one is wrong. The
checks here are stricter and look at the data from several directions:

high priority (a value is probably wrong)
- disagree:   independent sources differ by more than DISAGREE[trait]
              (max/min of per-source values) and there are only two, so the
              median is their average and a bad one moves the headline;
- off-range:  the headline lies outside the range a source reports for the
              species (all of that source's ranges together, so a female and
              a male range count as one span);
- allometry:  forearm and mass do not fit together: the species sits more than
              ALLOMETRY_SIGMAS robust SDs off its family's log-log line;
- wide-range: the ranges other than HMW's span more than WIDE_RANGE[trait]
              (max/min), usually two species or juveniles mixed in. HMW's own
              range is the reference (build_size.REFERENCE_RANGES) and is wide
              by design, compiled across the whole species;
medium (an odd source exists, but the median outvotes it)
- outvoted:   as disagree, with three or more sources; the headline is
              usually fine, the odd record still misleads on the card;
low (thin evidence, nothing contradicts it)
- compilation-only: every source behind the headline is a compilation;
- single:     one independent source;
- estimated:  no measurement at all.

A genus-outlier check was tried and dropped: every hit was a genuinely large
or small species (Hipposideros armiger, Sturnira magna, Myotis chinensis).
An off-range check against a one-animal "range" (SONOZOTZ n=1, 31-31) is
skipped too; such a record already counts in the disagree check.

Values build_size.py already left out of the headline for lying outside the
HMW range (marked "out") are ignored here: the card already handles them.

Allometry cannot tell which trait is wrong, so it is listed under both.

Run after build_size.py:  uv run data/size/flag_size_outliers.py
"""
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE.parent
SIZE = DATA / "chiroptera_body_size.json"
TAXONOMY = DATA / "chiroptera_taxonomy.json"
OUT = HERE / "unresolved" / "size_flags.csv"

TRAITS = {"fa": "forearm_length", "m": "body_mass"}
DISAGREE = {"fa": 1.10, "m": 1.40}
WIDE_RANGE = {"fa": 1.35, "m": 2.5}
OFF_RANGE_SLACK = 0.05
ALLOMETRY_SIGMAS = 3.0
ALLOMETRY_MIN_FAMILY = 15

REFERENCE = "HMW vol. 9 (2019)"
HIGH = ("disagree", "off-range", "allometry", "wide-range")
MEDIUM = ("outvoted",)


def robust_sd(values: list[float]) -> float:
    median = statistics.median(values)
    return 1.4826 * statistics.median(abs(v - median) for v in values)


def per_source_values(records: list[dict]) -> dict[int, float]:
    """One value per independent source: a record's upstream counts as its source."""
    measured = [r for r in records if "e" not in r and not r.get("ro") and not r.get("out")]
    by_source = defaultdict(list)
    for r in measured:
        by_source[r.get("us", r["s"])].append(r["v"])
    return {s: statistics.mean(vs) for s, vs in by_source.items()}


def describe(values: dict[int, float], refs: list) -> str:
    return "; ".join(f"{refs[s][1]} {v:g}" for s, v in sorted(values.items(), key=lambda x: x[1]))


def check_trait(key: str, h: dict, refs: list) -> list[tuple[str, str]]:
    flags = []
    values = per_source_values(h["r"])
    if len(values) > 1 and max(values.values()) / min(values.values()) > DISAGREE[key]:
        kind = "disagree" if len(values) <= 2 else "outvoted"
        flags.append((kind, describe(values, refs)))
    spans = defaultdict(list)
    for r in h["r"]:
        if r.get("lo") is not None and r["lo"] != r["hi"] and "e" not in r and not r.get("out"):
            spans[r["s"]].append((r["lo"], r["hi"]))
    for s, ranges in spans.items():
        lo, hi = min(x[0] for x in ranges), max(x[1] for x in ranges)
        if h["v"] < lo * (1 - OFF_RANGE_SLACK) or h["v"] > hi * (1 + OFF_RANGE_SLACK):
            flags.append(("off-range", f"headline {h['v']:g} vs {refs[s][1]} {lo:g}-{hi:g}"))
    others = [x for s, ranges in spans.items() if refs[s][1] != REFERENCE for x in ranges]
    if others and max(x[1] for x in others) / min(x[0] for x in others) > WIDE_RANGE[key]:
        flags.append(("wide-range", f"{min(x[0] for x in others):g}-{max(x[1] for x in others):g}"))
    if h.get("est"):
        flags.append(("estimated", "no measurement"))
    elif len(values) == 1:
        flags.append(("single", describe(values, refs)))
    if values and all(refs[s][5] == "compilation" for s in values):
        flags.append(("compilation-only", ", ".join(sorted({refs[s][1] for s in values}))))
    return flags


def allometry_flags(species: dict, family_of: dict) -> dict[str, str]:
    """Species whose mass is off their family's log(mass) ~ log(forearm) line."""
    points = defaultdict(list)
    for name, entry in species.items():
        fa, m = entry.get("fa"), entry.get("m")
        if fa and m and not fa.get("est") and not m.get("est"):
            points[family_of.get(name, "?")].append((name, math.log(fa["v"]), math.log(m["v"])))
    everyone = [p for ps in points.values() for p in ps]
    out = {}
    for family, ps in points.items():
        sample = ps if len(ps) >= ALLOMETRY_MIN_FAMILY else everyone
        slope, intercept = fit(sample)
        residuals = [y - (intercept + slope * x) for _, x, y in sample]
        sd = robust_sd(residuals)
        for name, x, y in ps:
            resid = y - (intercept + slope * x)
            if abs(resid) > ALLOMETRY_SIGMAS * sd:
                expected = math.exp(intercept + slope * x)
                out[name] = (f"mass {math.exp(y):g} g vs ~{expected:.0f} g expected for a "
                             f"{math.exp(x):g} mm forearm in {family if sample is ps else 'bats'}")
    return out


def fit(points: list[tuple]) -> tuple[float, float]:
    xs, ys = [p[1] for p in points], [p[2] for p in points]
    slope, intercept = statistics.linear_regression(xs, ys)
    return slope, intercept


def priority(flags: list[tuple[str, str]]) -> str:
    kinds = {k for k, _ in flags}
    if kinds & set(HIGH):
        return "high"
    return "medium" if kinds & set(MEDIUM) else "low"


def main() -> None:
    data = json.loads(SIZE.read_text(encoding="utf-8"))
    refs, species = data["refs"], data["species"]
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))["species"]
    family_of = {t["sciName"].replace("_", " "): t["family"] for t in taxonomy}

    allometry = allometry_flags(species, family_of)

    rows = []
    for name, entry in sorted(species.items()):
        for key, trait in TRAITS.items():
            h = entry.get(key)
            if not h:
                continue
            flags = check_trait(key, h, refs)
            if name in allometry:
                flags.append(("allometry", allometry[name]))
            if flags:
                rows.append({
                    "species": name, "family": family_of.get(name, ""), "trait": trait,
                    "headline": h["v"], "sources": h["k"], "priority": priority(flags),
                    "flags": " ".join(sorted({k for k, _ in flags})),
                    "detail": " | ".join(f"{k}: {d}" for k, d in flags),
                })

    order = {"high": 0, "medium": 1, "low": 2}
    rows.sort(key=lambda r: (order[r["priority"]], r["trait"], r["species"]))
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {OUT.relative_to(DATA.parent)}: {len(rows)} species-trait rows")
    for trait in TRAITS.values():
        for level in order:
            n = sum(1 for r in rows if r["trait"] == trait and r["priority"] == level)
            print(f"  {trait:15} {level:7} {n}")
    flag_counts = defaultdict(int)
    for r in rows:
        for k in r["flags"].split():
            flag_counts[(r["trait"], k)] += 1
    for (trait, k), n in sorted(flag_counts.items()):
        print(f"  {trait:15} {k:17} {n}")


if __name__ == "__main__":
    main()
