"""Search for published calls of the bats that have none in the dataset.

Targets are the living species in echolocating families (every family but
Pteropodidae) with no entry in data/calls/exports/calls.json. Each is searched
under every name it has carried (data/chiroptera_name_history.json): older
papers use older combinations and trinomials.

Passes (run any; each writes a review queue, never a measurement):

  plazi     Plazi TreatmentBank. Every treatment filed under one of the
            species' names is fetched and every sentence naming kHz or
            echolocation is kept. Plazi holds the Handbook of the Mammals of
            the World vol. 9 accounts and many open descriptions; treatments
            are CC0 or open access.
            -> data/calls/search/plazi.json
  openalex  OpenAlex works whose title or abstract names the species (any of
            its names) together with an echolocation term.
            -> data/calls/search/openalex.json
  gbif      GBIF occurrence records with a sound file: evidence that a
            recording exists, not a measurement. Counts only, no audio.
            -> data/calls/search/gbif_sound.json

Each queue is read by a person; values found go into an importer as usual.

  log       Writes data/calls/search_log.csv, one row per target species with
            its status (STATUSES below). The status is automatic unless
            data/calls/search_decisions.csv records a person's verdict
            (columns mdd_id, species, status, decided_on, note).
            build_calls.py copies the log into the export for the card.

Raw downloads are cached in data/raw/calls/ (gitignored).

Run:  uv run data/calls/search_call_gaps.py plazi openalex
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE.parent
OUT = HERE / "search"
RAW = DATA / "raw" / "calls"
UA = {"User-Agent": "TreeOfBatLife call-gap search (open-source research site)"}

NON_ECHOLOCATING = {"Pteropodidae"}
TERMS = re.compile(r"\bkHz\b|kilohertz|echolocat|ultrason|\bcalls?\b.{0,40}\bfrequenc", re.I)


def get(url: str, tries: int = 4) -> bytes:
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return r.read()
        except Exception:  # noqa: BLE001 - Plazi answers 500 under load; back off
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def targets() -> list[dict]:
    taxonomy = json.loads((DATA / "chiroptera_taxonomy.json").read_text(encoding="utf-8"))["species"]
    calls = json.loads((HERE / "exports" / "calls.json").read_text(encoding="utf-8"))["species"]
    history = json.loads((DATA / "chiroptera_name_history.json").read_text(encoding="utf-8"))["species"]
    current = {s["sciName"].replace("_", " ") for s in taxonomy}
    out = []
    for s in taxonomy:
        if s["extinct"] == "1" or s["family"] in NON_ECHOLOCATING or s["id"] in calls:
            continue
        name = s["sciName"].replace("_", " ")
        h = history.get(name, {})
        names = {name}
        names |= {n[0] for n in h.get("names", [])}
        # Synonyms, unless the name is itself a current species (a split
        # parent): its literature is mostly about that other species.
        names |= {syn[0] for syn in h.get("syn", []) if syn and syn[0] not in current}
        names = {re.sub(r"\s+", " ", n.strip()) for n in names if n and len(n.split()) >= 2}
        out.append({"id": s["id"], "name": name, "family": s["family"],
                    "year": s["authoritySpeciesYear"], "names": sorted(names),
                    "description": h.get("link", "")})
    return out


def binomial_match(verbatim: str, names: list[str]) -> bool:
    words = re.sub(r"[^A-Za-z ]", " ", verbatim).split()
    for name in names:
        parts = name.split()
        if words[:len(parts)] == parts:
            return True
    return False


# --- Plazi ---------------------------------------------------------------------

SRS = ("https://tb.plazi.org/GgServer/srsStats/stats?outputFields=doc.uuid+bib.source+doc.date+tax.name"
       "&groupingFields=doc.uuid+bib.source+doc.date+tax.name&FP-tax.name={}&format=JSON")


def plazi_docs(target: dict) -> list[dict]:
    epithets = {n.split()[-1] for n in target["names"]}
    docs = {}
    for epithet in sorted(epithets):
        raw = get(SRS.format(urllib.parse.quote(f"%{epithet}%")))
        for row in json.loads(raw.decode("utf-8", "replace"))["data"]:
            if binomial_match(row["TaxName"], target["names"]):
                docs[row["DocUuid"]] = {"uuid": row["DocUuid"], "source": row.get("BibSource", ""),
                                        "date": row.get("DocDate", ""), "taxon": row["TaxName"]}
    return list(docs.values())


def plazi_text(uuid: str) -> str:
    cache = RAW / "plazi" / f"{uuid}.xml"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(get(f"https://tb.plazi.org/GgServer/xml/{uuid}"))
    try:
        root = ET.fromstring(cache.read_bytes())
    except ET.ParseError:
        return ""
    return re.sub(r"\s+", " ", " ".join(root.itertext()))


def snippets(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.;])\s+(?=[A-Z(])", text)
    return [s.strip()[:600] for s in sentences if TERMS.search(s)]


def run_plazi(items: list[dict]) -> None:
    def one(t):
        try:
            docs = plazi_docs(t)
        except Exception as e:  # noqa: BLE001
            return {**t, "error": str(e), "docs": []}
        for d in docs:
            try:
                d["snippets"] = snippets(plazi_text(d["uuid"]))
            except Exception as e:  # noqa: BLE001
                d["error"] = str(e)
        return {**t, "docs": docs}

    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(one, items))
    write("plazi", results, lambda r: any(d.get("snippets") for d in r["docs"]))


# --- OpenAlex ------------------------------------------------------------------

OA = "https://api.openalex.org/works?filter=title_and_abstract.search:{}&per-page=50&select={}"
SELECT = "id,doi,title,publication_year,open_access,primary_location,type"


def previous(name: str) -> dict:
    """Earlier successful results, so a rate-limited pass can resume."""
    path = OUT / f"{name}.json"
    if not path.exists():
        return {}
    return {r["id"]: r for r in json.loads(path.read_text(encoding="utf-8"))["species"]
            if not r.get("error")}


def run_openalex(items: list[dict]) -> None:
    # OpenAlex meters keyless use in daily credits (a search costs 10 of
    # 1,000), so a full pass takes several days. Finished species are kept and
    # only the rest are asked; a 429 is recorded, not retried around.
    done = previous("openalex")
    blocked = False

    def one(t):
        nonlocal blocked
        if t["id"] in done:
            return done[t["id"]]
        if blocked:
            return {**t, "error": "not asked: daily OpenAlex limit reached", "works": []}
        names = " OR ".join(f'"{n}"' for n in t["names"])
        query = f"({names}) AND (echolocation OR ultrasonic OR acoustic OR call OR calls OR kHz)"
        url = OA.format(urllib.parse.quote(query), SELECT)
        try:
            data = json.loads(get(url, tries=1))
        except Exception as e:  # noqa: BLE001
            if "429" in str(e):
                blocked = True
            return {**t, "error": str(e), "works": []}
        works = [{"title": w.get("title"), "year": w.get("publication_year"), "doi": w.get("doi"),
                  "oa": (w.get("open_access") or {}).get("oa_status"),
                  "oa_url": (w.get("open_access") or {}).get("oa_url"),
                  "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name")}
                 for w in data.get("results", [])]
        time.sleep(0.15)  # OpenAlex asks for at most 10 requests a second
        return {**t, "works": works}

    with ThreadPoolExecutor(1) as pool:
        results = list(pool.map(one, items))
    write("openalex", results, lambda r: bool(r["works"]))


# --- Europe PMC ------------------------------------------------------------------
#
# Europe PMC's REST API searches titles, abstracts and the full text of its
# open-access papers, so it also finds calls reported only in a paper's
# results. Meant for programmatic use; no key.

EPMC = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&pageSize=50"
        "&resultType=lite&query={}")


def run_europepmc(items: list[dict]) -> None:
    done = previous("europepmc")

    def one(t):
        if t["id"] in done:
            return done[t["id"]]
        names = " OR ".join(f'"{n}"' for n in t["names"])
        query = f'({names}) AND (echolocation OR "echolocation call" OR kHz OR ultrasonic)'
        try:
            data = json.loads(get(EPMC.format(urllib.parse.quote(query))))
        except Exception as e:  # noqa: BLE001
            return {**t, "error": str(e), "works": []}
        works = [{"title": w.get("title"), "year": w.get("pubYear"), "doi": w.get("doi"),
                  "pmcid": w.get("pmcid"), "oa": w.get("isOpenAccess"),
                  "venue": w.get("journalTitle"), "source": w.get("source"), "id": w.get("id")}
                 for w in data.get("resultList", {}).get("result", [])]
        time.sleep(0.2)
        return {**t, "hit_count": data.get("hitCount", 0), "works": works}

    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(one, items))
    write("europepmc", results, lambda r: bool(r["works"]))


# --- GBIF sound records ----------------------------------------------------------
#
# Whether a recording exists at all, from GBIF's occurrence index (its API is
# meant for programmatic use). Only counts and dataset names are read; no audio
# is downloaded. ChiroVox (robots.txt: Disallow /) and xeno-canto (robots.txt
# disallows Anthropic's agents and /api/) are not contacted: a recording held
# there shows up here only if the archive itself publishes to GBIF.

GBIF = "https://api.gbif.org/v1"


def run_gbif(items: list[dict]) -> None:
    def one(t):
        try:
            # Only a binomial GBIF accepts as a species of its own. A synonym's
            # records are filed under its accepted name -- for a recent split,
            # the parent species -- so following it would count the parent's
            # recordings as this species'.
            keys = set()
            for name in t["names"]:
                if len(name.split()) != 2:
                    continue
                m = json.loads(get(f"{GBIF}/species/match?rank=SPECIES&strict=true&name="
                                   + urllib.parse.quote(name)))
                if (m.get("usageKey") and m.get("matchType") == "EXACT"
                        and m.get("status") in ("ACCEPTED", "DOUBTFUL")
                        and m.get("rank") == "SPECIES"):
                    keys.add(m["usageKey"])
            records, datasets = 0, {}
            for key in sorted(keys):
                q = json.loads(get(f"{GBIF}/occurrence/search?taxonKey={key}&mediaType=Sound"
                                   "&limit=0&facet=datasetKey&datasetKey.facetLimit=20"))
                records += q.get("count", 0)
                for f in (q.get("facets") or [{}])[0].get("counts", []):
                    datasets[f["name"]] = datasets.get(f["name"], 0) + f["count"]
            named = {}
            for key, n in datasets.items():
                title = json.loads(get(f"{GBIF}/dataset/{key}")).get("title", key)
                named[title] = n
            return {**t, "gbif_keys": sorted(keys), "sound_records": records, "datasets": named}
        except Exception as e:  # noqa: BLE001
            return {**t, "error": str(e)}

    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(one, items))
    write("gbif_sound", results, lambda r: r.get("sound_records", 0) > 0)


def run_triage(items: list[dict]) -> None:
    """Read each Europe PMC candidate far enough to tell whether it reports
    this species' call: the full text of an open-access paper, otherwise its
    abstract. Keeps the sentences that name the species (in full or as
    "G. epithet") and give kHz or speak of echolocation."""
    _, epmc = load_queue("europepmc")
    cache = RAW / "europepmc"
    cache.mkdir(parents=True, exist_ok=True)

    def text_of(work: dict) -> tuple[str, str]:
        if work.get("pmcid"):
            path = cache / f"{work['pmcid']}.xml"
            if not path.exists():
                try:
                    path.write_bytes(get("https://www.ebi.ac.uk/europepmc/webservices/rest/"
                                         f"{work['pmcid']}/fullTextXML"))
                except Exception:  # noqa: BLE001 - not every PMC id has text
                    path.write_bytes(b"")
            raw = path.read_bytes()
            if raw:
                try:
                    return "full text", " ".join(ET.fromstring(raw).itertext())
                except ET.ParseError:
                    pass
        key = f"{work.get('source')}-{work.get('id')}"
        path = cache / f"{key}.json"
        if not path.exists():
            path.write_bytes(get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json"
                                 f"&resultType=core&query=EXT_ID:{work.get('id')}%20AND%20SRC:{work.get('source')}"))
        hits = json.loads(path.read_text(encoding="utf-8")).get("resultList", {}).get("result", [])
        return "abstract", (hits[0].get("abstractText") or "") if hits else ""

    def one(t):
        pats = set()
        for name in t["names"]:
            genus, *rest = name.split()
            pats.add(re.escape(name))
            pats.add(rf"{re.escape(genus[0])}\.\s*{re.escape(' '.join(rest))}")
        name_re = re.compile("|".join(sorted(pats)))
        out = []
        for w in epmc.get(t["id"], {}).get("works", []):
            try:
                kind, text = text_of(w)
            except Exception as e:  # noqa: BLE001
                out.append({**w, "read": "error", "error": str(e), "evidence": []})
                continue
            text = re.sub(r"\s+", " ", text)
            sentences = re.split(r"(?<=[.;])\s+(?=[A-Z(])", text)
            evidence = [s[:500] for s in sentences
                        if name_re.search(s) and re.search(r"kHz|echolocat", s, re.I)]
            out.append({**w, "read": kind, "evidence": evidence[:8]})
        return {**t, "works": out}

    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(one, [t for t in items if t["id"] in epmc]))
    write("europepmc_triage", results, lambda r: any(w["evidence"] for w in r["works"]))


# --- search log ------------------------------------------------------------------
#
# One row per target species: what was searched, what turned up, and where the
# species stands. The automatic status comes from the queues; a person's
# verdict after reading them, in search_decisions.csv, overrides it.

STATUSES = {
    "to_read": "Candidate sources found; not yet read.",
    "published_not_open": "A source with call measurements exists but is not openly available.",
    "recording_only": "Recordings exist (sound records in GBIF), but no published measurement was found.",
    "searched_none_found": "No published call measurement or recording was found.",
    "stated_unknown": "A source states that the call has not been described.",
    "described_not_measured": "A source describes the call, but gives no value the dataset can hold "
                              "(an unnamed frequency, a 'mean frequency', or values reassigned from other studies).",
}
LOG = HERE / "search_log.csv"
DECISIONS = HERE / "search_decisions.csv"


def load_queue(name: str) -> tuple[str, dict]:
    path = OUT / f"{name}.json"
    if not path.exists():
        return "", {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["searched_on"], {r["id"]: r for r in data["species"]}


def run_log(items: list[dict]) -> None:
    import csv
    plazi_on, plazi = load_queue("plazi")
    oa_on, oa = load_queue("openalex")
    gbif_on, gbif = load_queue("gbif_sound")
    epmc_on, epmc = load_queue("europepmc")
    _, triage = load_queue("europepmc_triage")
    decisions = {}
    if DECISIONS.exists():
        with DECISIONS.open(encoding="utf-8", newline="") as f:
            decisions = {r["mdd_id"]: r for r in csv.DictReader(f)}
    rows = []
    for t in items:
        p, o, g = plazi.get(t["id"], {}), oa.get(t["id"], {}), gbif.get(t["id"], {})
        e = epmc.get(t["id"], {})
        # A treatment counts only if it states a frequency, not merely the word.
        plazi_hits = [d["uuid"] for d in p.get("docs", [])
                      if any(re.search(r"kHz|kilohertz", s, re.I) for s in d.get("snippets", []))]
        oa_hits = [w["doi"] or w["title"] for w in o.get("works", [])]
        # Europe PMC hits count once triage has found the species named with
        # a call term in the paper's text; until then, every hit counts.
        tri = triage.get(t["id"])
        if tri:
            oa_hits += [w["doi"] or w["id"] for w in tri["works"] if w.get("evidence")]
        else:
            oa_hits += [w["doi"] or w["id"] for w in e.get("works", [])]
        sounds = g.get("sound_records", 0)
        status = ("to_read" if plazi_hits or oa_hits
                  else "recording_only" if sounds else "searched_none_found")
        note = ""
        d = decisions.get(t["id"])
        if d:
            status, note = d["status"], d.get("note", "")
        if status not in STATUSES:
            raise SystemExit(f"{t['name']}: unknown status {status!r} in {DECISIONS.name}")
        rows.append({
            "mdd_id": t["id"], "species": t["name"], "family": t["family"], "status": status,
            "searched_on": max(filter(None, [plazi_on, oa_on, gbif_on, epmc_on]), default=""),
            "plazi_treatments": len(p.get("docs", [])), "plazi_with_call_text": len(plazi_hits),
            "literature_candidates": len(oa_hits),
            "openalex_complete": "no" if o.get("error") or not o else "yes",
            "gbif_sound_records": sounds,
            "decided_on": d.get("decided_on", "") if d else "", "note": note,
        })
    with LOG.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(f"{LOG.name}: {len(rows)} species -> "
          + ", ".join(f"{n} {s}" for s, n in Counter(r['status'] for r in rows).most_common()))


def write(name: str, results: list[dict], has_hit) -> None:
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps({"searched_on": time.strftime("%Y-%m-%d"), "species": results},
                               ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    hits = sum(1 for r in results if has_hit(r))
    errors = sum(1 for r in results if r.get("error"))
    print(f"{name}: {len(results)} species searched, {hits} with candidates, {errors} errors -> {path}")


def main() -> None:
    items = targets()
    print(f"{len(items)} target species")
    if "--limit" in sys.argv:
        items = items[:int(sys.argv[sys.argv.index("--limit") + 1])]
    if "plazi" in sys.argv:
        run_plazi(items)
    if "openalex" in sys.argv:
        run_openalex(items)
    if "europepmc" in sys.argv:
        run_europepmc(items)
    if "triage" in sys.argv:
        run_triage(items)
    if "gbif" in sys.argv:
        run_gbif(items)
    if "log" in sys.argv:
        run_log(items)


if __name__ == "__main__":
    main()
