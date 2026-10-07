"""Build data/chiroptera_name_history.json: what each bat species was called
before, and which species it was split from.

Run:  uv run python data/build_name_history.py

Two MDD v2.5 tables feed it, both from the same Zenodo release as the
taxonomy (downloaded into the gitignored data/raw/ if missing):

- the species table's history columns: taxonomyNotes ("split from M. x",
  "previously included M. y", "moved from A to B") with their citations, and
  the name each species carried in MSW3 (2005) and in the Illustrated
  Checklist of the Mammals of the World (CMW, 2020);
- the synonym table (Species_Syn), which MDD keeps in step with Hesperomys:
  every name combination a species has gone under, each dated by the first
  use Hesperomys records. That date is a lower bound on the record, not
  always the date of the taxonomic act -- the page says so.

Split links come from two independent signals, and each link records which:
  n  MDD's own taxonomyNotes say so ("split from", "previously included",
     "populations previously attributed to");
  s  the species' own name was once used as a subspecies of another current
     species (Glossophaga commissarisi bakeri, 1987 -> Glossophaga bakeri).

batnames.org (Simmons & Cirranello) was surveyed as a second source. Its
species entries carry only name, authority and common name; its taxonomic
history is free-text commentary at genus level. The page links to those
genus pages rather than paraphrasing them here.
"""
import csv
import json
import re
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "raw"
SPECIES_CSV = RAW / "MDD_v2.5_6904species.csv"
SYN_CSV = RAW / "Species_Syn_v2.5.csv"
RECORD = "https://zenodo.org/api/records/21654811/files/%s/content"
OUT = HERE / "chiroptera_name_history.json"
ORDER = "Chiroptera"
MSW3_YEAR = 2005

# synonym-table statuses that name a distinct taxon now folded into the
# species (as opposed to respellings and recombinations of one name)
SYNONYM_STATUSES = {"available", "preoccupied", "nomen_novum", "nomen_nudum"}


def fetch(path: Path) -> Path:
    if not path.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {path.name} ...")
        urllib.request.urlretrieve(RECORD % path.name, path)
    return path


def fold(text: str) -> str:
    """Compare names the way a reader would: no accents, ligatures, case."""
    text = text.replace("æ", "ae").replace("Æ", "Ae").replace("œ", "oe").replace("Œ", "Oe")
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def parts(combination: str) -> list[str]:
    """Genus and epithets of a combination, without subgenus or 'var.'."""
    text = re.sub(r"\([^)]*\)", " ", combination)
    text = re.sub(r"\b(var|subsp|forma|f|morpha)\.\s*", " ", text)
    return text.split()


def display(combination: str) -> str:
    """The combination as printed, with case normalised and subgenus kept."""
    out = []
    for i, word in enumerate(combination.split()):
        if i == 0 or word.startswith("("):
            out.append(word[:1].upper() + word[1:])
        else:
            out.append(word if word.endswith(".") else word.lower())
    return " ".join(out)


def year_of(text: str) -> int | None:
    m = re.search(r"\b(1[789]\d\d|20[0-2]\d)\b", text)
    return int(m.group(1)) if m else None


def as_year(text: str) -> int | None:
    return int(text) if text.isdigit() else None


def main() -> None:
    species_rows = [
        r for r in csv.DictReader(fetch(SPECIES_CSV).open(encoding="utf-8-sig"))
        if r["order"] == ORDER
    ]
    syn_rows = [
        r for r in csv.DictReader(fetch(SYN_CSV).open(encoding="utf-8-sig"))
        if r["MDD_order"] == ORDER
    ]
    current = {r["sciName"].replace("_", " "): r for r in species_rows}
    by_species = defaultdict(list)
    for r in syn_rows:
        by_species[r["MDD_species"]].append(r)

    # every binomial a valid species has gone under -> that species, so an old
    # combination ("Eptesicus serotinus") resolves to today's ("Cnephaeus serotinus")
    binomials: dict[str, set[str]] = defaultdict(set)
    for name in current:
        binomials[fold(name)].add(name)
    for r in syn_rows:
        if r["MDD_species"] not in current or r["MDD_original_rank"] != "species":
            continue
        p = parts(r["MDD_original_combination"])
        if len(p) == 2 and not p[0].endswith("."):
            binomials[fold(" ".join(p))].add(r["MDD_species"])

    def resolve(ref: str, home: str) -> str | None:
        """'M. muricola', 'Myotis muricola' or bare 'bonariensis' -> species."""
        words = ref.replace("_", " ").split()
        if not words:
            return None
        home_genus = home.split()[0]
        if len(words) == 1:
            words = [home_genus, words[0]]
        genus, epithet = words[0], fold(words[-1])
        if not genus.endswith("."):
            hits = binomials.get(fold(genus + " " + epithet), set()) - {home}
            if len(hits) == 1:
                return next(iter(hits))
        initial = fold(genus[0])
        candidates = [n for n in current
                      if n != home and fold(n.split()[1]) == epithet and fold(n[0]) == initial]
        if len(candidates) > 1:
            candidates = [n for n in candidates if n.split()[0] == home_genus] or candidates
        if len(candidates) == 1:
            return candidates[0]
        # an abbreviation of a genus the species has since left
        hits = {sp for key, names in binomials.items() for sp in names
                if sp != home and key.split()[1:] == [epithet] and key[0] == initial}
        return next(iter(hits)) if len(hits) == 1 else None

    refs: list[list] = []      # [text, year, doi] -- shared, cited by index
    ref_index: dict[str, int] = {}

    def citations(row: dict) -> list[int]:
        out = []
        for text in row["taxonomyNotesCitation"].split("|"):
            text = text.replace("_", "").strip()
            if not text or text == "NA":
                continue
            if text not in ref_index:
                doi = re.search(r"(?:doi:\s*|doi\.org/)(10\.\S+?)\.?$", text)
                ref_index[text] = len(refs)
                refs.append([text, year_of(text), doi.group(1) if doi else ""])
            if ref_index[text] not in out:
                out.append(ref_index[text])
        return out

    history: dict[str, dict] = {}
    links: list[tuple[str, str, str, set[int]]] = []  # parent, child, via, candidate years

    for name, row in current.items():
        rows = by_species.get(name, [])
        valid = next((r for r in rows if r["MDD_validity"] == "species"), None)
        epithet = fold(name.split()[1])
        entry: dict = {}

        # ---- the names this species' own name has carried; [0] is the original
        names = []
        if valid:
            tag = "[%s]" % valid["MDD_syn_ID"]
            lineage = [valid] + [
                r for r in rows
                if tag in r["MDD_variant_of"]
                and "name_combination" in r["MDD_nomenclature_status"]
                and "incorrect" not in r["MDD_nomenclature_status"]
            ]
            seen = set()
            for r in sorted(lineage, key=lambda r: (r is not valid, r["MDD_year"] or "9999")):
                p = parts(r["MDD_original_combination"])
                if len(p) < 2 or any(w.endswith(".") for w in p):
                    continue  # "C. p. faini" -- an abbreviation, not a name
                key = fold(" ".join(p))
                if key in seen:
                    continue
                if len(p) == 3 and fold(p[1]) == fold(p[2]) and r is not valid:
                    continue  # nominotypical subspecies: says only that it had some
                seen.add(key)
                item = {"n": display(r["MDD_original_combination"]), "y": as_year(r["MDD_year"]),
                        "a": r["MDD_author"], "key": key}
                if len(p) == 3:
                    parent = resolve(p[0] + " " + p[1], name)
                    if parent:
                        item["of"] = parent
                names.append(item)
            if valid["MDD_original_rank"] != "species":
                entry["rank"] = valid["MDD_original_rank"].replace("_", " ")
            if valid["MDD_authority_link"] not in ("", "NA"):
                entry["link"] = valid["MDD_authority_link"]
        if not any(n["key"] == fold(name) for n in names):
            names.append({"n": name, "y": None, "a": "", "key": fold(name)})

        # ---- subspecies-of evidence, and when it first stood as a species again
        as_ssp = [n for n in names if n.get("of")]
        if as_ssp:
            first_ssp = min((n["y"] for n in as_ssp if n["y"]), default=0)
            later = [n for n in names if not n.get("of") and len(n["key"].split()) == 2
                     and n["y"] and n["y"] >= first_ssp]
            raised = min((n["y"] for n in later), default=None)
            for parent in dict.fromkeys(n["of"] for n in as_ssp):
                links.append((parent, name, "s", {raised} if raised else set()))
        entry["names"] = [[n["n"], n["y"], n["a"]] + ([n["of"]] if n.get("of") else []) for n in names]

        # ---- MDD's own notes
        notes = row["taxonomyNotes"] if row["taxonomyNotes"] != "NA" else ""
        cites = citations(row)
        if notes:
            entry["notes"] = notes
        if cites:
            entry["cites"] = cites

        def note_years(*epithets: str) -> set[int]:
            """Citation years that can date this clause: those naming either
            species, else all of them -- the floor below picks among them."""
            dated = [refs[i] for i in cites if refs[i][1]]
            relevant = {r[1] for r in dated if any(e and e in fold(r[0]) for e in epithets)}
            return relevant or {r[1] for r in dated}

        for clause in re.split(r";\s*", notes):
            for m in re.finditer(r"split from (_?[A-Z]?[a-z]*\.? ?[a-z]+_?)", clause):
                parent = resolve(m.group(1), name)
                if parent:
                    links.append((parent, name, "n", note_years(epithet, fold(parent.split()[1]))))
            m = re.search(r"populations previously (?:attributed to|included (?:under|in)) (_?[A-Z]\. [a-z]+_?)", clause)
            if m and not clause.startswith("previously included populations"):
                parent = resolve(m.group(1), name)
                if parent:
                    links.append((parent, name, "n", note_years(epithet)))
            m = re.match(r"previously included (?:populations now attributed to )?(.+)", clause)
            if m:
                for ref in re.split(r",\s*(?:and\s+)?|\s+and\s+", m.group(1)):
                    ref = re.sub(r"\(.*", "", ref).strip()
                    if not re.fullmatch(r"_?[A-Z]\. [a-z]+_?|[a-z]+", ref):
                        continue
                    child = resolve(ref, name)
                    if child:
                        links.append((name, child, "n", note_years(fold(child.split()[1]))))
            m = re.search(r"moved from (?:the recently described )?([A-Z][a-z]+) to (?:the recently described )?([A-Z][a-z]+)", clause)
            if m:
                entry.setdefault("moves", []).append([m.group(1), m.group(2)])

        # ---- the two reference checklists: the name there, or null if absent
        msw3 = row["MSW3_sciName"].replace("_", " ")
        if row["MSW3_matchtype"] in ("sciname match", "oldname match", "manual") and msw3 not in ("NA", ""):
            if msw3 != name:
                entry["msw3"] = msw3
        else:
            entry["msw3"] = None
        cmw = row["CMW_sciName"].replace("_", " ")
        if cmw in ("NA", ""):
            entry["cmw"] = None
        elif cmw != name:
            entry["cmw"] = cmw

        # ---- other names (distinct taxa) now folded into this species
        syns = []
        for r in rows:
            if r is valid or r["MDD_validity"] != "synonym":
                continue
            if not set(r["MDD_nomenclature_status"].split(" | ")) & SYNONYM_STATUSES:
                continue
            item = [display(r["MDD_original_combination"]), r["MDD_author"], as_year(r["MDD_year"])]
            if r["MDD_nomenclature_status"] != "available":
                item.append(r["MDD_nomenclature_status"].replace("_", " "))
            syns.append(item)
        if syns:
            entry["syn"] = sorted(syns, key=lambda s: (s[2] or 9999, s[0]))

        history[name] = entry

    # A species MSW3 did not list was not yet split in 2005, whatever an older
    # name usage suggests (Eptesicus isabellinus appears in 1951, but was split
    # from E. serotinus by Juste et al. 2013). MDD's cited year beats a
    # first-usage year, which only bounds when Hesperomys saw the name.
    #
    # One author using a name as a subspecies is not a split. Without an MDD
    # note, a subspecies usage only links two species when the child was
    # described as a subspecies, or was not a species in MSW3 -- otherwise
    # Myotis macrodactylus, a species before and after one 1906 usage, would
    # read as "split 1906". The usage still shows in the child's name list.
    pairs: dict[tuple[str, str], dict] = {}
    for parent, child, via, years in links:
        if parent == child:
            continue
        pairs.setdefault((parent, child), {}).setdefault(via, set()).update(years)
    for (parent, child), rec in list(pairs.items()):
        lumped = "rank" in history[child] or history[child].get("msw3", "") is None
        if "n" not in rec and not lumped:
            del pairs[(parent, child)]
    for (parent, child), rec in pairs.items():
        floor = MSW3_YEAR if history[child].get("msw3", "") is None else 0
        year = None
        for via in ("n", "s"):
            usable = [y for y in rec.get(via, ()) if y >= floor]
            if usable:
                year = min(usable)
                break
        via = "".join(sorted(rec))
        history[child].setdefault("from", []).append([parent, year, via])
        history[parent].setdefault("into", []).append([child, year, via])
    for entry in history.values():
        for key in ("from", "into"):
            if key in entry:
                entry[key].sort(key=lambda r: (r[1] or 9999, r[0]))

    payload = {
        "_meta": {
            "source": "Mammal Diversity Database v2.5 — species and synonym tables",
            "sourceDoi": "10.5281/zenodo.21654811",
            "note": "Name years are the first use recorded by MDD/Hesperomys: a lower bound, "
                    "not always the date of the taxonomic act.",
            "splitLinks": len(pairs),
            "fields": {
                "names": "[combination, first year, first user, parent species if a subspecies of it]; [0] is the original",
                "rank": "original rank, when not species",
                "link": "original description",
                "from/into": "[species, year or null, via: n = MDD note, s = once its subspecies]",
                "msw3/cmw": "name in that checklist when different; null = not a species there",
                "moves": "[from genus, to genus], per MDD note",
                "notes": "MDD taxonomyNotes",
                "cites": "indices into refs",
                "syn": "[original combination, author, year, status when not available]",
            },
        },
        "refs": refs,
        "species": history,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    renamed = sum(1 for v in history.values() if v.get("msw3"))
    undated = sum(1 for v in history.values() for r in v.get("from", []) if r[1] is None)
    print(f"Wrote {OUT.name}: {len(history)} species, {len(pairs)} split links "
          f"({undated} undated), {renamed} renamed since MSW3, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
