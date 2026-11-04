"""Shared helpers for the body-size importers in data/size/import_<source>.py.

Each importer reads one source's own raw table (cached under the gitignored
data/raw/size/<source>/, checksum-pinned), resolves its names against the
current MDD taxonomy and writes one CSV of size rows to
data/size/<reference_id>.csv. data/size/build_size.py validates every row
against data/size/references.json and builds data/chiroptera_body_size.json,
which the species card reads.

The policy is the one the call importers follow (see data/call_import_lib.py):

- species level only: a row is written only when its name resolves to exactly
  one MDD species, never to a genus or family;
- names are resolved, never guessed. On top of the call importers' routes
  (exact name, hand-checked mapping, a one-to-one MSW3 name) this adds two
  that the older trait databases need, both read from MDD v2.5 itself and both
  only when they point at exactly one species: the CMW (2020) name, and a
  former combination of the species from the name history
  (data/chiroptera_name_history.json);
- nothing is dropped silently: unresolved names go to data/size/unresolved/;
- every row says whether it is a measurement or an estimate (basis), and
  every estimate says how it was made (estimate_method).
"""
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE.parent
RAW = DATA / "raw" / "size"
REVIEW_DIR = HERE / "unresolved"
HISTORY = DATA / "chiroptera_name_history.json"

sys.path.insert(0, str(DATA))
from call_import_lib import SPLIT_ASSIGNMENTS, TaxonResolver, norm  # noqa: E402

TRAITS = {"forearm_length": "mm", "body_mass": "g"}

# basis: measured = the source reports values taken from real bats (itself or
# by compiling the literature); estimated = the source computed the value for a
# species nobody had measured (imputation, genus averages, allometry).
BASES = {"measured", "estimated"}
STATISTICS = {"mean", "median", "single", "range_only"}
# range_type: what value_min/value_max mean.
#   min_max    -- smallest and largest value the source reports
#   central_95 -- 2.5th to 97.5th percentile of the individuals, used for
#                 individual-level sources with 20 or more adults so that one
#                 mis-keyed record cannot set the range
#   field_key  -- the identification range a field key prints for live bats
#   mean_sd    -- never written as a range; SD is carried in its own column
RANGE_TYPES = {"", "min_max", "central_95", "field_key"}
SEXES = {"pooled", "male", "female"}

COLUMNS = [
    "observation_id", "mdd_id", "verbatim_taxon_name", "taxon_match_method",
    "reference_id", "locator", "trait", "basis", "estimate_method",
    "statistic", "value", "value_min", "value_max", "range_type", "sd", "n",
    "sex", "area", "upstream_source", "data_year", "verbatim_value", "notes",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_raw(files: dict[str, str]) -> None:
    """Refuse to import from anything but the exact bytes the importer was written against."""
    for rel, expected in files.items():
        path = RAW / rel if not Path(rel).is_absolute() else Path(rel)
        if not path.exists():
            raise SystemExit(f"missing raw file {path}; see the fetch command in the importer's docstring")
        got = sha256(path)
        if got != expected:
            raise SystemExit(f"{path}: sha256 {got} does not match the pinned {expected}")


class SizeResolver(TaxonResolver):
    """TaxonResolver plus the CMW and former-combination bridges."""

    def __init__(self) -> None:
        super().__init__()
        taxonomy = self.accepted.values()
        self.cmw = defaultdict(list)
        self.by_bin = {}
        for species in taxonomy:
            self.by_bin[species["sciName"].replace("_", " ")] = species
        raw_rows = self._mdd_rows()
        for species in taxonomy:
            cmw = (raw_rows.get(species["id"], {}).get("CMW_sciName") or "").replace("_", " ").strip()
            if cmw and cmw != "NA":
                self.cmw[norm(cmw)].append(species)
        self.former = defaultdict(set)
        history = json.loads(HISTORY.read_text(encoding="utf-8"))["species"]
        for binomial, entry in history.items():
            species = self.by_bin.get(binomial)
            if not species:
                continue
            for name in [n[0] for n in entry.get("names", [])] + [n[0] for n in entry.get("syn", [])]:
                if len(name.split()) == 2:
                    self.former[norm(name)].add(species["id"])
        self.by_id = {s["id"]: s for s in taxonomy}
        self.matched_cmw = 0
        self.matched_former = 0

    @staticmethod
    def _mdd_rows() -> dict:
        """CMW names live in the MDD CSV, not in the exported taxonomy."""
        path = DATA / "raw" / "MDD_v2.5_6904species.csv"
        if not path.exists():
            raise SystemExit(f"missing {path}; run data/build_taxonomy.py to fetch the MDD release")
        with path.open(encoding="utf-8") as handle:
            return {r["id"]: r for r in csv.DictReader(handle) if r["order"] == "Chiroptera"}

    def resolve(self, name: str):
        name = " ".join(name.replace("_", " ").split())
        key = norm(name)
        # A size measured under a name that has since been split belongs to one
        # daughter we cannot identify. The call importers spread such values
        # over every daughter; a body size cannot be spread that way, so the
        # name is parked. This also catches the dangerous case where the old
        # name survives with a narrower meaning (Pteronotus parnellii).
        split = {norm(k): v for k, v in SPLIT_ASSIGNMENTS.items()}.get(key)
        if split:
            daughters = ", ".join(sorted(self.by_id[i]["sciName"].replace("_", " ") for i in split["daughters"]))
            self.unresolved.append((name, f"split since the source used it, into {daughters}; "
                                          "the measured bats cannot be assigned to one of them"))
            return None, "split"
        if key in self.accepted or key in self.manual:
            return super().resolve(name)
        candidates = self.msw3.get(key, [])
        if len(candidates) == 1:
            return super().resolve(name)
        cmw = self.cmw.get(key, [])
        if len(cmw) == 1 and not candidates:
            self.matched_cmw += 1
            return cmw[0], "cmw_via_mdd"
        former = self.former.get(key, set())
        if len(former) == 1 and not candidates and not cmw:
            self.matched_former += 1
            return self.by_id[next(iter(former))], "former_name_via_mdd"
        if len(candidates) > 1 or len(cmw) > 1 or len(former) > 1:
            pool = {s["id"] for s in candidates} | {s["id"] for s in cmw} | former
            names = ", ".join(sorted(self.by_id[i]["sciName"].replace("_", " ") for i in pool))
            reason = f"older name now covers several MDD species: {names}"
        else:
            reason = "no accepted name, MSW3, CMW or former-combination bridge in MDD v2.5"
        self.unresolved.append((name, reason))
        return None, reason



def number(text) -> str:
    """A cell as a canonical decimal string, or '' for the sources' many spellings of missing."""
    if text is None:
        return ""
    text = str(text).strip().replace(",", ".")
    if text in {"", "NA", "-999", "-999.0", "-999.00", "nan", "NaN", "None"}:
        return ""
    value = float(text)
    if value <= 0:
        return ""
    return f"{value:.4g}" if value < 1000 else f"{value:.0f}"


def summarise(values: list[float]) -> dict:
    """Mean, SD and range of individual measurements, as size-row fields.

    With 20 or more individuals the range is the 2.5th-97.5th percentile
    (central_95), so a single mis-keyed record cannot stretch it; with fewer it
    is the plain minimum and maximum (min_max).
    """
    values = sorted(values)
    n = len(values)
    mean = sum(values) / n
    sd = (sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5 if n > 1 else None

    def quantile(q: float) -> float:
        position = q * (n - 1)
        low = int(position)
        high = min(low + 1, n - 1)
        return values[low] + (values[high] - values[low]) * (position - low)

    central = n >= 20
    low, high = (quantile(0.025), quantile(0.975)) if central else (values[0], values[-1])
    return {
        "statistic": "mean", "value": number(mean), "n": str(n),
        "sd": number(sd) if sd else "",
        "value_min": number(low), "value_max": number(high),
        "range_type": "central_95" if central else "min_max",
    }


def write_rows(reference_id: str, rows: list[dict]) -> Path:
    path = HERE / f"{reference_id}.csv"
    counts = Counter(r["observation_id"] + "|" + r["trait"] for r in rows)
    duplicates = {i for i, c in counts.items() if c > 1}
    if duplicates:
        raise SystemExit(f"{reference_id}: duplicate observation ids {sorted(duplicates)[:5]}")
    rows = sorted(rows, key=lambda r: (r["observation_id"], r["trait"]))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in COLUMNS})
    return path


def write_review(reference_id: str, unresolved: list[tuple[str, str]]) -> None:
    path = REVIEW_DIR / f"{reference_id}.md"
    if not unresolved:
        path.unlink(missing_ok=True)
        return
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Unresolved taxon names — {reference_id}", "",
        f"{len(set(unresolved))} name(s) in this source do not resolve to exactly one",
        "species in MDD v2.5, so no size rows were imported for them.", "",
        "| Name as printed in source | Why unresolved |", "|---|---|",
    ]
    lines += [f"| {name} | {reason} |" for name, reason in sorted(set(unresolved))]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def report(reference_id: str, rows: list[dict], resolver: SizeResolver) -> None:
    species = {r["mdd_id"] for r in rows}
    by_trait = defaultdict(set)
    for r in rows:
        by_trait[(r["trait"], r["basis"])].add(r["mdd_id"])
    print(f"{reference_id}: {len(rows)} rows for {len(species)} species")
    for (trait, basis), ids in sorted(by_trait.items()):
        print(f"  {trait} {basis}: {len(ids)} species")
    print(f"  names: {resolver.matched_exact} exact, {resolver.matched_synonym} via MSW3, "
          f"{resolver.matched_cmw} via CMW, {resolver.matched_former} via a former combination, "
          f"{resolver.matched_manual} hand-checked, {resolver.matched_split} spread over split daughters")
    unresolved = sorted(set(resolver.unresolved))
    if unresolved:
        print(f"  {len(unresolved)} names unresolved, listed in data/size/unresolved/{reference_id}.md")


def base_row(reference_id: str, species: dict, printed: str, method: str, locator: str) -> dict:
    return {
        "mdd_id": species["id"], "verbatim_taxon_name": printed,
        "taxon_match_method": method, "reference_id": reference_id, "locator": locator,
    }
