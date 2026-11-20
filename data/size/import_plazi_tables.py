"""Import forearm length and body mass from the measurement tables of bat
papers that Plazi digitised.

import_plazi_literature.py reads only the running text of a treatment; Plazi
keeps tables apart (table.plazi.org, mirrored as records in Zenodo's
Biodiversity Literature Repository). fetch_plazi_tables.py caches every table
that a cached bat treatment cites. This importer reads them and writes
data/size/plazi-tables.csv, one row per species, sex and series.

A table is laid out as a grid (row and column spans expanded; a row printed
with fewer cells than the table is width is right-aligned and its missing
leading label cells are taken from the row above, as typeset tables imply).
The first data row is the first whose first cell is a text label and whose
other cells are mostly numbers; the rows above it are the header block.

A forearm or mass label is a header or label cell reading "FA", "FAL",
"forearm (length)", "body mass", "mass", "weight" and the like (units in
parentheses allowed). The ambiguous abbreviations FL, W, BW, BM, WT and M are
accepted only when the caption or table footnote defines them as forearm or
mass, and a mass is imported only when the table states its unit (g).

- a label in the header block makes a column of values (species down the
  rows); a label in a row's leading cells makes a row of values (species
  across the columns);
- each value's context is the header-block cells above it, the label cells
  beside it (for a column: the first column and any column headed species,
  taxon, sex, n, specimen, catalogue, locality ...) and the nearest
  full-width section row above it;
- the species is the one taxon name Plazi tagged in that context (or, when
  the grid tags none at all, the single species the caption names). A
  context with two species, or none, is skipped;
- a context citing a publication (a year, "et al.", "literature") is a value
  quoted from older work and is skipped, as is every table whose caption or
  footnote says it includes literature data;
- statistics come from the context ("mean", "SD", "min", "max", "range",
  "n", "holotype") or from the cell itself, which may read "45.2", "43.0-47.1",
  "45.2 ± 1.1", "45.2 ± 1.1 (43.0-47.1)", "43.0-47.1 (45.2 ± 1.1)" or
  "45.2 (43.0-47.1)", optionally with n as "; 12", "[12]", "(12)" or "n = 12".
  Any other cell (several values, footnote marks, "a, b, n" lists) is skipped;
- cells sharing a context apart from their statistic word merge into one
  series ("Mean" row, "SD" row, "Range" row). Where a species and sex have a
  series, single specimens (holotype, catalogue numbers) are dropped; where
  they have only single specimens, two or more become their mean, range and n;
- tables of test results (ANOVA, loadings, principal components,
  discriminant functions, correlations) are not read.

Values pass the same plausibility check as the text importer (bounds for any
bat, and -20%/+25% of HMW's range); failures are listed in
data/size/unresolved/plazi-tables-figures.md. A table with a forearm or mass
label from which nothing could be read is listed there too, with the reason.

Rows cite the article (authors, year, title, DOI) in upstream_source, the same
text import_plazi_literature.py writes, so an article's text and tables are
one study in build_size.py. A table value that repeats a value the text import
already holds for that article, species, trait and sex is not written again.
Articles already imported by hand are skipped. The locator names the table
and its Plazi uuid; data/build_claims.py links the table's Zenodo record.

Raw files: data/raw/size/plazi-tables/<uuid>.xml, pinned in
data/size/plazi-tables-sources.json.
Run:  uv run data/size/fetch_plazi_tables.py   (once; caches the tables)
      uv run data/size/import_plazi_tables.py
"""
import csv
import html
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

from import_plazi_literature import hmw_ranges, known_dois, plausible, upstream
from size_lib import RAW, REVIEW_DIR, SizeResolver, check_raw, number, report, write_review, write_rows

HERE = Path(__file__).parent
MANIFEST = HERE / "plazi-tables-sources.json"
TABLES = RAW / "plazi-tables"
REFERENCE = "plazi-tables"
TEXT_ROWS = HERE / "plazi-literature.csv"
FIGURE_REVIEW = REVIEW_DIR / "plazi-tables-figures.md"

UNIT = r"(?:\s*[(\[](?:in\s+)?(?:mm|g|grams?)[)\]])?"
LABEL = {
    "forearm_length": re.compile(rf"^(?:FA|FAL|LFA|FOA|Fa|[Ff]orearms?(?:\s+length)?(?:\s+\(FA\))?){UNIT}$"),
    "body_mass": re.compile(rf"^(?:[Bb]ody\s+(?:mass|weight)|[Mm]ass|MASS|[Ww]eigh[t]?|[Ww]eight|[Ww]eigth){UNIT}$"),
}
AMBIGUOUS = re.compile(rf"^(?P<abbr>FL|W|BW|BM|WT|Wt|M|Mass|BMS){UNIT}$")
DEFINED = {
    "forearm_length": r"forearm(?:\s+length)?",
    "body_mass": r"(?:body\s+)?(?:mass|weight|weigth)",
}
MASS_UNIT = re.compile(r"\(\s*(?:in\s+)?g\s*\)|\bin\s+g(?:rams)?\b|\bgrams?\b|\bmass(?:es)?\s*\(g\)|weight\s*\(g\)|weigth\s*\(g\)|\bg\)", re.I)
TEST_TABLE = re.compile(r"ANOVA|loading|principal component|\bPCA\b|discriminant|eigen|correlation|"
                        r"coefficient|nonoverlap|non-overlap|Kruskal|t-test|Mann|canonical|\bratio", re.I)
# a caption sentence saying some values come from older work
YEAR = r"(?:1[89]|20)\d\d"
LITERATURE_TABLE = re.compile(
    rf"literature|published|compiled|unpubl|"
    rf"\b(?:taken|cited|data|values|measurements)\s+(?:were\s+|are\s+)?(?:taken\s+|cited\s+)?from\b[^.]{{0,80}}?(?:{YEAR}|et al)|"
    rf"\b(?:after|following|from|in)\s+[A-Z][a-z]+(?:\s+et al\.?|\s+(?:and|&)\s+[A-Z][a-z]+)?,?\s+\(?{YEAR}|"
    rf"\b[A-Z][a-z]+(?:\s+et al\.?|\s+(?:and|&)\s+[A-Z][a-z]+)?,?\s+\(\s*{YEAR}", re.I)
NOT_DATA_CITATION = re.compile(r"IUCN|conservation status|Red List|nomenclature follows|taxonomy follows|"
                               r"abbreviations? (?:follow|as in)|measurements? (?:were )?taken (?:as|following)", re.I)
# "* Mean values from Tavares and Taddei (2003)": the quoted values carry the mark,
# and a marked cell is never read
MARKED_NOTE = re.compile(r"^\s*[*†‡§¶]")
# a year cites a publication after a surname ("Eger 2011", "Kruskop & Eger, 2008") or in
# parentheses; "CML 1802" is a catalogue number
CITED = re.compile(r"\bet al\b|literature|\bLit\.|\(\s*(?:1[89]|20)\d\d[a-z]?\s*\)|"
                   r"\b[A-Z][a-z]{2,}(?:\s+(?:&|and)\s+[A-Z][a-z]{2,})?,?\s+(?:1[89]|20)\d\d[a-z]?\b")
CONTEXT_COLUMN = re.compile(r"^(?:species|taxon|taxa|sex|n|N|no\.|specimens?|catalog\w*|catalogue\w*|voucher|"
                            r"localit\w*|population|sample|museum.*|id|age|family/species|country|region)\b", re.I)

NUM = r"\d{1,4}(?:\.\d{1,3})?"
DASH = r"\s*[-–—−‒]\s*"
N_TAIL = r"(?:\s*(?:[;,]\s*(?:[nN]\s*=\s*)?(?P<n1>\d+))?)"
N_AFTER = r"(?:\s*(?:[\[(]\s*(?:[nN]\s*=\s*)?(?P<n2>\d+)\s*[\])]|[;,]?\s*[nN]\s*=\s*(?P<n3>\d+)|;\s*(?P<n4>\d+)))?"
CELL = [re.compile(p) for p in (
    rf"^(?P<mean>{NUM})$",
    rf"^(?P<lo>{NUM}){DASH}(?P<hi>{NUM}){N_AFTER}$",
    rf"^(?P<mean>{NUM})\s*±\s*(?P<sd>{NUM}){N_AFTER}$",
    rf"^(?P<mean>{NUM})\s*(?:±\s*(?P<sd>{NUM}))?\s*[(\[]\s*(?P<lo>{NUM}){DASH}(?P<hi>{NUM}){N_TAIL}\s*[)\]](?:\s*(?P<sd2>{NUM}))?{N_AFTER}$",
    rf"^(?P<lo>{NUM}){DASH}(?P<hi>{NUM})\s*[(\[]\s*(?P<mean>{NUM})\s*(?:±\s*(?P<sd>{NUM}))?{N_TAIL}\s*[)\]]{N_AFTER}$",
)]
EMPTY = re.compile(r"^(?:|[-–—−]+|NA|N/A|n\.a\.|nd|–-|\?)$", re.I)
STAT_WORDS = [
    ("mean", re.compile(r"^(?:mean|average|x̄|x|X̄|M ± SD|mean ± SD|mean±SD)$|^(?:mean|average)\b(?!.*\b(?:SD|range|min)\b)", re.I)),
    ("sd", re.compile(r"^(?:SD|s\.d\.|std\.?\s*dev\.?|standard deviation|±\s*SD)$", re.I)),
    ("min", re.compile(r"^(?:min\.?|minimum)$", re.I)),
    ("max", re.compile(r"^(?:max\.?|maximum)$", re.I)),
    ("range", re.compile(r"^(?:range|R|min\.?\s*[-–—]\s*max\.?|minimum\s*[-–—]\s*maximum|OR|observed range)$", re.I)),
    ("n", re.compile(r"^(?:n|N|sample size|no\.)$")),
    ("skip", re.compile(r"^(?:SE|s\.e\.|CV|C\.V\.|SEM|variance|median|mode|95% CI|CI)$", re.I)),
]
# a bare "M" or "F" is a sex only as the whole label ("M. gigas" is a genus initial)
SEX = [("male", re.compile(r"^M$|\bmales?\b|♂", re.I)),
       ("female", re.compile(r"^F$|\bfemales?\b|♀", re.I))]
HOLOTYPE = re.compile(r"\bholotype\b", re.I)
FOOTNOTE = re.compile(r"[*†‡§¶#]|[a-z]$")


# ---------------------------------------------------------------- grid

def text_of(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).replace(" ,", ",").strip()


def taxa_of(fragment: str) -> set:
    out = set()
    for tag in re.findall(r"<taxonomicName\b([^>]*)>", fragment):
        attrs = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', tag))
        if attrs.get("rank") in ("species", "subspecies") and attrs.get("genus") and attrs.get("species"):
            out.add((attrs["genus"], attrs["species"]))
    return out


class Table:
    def __init__(self, xml: str):
        body = xml[xml.find("<table"):]
        caption = re.search(r"<caption\b.*?</caption>", body, re.S)
        foot = re.search(r"<tfoot\b.*?</tfoot>", body, re.S)
        self.caption = text_of(caption.group(0)) if caption else ""
        self.caption_taxa = taxa_of(caption.group(0)) if caption else set()
        self.foot = text_of(foot.group(0)) if foot else ""
        body = re.sub(r"<caption\b.*?</caption>|<tfoot\b.*?</tfoot>", " ", body, flags=re.S)
        body = re.sub(r"<(t[hd])\b([^>]*?)/>", r"<\1\2></\1>", body)  # empty cells: <th/>
        raw = []
        for row in re.findall(r"<tr\b.*?</tr>", body, re.S):
            cells = []
            for attrs, inner in re.findall(r"<t[hd]\b([^>]*)>(.*?)</t[hd]>", row, re.S):
                span = re.search(r'colspan="(\d+)"', attrs)
                down = re.search(r'rowspan="(\d+)"', attrs)
                cells.append((text_of(inner), taxa_of(inner), int(span.group(1)) if span else 1,
                              int(down.group(1)) if down else 1))
            raw.append(cells)
        self.width = max((sum(c[2] for c in r) for r in raw), default=0)
        self.grid, self.spanning = self._expand(raw)
        self.start = self._first_data_row()

    def _expand(self, raw):
        grid, spanning, pending = [], [], {}
        for cells in raw:
            row = [None] * self.width
            for col, (left, cell) in list(pending.items()):
                row[col] = cell
                if left <= 1:
                    del pending[col]
                else:
                    pending[col] = (left - 1, cell)
            free = [c for c in range(self.width) if row[c] is None]
            need = sum(c[2] for c in cells)
            # a short row is right-aligned; its leading label cells repeat the row above
            short = need < len(free) and len(cells) > 1
            skip = len(free) - need if short and grid and any(parse_cell(c[0]) for c in cells) else 0
            if short and not skip:
                # a short header row cannot be placed over its columns: keep its text, drop its names
                cells = [(t, set(), sp, dn) for t, _, sp, dn in cells]
            for col in free[:skip]:
                row[col] = grid[-1][col] if grid else ("", set())
            slots = iter(free[skip:])
            for text, taxa, span, down in cells:
                for k in range(span):
                    col = next(slots, None)
                    if col is None:
                        break
                    # a spanning header ("Females", a species) applies to every column under it
                    row[col] = (text, taxa)
                    if down > 1:
                        pending[col] = (down - 1, row[col])
            grid.append([c if c is not None else ("", set()) for c in row])
            spanning.append(len(cells) == 1 and cells[0][2] >= max(2, self.width - 1))
        return grid, spanning

    def _first_data_row(self) -> int:
        for i, row in enumerate(self.grid):
            if self.spanning[i]:
                continue
            label = row[0][0]
            values = [c[0] for c in row[1:] if c[0] and not EMPTY.match(c[0])]
            if label and not re.fullmatch(r"[\d.\s]+", label) and values and \
                    sum(1 for v in values if parse_cell(v)) >= max(1, len(values) // 2):
                return i
        return len(self.grid)


# ---------------------------------------------------------------- cells

def parse_cell(text: str) -> dict | None:
    text = text.strip().replace(" ,", ",")
    if EMPTY.match(text):
        return None
    text = re.sub(r"(?<=\d),(?=\d{1,3}(?!\d))", ".", text) if text.count(",") == 1 and "." not in text else text
    for pattern in CELL:
        m = pattern.match(text)
        if not m:
            continue
        g = m.groupdict()
        n = next((g.get(k) for k in ("n1", "n2", "n3", "n4") if g.get(k)), None)
        sd = g.get("sd") or g.get("sd2")
        out = {"mean": float(g["mean"]) if g.get("mean") else None, "sd": float(sd) if sd else None,
               "low": float(g["lo"]) if g.get("lo") else None, "high": float(g["hi"]) if g.get("hi") else None,
               "n": int(n) if n else None, "verbatim": text}
        return out
    return None


def trait_of(label: str, table: Table) -> str:
    label = label.strip()
    for trait, pattern in LABEL.items():
        if pattern.match(label):
            return trait
    m = AMBIGUOUS.match(label)
    if m:
        abbr = re.escape(m.group("abbr"))
        notes = table.caption + " " + table.foot
        for trait, words in DEFINED.items():
            if re.search(rf"\b{abbr}\b\s*(?:[:=,–—-]|\(|is|for)?\s*(?:the\s+)?{words}", notes, re.I) or \
                    re.search(rf"{words}\s*\(\s*{abbr}\s*[),]", notes, re.I):
                return trait
    return ""


# ---------------------------------------------------------------- reading

def read_table(table: Table) -> tuple[list[dict], str]:
    """(values with their context, reason nothing was read) for one table."""
    labels = []
    for i, row in enumerate(table.grid):
        for j, (text, _) in enumerate(row):
            trait = trait_of(text, table) if text else ""
            if trait:
                labels.append((i, j, trait))
    if not labels:
        return [], ""
    if TEST_TABLE.search(table.caption):
        return [], "table of test results"
    table.quoted = quoted_species(table)
    if table.quoted is None:
        return [], "caption or footnote says the table includes literature data, without naming whose"
    if sparse_header(table):
        return [], "header labels do not cover their columns (centred over column groups)"
    values, h = [], table.start
    for i, j, trait in labels:
        if trait == "body_mass" and not MASS_UNIT.search(table.caption + " " + table.foot + " " + table.grid[i][j][0]):
            continue
        if i < h:  # a column of values
            context_cols = [c for c in range(table.width) if c != j and (c == 0 or any(
                CONTEXT_COLUMN.match(table.grid[r][c][0]) for r in range(h)))]
            label_cols = [c for c in context_cols if c < j or c == 0]
            for r in range(h, len(table.grid)):
                if table.spanning[r]:
                    continue
                below = table.grid[r][j][0]
                if below and not EMPTY.match(below) and not parse_cell(below) and re.search(r"[A-Za-z]{2}", below):
                    break  # a repeated header row starts a block with other columns
                cells = [table.grid[k][j] for k in range(h)] + [table.grid[r][c] for c in label_cols]
                values.append(_value(table, r, j, trait, cells))
        else:  # a row of values
            first = next((c for c in range(j + 1, table.width) if parse_cell(table.grid[i][c][0])
                          or EMPTY.match(table.grid[i][c][0])), table.width)
            for c in range(first, table.width):
                cells = [table.grid[k][c] for k in range(h)] + [table.grid[i][k] for k in range(first)]
                values.append(_value(table, i, c, trait, cells))
    values = [v for v in values if v and v["cell"]]
    return values, "" if values else "no readable cells"


def quoted_species(table: Table) -> set | None:
    """Epithets of the species whose values a caption or footnote sentence says come
    from older work ("Measurements for P. brunnea ... after Monadjem et al. (2021a)").
    None when such a sentence names none of the table's species: then whose values
    are quoted is unknown and the table is not read."""
    epithets = {s for row in table.grid for _, taxa in row for _, s in taxa} | {s for _, s in table.caption_taxa}
    quoted = set()
    for sentence in re.split(r"(?<=[a-z0-9)\]])\s?\.\s+(?=[A-Z*†‡§¶])|\s\|\|\s", table.caption + " || " + table.foot):
        if not LITERATURE_TABLE.search(sentence) or NOT_DATA_CITATION.search(sentence) or \
                MARKED_NOTE.match(sentence):
            continue
        named = {e for e in epithets if re.search(rf"\b{re.escape(e)}\b", sentence)}
        if not named:
            return None
        quoted |= named
    return quoted


def sparse_header(table: Table) -> bool:
    """A header row that names species, sexes or statistics but leaves some value
    columns blank: its labels were typeset centred over groups of columns without a
    span, so which columns a label covers is unknown."""
    value_cols = {c for r in range(table.start, len(table.grid)) for c in range(1, table.width)
                  if parse_cell(table.grid[r][c][0])}
    for r in range(table.start):
        row = table.grid[r]
        labelled = [c for c in value_cols if row[c][0]]
        if not labelled or len(labelled) == len(value_cols):
            continue
        if any(row[c][1] or any(p.search(row[c][0]) for _, p in SEX) or
               any(p.match(row[c][0]) for _, p in STAT_WORDS) for c in labelled):
            return True
    return False


def _value(table: Table, r: int, c: int, trait: str, context: list) -> dict | None:
    text = table.grid[r][c][0]
    if not text or EMPTY.match(text):
        return None
    section = next((table.grid[k][0] for k in range(r - 1, table.start - 1, -1) if table.spanning[k]), None)
    if section:
        context = context + [section]
    words, taxa = [], set()
    for t, x in context:
        if t:
            words.append(t)
        taxa |= x
    return {"row": r, "col": c, "trait": trait, "text": text, "cell": parse_cell(text),
            "footnote": bool(re.search(r"[*†‡§¶]", text)), "words": words, "taxa": taxa}


def interpret(value: dict, table: Table, all_taxa: set) -> tuple[dict | None, str]:
    words = value["words"]
    if value["footnote"]:
        return None, "footnote mark on the value"
    label_words = [w for w in words if not LABEL[value["trait"]].match(w) and not trait_of(w, table)]
    if any(CITED.search(w) for w in label_words):
        return None, "quoted from the literature"
    taxa = value["taxa"]
    if not taxa and not all_taxa and len(table.caption_taxa) == 1:
        taxa = table.caption_taxa
    if len(taxa) != 1:
        return None, "no single species" if not taxa else "several species in context"
    stat, sex, holotype, residual = "", "pooled", False, []
    for w in label_words:
        bare = re.sub(r"\s*\(n\s*=\s*\d+\)", "", w).strip()
        hit = next((name for name, p in STAT_WORDS if p.match(bare)), "")
        if hit:
            stat = hit
            continue
        sexes = {name for name, p in SEX if p.search(bare)}
        if len(sexes) == 1:
            sex = sexes.pop()
        elif len(sexes) == 2 and not re.search(r"males?\s*(?:and|&|\+|/)\s*females?", bare, re.I):
            return None, "both sexes in one label"
        if HOLOTYPE.search(bare):
            holotype = True
        n_in_label = re.search(r"\(\s*n\s*=\s*(\d+)\s*\)", w)
        cell = value["cell"]
        if n_in_label and cell["n"] is None and (cell["sd"] is not None or cell["low"] is not None):
            value["cell"]["n"] = int(n_in_label.group(1))
        residual.append(bare)
    if stat == "skip":
        return None, "statistic other than mean, SD, range or n"
    (genus, species), = taxa
    if species in getattr(table, "quoted", set()):
        return None, "caption says this species' values come from older work"
    return {"species": f"{genus} {species}", "stat": stat, "sex": sex, "holotype": holotype,
            "residual": tuple(sorted(set(residual))), **value}, ""


def observations(items: list[dict]) -> list[dict]:
    """Merge a series' statistic cells; then reduce single specimens."""
    series = defaultdict(dict)

    def put(obs, field, value):
        if value is None:
            return
        if obs.get(field) is not None and obs[field] != value:
            obs["conflict"] = True  # two cells claim one statistic: the context is not understood
        obs[field] = value

    for it in items:
        key = (it["species"], it["trait"], it["sex"], it["residual"])
        obs = series[key]
        obs.setdefault("verbatim", []).append(it["text"])
        obs.update(species=it["species"], trait=it["trait"], sex=it["sex"], holotype=it["holotype"])
        cell, stat = it["cell"], it["stat"]
        if stat in ("", "mean"):
            for k in ("mean", "sd", "low", "high", "n"):
                put(obs, k, cell[k])
            if stat == "mean":
                obs["stated_mean"] = True
        elif stat == "sd":
            put(obs, "sd", cell["mean"])
        elif stat == "min":
            put(obs, "low", cell["mean"])
        elif stat == "max":
            put(obs, "high", cell["mean"])
        elif stat == "range":
            if cell["low"] is not None:
                put(obs, "low", cell["low"])
                put(obs, "high", cell["high"])
                put(obs, "n", cell["n"])
            elif cell["mean"] is not None:  # a range of one specimen prints as one value
                put(obs, "low", cell["mean"])
                put(obs, "high", cell["mean"])
        elif stat == "n" and cell["mean"] is not None and cell["mean"] == int(cell["mean"]):
            put(obs, "n", int(cell["mean"]))
    out = defaultdict(list)
    for obs in series.values():
        if obs.get("conflict"):
            continue
        if obs.get("low") is not None and obs.get("low") == obs.get("high"):
            obs["low"] = obs["high"] = None
        if obs.get("mean") is None and obs.get("low") is None:
            continue
        kind = "single" if obs.get("mean") is not None and obs.get("low") is None and obs.get("sd") is None \
            and (obs.get("n") in (None, 1)) and not obs.get("stated_mean") else "series"
        obs["kind"] = kind
        out[(obs["species"], obs["trait"], obs["sex"])].append(obs)
    final = []
    for key, group in out.items():
        series_rows = [o for o in group if o["kind"] == "series"]
        singles = [o for o in group if o["kind"] == "single"]
        if series_rows:
            # a stated mean printed beside its specimens ("46, 46.4, 46.5 | average 46.3")
            if len(series_rows) == 1 and len(singles) >= 2 and series_rows[0].get("n") is None \
                    and series_rows[0].get("low") is None:
                values = [o["mean"] for o in singles]
                if abs(statistics.mean(values) - series_rows[0]["mean"]) <= 0.01 * series_rows[0]["mean"]:
                    series_rows[0].update(n=len(values), low=min(values), high=max(values))
            final += series_rows
        elif len(singles) >= 2:
            values = [o["mean"] for o in singles]
            final.append({**singles[0], "kind": "specimens", "mean": statistics.mean(values), "sd": None,
                          "low": min(values), "high": max(values), "n": len(values), "holotype": False,
                          "verbatim": [v for o in singles for v in o["verbatim"]]})
        else:
            final += singles
    return final


# ---------------------------------------------------------------- rows

def text_rows() -> dict:
    out = defaultdict(list)
    if TEXT_ROWS.exists():
        with TEXT_ROWS.open(encoding="utf-8") as handle:
            for r in csv.DictReader(handle):
                out[(r["upstream_source"], r["mdd_id"], r["trait"], r["sex"])].append(float(r["value"]))
    return out


def fig_of(obs: dict) -> dict:
    """The shape import_plazi_literature.plausible() checks."""
    value = obs.get("mean")
    if value is None:
        value = (obs["low"] + obs["high"]) / 2
    return {"value": value, "low": obs.get("low"), "high": obs.get("high")}


def size_row(uuid: str, meta: dict, k: int, species: dict, obs: dict, method: str) -> dict:
    label = meta.get("label") or "Table"
    row = {
        "observation_id": f"{REFERENCE}-{uuid}-{k}", "mdd_id": species["id"],
        "verbatim_taxon_name": obs["species"], "taxon_match_method": method, "reference_id": REFERENCE,
        "locator": f"{label}; Plazi table {uuid}", "trait": obs["trait"], "basis": "measured",
        "sex": obs["sex"], "upstream_source": upstream(meta), "data_year": meta.get("year", ""),
        "verbatim_value": " | ".join(dict.fromkeys(obs["verbatim"]))[:300],
        "n": str(obs["n"]) if obs.get("n") else "",
    }
    notes = []
    if obs.get("mean") is None:
        row.update(statistic="range_only", value=number((obs["low"] + obs["high"]) / 2),
                   value_min=number(obs["low"]), value_max=number(obs["high"]), range_type="min_max")
    elif obs["kind"] == "single":
        row.update(statistic="single", value=number(obs["mean"]))
        row["n"] = "1"
        if obs["holotype"]:
            notes.append("Measurement of the holotype.")
    else:
        row.update(statistic="mean", value=number(obs["mean"]), sd=number(obs["sd"]) if obs.get("sd") else "")
        if obs.get("low") is not None:
            row.update(value_min=number(obs["low"]), value_max=number(obs["high"]), range_type="min_max")
        if obs["kind"] == "specimens":
            notes.append(f"Mean of the {obs['n']} specimens the table lists one by one.")
    row["notes"] = " ".join(notes)
    return row


def collect(manifest: dict, resolver: SizeResolver, hmw: dict, skip_dois: set):
    rows, review, repeats = [], [], 0
    texts = text_rows()
    for uuid, meta in sorted(manifest.items()):
        if meta["doi"].lower() in skip_dois:
            continue
        table = Table((TABLES / f"{uuid}.xml").read_text(encoding="utf-8", errors="replace"))
        values, reason = read_table(table)
        if reason:
            review.append(("", "", meta.get("label", ""), reason, uuid))
            continue
        all_taxa = set().union(*(x for row in table.grid for _, x in row))
        items = []
        for value in values:
            item, _ = interpret(value, table, all_taxa)
            if item:
                items.append(item)
        if values and not items:
            review.append(("", "", meta.get("label", ""), "no value with a single species and clear context", uuid))
        seen = set()
        k = 0
        for obs in observations(items):
            species, method = resolver.resolve(obs["species"])
            if not species:
                continue
            fig = fig_of(obs)
            problem = plausible(fig, obs["trait"], hmw.get((species["id"], obs["trait"])))
            if problem:
                review.append((obs["species"], obs["trait"], " | ".join(obs["verbatim"])[:120], problem, uuid))
                continue
            source = upstream(meta)
            key = (species["id"], obs["trait"], obs["sex"], round(fig["value"], 2), fig["low"], fig["high"])
            if key in seen:
                continue
            seen.add(key)
            if any(abs(v - fig["value"]) <= 0.01 * v for v in texts.get((source, species["id"], obs["trait"], obs["sex"]), [])):
                repeats += 1
                continue
            k += 1
            rows.append(size_row(uuid, meta, k, species, obs, method))
    return dedupe_across_tables(rows), review, repeats


def dedupe_across_tables(rows: list[dict]) -> list[dict]:
    """An article that prints one series in two tables gives one row."""
    seen, out = set(), []
    for r in rows:
        # Plazi holds some articles twice (two DOIs, title case differing)
        author_year = r["upstream_source"].split(")")[0].lower()
        key = (author_year, r["mdd_id"], r["trait"], r["sex"], r["value"], r.get("value_min", ""), r.get("value_max", ""))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def write_figure_review(review: list, manifest: dict) -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Plazi table values not imported", "",
             "Tables with a forearm or mass column that the importer could not read, and values that",
             "parsed but are implausible for the species. Read them by hand from the Zenodo record or",
             "http://table.plazi.org/id/<uuid>.", "",
             "| Species | Trait | Text / table | Why | Table uuid | Zenodo |", "|---|---|---|---|---|---|"]
    for s, t, v, why, uuid in sorted(set(review)):
        meta = manifest.get(uuid, {})
        what = v or (meta.get("caption", "")[:110])
        lines.append(f"| {s} | {t} | {what.replace('|', '/')} | {why} | {uuid} | {meta.get('zenodo', '')} |")
    FIGURE_REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    check_raw({str(TABLES / f"{uuid}.xml"): meta["sha256"] for uuid, meta in manifest.items()})
    resolver = SizeResolver()
    rows, review, repeats = collect(manifest, resolver, hmw_ranges(), known_dois())
    write_rows(REFERENCE, rows)
    write_review(REFERENCE, resolver.unresolved)
    write_figure_review(review, manifest)
    report(REFERENCE, rows, resolver)
    print(f"  {len(rows)} rows from {len({r['upstream_source'] for r in rows})} articles "
          f"({len({r['locator'] for r in rows})} tables); {repeats} values already in the text import; "
          f"{len(set(review))} items for review in {FIGURE_REVIEW.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
