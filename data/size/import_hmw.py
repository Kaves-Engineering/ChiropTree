"""Import forearm length and body mass from every species account of Handbook
of the Mammals of the World vol. 9, Bats (Wilson & Mittermeier 2019).

Each HMW account opens its "Descriptive notes" with the external measurements
compiled from the literature: "Head-body 75-99 mm, ..., forearm 68-5-81 mm;
weight 27-45 g." This importer reads the forearm and weight figures of every
account that data/size/fetch_hmw.py cached from Plazi TreatmentBank and writes
data/size/hmw-2019.csv. Every row is the range HMW prints (statistic
range_only, range_type min_max), or a single value where HMW prints one.
build_size.py uses these ranges as the reference range of each species: a
measured value well outside it is kept on the card but left out of the
headline (see REFERENCE_RANGES there).

Reading the OCR. Plazi's OCR of HMW turns decimal points into hyphens, colons
or stray characters, so "forearm 42-9-49 mm" is 42.9-49 mm. A figure is split
into digit groups and every way of reading it as one value or a low-high range
is tried, where a decimal part has one digit. A reading must rise (low < high)
and stay within a plausible spread for one species (RATIO). Two separators
decide a reading on their own: an en or em dash always separates a range, and
a hyphen followed by a space and one digit ("42- 3") is a decimal point. When more
than one reading survives (weight "4-8-6 g": 4.8-6 or 4-8.6), the row spans
every reading (4-8.6), which is still a safe reference range, and says so;
when none survives the figure is not imported. Both kinds are listed in
data/size/unresolved/hmw-2019-figures.md to be read by hand. ("3-9 g", two
digit groups, is read as the range 3-9: HMW prints ranges far more often than
a lone decimal value.) Checked against
the 67 forearms read by hand earlier (import_literature_forearm.py, Nov 2026):
all 67 agree.

A mass figure that cannot belong to the account's own forearm (more than
MISFIT_SIGMAS robust SDs off a mass-forearm line fitted to all accounts) goes
to the review file too: "611 g" for the 40 mm Lasiurus minor is HMW's 6-11 g
with the hyphen lost.

Several figures per account: HMW sometimes gives sexes apart ("57-65 mm
(males) and 56-67 mm (females)"); those become male and female rows.

Subspecies. Some accounts print a block of figures per subspecies: "forearm
59-68 mm; weight 43-59 g for subspecies intermedius. ... forearm 69-77 mm;
weight 55-90 g for subspecies palmarum." Every forearm and weight figure in
the notes is read, and a figure belongs to a subspecies when its own sentence
names one of the epithets the account lists under "Subspecies and
Distribution" ("for subspecies X", "for X", "Subspecies X:", "Nominate X",
"subspecies X are smallest (forearm ...)"). Requiring a listed epithet is what
keeps out figures HMW quotes for other species ("Horsfield's Myotis is smaller
(forearm 35-38 mm)"). A subspecies MDD v2.5 ranks as a species takes its own
figures (A. lituratus intermedius -> Artibeus intermedius, Dobsonia
moluccensis magna -> D. magna); the other subspecies are pooled into one row
for the account's species. A later figure that names no listed subspecies is
not imported and is listed for review. A species-wide figure from an account
whose subspecies include a species MDD now splits off says so in its notes.
Checked by hand, Nov 2026, on the nine accounts that print several forearm
ranges (A. jamaicensis, A. lituratus, A. planirostris, D. moluccensis,
M. orianae, M. megalophylla, M. macrotarsus, P. vampyrus, S. adrianae).

Which species: each account's text opens with its number, English name and
binomial ("162. Great Evening Bat Ia io French: ..."). That printed binomial is
used, not Plazi's metadata title, which is wrong for a few accounts (the
account of Ia io is titled Pharotis imogene, R. io's is titled R. innoxius)
and carries OCR typos in others ("Pleronotus", "Anthops omatus"). The name
resolves against MDD v2.5 like every other source. Where MDD lumps species
HMW keeps apart (R. kahuzi into R. ruwenzorii), the accounts' figures are
pooled into one row that says so. EXCLUDE lists figures known to be wrong.

Run:  uv run data/size/fetch_hmw.py  (once; caches the XML)
      uv run data/size/import_hmw.py
"""
import difflib
import html
import json
import math
import re
import statistics
from collections import defaultdict
from itertools import product
from pathlib import Path

from size_lib import (
    RAW,
    REVIEW_DIR,
    SizeResolver,
    check_raw,
    number,
    report,
    write_review,
    write_rows,
)

HERE = Path(__file__).parent
MANIFEST = HERE / "hmw-2019-sources.json"
PLAZI = RAW / "plazi"
REFERENCE = "hmw-2019"
AMBIGUOUS_FILE = REVIEW_DIR / "hmw-2019-figures.md"

# the widest max/min one species' range plausibly spans
RATIO = {"forearm_length": 1.6, "body_mass": 4.0}
# any bat (forearm mm; mass g, after a kg figure is converted); kg figures are
# checked in kg, so the mass bounds allow both
BOUNDS = {"forearm_length": (18, 240), "body_mass": (0.3, 1700)}
MISFIT_SIGMAS = 4.0
# "¢" (cent sign) is how the OCR often renders a "g" or the "c." of "c. 13 g"
UNIT = {"forearm_length": r"mm", "body_mass": r"(?:kg|g|�|¢)"}
APPROX = r"(?:c\s*¢?\s*\.|¢\s*\.?)\s*"
KEYWORD = {"forearm_length": r"(?i)\bforearms?\b(?:\s+lengths?)?(?:\s+of)?", "body_mass": r"(?i)\bweight\b"}
# Where a subspecies is named next to its figures, within one sentence: after
# them ("... for subspecies X", "for nominotypical X", "for X") or before them
# ("Subspecies X:", "Nominate X ... has forearm", "subspecies X are smallest (").
LABEL_AFTER = re.compile(r"\bfor\s+(?:the\s+)?(?:subspecies\s+|nominotypical\s+|nominate\s+)?([a-z]{3,})\b")
LABEL_BEFORE = re.compile(r"(?i:subspecies|nominate|nominotypical)\s+(?:(?:is|are)\s+)?([a-z]{3,})\b")
# "A. l. intermedius J. A. Allen, 1897" in the Subspecies and Distribution section
SUBSPECIES_ENTRY = re.compile(r"\b[A-Z]\s?\.\s?[a-z]\s?\.\s?([a-z]{3,})")
SENTENCE_END = re.compile(r"\.\s+(?=[A-Z])")
NUMBER = r"\d[\d\s\-–—:·.*�]*\d|\d"
# "162. Great Evening Bat Ia io French: ..."
HEADER = re.compile(r"^\s*\d+\s*\.\s*[^.]{0,80}?\b([A-Z][a-z]+ [a-z]+)\s+French\b")

# OCR misreadings of account names (header or title), checked by hand
TYPOS = {
    "Anthops omatus": "Anthops ornatus",
    "Balantiopteryx infosca": "Balantiopteryx infusca",
    "Glauconycteris poensts": "Glauconycteris poensis",
    "Leptonyctenis curasoae": "Leptonycteris curasoae",
    "Lonchorhina fernandez": "Lonchorhina fernandezi",
    "Pipustrellus sturdeei": "Pipistrellus sturdeei",
    "Platyrriunus aquilus": "Platyrrhinus aquilus",
    "Platyrrhainus brachycephalus": "Platyrrhinus brachycephalus",
    "Pleronotus fuscus": "Pteronotus fuscus",
    "Pleronotus macleayii": "Pteronotus macleayii",
    "Pleronotus quadridens": "Pteronotus quadridens",
}
# (MDD species, trait) -> why HMW's printed figure is not used
EXCLUDE = {
    ("Hipposideros hypophyllus", "forearm_length"): "HMW prints 38-49 mm; the species' own specimens measure 37.1-40.0 mm (Srinivasulu et al. 2014), so the printed range is taken as an error.",
}


def text_of(xml: str) -> str:
    return html.unescape(" ".join(re.sub(r"<[^>]+>", " ", xml).split()))


def account_name(xml: str) -> str | None:
    match = HEADER.match(text_of(xml[xml.find("</mods:mods>"):]))
    return match.group(1) if match else None


def descriptive_notes(text: str) -> str:
    start = text.find("Descriptive notes")
    return text[start:start + 1200] if start >= 0 else ""


def listed_subspecies(text: str, epithet: str) -> set[str]:
    """The subspecies epithets an account lists, plus its own (the nominate)."""
    start = text.find("Subspecies and Distribution")
    end = text.find("Descriptive notes", start)
    section = text[start:end] if start >= 0 and end > start else ""
    return {m.group(1) for m in SUBSPECIES_ENTRY.finditer(section)} | {epithet}


def sentence_around(notes: str, start: int, end: int) -> tuple[int, int]:
    begin = max([m.end() for m in SENTENCE_END.finditer(notes, 0, start)], default=0)
    after = SENTENCE_END.search(notes, end)
    return begin, after.start() if after else len(notes)


def listed_as(word: str, listed: set[str]) -> str:
    """The listed epithet a word names, allowing one OCR slip: the notes of
    A. planirostris print "trinitatis" where its list has "trinatatis", and
    S. adrianae's print "carpana" for "caripana"."""
    if word in listed:
        return word
    close = difflib.get_close_matches(word, listed, n=1, cutoff=0.85) if len(word) >= 6 else []
    return close[0] if close else ""


def subspecies_label(notes: str, start: int, end: int, listed: set[str]) -> str:
    """The listed subspecies a figure chain is printed for, or ''."""
    begin, finish = sentence_around(notes, start, end)
    for match in LABEL_AFTER.finditer(notes, end, finish):
        if found := listed_as(match.group(1), listed):
            return found
    before = [found for m in LABEL_BEFORE.finditer(notes, begin, start) if (found := listed_as(m.group(1), listed))]
    return before[-1] if before else ""


def readings(figure: str, trait: str) -> set[tuple[float, float]]:
    """Every (low, high) reading of an OCR figure; low == high is one value."""
    parts = re.split(r"([^\d]+)", figure.strip())
    digits, separators = parts[0::2], parts[1::2]
    strict = []
    for sep, following in zip(separators, digits[1:]):
        if re.search(r"[–—]", sep):
            strict.append(["range"])
        elif re.fullmatch(r"[.·*:]", sep) or (re.fullmatch(r"-\s+", sep) and len(following) == 1):
            strict.append(["decimal"])
        else:
            strict.append(["range", "decimal"])
    found = _readings(digits, strict, trait)
    if not found:  # a separator broke the rules ("0.5- 1 kg"): read every one freely
        found = _readings(digits, [["range", "decimal"]] * len(separators), trait)
    if len(digits) == 2 and len(found) > 1:
        # "3-9 g": HMW prints a range far more often than a lone decimal value
        found = {r for r in found if r[0] != r[1]}
    return found


def _readings(digits: list[str], options: list[list[str]], trait: str) -> set[tuple[float, float]]:
    found = set()
    for choice in product(*options):
        values, current, ok = [], digits[0], True
        for kind, digit in zip(choice, digits[1:]):
            if kind == "decimal":
                if "." in current or len(digit) != 1:
                    ok = False
                    break
                current += "." + digit
            else:
                values.append(current)
                current = digit
        values.append(current)
        if not ok or len(values) > 2:
            continue
        low, high = float(values[0]), float(values[-1])
        if low <= 0 or high < low or (len(values) == 2 and high == low):
            continue
        if high / low > RATIO[trait] or not BOUNDS[trait][0] <= low <= high <= BOUNDS[trait][1]:
            continue
        found.add((low, high))
    return found


def figure_chains(notes: str, trait: str) -> list[tuple[list[dict], int, int]]:
    """Every run of figures right after the trait's keyword, with where it sits:
    "forearm 57-65 mm (males) and 56-67 mm (females)". Only figures chained by
    "and" or a comma count, so the next measurement ("..., tibia 45 mm") is
    never read as this one."""
    figure = re.compile(rf"[:.]?\s*(?:of\s+(males|females)\s+)?({APPROX})?({NUMBER})\s*({UNIT[trait]})(?![a-z])\s*(?:\(([^)]*)\))?")
    joint = re.compile(r"\s*(?:,\s*and|,|and|or)\s+")
    chains = []
    for match in re.finditer(KEYWORD[trait], notes):
        position, out, end = match.end(), [], match.end()
        while True:
            found = figure.match(notes, position + len(re.match(r"\s*", notes[position:]).group(0)))
            if not found:
                break
            out.append({"figure": found.group(3), "unit": found.group(4),
                        "qualifier": (found.group(5) or found.group(1) or "").strip(),
                        "verbatim": found.group(0).strip(), "approx": bool(found.group(2))})
            end = found.end()
            link = joint.match(notes, found.end())
            if not link:
                break
            position = link.end()
        if out:
            chains.append((out, match.start(), end))
    return chains


def figures(notes: str, trait: str) -> list[dict]:
    """The first run of figures for the trait (the species-wide one)."""
    chains = figure_chains(notes, trait)
    return chains[0][0] if chains else []


def split_species(resolver: SizeResolver, genus: str, epithet: str, account_id: str):
    """The MDD species a subspecies now is, when MDD ranks it as one."""
    mark = len(resolver.unresolved)
    species, method = resolver.resolve(f"{genus} {epithet}")
    del resolver.unresolved[mark:]
    if species and method == "exact" and species["id"] != account_id:
        return species
    return None


def sex_of(qualifier: str) -> str:
    q = qualifier.lower().strip()
    if re.fullmatch(r"males?", q):
        return "male"
    if re.fullmatch(r"females?", q):
        return "female"
    return "pooled"


def resolve_account(resolver: SizeResolver, header: str | None, title: list[str]):
    """The account's name and MDD species: the printed header first, then the
    title, then a title's subspecies epithet as a species ("Pipistrellus tenuis
    subsp. westralis" is MDD's P. westralis); TYPOS fixes OCR in either."""
    names = [header, " ".join(title[:2])]
    if len(title) > 3 and title[2] == "subsp.":
        names.insert(0, f"{title[0]} {title[3]}")
    names = [TYPOS.get(n, n) for n in names if n]
    for name in dict.fromkeys(names):
        mark = len(resolver.unresolved)
        species, method = resolver.resolve(name)
        if species:
            del resolver.unresolved[mark:]
            if name not in (header, " ".join(title[:2])):
                method = "manual"
            return name, species, method
        del resolver.unresolved[mark:]
    resolver.resolve(names[0])  # record the failure once
    return names[0], None, None


def collect(manifest: dict, resolver: SizeResolver) -> tuple[dict, list]:
    """(MDD id, trait, sex) -> figures from one or more accounts; plus unreadable figures."""
    pooled, ambiguous = defaultdict(list), []
    for doc, meta in sorted(manifest.items()):
        title = html.unescape(meta["title"]).split()
        if len(title) < 2 or not title[1].islower():
            continue  # a genus or family treatment
        xml = (PLAZI / f"{doc}.xml").read_text(encoding="utf-8", errors="replace")
        printed, species, method = resolve_account(resolver, account_name(xml), title)
        if not species:
            continue
        binomial = species["sciName"].replace("_", " ")
        text = text_of(xml)
        notes = descriptive_notes(text)
        genus, epithet = printed.split()[:2]
        listed = listed_subspecies(text, epithet)
        # subspecies of this account that MDD now ranks as species of their own
        split_off = {e: s for e in sorted(listed - {epithet})
                     if (s := split_species(resolver, genus, e, species["id"]))}
        for trait in ("forearm_length", "body_mass"):
            if (binomial, trait) in EXCLUDE:
                continue
            for i, (chain, start, end) in enumerate(figure_chains(notes, trait)):
                label = subspecies_label(notes, start, end, listed)
                if i > 0 and not label:
                    # a later figure with no subspecies named: possibly another
                    # species HMW compares this one with, so it is not used
                    for fig in chain:
                        ambiguous.append((binomial, trait, fig["verbatim"],
                                          "a further figure that names no listed subspecies; not imported", doc))
                    continue
                target, target_method = species, method
                if label in split_off:
                    target, target_method = split_off[label], "manual"
                for fig in chain:
                    found = readings(fig["figure"], trait)
                    if len(found) != 1:
                        ambiguous.append((binomial, trait, fig["verbatim"], sorted(found), doc))
                        if not found:
                            continue
                        # every reading lies inside their span, so the span is safe
                        # as a reference range even before a person reads the figure
                        fig["readings"] = sorted(found)
                    low, high = min(r[0] for r in found), max(r[1] for r in found)
                    if fig["unit"] == "kg":
                        low, high = low * 1000, high * 1000
                    fig["subspecies"] = label
                    if target is not species:
                        fig["moved_from"] = printed
                    elif not label and split_off:
                        fig["covers"] = [f"{genus} {e}" for e in split_off]
                    pooled[(target["id"], trait, sex_of(fig["qualifier"]))].append(
                        {"low": low, "high": high, "fig": fig, "doc": doc, "page": meta["page"],
                         # a moved figure is printed for the trinomial
                         "printed": printed if target is species else f"{printed} {label}",
                         "method": target_method})
    return pooled, ambiguous


def size_row(mdd_id: str, trait: str, sex: str, figs: list[dict]) -> dict:
    low, high = min(f["low"] for f in figs), max(f["high"] for f in figs)
    accounts = sorted({f["printed"] for f in figs})
    qualifiers = [f["fig"]["qualifier"] for f in figs if f["fig"]["qualifier"] and sex_of(f["fig"]["qualifier"]) == "pooled"]
    notes = ["Single value printed by HMW." if low == high else "Range compiled from the literature by HMW."]
    if len(accounts) > 1:
        notes.append(f"Spans HMW's accounts of {' and '.join(accounts)}, which MDD v2.5 treats as one species.")
    if len(figs) > 1 and qualifiers:
        notes.append(f"Spans HMW's {len(figs)} figures ({'; '.join(qualifiers)}).")
    elif qualifiers:
        notes.append(f"HMW's figure is for: {qualifiers[0]}.")
    moved = sorted({f["printed"] for f in figs if f["fig"].get("moved_from")})
    if moved:
        notes.append(f"HMW prints it in the account of {figs[0]['fig']['moved_from']}, for subspecies "
                     f"{', '.join(m.split()[-1] for m in moved)}, which MDD v2.5 ranks as this species.")
    subspecies = sorted({f["fig"]["subspecies"] for f in figs if f["fig"].get("subspecies") and not f["fig"].get("moved_from")})
    if subspecies:
        notes.append(f"HMW gives it per subspecies; spans {', '.join(subspecies)}.")
    covers = sorted({c for f in figs for c in f["fig"].get("covers", [])})
    if covers:
        named = covers[0] if len(covers) == 1 else ", ".join(covers[:-1]) + " and " + covers[-1]
        notes.append(f"HMW's figure is for the species as it treats it, which includes {named}, "
                     + ("a separate species" if len(covers) == 1 else "separate species") + " in MDD v2.5.")
    for f in figs:
        if "readings" in f["fig"]:
            options = " or ".join(f"{lo:g}-{hi:g}" if lo != hi else f"{lo:g}" for lo, hi in f["fig"]["readings"])
            notes.append(f"The OCR of \"{f['fig']['verbatim']}\" reads as {options}; the row spans every reading.")
    if any(f["fig"]["approx"] for f in figs):
        notes.append("HMW gives it as approximate (c.).")
    single = low == high
    by_doc = {f["doc"]: f for f in figs}
    return {
        "observation_id": f"{REFERENCE}-{mdd_id}-{sex}", "mdd_id": mdd_id,
        "verbatim_taxon_name": " / ".join(accounts),
        "taxon_match_method": figs[0]["method"] if len(accounts) == 1 else "manual",
        "reference_id": REFERENCE,
        "locator": "; ".join(f"p. {f['page']}, Descriptive notes; Plazi treatment {d}" for d, f in by_doc.items()),
        "trait": trait, "basis": "measured",
        "statistic": "single" if single else "range_only",
        "value": number(low) if single else number((low + high) / 2),
        "value_min": "" if single else number(low), "value_max": "" if single else number(high),
        "range_type": "" if single else "min_max", "sex": sex, "data_year": "2019",
        "verbatim_value": " | ".join(f["fig"]["verbatim"] for f in figs),
        "notes": " ".join(notes),
    }


def write_ambiguous(ambiguous: list) -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# HMW 9 figures not imported", "",
             "Their OCR allows more than one reading, or none; read them by hand.", "",
             "| Species | Trait | OCR text | Readings | Plazi docId |", "|---|---|---|---|---|"]
    lines += [f"| {s} | {t} | {v} | {r or 'none'} | {d} |" for s, t, v, r, d in ambiguous]
    AMBIGUOUS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def drop_misfit_masses(pooled: dict, ambiguous: list) -> None:
    """Move to review the mass figures that cannot belong to the account's own
    forearm: off a log-log mass-forearm line fitted to all accounts by more
    than MISFIT_SIGMAS robust SDs. This catches an OCR that lost a separator,
    "611 g" for Lasiurus minor (forearm 37-42 mm) where HMW printed 6-11 g."""
    def mid(figs):
        return math.log((min(f["low"] for f in figs) + max(f["high"] for f in figs)) / 2)

    forearm, mass = defaultdict(list), defaultdict(list)
    for (mdd_id, trait, _), figs in pooled.items():
        (forearm if trait == "forearm_length" else mass)[mdd_id] += figs
    pairs = {i: (mid(forearm[i]), mid(mass[i])) for i in mass if i in forearm}
    slope, intercept = statistics.linear_regression([x for x, _ in pairs.values()], [y for _, y in pairs.values()])
    residuals = {i: y - (intercept + slope * x) for i, (x, y) in pairs.items()}
    centre = statistics.median(residuals.values())
    sd = 1.4826 * statistics.median(abs(r - centre) for r in residuals.values())
    for i, r in residuals.items():
        if abs(r - centre) > MISFIT_SIGMAS * sd:
            for key in [k for k in pooled if k[0] == i and k[1] == "body_mass"]:
                for f in pooled.pop(key):
                    expected = math.exp(intercept + slope * pairs[i][0] + centre)
                    ambiguous.append((f["printed"], "body_mass", f["fig"]["verbatim"],
                                      f"does not fit its forearm (about {expected:.0f} g expected)", f["doc"]))


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    check_raw({str(PLAZI / f"{doc}.xml"): meta["sha256"] for doc, meta in manifest.items()})
    resolver = SizeResolver()
    pooled, ambiguous = collect(manifest, resolver)
    drop_misfit_masses(pooled, ambiguous)
    rows = [size_row(mdd_id, trait, sex, figs) for (mdd_id, trait, sex), figs in sorted(pooled.items())]
    write_rows(REFERENCE, rows)
    write_review(REFERENCE, resolver.unresolved)
    write_ambiguous(ambiguous)
    report(REFERENCE, rows, resolver)
    print(f"  {len(ambiguous)} figures left for review in {AMBIGUOUS_FILE.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
