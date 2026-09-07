"""Shared helpers for build_<source>_calls.py importers.

Each importer fetches one source's own raw table, resolves its taxon names
against the current MDD taxonomy, and writes one CSV of measurement rows to
data/calls/<reference_id>.csv. data/calls/build_calls.py then validates every
row against the parameter registry and builds the browser export.

Policy this enforces for every source:

- species-level only: a row is written only when the name resolves to exactly
  one MDD species, never to a genus or family fallback;
- names are resolved, never guessed. Two routes count as resolution: an exact
  match on the accepted binomial, and a 1:1 match on MDD's own recorded MSW3
  name (taxon_match_method='synonym_via_mdd'). An MSW3 name that maps to
  several MDD species is a split, not a synonym, and is left unresolved;
- nothing is dropped silently. Unresolved names are written to a review file
  for a human decision;
- no first-wins skipping. Every source writes its own CSV and conflicts are
  surfaced by the builder, not resolved by import order.
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
TAXONOMY = HERE / "chiroptera_taxonomy.json"
CALLS_DIR = HERE / "calls"
REVIEW_DIR = CALLS_DIR / "unresolved"

# Column order every source CSV uses. build_calls.py reads by name, so the
# order is for human review only -- context first, then the measurement.
COLUMNS = [
    "observation_id", "mdd_id", "verbatim_taxon_name", "taxon_match_method",
    "reference_id", "locator", "method_id",
    "call_phase", "call_variant", "variant_label", "signal_direction",
    "recording_condition", "habitat_class", "country", "locality", "date_or_season",
    "n_individuals", "n_calls",
    "parameter", "statistic", "value", "value_min", "value_max", "unit",
    "dispersion_type", "dispersion_value", "verbatim_value", "quality_flag", "notes",
]


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


class TaxonResolver:
    """Resolves source taxon names to MDD species, or reports why it cannot."""

    def __init__(self) -> None:
        taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
        self.accepted = {norm(s["sciName"].replace("_", " ")): s for s in taxonomy["species"]}
        self.msw3 = defaultdict(list)
        for species in taxonomy["species"]:
            legacy = (species.get("MSW3_sciName") or "").replace("_", " ").strip()
            if legacy and legacy != "NA":
                self.msw3[norm(legacy)].append(species)
        self.unresolved: list[tuple[str, str]] = []
        self.manual: dict[str, dict] = {}
        self.matched_exact = 0
        self.matched_synonym = 0
        self.matched_manual = 0

    def add_manual(self, mapping: dict[str, str]) -> None:
        """Register hand-checked name -> MDD id mappings for one source.

        Only for cases a person has resolved against an authority and written
        down the evidence. Safe for a lump (several old names now one species);
        a split cannot be resolved this way, because the source's recording
        cannot be assigned to one of the daughters.
        """
        by_id = {record["id"]: record for record in self.accepted.values()}
        for name, mdd_id in mapping.items():
            if mdd_id not in by_id:
                raise KeyError(f"manual mapping for {name!r} points at unknown MDD id {mdd_id!r}")
            self.manual[norm(name)] = by_id[mdd_id]

    def resolve(self, name: str) -> tuple[dict | None, str]:
        """Return (species record, match method). (None, reason) when unresolved."""
        key = norm(name)
        if key in self.accepted:
            self.matched_exact += 1
            return self.accepted[key], "exact"
        if key in self.manual:
            self.matched_manual += 1
            return self.manual[key], "manual"

        candidates = self.msw3.get(key, [])
        if len(candidates) == 1:
            self.matched_synonym += 1
            return candidates[0], "synonym_via_mdd"
        if len(candidates) > 1:
            names = ", ".join(c["sciName"].replace("_", " ") for c in candidates)
            reason = f"MSW3 name split into several MDD species: {names}"
        else:
            reason = "no accepted name and no MSW3 bridge in MDD v2.5"
        self.unresolved.append((name, reason))
        return None, reason


def write_rows(reference_id: str, rows: list[dict]) -> Path:
    """Write one source's measurement rows, sorted for a stable diff."""
    CALLS_DIR.mkdir(parents=True, exist_ok=True)
    path = CALLS_DIR / f"{reference_id}.csv"
    rows = sorted(rows, key=lambda r: (r["observation_id"], r["parameter"]))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in COLUMNS})
    return path


def write_review(reference_id: str, unresolved: list[tuple[str, str]]) -> Path | None:
    """Park unresolved names where a human can act on them.

    These are not failures of the importer; they are taxonomic decisions that
    only a person should make. Keeping them in the repo means they cannot be
    quietly forgotten.
    """
    if not unresolved:
        return None
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    path = REVIEW_DIR / f"{reference_id}.md"
    lines = [
        f"# Unresolved taxon names — {reference_id}",
        "",
        f"{len(unresolved)} name(s) in this source do not resolve to exactly one",
        "species in the current MDD taxonomy, so no rows were imported for them.",
        "Resolve by hand and add the mapping to the importer, or record the",
        "decision to exclude them.",
        "",
        "| Name as printed in source | Why unresolved |",
        "|---|---|",
    ]
    lines += [f"| {name} | {reason} |" for name, reason in sorted(unresolved)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def report(reference_id: str, written: int, species: int, resolver: TaxonResolver) -> None:
    print(f"{reference_id}: wrote {written} measurement rows for {species} species")
    exact = "resolved by exact name"
    print(f"  {resolver.matched_exact} {exact}, {resolver.matched_synonym} via MSW3 synonym"
          + (f", {resolver.matched_manual} by hand-checked mapping" if resolver.matched_manual else ""))
    if resolver.unresolved:
        print(f"  {len(resolver.unresolved)} unresolved, parked for review:")
        for name, reason in sorted(resolver.unresolved):
            print(f"    - {name}: {reason}")
