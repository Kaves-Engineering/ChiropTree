"""Build the evidence ledger: one row for every value a species card shows.

The ledger answers, for each bat, "where does this come from?" -- for every
forearm, body mass, call parameter, diet guild and country on the card it names
the source, the link a reader can follow, where in the source the value is
printed (page, table, file row), what the source printed verbatim, and how far
the claim can be checked from the link.

It is built from the same rows the cards are built from, by the same loading
code, so a value cannot appear on a card without appearing here:

    size   data/size/<ref>.csv       via build_size.load_rows / fold_copies
    calls  data/calls/<ref>.csv      via build_calls.load_rows / reassign_by_locality
           plus legacy prose entries and genus/family inference (calls.json)
    diet   data/chiroptera_diet.json (EltonTraits 1.0)
    range  MDD countryDistribution + data/gbif_country_supplement.json

Each claim gets a status. Without --check it says what the link can do; with
--check it also fetches the open, per-species pages and looks for the printed
value in them:

    located      the value was found on the page the deep link opens (--check)
    not_found    the page opened but the value was not found in it (--check)
    cited        a link and a locator exist; the value is not machine-checked
    generic_link the link opens an index or chapter summary, not the source of
                 this value, and no deeper link can be built
    no_locator   the source is linked, but nothing says where in it the value is
    unpublished  the source is not published, so there is nothing to link
    unlinked     the source has no link at all

Run:
    uv run data/build_claims.py                         # every species
    uv run data/build_claims.py --country Belize,Denmark --report report.md
    uv run data/build_claims.py --country Denmark --check   # fetch Plazi/MDD pages

Writes data/claims/claims.json and data/claims/claims.csv (or --out-dir).
"""
import argparse
import csv
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

DATA = Path(__file__).parent
sys.path.insert(0, str(DATA / "size"))
sys.path.insert(0, str(DATA / "calls"))
sys.path.insert(0, str(DATA))

import build_calls
import build_size
from parameter_registry import Registry
from size_lib import (
    PLAZI_PAGE,
    PLAZI_TABLE_PAGE,
    highlight_text,
    plazi_table,
    plazi_treatment,
)

TAXONOMY = DATA / "chiroptera_taxonomy.json"
HISTORY = DATA / "chiroptera_name_history.json"
CALLS_EXPORT = DATA / "calls" / "exports" / "calls.json"
DIET = DATA / "chiroptera_diet.json"
GBIF_SUPPLEMENT = DATA / "gbif_country_supplement.json"
DANISH = DATA / "danish_names.json"
GBIF_CACHE = DATA / "raw" / "gbif_country_cache.json"      # local only (data/raw is ignored)
GBIF_COUNTRIES = DATA / "raw" / "gbif_country_enum.json"   # local only
FETCH_CACHE = DATA / "raw" / "claims_fetch"                # pages fetched by --check
OUT_DIR = DATA / "claims"
PAGE_EXPORT = DATA / "evidence.json"                       # read by the species card

ELTONTRAITS_DATA = "https://doi.org/10.6084/m9.figshare.c.3306933.v1"
ARTICLE_DOI = re.compile(r"https://doi\.org/\S+$")
# Pages that cover many species: following one does not lead to a value.
INDEX_PAGES = ("genomics.senescence.info/species/", "tb.plazi.org/GgServer/summary/")
DATASET_HOSTS = ("figshare.com", "datadryad.org", "github.com", "dryad.", "figshare.")


# ---------------------------------------------------------------- sources

def link_scope(ref: dict) -> str:
    """What following a reference's own link gets a reader to."""
    url = ref.get("url") or ""
    if not url:
        return "none"
    if any(p in url for p in INDEX_PAGES):
        return "index"
    if ref.get("type") in ("dataset", "database") or any(h in url for h in DATASET_HOSTS):
        return "dataset"
    return "document"


def load_sources() -> dict:
    """Every reference the cards can cite, keyed by id, size and calls merged."""
    size_refs = build_size.load_references()
    call_file = json.loads(build_calls.REFERENCES.read_text(encoding="utf-8"))
    sources = {}
    for rid, ref in call_file["references"].items():
        sources[rid] = {"id": rid, "label": build_calls.short_label(rid, ref), **_public(ref)}
    for rid, ref in size_refs.items():
        entry = sources.setdefault(rid, {"id": rid})
        entry.setdefault("label", ref.get("short") or rid)
        for key, value in _public(ref).items():
            entry.setdefault(key, value)
    legacy = json.loads(CALLS_EXPORT.read_text(encoding="utf-8"))["references"]
    for rid, ref in legacy.items():
        sources.setdefault(rid, {"id": rid, "label": ref.get("label") or rid, "url": ref.get("url") or ""})
    for entry in sources.values():
        entry["link_scope"] = link_scope(entry)
    return sources


def _public(ref: dict) -> dict:
    keep = ("type", "citation", "doi", "url", "licence", "accessed_at", "access_note", "role")
    return {k: ref[k] for k in keep if ref.get(k) not in (None, "")}


# ---------------------------------------------------------------- deep links

def text_fragment(text: str) -> str:
    """A #:~:text= fragment that makes Chrome, Edge and Safari highlight text.

    '-', '&' and ',' are syntax inside a text directive, so they are escaped."""
    quoted = urllib.parse.quote(text, safe="")
    return "#:~:text=" + quoted.replace("-", "%2D")


def plazi_link(locator: str, verbatim: str, trait_word: str = "") -> tuple[str, str]:
    """(deep link, the text it should highlight) for a row read from a Plazi treatment or table."""
    treatment, table = plazi_treatment(locator), plazi_table(locator)
    if not treatment and not table:
        return "", ""
    page = PLAZI_PAGE.format(treatment) if treatment else PLAZI_TABLE_PAGE.format(table)
    needle = highlight_text(verbatim)
    if not needle:
        return page, ""
    return page + text_fragment(needle), needle


# ---------------------------------------------------------------- claims

def claim(**fields) -> dict:
    base = {"section": "", "item": "", "value": "", "basis": "", "role": "shown",
            "source": "", "link": "", "deep_link": "", "highlight": "", "locator": "",
            "verbatim": "", "row": "", "upstream": "", "status": "", "issues": []}
    base.update(fields)
    return base


def judge(c: dict, sources: dict) -> None:
    """Set the status a claim can honestly carry without fetching anything."""
    src = sources.get(c["source"], {})
    issues = c["issues"]
    if "�" in (c["verbatim"] or ""):
        issues.append("verbatim text has encoding damage (U+FFFD)")
    if src.get("type") == "unpublished":
        c["status"] = "unpublished"
    elif not (c["link"] or c["deep_link"]):
        c["status"] = "unlinked"
    elif not c["locator"]:
        c["status"] = "no_locator"
    elif src.get("link_scope") == "index" and not c["deep_link"]:
        c["status"] = "generic_link"
    else:
        c["status"] = "cited"


def size_claims(species_ids: set, sources: dict) -> dict:
    refs = build_size.load_references()
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))["species"]
    names = {s["id"]: s["sciName"].replace("_", " ") for s in taxonomy}
    rows, _ = build_size.load_rows(refs, names, build_size.bounds())
    build_size.fold_copies(rows, refs)

    grouped = defaultdict(list)
    for row in rows:
        if not row.get("_copy_of"):
            grouped[(row["mdd_id"], row["trait"])].append(row)
    outside = set()
    for records in grouped.values():
        outside |= build_size.outside_reference(records)

    out = defaultdict(list)
    for row in rows:
        if row["mdd_id"] not in species_ids:
            continue
        trait = row["trait"]
        ref = refs.get(row["reference_id"], {})  # the link the size card shows
        role = "shown"
        if row.get("_copy_of"):
            role = f"same value as {row['_copy_of']['reference_id']}; shown there as 'also in'"
        elif id(row) in outside:
            role = "shown, left out of the headline (outside the HMW range)"
        # any row read from a Plazi treatment (HMW, the Plazi literature import,
        # hand-read descriptions) links to that treatment with the figure highlighted
        deep, needle = plazi_link(row["locator"], row["verbatim_value"])
        # a harvested row's own article, which the card links as "from ..."
        article = ARTICLE_DOI.search(row["upstream_source"] or "")
        c = claim(section=trait, item=trait.replace("_", " "),
                  value=_size_display(row), basis=row["basis"] + (f" ({row['estimate_method']})" if row["estimate_method"] else ""),
                  role=role, source=row["reference_id"],
                  link=article.group(0) if article else ref.get("url", ""),
                  deep_link=deep, highlight=needle, locator=row["locator"],
                  verbatim=row["verbatim_value"], row=row["_where"],
                  upstream=row["upstream_source"])
        if not row["verbatim_value"]:
            c["issues"].append("no verbatim value recorded")
        if row["taxon_match_method"] != "exact":
            c["issues"].append(f"source names it {row['verbatim_taxon_name']} ({row['taxon_match_method']})")
        judge(c, sources)
        out[row["mdd_id"]].append(c)
    return out


def _size_display(row: dict) -> str:
    unit = "mm" if row["trait"] == "forearm_length" else "g"
    if row["statistic"] == "range_only":
        return f"{row['value_min']}–{row['value_max']} {unit} (range)"
    text = f"{row['value']} {unit}"
    if row["value_min"]:
        text += f" (range {row['value_min']}–{row['value_max']})"
    if row["n"]:
        text += f", n {row['n']}"
    if row["sex"] != "pooled":
        text += f", {row['sex']}"
    return text


def call_claims(species_ids: set, sources: dict) -> dict:
    registry = Registry()
    ref_file = json.loads(build_calls.REFERENCES.read_text(encoding="utf-8"))
    refs, methods = ref_file["references"], ref_file["methods"]
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    history = json.loads(HISTORY.read_text(encoding="utf-8"))["species"]
    rows, _ = build_calls.load_rows(set(refs))
    issues = build_calls.validate(rows, registry, refs, methods, {s["id"] for s in taxonomy["species"]})
    if issues:
        sys.exit(f"build_claims: the call rows do not validate ({len(issues)} problems); run build_calls.py")
    build_calls.reassign_by_locality(rows, taxonomy["species"], history, refs)

    # Mirror build_species: per comparable parameter the best row is shown as
    # the value, the rest as republications or alternatives.
    role = {}
    by_species = defaultdict(list)
    for row in rows:
        by_species[row["mdd_id"]].append(row)
    for mdd_id, srows in by_species.items():
        if mdd_id not in species_ids:
            continue
        groups = defaultdict(list)
        for row in srows:
            key = (row.get("call_variant") or "default", row["parameter"],
                   build_calls.comparability_key(row, registry, methods))
            groups[key].append(row)
        for prows in groups.values():
            prows.sort(key=lambda r: build_calls.rank(r, refs))
            role[id(prows[0])] = "shown"
            for other in prows[1:]:
                same_group = refs[other["reference_id"]].get("independence_group") == \
                    refs[prows[0]["reference_id"]].get("independence_group")
                role[id(other)] = "republished (listed with the shown value)" if same_group and \
                    other["value"] and other["value"] == prows[0]["value"] else "alternative value"

    out = defaultdict(list)
    for mdd_id, srows in by_species.items():
        if mdd_id not in species_ids:
            continue
        for row in srows:
            ref = sources.get(row["reference_id"], {})
            param = registry.get(row["parameter"])
            deep, needle = plazi_link(row["locator"], row.get("verbatim_value", ""))
            c = claim(section="echolocation", item=param["label"],
                      value=build_calls.format_value(row, registry), basis="measured",
                      role=role.get(id(row), "shown"), source=row["reference_id"],
                      link=ref.get("url", ""), deep_link=deep, highlight=needle,
                      locator=row["locator"], verbatim=row.get("verbatim_value", ""),
                      row=f"{row['_source_file']}:{row['_line']}")
            if row.get("taxon_match_method") == "locality_assigned":
                c["issues"].append(f"source names it {row['verbatim_taxon_name']}; placed here by recording locality")
            judge(c, sources)
            out[mdd_id].append(c)
    return out


def call_page_claims(species: list, sources: dict, measured: dict) -> dict:
    """Legacy prose entries and genus/family inference: shown, but from no row."""
    export = json.loads(CALLS_EXPORT.read_text(encoding="utf-8"))
    out = defaultdict(list)
    for s in species:
        entry = export["species"].get(s["id"])
        if entry and entry.get("format") == "legacy":
            c = claim(section="echolocation", item="summary (legacy entry)",
                      value=entry.get("summary", ""), basis="prose summary",
                      source=entry.get("reference", ""),
                      link=sources.get(entry.get("reference"), {}).get("url", ""))
            c["issues"].append("legacy prose entry: no structured row, no locator")
            judge(c, sources)
            out[s["id"]].append(c)
        if s["id"] in measured or (entry and entry.get("format") == "structured"):
            continue
        if entry:
            continue
        inference = export["genusInference"].get(s["genus"]) or export["familyInference"].get(s["family"])
        if not inference:
            continue
        shown = f"{inference['low']}–{inference['high']} kHz" if inference.get("show_range") else inference["mode"]
        for cite in inference.get("citations", []):
            c = claim(section="echolocation (inferred)",
                      item=f"{inference['scope']} expectation for {inference['taxon']}",
                      value=shown, basis="inferred, not measured in this species",
                      source=cite.get("id") or cite.get("label", ""),
                      link=cite.get("url") or "")
            sources.setdefault(c["source"], {"id": c["source"], "label": cite.get("label", ""),
                                             "citation": cite.get("citation", ""),
                                             "url": cite.get("url") or "", "link_scope": link_scope(cite)})
            if not cite.get("doi_verified", True):
                c["issues"].append("DOI not confirmed")
            judge(c, sources)
            if c["status"] == "no_locator":
                c["issues"].append("cited for the expectation as a whole; no page or table")
            out[s["id"]].append(c)
    return out


def diet_claims(species: list, sources: dict) -> dict:
    diet = json.loads(DIET.read_text(encoding="utf-8"))
    guilds = diet["_meta"]["guilds"]
    sources.setdefault("eltontraits-diet", {
        "id": "eltontraits-diet", "label": "EltonTraits 1.0", "type": "dataset",
        "citation": "Wilman H, et al. (2014) EltonTraits 1.0: Species-level foraging attributes "
                    "of the world's birds and mammals. Ecology 95: 2027.",
        "url": ELTONTRAITS_DATA, "licence": "CC0-1.0", "link_scope": "dataset",
        "sha256": diet["_meta"].get("sha256", "")})
    routes = {"s": ("measured", "MamFuncDat.txt, Diet-* columns, row for this species"),
              "p": ("compiled", "MamFuncDat.txt, Diet-* columns, row for the name before the split"),
              "g": ("inferred from the genus", ""),
              "r": ("rule: vampire bats feed on blood", "")}
    out = defaultdict(list)
    for s in species:
        entry = diet["species"].get(s["sciName"].replace("_", " "))
        if not entry:
            continue
        basis, locator = routes[entry["b"]]
        shares = ", ".join(f"{k} {v}%" for k, v in entry.get("sh", {}).items())
        c = claim(section="diet", item="guilds", value=", ".join(guilds[g] for g in entry["g"]),
                  basis=basis + f" (EltonTraits certainty {entry.get('c', '?')})",
                  source="eltontraits-diet", link=ELTONTRAITS_DATA, locator=locator,
                  verbatim=shares)
        judge(c, sources)
        if entry["b"] in "gr":
            c["status"] = "cited"
            c["issues"].append("derived by this project's rule, not printed in a source")
        out[s["id"]].append(c)
    return out


def range_claims(species: list, sources: dict, meta: dict) -> dict:
    supplement = json.loads(GBIF_SUPPLEMENT.read_text(encoding="utf-8"))
    danish = json.loads(DANISH.read_text(encoding="utf-8"))
    counts = json.loads(GBIF_CACHE.read_text(encoding="utf-8"))["species"] if GBIF_CACHE.exists() else {}
    iso2 = {}
    if GBIF_COUNTRIES.exists():
        for r in json.loads(GBIF_COUNTRIES.read_text(encoding="utf-8")):
            iso2[_norm(r.get("title", ""))] = r.get("iso2")
    sources.setdefault("mdd-v2.5", {"id": "mdd-v2.5", "label": meta["source"], "type": "dataset",
                                    "url": "https://doi.org/" + meta["sourceDoi"],
                                    "sha256": meta.get("sourceChecksum", ""), "link_scope": "dataset"})
    sources.setdefault("gbif", {"id": "gbif", "label": "GBIF occurrence records", "type": "database",
                                "url": "https://www.gbif.org", "link_scope": "dataset",
                                "access_note": "Human and machine observations only, at least 3 "
                                               "records, near MDD's range (build_country_distribution.py)."})
    out = defaultdict(list)
    for s in species:
        mdd = [c for c in (s.get("countryDistribution") or "").split("|") if c and c != "NA"]
        if mdd:
            c = claim(section="distribution", item="countries (MDD)", value=", ".join(mdd),
                      basis="checklist", source="mdd-v2.5", link=sources["mdd-v2.5"]["url"],
                      deep_link=f"https://www.mammaldiversity.org/taxon/{s['id']}/",
                      locator="countryDistribution", verbatim="|".join(mdd))
            judge(c, sources)
            out[s["id"]].append(c)
        key = (danish.get(s["id"]) or {}).get("gbifKey")
        for country in supplement.get(s["sciName"], []):
            code = iso2.get(_norm(country))
            n = (counts.get(s["sciName"]) or {}).get(code) if code else None
            deep = ""
            if key and code:
                deep = ("https://www.gbif.org/occurrence/search?occurrence_status=present"
                        "&basis_of_record=HUMAN_OBSERVATION&basis_of_record=MACHINE_OBSERVATION"
                        f"&taxon_key={key}&country={code}")
            c = claim(section="distribution", item=f"{country} (GBIF records)",
                      value=f"{n} observation records" if n else "observation records",
                      basis="observation records", source="gbif",
                      link=f"https://www.gbif.org/species/{key}" if key else "https://www.gbif.org",
                      deep_link=deep, locator=f"occurrence search, country={code or '?'}")
            if not deep:
                c["issues"].append("no record-level link: GBIF key or country code unknown here")
            judge(c, sources)
            out[s["id"]].append(c)
    return out


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


# ---------------------------------------------------------------- --check

_FAILED: set[str] = set()


def fetch_text(url: str, retries: int = 4) -> str | None:
    """Page text, cached under data/raw/claims_fetch so a re-run is free.

    Plazi answers a burst of requests with sporadic HTTP 500s, so a failure is
    retried with backoff; a page that still fails is not asked for again this run."""
    page_url = url.split("#")[0]
    if page_url in _FAILED:
        return None
    FETCH_CACHE.mkdir(parents=True, exist_ok=True)
    path = FETCH_CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", page_url)[-150:] + ".txt")
    if path.exists():
        return path.read_text(encoding="utf-8")
    request = urllib.request.Request(page_url, headers={"User-Agent": "treeofbatlife-claims/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8", errors="replace")
            break
        except Exception as error:  # noqa: BLE001
            if attempt == retries - 1:
                print(f"  could not fetch {page_url}: {error}")
                _FAILED.add(page_url)
                return None
            time.sleep(2 * (attempt + 1))
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    path.write_text(text, encoding="utf-8")
    time.sleep(0.5)  # be polite to Plazi and MDD
    return text


def _flat(text: str) -> str:
    """Compare without whitespace: OCR on these pages drops and adds spaces."""
    return re.sub(r"\s+", "", text.replace("–", "-").replace("—", "-")).lower()


def check(claims: dict) -> None:
    """Look for each claim's printed text on the open page its deep link opens."""
    for items in claims.values():
        for c in items:
            url = c["deep_link"]
            if ("tb.plazi.org" in url or "table.plazi.org" in url) and c["highlight"]:
                needle = c["highlight"]
            elif "mammaldiversity.org/taxon/" in url:
                needle = None
            else:
                continue
            text = fetch_text(url)
            if text is None:
                continue
            page = _flat(text)
            if needle is not None:
                found = _flat(needle) in page
            else:
                missing = [x for x in c["verbatim"].split("|") if _flat(x) not in page]
                found = not missing
                if missing:
                    c["issues"].append("not on the MDD page: " + ", ".join(missing))
            c["status"] = "located" if found else "not_found"
            c["checked_on"] = date.today().isoformat()


# ---------------------------------------------------------------- output

CSV_FIELDS = ["mdd_id", "species", "section", "item", "value", "basis", "role", "status",
              "source", "source_label", "link", "deep_link", "locator", "verbatim", "row",
              "upstream", "issues"]
STATUS_ORDER = ["located", "cited", "not_found", "generic_link", "no_locator", "unpublished", "unlinked"]


def write(species: list, claims: dict, sources: dict, out_dir: Path, scope: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    used = {c["source"] for items in claims.values() for c in items}
    payload = {
        "_meta": {"built": date.today().isoformat(), "builder": "data/build_claims.py", "scope": scope,
                  "statuses": STATUS_ORDER,
                  "claims": sum(len(v) for v in claims.values()), "species": len(claims)},
        "sources": {rid: sources[rid] for rid in sorted(used) if rid in sources},
        "species": {s["id"]: {"name": s["sciName"].replace("_", " "), "claims": claims.get(s["id"], [])}
                    for s in species},
    }
    (out_dir / "claims.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out_dir / "claims.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for s in species:
            for c in claims.get(s["id"], []):
                writer.writerow({**{k: c.get(k, "") for k in CSV_FIELDS},
                                 "mdd_id": s["id"], "species": s["sciName"].replace("_", " "),
                                 "source_label": sources.get(c["source"], {}).get("label", c["source"]),
                                 "issues": "; ".join(c["issues"])})


PAGE_FIELDS = ["section", "item", "value", "basis", "role", "status", "source", "link",
               "deep_link", "locator", "verbatim", "row", "issues", "checked_on"]


def page_export(species: list, claims: dict, sources: dict, path: Path, scope: str, checked: bool) -> None:
    """The compact file the species card's "Sources & evidence" panel reads.

    Each source is written once; each claim is an array in PAGE_FIELDS order,
    with its link left empty when it is the source's own link."""
    used = {c["source"] for items in claims.values() for c in items}
    keep = ("label", "url", "citation", "type", "licence", "link_scope", "access_note")
    out_sources = {rid: {k: sources[rid][k] for k in keep if sources[rid].get(k)}
                   for rid in sorted(used) if rid in sources}
    for entry in out_sources.values():
        if len(entry.get("access_note", "")) > 400:
            entry["access_note"] = entry["access_note"][:397].rsplit(" ", 1)[0] + " …"

    def row(c):
        same = c["link"] == sources.get(c["source"], {}).get("url", "")
        values = {**c, "link": "" if same else c["link"], "issues": "; ".join(c["issues"]),
                  "checked_on": c.get("checked_on", "")}
        return [values.get(k, "") for k in PAGE_FIELDS]

    payload = {
        "_meta": {"built": date.today().isoformat(), "builder": "data/build_claims.py", "scope": scope,
                  "checked": checked, "fields": PAGE_FIELDS, "statuses": STATUS_ORDER},
        "sources": out_sources,
        "species": {s["id"]: [row(c) for c in claims.get(s["id"], [])] for s in species},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  page export {path} ({path.stat().st_size // 1024} KB)")


def report(species: list, claims: dict, sources: dict, path: Path, scope: str) -> None:
    """A readable per-species ledger, for review before any of it reaches the page."""
    every = [c for items in claims.values() for c in items]
    lines = [f"# Evidence ledger: {scope}", "",
             (f"{len(species)} species, {len(every)} claims. Built {date.today().isoformat()} "
              "by data/build_claims.py."), "", "## Status by section", ""]
    sections = sorted({c["section"] for c in every})
    lines.append("| Section | " + " | ".join(STATUS_ORDER) + " | total |")
    lines.append("|---" * (len(STATUS_ORDER) + 2) + "|")
    for section in sections:
        n = Counter(c["status"] for c in every if c["section"] == section)
        lines.append(f"| {section} | " + " | ".join(str(n[s] or "") for s in STATUS_ORDER)
                     + f" | {sum(n.values())} |")
    lines += ["", "## Sources, worst first", "",
              "| Source | Link reaches | Claims | Statuses |", "|---|---|---|---|"]
    by_source = defaultdict(list)
    for c in every:
        by_source[c["source"]].append(c)

    def badness(item):
        statuses = Counter(c["status"] for c in item[1])
        return (-(statuses["unlinked"] + statuses["unpublished"] + statuses["no_locator"]
                  + statuses["generic_link"] + statuses["not_found"]), -len(item[1]))
    for rid, items in sorted(by_source.items(), key=badness):
        src = sources.get(rid, {})
        n = Counter(c["status"] for c in items)
        link = f"[{src.get('label', rid)}]({src['url']})" if src.get("url") else src.get("label", rid)
        lines.append(f"| {link} | {src.get('link_scope', '?')} | {len(items)} | "
                     + ", ".join(f"{k} {n[k]}" for k in STATUS_ORDER if n[k]) + " |")
    issue_counts = Counter(i.split(":")[0] for c in every for i in c["issues"])
    if issue_counts:
        lines += ["", "## Issues", ""] + [f"- {n} x {issue}" for issue, n in issue_counts.most_common()]
    lines += ["", "## Per species", ""]
    for s in species:
        items = claims.get(s["id"], [])
        lines += [f"### {s['sciName'].replace('_', ' ')}", ""]
        if not items:
            lines += ["No values with a source.", ""]
            continue
        by_section = defaultdict(list)
        for c in items:
            by_section[c["section"]].append(c)
        for section, cs in by_section.items():
            lines.append(f"**{section}**")
            lines.append("")
            per_source = defaultdict(list)
            for c in cs:
                per_source[c["source"]].append(c)
            for rid, group in per_source.items():
                src = sources.get(rid, {})
                label = src.get("label", rid)
                head = f"[{label}]({src['url']})" if src.get("url") else f"{label} (no link)"
                lines.append(f"- {head}")
                for c in group[:8]:
                    deep = f" · [open at the value]({c['deep_link']})" if c["deep_link"] else ""
                    where = f" · {c['locator']}" if c["locator"] else ""
                    note = f" · ⚠ {'; '.join(c['issues'])}" if c["issues"] else ""
                    lines.append(f"  - `{c['status']}` {c['item']}: {c['value']}{where}{deep}{note}")
                if len(group) > 8:
                    lines.append(f"  - … {len(group) - 8} more from this source")
            lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--country", help="comma-separated countries, as the page counts them "
                                          "(MDD list plus the GBIF supplement)")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report", type=Path, help="also write a readable Markdown ledger here")
    parser.add_argument("--page-export", type=Path, nargs="?", const=PAGE_EXPORT,
                        help=f"also write the species card's evidence file (default {PAGE_EXPORT.name})")
    parser.add_argument("--check", action="store_true",
                        help="fetch the open per-species pages (Plazi, MDD) and look for each value")
    args = parser.parse_args()

    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    species = taxonomy["species"]
    scope = "all species"
    if args.country:
        wanted = {c.strip() for c in args.country.split(",")}
        supplement = json.loads(GBIF_SUPPLEMENT.read_text(encoding="utf-8"))
        species = [s for s in species
                   if wanted & set((s.get("countryDistribution") or "").split("|"))
                   or wanted & set(supplement.get(s["sciName"], []))]
        scope = ", ".join(sorted(wanted))
    ids = {s["id"] for s in species}

    sources = load_sources()
    claims = defaultdict(list)
    measured_calls = call_claims(ids, sources)
    for part in (size_claims(ids, sources), measured_calls,
                 call_page_claims(species, sources, measured_calls),
                 diet_claims(species, sources), range_claims(species, sources, taxonomy["_meta"])):
        for mdd_id, items in part.items():
            claims[mdd_id].extend(items)
    if args.check:
        check(claims)

    write(species, claims, sources, args.out_dir, scope)
    if args.report:
        report(species, claims, sources, args.report, scope)
    if args.page_export:
        page_export(species, claims, sources, args.page_export, scope, args.check)
    every = [c for items in claims.values() for c in items]
    n = Counter(c["status"] for c in every)
    print(f"{scope}: {len(species)} species, {len(every)} claims -> {args.out_dir}")
    print("  " + ", ".join(f"{n[s]} {s}" for s in STATUS_ORDER if n[s]))


if __name__ == "__main__":
    main()
