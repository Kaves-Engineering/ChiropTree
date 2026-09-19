"""Build data/dinosaur_taxonomy.json from the Paleobiology Database.

Run:  uv run python data/build_dinosaur_taxonomy.py [--refresh]

The mammal pages are built from the Mammal Diversity Database and the bird page
from AviList. Neither covers anything that died 66 million years ago, so this
page uses the Paleobiology Database (PBDB, https://paleobiodb.org, CC BY 4.0),
the community database of fossil taxa and occurrences. PBDB has a public JSON
API; two calls fetch everything the page needs:

  taxa/list   every accepted taxon under Dinosauria, with its parent,
              authority, first/last appearance and ecology (diet)
  occs/list   every fossil occurrence under Dinosauria, with the country it
              was found in and its geological formation

Both responses are cached in data/raw/ (gitignored). --refresh re-downloads.

What counts as a species here:

  * accepted names only: PBDB's "valid" status would include junior synonyms
    (Brontosaurus excelsus is valid, Antrodemus is valid-as-a-synonym), so the
    query asks for taxon_status=accepted.
  * body fossils only (pres=regular): ichnotaxa, which name footprints, and
    oospecies, which name eggs, are left out; they are not animals one could
    put on a tree.
  * no birds. Birds are dinosaurs, and the bird page covers the living ones.
    Everything under PBDB's Avialae and Aves is cut, which also takes
    Archaeopteryx and the Mesozoic birds with it: the page is the non-avialan
    dinosaurs.

PBDB's hierarchy is uneven: half the genera have no family, and it carries
some families few workers use. So the page does not draw PBDB's families
directly. GROUPS below names the groups the tree draws, each by the PBDB taxa
it absorbs, and every genus lands in the group of its nearest ancestor that is
named there. That is the one editorial layer; everything else -- which genus
belongs to which clade, the species, their ages and where they were found --
is PBDB's. The build fails if any genus finds no group.

The output keeps MDD's record shape (id, sciName as Genus_species, order,
family, genus, specificEpithet, countryDistribution, ...) so the master
page's lookup, card and map code reads it unchanged. Fields particular to
fossils are carried under their own names:

  age          geological stage(s), e.g. "Campanian to Maastrichtian"
  maxMa/minMa  first and last appearance, millions of years ago
  diet         PBDB's ecospace diet
  formations   rock formations the species is recorded from, most records first
  occurrences  number of PBDB occurrence records
  reference    the publication that named it
  pbdb         PBDB taxon number (for the link to its PBDB page)

Countries are where the fossils were found: present-day political
geography, not where the animal lived on a Mesozoic map. Only occurrences
identified to the species count -- "Tyrannosaurus sp." says nothing about
which species it was.
"""
import collections
import hashlib
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "raw"
TAXA_RAW = RAW / "pbdb_dinosauria_taxa.json"
OCCS_RAW = RAW / "pbdb_dinosauria_occs.json"
COUNTRY_ENUM_RAW = RAW / "gbif_country_enum.json"
MDD_CSV = RAW / "MDD_v2.5_6904species.csv"
WORLD_MAP = HERE / "marine_world_map.json"
OUT = HERE / "dinosaur_taxonomy.json"

API = "https://paleobiodb.org/data1.2"
# compact vocabulary: PBDB's long-name vocabulary leaves the rank empty on
# accepted-only taxon queries, the compact one does not
TAXA_URL = (API + "/taxa/list.json?base_name=Dinosauria&taxon_status=accepted&pres=regular"
            "&show=app,attr,common,ecospace,parent,ref")
OCCS_URL = API + "/occs/list.json?base_name=Dinosauria&pres=regular&show=loc,strat&vocab=pbdb"
COUNTRY_ENUM_URL = "https://api.gbif.org/v1/enumeration/country"

# Not dinosaurs for this page's purposes: see the docstring.
EXCLUDE = {"Avialae", "Aves"}

# Egg taxa PBDB has not flagged as form taxa, so pres=regular lets them
# through (Himeoolithus). Oogenera are named -oolithus by convention.
OOTAXON = re.compile(r"oolithus$")

# PBDB country codes that are not ISO 3166-1 alpha-2
PBDB_CC = {"UK": "GB"}

# The groups the tree draws, as {group: PBDB taxa it absorbs}. A genus goes
# to the group of its nearest named ancestor, so a named subgroup always wins
# over its parent: a hadrosaurid goes to Hadrosauridae, not Hadrosauroidea.
# A group keyed by a clade name and absorbing only that clade is a catch-all
# for genera PBDB places no deeper.
GROUPS = {
    # --- early and unplaced
    "Dinosauria": ["Dinosauria"],
    "Herrerasauridae": ["Herrerasauridae"],
    "Saurischia": ["Saurischia"],
    # --- Ornithischia
    "Silesauridae": ["Silesauridae"],
    "Ornithischia": ["Ornithischia", "Parapredentata", "Saphornithischia", "Prionodontia",
                     "Genasauria", "Fabrosauridae"],
    "Heterodontosauridae": ["Heterodontosauridae"],
    "Thyreophora": ["Thyreophora", "Thyreophoroidea", "Eurypoda", "Scelidosauridae"],
    "Stegosauria": ["Stegosauria"],
    "Ankylosauria": ["Ankylosauria", "Euankylosauria", "Parankylosauria"],
    "Nodosauridae": ["Nodosauridae"],
    "Ankylosauridae": ["Ankylosauridae"],
    "Neornithischia": ["Neornithischia", "Pyrodontia", "Cerapoda"],
    "Thescelosauridae": ["Thescelosauridae"],
    "Ornithopoda": ["Ornithopoda", "Hypsilophodontidae"],
    "Elasmaria": ["Elasmaria"],
    "Rhabdodontomorpha": ["Rhabdodontomorpha"],
    "Iguanodontia": ["Iguanodontia", "Euiguanodontia", "Dryomorpha", "Ankylopollexia",
                     "Neoiguanodontia", "Iguanodontoidea"],
    "Dryosauridae": ["Dryosauridae"],
    "Styracosterna": ["Styracosterna", "Hadrosauriformes"],
    "Hadrosauroidea": ["Hadrosauroidea"],
    "Hadrosauridae": ["Hadrosauridae"],
    "Lambeosaurinae": ["Lambeosaurinae"],
    "Pachycephalosauria": ["Marginocephalia", "Pachycephalosauria"],
    "Ceratopsia": ["Ceratopsia", "Chaoyangsauridae"],
    "Neoceratopsia": ["Neoceratopsia", "Coronosauria", "Ceratopsoidea"],
    "Leptoceratopsidae": ["Leptoceratopsidae"],
    "Protoceratopsidae": ["Protoceratopsidae"],
    "Centrosaurinae": ["Ceratopsidae", "Centrosaurinae", "Centrasaurinae"],
    "Chasmosaurinae": ["Chasmosaurinae"],
    # --- Sauropodomorpha
    "Sauropodomorpha": ["Sauropodomorpha", "Saturnaliidae", "Guaibasauridae", "Unaysauridae",
                        "Bagualosauria"],
    "Plateosauridae": ["Plateosauridae", "Plateosauria"],
    "Massospondylidae": ["Massospondylidae"],
    "Massopoda": ["Massopoda", "Sauropodiformes", "Riojasauridae"],
    "Sauropoda": ["Sauropoda", "Lessemsauridae", "Gravisauria", "Eusauropoda", "Cetiosauridae"],
    "Mamenchisauridae": ["Mamenchisauridae"],
    "Turiasauria": ["Turiasauria"],
    "Diplodocoidea": ["Diplodocoidea", "Diplodocimorpha", "Flagellicaudata", "Neosauropoda"],
    "Rebbachisauridae": ["Rebbachisauridae"],
    "Dicraeosauridae": ["Dicraeosauridae"],
    "Diplodocidae": ["Diplodocidae"],
    "Macronaria": ["Macronaria", "Camarasauromorpha", "Camarasauridae", "Titanosauriformes"],
    "Brachiosauridae": ["Brachiosauridae"],
    "Somphospondyli": ["Somphospondyli", "Diamantinasauria"],
    "Euhelopodidae": ["Euhelopodidae"],
    "Titanosauria": ["Titanosauria", "Eutitanosauria"],
    "Colossosauria": ["Colossosauria"],
    "Lithostrotia": ["Lithostrotia"],
    "Saltasauroidea": ["Saltasauroidea"],
    # --- Theropoda
    "Theropoda": ["Theropoda", "Neotheropoda", "Averostra"],
    "Coelophysoidea": ["Coelophysoidea"],
    "Ceratosauria": ["Ceratosauria", "Ceratosauridae"],
    "Noasauridae": ["Noasauridae"],
    "Abelisauridae": ["Abelisauridae", "Abelisauroidea"],
    "Tetanurae": ["Tetanurae", "Avetheropoda"],
    "Megalosauroidea": ["Megalosauroidea", "Piatnitzkysauridae", "Megalosauridae"],
    "Spinosauridae": ["Spinosauridae"],
    "Allosauroidea": ["Allosauroidea", "Metriacanthosauridae"],
    "Carcharodontosauria": ["Carcharodontosauria", "Carcharodontosauridae", "Neovenatoridae"],
    "Megaraptora": ["Megaraptora"],
    "Coelurosauria": ["Coelurosauria", "Maniraptoriformes", "Compsognathidae", "Sinosauropterygidae"],
    "Tyrannosauroidea": ["Tyrannosauroidea"],
    "Tyrannosauridae": ["Tyrannosauridae"],
    "Ornithomimosauria": ["Ornithomimosauria"],
    "Alvarezsauria": ["Alvarezsauria"],
    "Therizinosauria": ["Therizinosauria"],
    "Oviraptorosauria": ["Oviraptorosauria"],
    "Caenagnathidae": ["Caenagnathidae"],
    "Oviraptoridae": ["Oviraptoridae"],
    "Paraves": ["Maniraptora", "Paraves", "Scansoriopterygidae", "Anchiornithidae", "Deinonychosauria"],
    "Troodontidae": ["Troodontidae"],
    "Dromaeosauridae": ["Dromaeosauridae"],
}

# Clades the card's lineage line names above the group, broadest first. PBDB
# hangs Theropoda straight off Dinosauria rather than under Saurischia, so
# membership in either saurischian branch counts as saurischian.
ORDERS = {"Ornithischia": "Ornithischia", "Saurischia": "Saurischia",
          "Theropoda": "Saurischia", "Sauropodomorpha": "Saurischia"}
SUBORDERS = ("Thyreophora", "Ornithopoda", "Marginocephalia", "Sauropodomorpha", "Theropoda")


def fetch(url: str, path: Path, refresh: bool):
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {url} ...", flush=True)
        request = urllib.request.Request(url, headers={"User-Agent": "chiroptree-data/1.0"})
        with urllib.request.urlopen(request, timeout=300) as response:
            path.write_bytes(response.read())
    return json.loads(path.read_text(encoding="utf-8"))


def num(oid: str) -> str:
    return oid.split(":")[-1]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def canonical_names(index: dict) -> dict:
    """map key -> the spelling MDD uses for it, so every page names places alike."""
    import csv
    canonical = {}
    if not MDD_CSV.exists():
        return canonical
    with MDD_CSV.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            for raw in row["countryDistribution"].split("|"):
                name = raw.strip().rstrip("?").strip()
                key = index.get(norm(name)) if name and name != "NA" else None
                if key and key not in canonical:
                    canonical[key] = name
    return canonical


def age_text(r: dict) -> str:
    early, late = r.get("tei"), r.get("tli")
    if early and late and late != early:
        return f"{early} to {late}"
    return early or ""


def ma(value) -> float | None:
    return round(float(value), 1) if value not in (None, "") else None


def main():
    refresh = "--refresh" in sys.argv
    taxa = fetch(TAXA_URL, TAXA_RAW, refresh)["records"]
    occs = fetch(OCCS_URL, OCCS_RAW, refresh)["records"]
    enum = {r["iso2"]: r for r in fetch(COUNTRY_ENUM_URL, COUNTRY_ENUM_RAW, refresh) if r.get("iso2")}
    index = json.loads(WORLD_MAP.read_text(encoding="utf-8"))["index"]
    canonical = canonical_names(index)

    by = {num(r["oid"]): r for r in taxa}
    absorbed = {}
    for group, names in GROUPS.items():
        for name in names:
            assert name not in absorbed, f"{name} is absorbed by two groups"
            absorbed[name] = group
    known = {r["nam"] for r in taxa}
    stale = sorted(set(absorbed) - known)
    if stale:
        sys.exit(f"GROUPS names taxa PBDB no longer has: {stale}")

    def chain(r):
        out = []
        while r is not None:
            out.append(r)
            r = by.get(num(r["par"])) if r.get("par") else None
        return out

    # ------------------------------------------------------------ occurrences
    # subspecies occurrences count for their species
    to_species = {num(r["oid"]): num(r["par"]) for r in taxa if r["rnk"] == "subspecies"}
    countries = collections.defaultdict(collections.Counter)
    formations = collections.defaultdict(collections.Counter)
    unplaced = collections.Counter()
    for occ in occs:
        if occ.get("accepted_rank") not in ("species", "subspecies"):
            continue
        sid = to_species.get(occ["accepted_no"], occ["accepted_no"])
        if occ.get("formation"):
            formations[sid][occ["formation"].strip()] += 1
        cc = PBDB_CC.get(occ.get("cc"), occ.get("cc"))
        country = enum.get(cc)
        if not country:
            unplaced[occ.get("cc")] += 1
            continue
        key = index.get(country["iso3"].lower()) or index.get(norm(country["title"]))
        if not key:
            unplaced[country["title"]] += 1
            continue
        countries[sid][canonical.get(key) or country["title"]] += 1

    # ------------------------------------------------------------ species
    species, orphans, cut, eggs = [], [], 0, 0
    for r in taxa:
        if r["rnk"] != "species":
            continue
        line = chain(r)
        names = [x["nam"] for x in line]
        if names[-1] != "Dinosauria":
            orphans.append(r["nam"])          # parent genus not accepted
            continue
        if EXCLUDE & set(names):
            cut += 1
            continue
        genus = next((x for x in line if x["rnk"] == "genus"), None)
        if genus is None:
            orphans.append(r["nam"])
            continue
        if OOTAXON.search(genus["nam"]):
            eggs += 1
            continue
        above = line[line.index(genus) + 1:]
        hit = next((i for i, x in enumerate(above) if x["nam"] in absorbed), None)
        if hit is None:
            sys.exit(f"{genus['nam']} lands in no group: {' < '.join(x['nam'] for x in above)}")
        group = absorbed[above[hit]["nam"]]
        # PBDB's own subgroups below the drawn group become the page's
        # subfamily and tribe rows -- unless GROUPS draws them itself
        below = [x["nam"] for x in reversed(above[:hit]) if x["nam"] not in absorbed]
        epithet = r["nam"].split(" ", 1)[1]
        sid = num(r["oid"])
        record = {
            "id": f"pbdb-{sid}",
            "sciName": f"{genus['nam']}_{epithet}",
            "mainCommonName": r.get("nm2", ""),
            "order": next((ORDERS[n] for n in names if n in ORDERS), "Dinosauria"),
            "suborder": next((n for n in names if n in SUBORDERS), ""),
            "family": group,
            "subfamily": below[0] if below else "",
            "tribe": below[1] if len(below) > 1 else "",
            "genus": genus["nam"],
            "specificEpithet": epithet,
            "authoritySpeciesAuthor": r.get("att", ""),
            "extinct": "1",
            "age": age_text(r),
            "maxMa": ma(r.get("fea")),
            "minMa": ma(r.get("lla")),
            "diet": r.get("jdt", ""),
            "reference": r.get("ref", ""),
            "pbdb": sid,
            "occurrences": r.get("noc", 0),
        }
        found = countries.get(sid)
        if found:
            record["countryDistribution"] = "|".join(sorted(found))
        forms = formations.get(sid)
        if forms:
            record["formations"] = "|".join(f for f, _ in forms.most_common(6))
        species.append({k: v for k, v in record.items() if v not in ("", None)})

    # PBDB occasionally keeps a species under both its original combination
    # and its current one (Asiamericana asiatica, now Richardoestesia
    # asiatica); both resolve to the same name here. Keep the better-recorded.
    merged = {}
    for s in sorted(species, key=lambda s: -s.get("occurrences", 0)):
        merged.setdefault(s["sciName"], s)
    dupes = len(species) - len(merged)
    species = sorted(merged.values(), key=lambda s: s["sciName"])
    ids = [s["id"] for s in species]
    assert len(ids) == len(set(ids)), "duplicate species id"
    empty = sorted(set(GROUPS) - {s["family"] for s in species})
    if empty:
        sys.exit(f"GROUPS draws groups with no species: {empty}")

    checksum = hashlib.sha256(TAXA_RAW.read_bytes() + OCCS_RAW.read_bytes()).hexdigest()
    payload = {
        "_meta": {
            "source": "Paleobiology Database",
            "sourceDoi": None,
            "sourceUrl": "https://paleobiodb.org",
            "sourceApi": TAXA_URL,
            "sourceChecksum": checksum,
            "license": "CC BY 4.0",
            "citation": "Paleobiology Database, https://paleobiodb.org, data downloaded via the PBDB API",
            "speciesCount": len(species),
            "familyCount": len(GROUPS),
            "genusCount": len({s["genus"] for s in species}),
            "countrySource": "PBDB occurrences identified to species: the present-day country each fossil was found in",
        },
        "families": sorted(GROUPS),
        "species": species,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    with_countries = sum(1 for s in species if s.get("countryDistribution"))
    print(f"Wrote {len(species)} species, {payload['_meta']['genusCount']} genera, {len(GROUPS)} groups "
          f"to {OUT} ({OUT.stat().st_size / 1024:.0f} KB); {with_countries} with countries; "
          f"{cut} avialan species cut; {len(orphans)} species under a non-accepted genus skipped; "
          f"{dupes} duplicate names merged; {eggs} egg taxa dropped")
    if unplaced:
        print("Country codes the map cannot place (occurrences skipped):", dict(unplaced.most_common()))


if __name__ == "__main__":
    main()
