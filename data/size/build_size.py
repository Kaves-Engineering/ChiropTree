"""Build data/chiroptera_body_size.json from the per-source size CSVs.

Reads every data/size/<reference_id>.csv written by the import_*.py scripts,
validates each row against data/size/references.json, the taxonomy and the
plausible bounds in data/calls/parameters.json, and writes what the species
card shows: per species, a forearm length and a body mass, each with the
records behind it.

How a species' headline value is chosen:

1. Copies are folded. Compilations copy each other (COMBINE <- Amniote <-
   PanTHERIA). A row whose upstream_source is another imported reference, and
   whose value matches that reference's row for the same species within 3%,
   is folded into it: the original row lists the copy under "also in". Copies
   whose value differs stay as their own record but share the upstream's
   independence group, so they never count as a second source.
2. Measured before estimated. If any measured row exists, estimates are
   shown in the record list but never used for the headline.
3. One value per independent source. Rows are grouped by independence
   group (a study cited inside a compilation is its own group). Each group
   contributes the n-weighted mean of its pooled-sex rows, or the mean of its
   male and female rows when it has only those.
4. The headline is the median of those group values, so one odd source
   cannot drag it. The range is the widest span reported by any measured row
   that gives one (min-max, the central 95% of individuals, or a field key's
   identification range). No range is invented for a species whose sources
   give only means.
5. A range with no mean (statistic range_only: a field key's "F.A.=61-69")
   never enters the median while any real mean exists. When ranges are all a
   species has, the headline is flagged ro: the card shows the range itself,
   and the stored value is only its midpoint, to place the marker.

Flags carried to the page:
- est: the headline is an estimate (no measurement exists);
- pre-split: a record's source predates a split of this species, so its bats
  may include populations now in the split-off species (from the name history);
- spread: independent sources disagree by more than 30% of the median.

Run after the importers: uv run data/size/build_size.py
"""
import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE.parent
sys.path.insert(0, str(HERE))
from size_lib import BASES, COLUMNS, RANGE_TYPES, SEXES, STATISTICS, TRAITS  # noqa: E402

OUT = DATA / "chiroptera_body_size.json"
TAXONOMY = DATA / "chiroptera_taxonomy.json"
HISTORY = DATA / "chiroptera_name_history.json"
PARAMETERS = DATA / "calls" / "parameters.json"
CALL_REFS = DATA / "calls" / "references.json"
COPY_TOLERANCE = 0.03
SPREAD_TOLERANCE = 0.30
SHORT_TRAIT = {"forearm_length": "fa", "body_mass": "m"}


class BuildError(Exception):
    pass


def load_references() -> dict:
    refs = json.loads((HERE / "references.json").read_text(encoding="utf-8"))["references"]
    calls = json.loads(CALL_REFS.read_text(encoding="utf-8"))["references"]
    for rid, ref in refs.items():
        if ref.get("same_as_calls"):
            if rid not in calls:
                raise BuildError(f"references.json: {rid} says same_as_calls but data/calls/references.json has no {rid}")
            for key in ("type", "citation", "doi", "url", "licence", "geographic_scope", "taxonomic_scope"):
                ref.setdefault(key, calls[rid].get(key))
        for key in ("short", "role", "citation", "independence_group"):
            if not ref.get(key):
                raise BuildError(f"references.json: {rid} has no {key}")
    return refs


def bounds() -> dict:
    params = {p["id"]: p for p in json.loads(PARAMETERS.read_text(encoding="utf-8"))["parameters"]}
    return {t: (params[t]["sane_min"], params[t]["sane_max"]) for t in TRAITS}


def load_rows(refs: dict, species: dict, sane: dict) -> tuple[list[dict], list[str]]:
    errors, rejected, rows = [], [], []
    for path in sorted(HERE.glob("*.csv")):
        with path.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != COLUMNS:
                errors.append(f"{path.name}: columns differ from size_lib.COLUMNS")
                continue
            for line, row in enumerate(reader, start=2):
                where = f"{path.name}:{line}"
                problems = []
                if row["reference_id"] != path.stem:
                    problems.append("reference_id does not match the file name")
                if row["reference_id"] not in refs or refs[row["reference_id"]]["role"] == "upstream":
                    problems.append(f"unknown or upstream-only reference {row['reference_id']}")
                if row["mdd_id"] not in species:
                    problems.append(f"unknown MDD id {row['mdd_id']}")
                if row["trait"] not in TRAITS:
                    problems.append(f"unknown trait {row['trait']}")
                if row["basis"] not in BASES:
                    problems.append(f"basis {row['basis']!r}")
                if (row["basis"] == "estimated") != bool(row["estimate_method"]):
                    problems.append("an estimate needs an estimate_method, and only an estimate has one")
                if row["statistic"] not in STATISTICS or row["range_type"] not in RANGE_TYPES or row["sex"] not in SEXES:
                    problems.append("statistic, range_type or sex outside the allowed values")
                if bool(row["value_min"]) != bool(row["value_max"]) or bool(row["range_type"]) != bool(row["value_min"]):
                    problems.append("a range needs both ends and a range_type")
                if problems:
                    errors += [f"{where}: {p}" for p in problems]
                    continue
                low, high = sane[row["trait"]]
                numbers = {k: float(row[k]) for k in ("value", "value_min", "value_max", "sd", "n") if row[k]}
                if not low <= numbers["value"] <= high:
                    rejected.append(f"{where}: {row['trait']} {row['value']} outside {low}-{high}, {row['verbatim_taxon_name']}")
                    continue
                if "value_min" in numbers and not numbers["value_min"] <= numbers["value"] <= numbers["value_max"]:
                    errors.append(f"{where}: value outside its own range")
                    continue
                row.update(_num=numbers)
                rows.append(row)
    if errors:
        raise BuildError("\n".join(errors[:40]) + (f"\n... and {len(errors) - 40} more" if len(errors) > 40 else ""))
    return rows, rejected


def fold_copies(rows: list[dict], refs: dict) -> None:
    """Mark rows that copy an upstream row (_copy_of) and give every row its group (_group)."""
    by_key = defaultdict(list)
    for row in rows:
        by_key[(row["mdd_id"], row["trait"], row["reference_id"])].append(row)
        row["_also"] = []

    def final(row):
        while row.get("_copy_of"):
            row = row["_copy_of"]
        return row

    # upstreams first: a reference cited as upstream is resolved before its citers
    order = {rid: 0 for rid in refs}
    for _ in refs:
        for row in rows:
            up = row["upstream_source"]
            if up in refs and row["reference_id"] in order:
                order[row["reference_id"]] = max(order[row["reference_id"]], order.get(up, 0) + 1)
    for row in sorted(rows, key=lambda r: order[r["reference_id"]]):
        up = row["upstream_source"]
        if up in refs and up != row["reference_id"]:
            candidates = [final(r) for r in by_key.get((row["mdd_id"], row["trait"], up), [])
                          if r["sex"] == row["sex"]]
            match = next((c for c in candidates
                          if abs(c["_num"]["value"] - row["_num"]["value"]) <= COPY_TOLERANCE * c["_num"]["value"]), None)
            if match is not None and match is not row:
                row["_copy_of"] = match
                match["_also"].append(row["reference_id"])
                continue
            row["_group"] = refs[up]["independence_group"]
        elif up:
            # a study cited inside a compilation; the same study's bats from
            # another area are other bats ("Unpublished data" covers many)
            row["_group"] = "study:" + " ".join(up.lower().split())[:120] + "|" + row["area"].lower()
        else:
            row["_group"] = refs[row["reference_id"]]["independence_group"]


def group_values(rows: list[dict]) -> dict[str, float]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["_group"]].append(row)
    out = {}
    for group, members in groups.items():
        pooled = [r for r in members if r["sex"] == "pooled"]
        if pooled:
            weights = [r["_num"].get("n", 1.0) for r in pooled]
            out[group] = sum(w * r["_num"]["value"] for w, r in zip(weights, pooled)) / sum(weights)
        else:
            out[group] = statistics.mean(r["_num"]["value"] for r in members)
    return out


def rounded(value: float, trait: str) -> float:
    if trait == "forearm_length" or value < 10:
        return round(value, 1)
    return round(value) if value >= 100 else round(value, 1)


def main() -> None:
    refs = load_references()
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))["species"]
    species = {s["id"]: s["sciName"].replace("_", " ") for s in taxonomy}
    history = json.loads(HISTORY.read_text(encoding="utf-8"))["species"]
    rows, rejected = load_rows(refs, species, bounds())
    fold_copies(rows, refs)

    ref_ids = sorted(refs, key=lambda r: (refs[r]["role"] != "primary", refs[r]["short"]))
    ref_index = {rid: i for i, rid in enumerate(ref_ids)}
    strings, string_index = [], {}

    def text(value: str):
        if not value:
            return None
        if value not in string_index:
            string_index[value] = len(strings)
            strings.append(value)
        return string_index[value]

    per_species = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if not row.get("_copy_of"):
            per_species[species[row["mdd_id"]]][row["trait"]].append(row)

    out_species, scale = {}, {t: [] for t in TRAITS}
    counts = {t: {"measured": 0, "estimated": 0} for t in TRAITS}
    for binomial in sorted(per_species):
        splits = [(sp, year) for sp, year, _ in history.get(binomial, {}).get("into", []) if year]
        entry = {}
        for trait, records in per_species[binomial].items():
            measured = [r for r in records if r["basis"] == "measured"]
            # a range-only row (a field key's identification range) has no
            # mean; its midpoint never joins a median of real means
            with_value = [r for r in measured if r["statistic"] != "range_only"]
            basis_rows = with_value or measured or records
            values = group_values(basis_rows)
            headline = statistics.median(values.values())
            ranged = [r for r in measured if "value_min" in r["_num"]]
            h = {"v": rounded(headline, trait), "k": len(values)}
            if not measured:
                h["est"] = 1
            elif not with_value:
                h["ro"] = 1  # only ranges: the card shows the range, v is its midpoint
            if ranged:
                h["lo"] = rounded(min(r["_num"]["value_min"] for r in ranged), trait)
                h["hi"] = rounded(max(r["_num"]["value_max"] for r in ranged), trait)
                h["rs"] = sorted({ref_index[r["reference_id"]] for r in ranged})
            if len(values) > 1 and (max(values.values()) - min(values.values())) > SPREAD_TOLERANCE * headline:
                h["spread"] = 1

            def predates(row):
                year = row["data_year"][:4]
                return [sp for sp, split_year in splits if year.isdigit() and int(year) < split_year]

            if splits and all(predates(r) for r in basis_rows):
                h["pre"] = sorted({sp for r in basis_rows for sp in predates(r)})
            recs = []
            for r in sorted(records, key=lambda r: (r["basis"] != "measured", r["sex"] != "pooled",
                                                    -r["_num"].get("n", 0), ref_index[r["reference_id"]])):
                rec = {"s": ref_index[r["reference_id"]], "v": rounded(r["_num"]["value"], trait)}
                if r["basis"] == "estimated":
                    rec["e"] = text(r["estimate_method"])
                if "value_min" in r["_num"]:
                    rec["lo"] = rounded(r["_num"]["value_min"], trait)
                    rec["hi"] = rounded(r["_num"]["value_max"], trait)
                    rec["rt"] = {"central_95": "c95", "field_key": "key"}.get(r["range_type"], "mm")
                if r["statistic"] == "range_only":
                    rec["ro"] = 1
                for key, field in (("sd", "sd"), ("n", "n")):
                    if field in r["_num"]:
                        rec[key] = rounded(r["_num"][field], trait) if key == "sd" else int(r["_num"]["n"])
                if r["sex"] != "pooled":
                    rec["x"] = r["sex"][0]
                for key, field in (("a", "area"), ("u", "upstream_source")):
                    value = r[field]
                    if field == "upstream_source" and value in refs:
                        rec["us"] = ref_index[value]
                    elif value:
                        rec[key] = text(value)
                if r["_also"]:
                    rec["al"] = sorted({ref_index[a] for a in r["_also"]})
                if predates(r):
                    rec["pre"] = 1
                if r["taxon_match_method"] not in ("exact",):
                    rec["nm"] = text(r["verbatim_taxon_name"])
                recs.append(rec)
            h["r"] = recs
            entry[SHORT_TRAIT[trait]] = h
            counts[trait]["estimated" if h.get("est") else "measured"] += 1
            scale[trait].append((h["v"], binomial))
        out_species[binomial] = entry

    def extremes(trait):
        ordered = sorted(scale[trait])
        return {"min": ordered[0][0], "minSp": ordered[0][1], "max": ordered[-1][0], "maxSp": ordered[-1][1]}

    out = {
        "_meta": {
            "built": date.today().isoformat(),
            "builder": "data/size/build_size.py",
            "policy": "Headline = median over independent sources of measured values; estimates only where no measurement exists, and flagged. Ranges only where a source reports one.",
            "species": len(out_species),
            "counts": counts,
            "rejected_out_of_bounds": len(rejected),
        },
        "refs": [[rid, refs[rid]["short"], refs[rid]["citation"], refs[rid].get("url") or "",
                  refs[rid].get("licence") or "", refs[rid]["role"]] for rid in ref_ids],
        "strings": strings,
        "scale": {SHORT_TRAIT[t]: extremes(t) for t in TRAITS},
        "species": out_species,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT.relative_to(DATA.parent)}: {len(out_species)} species, {OUT.stat().st_size // 1024} KB")
    for trait in TRAITS:
        print(f"  {trait}: {counts[trait]['measured']} measured, {counts[trait]['estimated']} estimate only")
    folded = sum(1 for r in rows if r.get("_copy_of"))
    print(f"  {len(rows)} rows read, {folded} folded into the record they copy")
    missing = len(species) - len(out_species)
    print(f"  {missing} species with no size data in any source")
    if rejected:
        print(f"  {len(rejected)} rows outside the plausible bounds in parameters.json, not used:")
        for line in rejected:
            print("    " + line)


if __name__ == "__main__":
    try:
        main()
    except BuildError as error:
        sys.exit(f"build_size: {error}")
