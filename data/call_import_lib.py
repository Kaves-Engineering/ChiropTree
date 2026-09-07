"""Shared helpers for build_<source>_calls.py importers.

Each importer fetches one source's own raw table, shapes it into
(mdd_id, entry) pairs, and calls merge_species() to write them into
call_measurements.json. Keeping the matching/merge/report logic in one
place means every source obeys the same policy:

- species-level only: caller must resolve to an exact MDD ID, never a
  genus/family fallback;
- first source wins: an MDD ID already present in the store is left
  untouched and reported as skipped, so import order is the (implicit)
  priority order between sources -- run more specific/direct-measurement
  sources before broader comparative databases;
- unmatched names are reported, never guessed.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
TAXONOMY = HERE / "chiroptera_taxonomy.json"
CALLS = HERE / "call_measurements.json"


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def load_species_by_name() -> dict[str, dict]:
    """MDD taxon records keyed by normalized 'genus species' binomial."""
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    return {norm(s["sciName"].replace("_", " ")): s for s in taxonomy["species"]}


def load_store() -> dict:
    return json.loads(CALLS.read_text(encoding="utf-8"))


def save_store(store: dict) -> None:
    CALLS.write_text(json.dumps(store, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def merge_species(store: dict, reference_id: str, reference: dict, rows: list[tuple[str, dict]]) -> dict:
    """Merge (mdd_id, entry) pairs into store, skipping IDs already present.

    rows: list of (mdd_id, {"summary": ..., "context": ...}) -- reference is
    filled in here. Returns a small report dict for the caller to print.
    """
    store["references"].setdefault(reference_id, reference)
    added = 0
    skipped_existing = 0
    for mdd_id, entry in rows:
        if mdd_id in store["species"]:
            skipped_existing += 1
            continue
        store["species"][mdd_id] = {**entry, "reference": reference_id}
        added += 1
    return {"added": added, "skipped_existing": skipped_existing}


def report(summary: dict, unmatched: list[str]) -> None:
    print(f"Added {summary['added']} species, skipped {summary['skipped_existing']} "
          f"already-curated, {len(unmatched)} unmatched to current MDD taxonomy")
    if unmatched:
        print("Unmatched species names (likely MDD synonym/taxonomy drift):")
        for name in sorted(unmatched):
            print(f"  - {name}")
