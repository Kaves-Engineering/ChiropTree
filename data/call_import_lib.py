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
    "dispersion_type", "dispersion_value", "harmonic", "verbatim_value",
    "quality_flag", "notes",
]

# Name decisions that hold for any source, because they are facts about the
# taxonomy rather than about one paper. Each was checked against MDD v2.5's own
# nominalNames synonym list and corroborated against batnames.org. Every entry
# is a lump or a respelling, so the source's measurement belongs to exactly one
# current species. A split is never listed here: where an old name now covers
# several species the recording cannot be assigned, and it stays unresolved.
SHARED_SYNONYMS = {
    "Dasiypterus intermedius": "1005584",     # misspelt Dasypterus, a Lasiurus subgenus
    "Doryrhina stenotis": "1004572",          # batnames keeps only camerunensis/cyclops in Doryrhina
    "Doryrhina wollastoni": "1004573",
    "Eptesicus guadeloupensis": "1006834",    # nominalNames: guadeloupensis Genoways & R. J. Baker
    "Gardnerycteris crenulatum": "1004969",   # epithet corrected to feminine crenulata
    "Hypsugo bodenheimeri": "1005715",        # nominalNames: bodenheimeri (D. L. Harrison)
    "Laephotis botswanae": "1005729",         # nominalNames: botswanae Setzer
    "Paratriaenops furculus": "1004763",      # batnames gives furcula
    "Rhinolophus paradoxolophus": "1004732",  # nominalNames: paradoxolophus (Bourret)
    "Afronycteris nana": "1005700",           # feminine form of the epithet; MDD has nanus
    "Neoromicia nana": "1005700",             # same species, pre-Afronycteris combination
    "Anoura caudifera": "1004891",            # MDD gives the masculine caudifer
    "Eptesicus anatolicus": "1005511",        # one-to-one recombination into Cnephaeus
    "Eptesicus isabellinus": "1005524",       # one-to-one recombination into Cnephaeus
    "Kerivoula papuensis": "1005313",         # one-to-one recombination into Phoniscus
}

# Names left unresolved on purpose, with the reason, so that a later pass does
# not "fix" them by guessing. Each is a split or an unsettled synonymy where the
# source's recording cannot be assigned to exactly one current species.
DECLINED_SYNONYMS = {
    "Tonatia saurophila": "split; saurophila sensu stricto is Jamaican and the mainland "
                          "populations are now Tonatia bakeri, so the source's bats cannot be placed",
    "Molossus barnesi": "treated as a synonym of both M. coibensis and M. molossus in "
                        "different treatments; not a settled one-to-one mapping",
    "Cynomops paranus": "synonymised with C. planirostris in older work but treated as "
                        "valid in recent revisions; not a settled one-to-one mapping",
}


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())

# Measurements published under a name that has since been split. Policy: the
# value is assigned to every daughter species, each carrying a note saying where
# it came from and flagged taxon_uncertain, rather than dropped or pinned to one
# daughter we cannot justify. One datum becomes several records, so they are
# excluded from anything that treats records as independent.
#
# Two shapes of split are covered:
#   - the old name is gone (Tonatia saurophila), which the resolver would fail on;
#   - the old name survives but its concept narrowed (Pteronotus parnellii), which
#     the resolver would silently match exactly and over-assign. That second case
#     is the dangerous one, because nothing looks wrong.
SPLIT_ASSIGNMENTS = {
    "Tonatia saurophila": {
        "daughters": ["1004984", "1004986"],  # T. bakeri, T. maresi
        "note": ("Published as Tonatia saurophila, a name the current taxonomy no longer "
                 "recognises; it was split into T. bakeri and T. maresi. The measurement is "
                 "shown for each daughter because the recording cannot be assigned to one."),
    },
    "Pteronotus parnellii": {
        "daughters": ["1004852", "1004855", "1004858", "1004859", "1004860",
                      "1004861", "1004863", "1004865", "1004867"],
        "note": ("Published as Pteronotus parnellii before that name was restricted to one "
                 "member of a nine-species cryptic complex. Pre-split recordings could belong "
                 "to any of them, so the measurement is shown for each. All nine are "
                 "high-duty-cycle CF bats with similar calls, but the assignment is unresolved."),
    },
}


def observation_suffix(printed_name: str, species: dict) -> str:
    """Disambiguator for an observation id, empty when the name is the accepted one.

    A source can list two names that the current taxonomy has since lumped into
    one species. Those are two separate measurements and must not share an
    observation id, or their values silently merge. Appending the printed
    epithet keeps them distinct and keeps the id readable.
    """
    accepted = species["sciName"].replace("_", " ")
    if norm(printed_name) == norm(accepted):
        return ""
    return "-" + printed_name.split()[-1].lower()


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
        self.matched_split = 0
        self.add_manual(SHARED_SYNONYMS)

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

    def resolve_many(self, name: str) -> tuple[list[dict], str, str]:
        """Resolve to every species a name may refer to.

        Normally one species. For a name covered by SPLIT_ASSIGNMENTS it is
        every daughter of the split, with the reason to record on each row.
        """
        split = SPLIT_ASSIGNMENTS.get(name)
        if split:
            by_id = {r["id"]: r for r in self.accepted.values()}
            self.matched_split += 1
            return [by_id[i] for i in split["daughters"]], "split_assigned", split["note"]
        species, method = self.resolve(name)
        return ([species] if species else []), method, ""

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
          + (f", {resolver.matched_manual} by hand-checked mapping" if resolver.matched_manual else "")
          + (f", {resolver.matched_split} spread across split daughters" if resolver.matched_split else ""))
    if resolver.unresolved:
        print(f"  {len(resolver.unresolved)} unresolved, parked for review:")
        for name, reason in sorted(resolver.unresolved):
            print(f"    - {name}: {reason}")
