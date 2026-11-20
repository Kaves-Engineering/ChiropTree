"""Import forearm length and body mass printed in the running text of bat
species treatments that Plazi digitised from journal articles and monographs.

data/size/fetch_plazi_bats.py lists every bat treatment through Plazi's
SPARQL endpoint and caches the XML of those outside HMW 9 and the MSW
checklists (species descriptions, revisions, regional inventories). This
importer reads their text and writes data/size/plazi-literature.csv. Each
row's upstream_source names the article (authors, year, title, DOI), so
build_size.py counts every article as its own independent study; the
locator names the Plazi treatment, so data/build_claims.py links the value
to the treatment page with the figure highlighted.

Reading is deliberately strict; a figure is imported only when all hold:

- it follows a forearm keyword ("forearm", "forearm length", "FA", "FAL")
  or a mass keyword ("body mass", "weight", "weighed", "mass", "BM") with
  nothing but a connector between them ("of", "=", ":", "averaging", ...);
- it has the shape of a single value, a range, or a mean with SD and/or a
  range and n; a mass figure must carry its unit (g or kg), a forearm figure
  may omit mm but must not be followed by another bare number (that is
  flattened table text);
- it is not approximate or a threshold ("about", "c.", "<", "up to", ...),
  not inside parentheses that cite a publication year, and not in a sentence
  that cites an author and year before it ("Thomas (1914) reported a
  forearm length of 42 mm"): those are values quoted from the literature;
- it is not followed by a comparison ("than", "compared", "vs") or by "in"
  or "for" and another species' name, and a mass is not one weighed with an
  embryo;
- it belongs to the treatment's own species. Plazi tags every taxon name in
  the text. When the sentence names another species, the figure is kept only
  if the nearest species named before it is the treatment's own species
  ("X is larger (FA 50-55 mm) than Y (FA 45-48 mm)" keeps the first figure,
  drops the second);
- it is not in a section that is about other taxa or names: keys,
  nomenclature, synonymies, reference lists, etymology, figure captions;
- it is plausible: inside the bounds for any bat and, where HMW 9 gives the
  species a range, within -20% / +25% of that range. A figure that fails
  only this check is listed in data/size/unresolved/plazi-literature-figures.md
  for a person to read, never imported.

Sex is taken from "males"/"females" right after the figure or just before
it; otherwise the row is pooled. A single value next to "holotype" is the
holotype's (n = 1); holotype values are dropped when the same treatment gives
a series for that trait and sex. Repeats of one figure within a treatment
(diagnosis and description) become one row.

Articles whose DOI is already a size reference (hand-read by
import_literature_forearm.py or a dedicated importer) are skipped, so no
study is counted twice. Measurement tables are not in Plazi's treatment XML
(only links to table.plazi.org); import_plazi_tables.py reads them.

Names: the treatment title's binomial (a subgenus in parentheses dropped)
resolves against MDD v2.5 like every other source; a trinomial title is read
as its species.

Raw files: data/raw/size/plazi/<docId>.xml, pinned in
data/size/plazi-literature-sources.json.
Run:  uv run data/size/fetch_plazi_bats.py   (once; caches the XML)
      uv run data/size/import_plazi_literature.py
"""
import csv
import html
import json
import re
from collections import defaultdict
from pathlib import Path

from size_lib import RAW, REVIEW_DIR, SizeResolver, check_raw, number, report, write_review, write_rows

HERE = Path(__file__).parent
MANIFEST = HERE / "plazi-literature-sources.json"
PLAZI = RAW / "plazi"
REFERENCE = "plazi-literature"
FIGURE_REVIEW = REVIEW_DIR / "plazi-literature-figures.md"

SKIP_SECTIONS = {"key", "nomenclature", "reference_group", "synonymic_list", "etymology",
                 "vernacular_names", "multiple"}
BOUNDS = {"forearm_length": (18.0, 240.0), "body_mass": (0.3, 1700.0)}
HMW_SLACK = (0.80, 1.25)
KEYWORD = {
    "forearm_length": re.compile(r"\b(?:[Ff]orearms?(?:\s+lengths?)?|FA|FAL|LFA)\b"),
    "body_mass": re.compile(r"\b(?:[Bb]ody\s+(?:mass|weight)|[Ww]eigh(?:ts?|ed|ing|s)|[Mm]ass|BM(?=\s*[=:]))\b"),
}
CONNECTOR = re.compile(
    r"(?:\s*\((?:FA|FAL|BM|W|BW|in g|g|mm)\))?"
    r"(?:\s*(?:of|=|:|is|was|were|averag\w*|ranged?|ranging|from|between|measur\w*|varies|varied|in|the|holotype|adults?)\b|\s*[=:,])*"
    r"\s*")
# old OCR prints the decimal point as an apostrophe or raised dot ("37 '7 mm")
NUM = r"\d{1,4}(?:,\d{1,3}|\s?['’·]\s?\d{1,2}|\.\d{1,3})?"
DASH = r"\s*(?:[-–—−‒‑‐]|to|and)\s*"
FIGURE = re.compile(rf"""
    (?:
        (?P<lo>{NUM})(?:\s*(?:mm|g|kg)\b)?{DASH}(?P<hi>{NUM})(?!\s*(?:±|\+/?-))
      | (?P<list>{NUM}(?:\s*[,/]\s*{NUM})+)(?=\s*(?:mm|g|kg)\b)
      | (?P<mean>{NUM})
        (?:\s*(?:±|\+/?-)\s*(?P<sd>{NUM}))?
        (?:\s*(?P<u0>mm|g|kg)\b)?
        (?:\s*[(\[]\s*(?:range[:\s]*)?(?P<rlo>{NUM}){DASH}(?P<rhi>{NUM})\s*(?:mm|g|kg)?
           \s*(?:[;,]\s*[nN]\s*=\s*(?P<n1>\d+))?\s*[)\]])?
    )
    (?:\s*(?P<unit>mm|g|kg)(?![A-Za-z]))?
    (?:\s*[(,;]?\s*[nN]\s*=\s*(?P<n>\d+)\s*\)?)?
""", re.X)
APPROX = re.compile(r"(?:<|>|≤|≥|~|\b(?:about|c|ca|approx\w*|around|up to|less than|more than|over|under|"
                    r"exceed\w*|at least|nearly|almost|typically|usually)\.?)\s*$", re.I)
SEX_AFTER = re.compile(r"^\s*(?:\(|in|for|of)?\s*(?:the\s+)?(?:adult\s+)?(?P<s>(?:fe)?males?|♂♂?|♀♀?)\b", re.I)
SEX_BEFORE = re.compile(r"(?P<s>\b(?:fe)?males?\b|♂|♀)[^.;]{0,40}$", re.I)
# "Measurements (in mm) and body mass (in g): ... mass, 7.5"
GRAMS_DECLARED = re.compile(r"(?:mass|weight)\s*\((?:in\s+)?g\)|in grams", re.I)
CITED = re.compile(r"\b[A-Z][a-z]+(?:\s+et\s+al\.?|\s+(?:&|and)\s+[A-Z][a-z]+)?,?\s+\(?(?:1[89]\d\d|20[0-2]\d)[a-z]?\)?")
CITATION_YEAR =re.compile(r"\b(1[89]\d\d|20[0-2]\d)[a-z]?\b")
NAME = "\x01"  # marks a tagged taxon name in the text


# ---------------------------------------------------------------- text

def sections(xml: str):
    """(section type, page number, text, [(position, genus, species)]) per subSubSection."""
    xml = re.sub(r"<caption\b.*?</caption>", " ", xml, flags=re.S)
    for match in re.finditer(r"<subSubSection\b([^>]*)>(.*?)</subSubSection>", xml, re.S):
        attrs = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', match.group(1)))
        if attrs.get("type") in SKIP_SECTIONS:
            continue
        text, names = flatten(match.group(2))
        yield attrs.get("type", ""), attrs.get("pageNumber", ""), text, names


def flatten(fragment: str) -> tuple[str, list]:
    out, names, length = [], [], 0
    for token in re.split(r"(<[^>]+>)", fragment):
        if token.startswith("<"):
            if token.startswith("<taxonomicName "):
                attrs = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', token))
                if attrs.get("rank") in ("species", "subspecies") and attrs.get("species"):
                    names.append((length, attrs.get("genus", ""), attrs["species"]))
            continue
        piece = html.unescape(token)
        piece = re.sub(r"\s+", " ", piece)
        if not piece.strip():
            if out and not out[-1].endswith(" "):
                out.append(" ")
                length += 1
            continue
        if out and out[-1].endswith(" ") and piece.startswith(" "):
            piece = piece[1:]
        out.append(piece)
        length += len(piece)
    return "".join(out), names


def sentence_bounds(text: str, position: int) -> tuple[int, int]:
    """Start and end of the sentence around position. A full stop after a
    single capital ("M. fionae") or a common abbreviation does not end one."""
    ends = [m.end() for m in re.finditer(r"\.\s+(?=[A-Z(])", text)
            if not re.search(r"(?:\b[A-Z]|\bsp|\bspp|\bnov|\bal|\bcf|\bvs|\bca|\bc|\bfig|\bFig|\bno|\bp|\bpp)\.\s+$",
                             text[max(0, m.start() - 4):m.end()])]
    start = max([e for e in ends if e <= position], default=0)
    end = min([e for e in ends if e > position], default=len(text))
    return start, end


# ---------------------------------------------------------------- figures

def candidates(text: str, names: list, own: tuple[str, str]):
    """Yield (trait, figure dict) or (trait, None, reason) for every keyword."""
    for trait, keyword in KEYWORD.items():
        for key in keyword.finditer(text):
            joint = CONNECTOR.match(text, key.end())
            start = joint.end()
            figure = FIGURE.match(text, start)
            if not figure or figure.end() == start:
                continue
            verbatim = text[key.start():figure.end()].strip(" ,;(")
            reason = reject(text, names, own, trait, key, figure)
            yield trait, parse(figure, trait, text), verbatim, key.start(), figure.end(), reason


def reject(text: str, names: list, own: tuple[str, str], trait: str, key, figure) -> str:
    between = text[key.end():figure.start()]
    if APPROX.search(text[max(0, key.start() - 12):key.start()] + " " + between):
        return "approximate or threshold"
    if re.search(r"\d", between):
        return "number between keyword and figure"
    following = text[figure.end():figure.end() + 8]
    units = re.findall(r"(?<![A-Za-z])(mm|kg|g)\b", figure.group(0))
    declared = GRAMS_DECLARED.search(text[max(0, key.start() - 300):key.start()])
    if trait == "body_mass" and not set(units) & {"g", "kg"} and not declared:
        return "mass without unit"
    if trait == "forearm_length" and set(units) & {"g", "kg"}:
        return "forearm with a mass unit"
    if re.match(r"\s+\d|[^\s\w.,;:()\[\]]\d", following):
        return "table text"
    if re.match(r"\s*[,/]\s*\d", following):
        return "list of values without a unit"
    if trait == "body_mass" and re.search(r"embryo|fo?etus|pregnan|gravid",
                                          text[max(0, key.start() - 60):figure.end() + 50], re.I):
        return "mass of a pregnant female"
    if re.search(r"\b(?:compared|than|vs\.?|versus|whereas|unlike)\b", text[figure.end():figure.end() + 30]):
        return "comparison"
    # "forearm 39.5-40.4 mm, ... in P. trinitatis": the figure names its species after it
    after = [n for n in names if figure.end() <= n[0] <= figure.end() + 60]
    if after and not same_species(after[0], own) and re.search(
            r"\b(?:in|for|of)\s+(?:the\s+)?$", text[figure.end():after[0][0]]):
        return "figure is for another species"
    # parentheses that cite a publication: a value quoted from the literature
    open_at = text.rfind("(", 0, key.start())
    if open_at > text.rfind(")", 0, key.start()):
        close_at = text.find(")", figure.end())
        inside = text[open_at:close_at if close_at > 0 else figure.end() + 60]
        if CITATION_YEAR.search(inside) or "et al" in inside:
            return "quoted from the literature"
    start, end = sentence_bounds(text, key.start())
    # "Thomas (1914) reported a forearm length of 42 mm": quoted, not measured here
    if CITED.search(text[start:key.start()]):
        return "quoted from the literature"
    in_sentence = [n for n in names if start <= n[0] < end]
    others = [n for n in in_sentence if not same_species(n, own)]
    if others:
        before = [n for n in in_sentence if n[0] <= key.start()]
        if not before or not same_species(before[-1], own):
            return "sentence is about another species"
    return ""


def same_species(name: tuple, own: tuple[str, str]) -> bool:
    _, genus, species = name
    return species == own[1] and (not genus or genus == own[0] or genus[:1] == own[0][:1])


def to_float(text: str | None) -> float | None:
    return float(re.sub(r"\s?[,'’·]\s?", ".", text)) if text else None


def parse(figure, trait: str, text: str) -> dict:
    g = figure.groupdict()
    unit = g["unit"] or g["u0"] or ""
    scale = 1000.0 if unit == "kg" else 1.0
    out = {"n": int(g["n"] or g["n1"]) if (g["n"] or g["n1"]) else None, "unit": unit}
    if g["list"]:
        values = [to_float(v) * scale for v in re.split(r"\s*[,/]\s*(?=\d)", g["list"])]
        if all(abs(v / values[0] - 1) < 0.3 for v in values):
            # several specimens' values: "52.9, 53.0 mm"
            out.update(kind="mean", value=sum(values) / len(values), sd=None, low=min(values),
                       high=max(values), n=len(values), values=values)
        else:
            out.update(kind="single", value=values[0], sd=None, low=None, high=None)
    elif g["lo"]:
        out.update(kind="range", low=to_float(g["lo"]) * scale, high=to_float(g["hi"]) * scale)
    else:
        out.update(kind="mean" if (g["sd"] or g["rlo"] or out["n"]) else "single",
                   value=to_float(g["mean"]) * scale,
                   sd=to_float(g["sd"]) * scale if g["sd"] else None,
                   low=to_float(g["rlo"]) * scale if g["rlo"] else None,
                   high=to_float(g["rhi"]) * scale if g["rhi"] else None)
    return out


def sex_of(text: str, start: int, end: int) -> str:
    after = SEX_AFTER.match(text[end:end + 25])
    hit = after.group("s") if after else None
    if not hit:
        before = SEX_BEFORE.search(text[max(0, start - 50):start])
        hit = before.group("s") if before else None
    if not hit:
        return "pooled"
    return "female" if hit.lower().startswith("fe") or "♀" in hit else "male"


def plausible(fig: dict, trait: str, hmw: dict | None) -> str:
    values = [v for v in (fig.get("value"), fig.get("low"), fig.get("high")) if v is not None]
    low, high = BOUNDS[trait]
    if not all(low <= v <= high for v in values):
        return "outside the bounds for any bat"
    if fig.get("low") is not None and fig.get("high") is not None and not fig["low"] < fig["high"]:
        return "range does not rise"
    if fig.get("value") is not None and fig.get("low") is not None and not fig["low"] <= fig["value"] <= fig["high"]:
        return "mean outside its own range"
    if hmw and not all(hmw[0] * HMW_SLACK[0] <= v <= hmw[1] * HMW_SLACK[1] for v in values):
        return f"far outside HMW's {hmw[0]:g}-{hmw[1]:g}"
    return ""


# ---------------------------------------------------------------- rows

def hmw_ranges() -> dict:
    ranges = {}
    with (HERE / "hmw-2019.csv").open(encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            low = float(r["value_min"] or r["value"])
            high = float(r["value_max"] or r["value"])
            key = (r["mdd_id"], r["trait"])
            old = ranges.get(key, (low, high))
            ranges[key] = (min(old[0], low), max(old[1], high))
    return ranges


def known_dois() -> set[str]:
    refs = json.loads((HERE / "references.json").read_text(encoding="utf-8"))["references"]
    return {(r.get("doi") or "").lower() for r in refs.values() if r.get("doi")}


def species_name(title: str) -> str:
    words = re.sub(r"\([^)]*\)", " ", html.unescape(title)).split()
    return " ".join(words[:2])


def upstream(meta: dict) -> str:
    authors = [a.strip() for a in re.split(r"\s*(?:&|;)\s*", meta.get("authors", "")) if a.strip()]
    first = authors[0].split(",")[0] if authors else "Anon."
    who = first if len(authors) == 1 else f"{first} & {authors[1].split(',')[0]}" if len(authors) == 2 else f"{first} et al."
    article = re.sub(r"\s+", " ", meta.get("article", "")).strip().rstrip(".")
    return f"{who} ({meta.get('year', '')}) {article}. https://doi.org/{meta['doi']}"


def size_row(doc: str, meta: dict, k: int, species: dict, printed: str, method: str, item: dict) -> dict:
    fig, trait = item["fig"], item["trait"]
    row = {
        "observation_id": f"{REFERENCE}-{doc}-{k}", "mdd_id": species["id"],
        "verbatim_taxon_name": printed, "taxon_match_method": method, "reference_id": REFERENCE,
        "locator": f"{item['section'] or 'text'}, p. {item['page'] or meta.get('page', '')}; Plazi treatment {doc}",
        "trait": trait, "basis": "measured", "sex": item["sex"], "upstream_source": upstream(meta),
        "data_year": meta.get("year", ""), "verbatim_value": item["verbatim"],
        "n": str(fig["n"]) if fig["n"] else "",
    }
    notes = []
    if fig["kind"] == "range":
        row.update(statistic="range_only", value=number((fig["low"] + fig["high"]) / 2),
                   value_min=number(fig["low"]), value_max=number(fig["high"]), range_type="min_max")
    elif fig["kind"] == "mean":
        row.update(statistic="mean", value=number(fig["value"]), sd=number(fig["sd"]) if fig["sd"] else "")
        if fig.get("values"):
            notes.append(f"Mean of the {len(fig['values'])} specimens' values the text lists.")
        if fig["low"] is not None:
            row.update(value_min=number(fig["low"]), value_max=number(fig["high"]), range_type="min_max")
    else:
        row.update(statistic="single", value=number(fig["value"]))
        if item["holotype"]:
            row["n"] = "1"
            notes.append("Measurement of the holotype.")
    if not fig["unit"]:
        unit = "mm" if trait == "forearm_length" else "g"
        notes.append(f"The text gives no unit at the figure; the article states its {'masses' if unit == 'g' else 'measurements'} in {unit}.")
    row["notes"] = " ".join(notes)
    return row


def collect(manifest: dict, resolver: SizeResolver, hmw: dict, skip_dois: set):
    rows, review = [], []
    for doc, meta in sorted(manifest.items()):
        if meta["doi"].lower() in skip_dois:
            continue
        printed = species_name(meta["title"])
        species, method = resolver.resolve(printed)
        if not species:
            continue
        own = tuple(printed.split())
        xml = (PLAZI / f"{doc}.xml").read_text(encoding="utf-8", errors="replace")
        found = {}
        for section, page, text, names in sections(xml):
            for trait, fig, verbatim, start, end, reason in candidates(text, names, own):
                if reason:
                    continue
                problem = plausible(fig, trait, hmw.get((species["id"], trait)))
                if problem:
                    review.append((printed, trait, verbatim, problem, doc))
                    continue
                s, e = sentence_bounds(text, start)
                item = {"trait": trait, "fig": fig, "verbatim": verbatim, "section": section, "page": page,
                        "sex": sex_of(text, start, end), "holotype": "holotype" in text[s:e].lower()}
                key = (trait, item["sex"], fig["kind"], fig.get("value"), fig.get("low"), fig.get("high"))
                found.setdefault(key, item)
        items = list(found.values())
        series = {(i["trait"], i["sex"]) for i in items if i["fig"]["kind"] != "single"}
        items = [i for i in items if not (i["fig"]["kind"] == "single" and (i["trait"], i["sex"]) in series)]
        for k, item in enumerate(items, start=1):
            rows.append(size_row(doc, meta, k, species, printed, method, item))
    return rows, review


def write_figure_review(review: list) -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Plazi treatment figures not imported", "",
             "These figures parsed cleanly but are implausible for the species; read them by hand.", "",
             "| Species | Trait | Text | Why | Plazi docId |", "|---|---|---|---|---|"]
    lines += [f"| {s} | {t} | {v.replace('|', '/')} | {why} | {d} |" for s, t, v, why, d in sorted(set(review))]
    FIGURE_REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    check_raw({str(PLAZI / f"{doc}.xml"): meta["sha256"] for doc, meta in manifest.items()})
    resolver = SizeResolver()
    rows, review = collect(manifest, resolver, hmw_ranges(), known_dois())
    write_rows(REFERENCE, rows)
    write_review(REFERENCE, resolver.unresolved)
    write_figure_review(review)
    report(REFERENCE, rows, resolver)
    print(f"  {len(rows)} rows from {len({r['upstream_source'] for r in rows})} articles; "
          f"{len(set(review))} implausible figures in {FIGURE_REVIEW.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
