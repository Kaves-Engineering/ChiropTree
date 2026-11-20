"""Build data/chiroptera_diet.json: the foods each bat species eats, for the call plot.

Source: EltonTraits 1.0 (Wilman et al. 2014), the same checksum-pinned table
data/size/import_eltontraits.py reads. Its Diet-* columns give the share (in
steps of 10%) of ten food types in each species' diet. They are compiled from
the handbooks, mostly at species level (Diet-Certainty ABC) and otherwise from
the genus or family (D1, D2); the certainty is kept per species.

Fetch (CC0, figshare 10.6084/m9.figshare.c.3306933.v1), into
data/raw/size/eltontraits/:
    curl -L -o MamFuncDat.txt https://ndownloader.figshare.com/files/5631084

The ten food types fold into six guilds:

    ins  insects and other invertebrates   Diet-Inv
    fru  fruit, seeds and other plant      Diet-Fruit, Diet-Seed, Diet-PlantO
    nec  nectar and pollen                 Diet-Nect
    ver  land vertebrates                  Diet-Vend, Diet-Vect, Diet-Vunk, Diet-Scav
    fis  fish                              Diet-Vfish
    blo  blood                             the three vampire bats (see below)

A species belongs to every guild making up at least 30% of its diet (MIN_SHARE),
listed largest share first, so a bat with a mixed diet sits in each of the
groups it eats rather than in a "mixed" group of its own. At 30% every species
with shares gets at least one guild (at 40% two would get none). EltonTraits
has no blood category and codes the vampires as endotherm-eaters, so every
species of the subfamily Desmodontinae is set to blood alone, by rule.

Names resolve against MDD v2.5 the way the size importers resolve them
(data/size/size_lib.py). Unlike a body size, a diet can be carried across a
split, so a name that has since been split gives its diet to every daughter.
An MDD species EltonTraits does not cover takes its genus's guilds only when
every covered species of that genus has the same set of guilds; otherwise it
stays unknown. Each entry says which of these routes it came from.

Run: uv run data/build_diet.py
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "size"))
from call_import_lib import SPLIT_ASSIGNMENTS  # noqa: E402
from size_lib import RAW, SizeResolver, check_raw, norm  # noqa: E402

OUT = HERE / "chiroptera_diet.json"
TABLE = "eltontraits/MamFuncDat.txt"
FILES = {TABLE: "51acbe6215b3c1f742463ff3fb37ef607150c052e0f7a9dc0d97fcaca61d3f76"}
TAXONOMY = HERE / "chiroptera_taxonomy.json"

BAT_FAMILIES = {
    "Craseonycteridae", "Emballonuridae", "Furipteridae", "Hipposideridae", "Megadermatidae",
    "Molossidae", "Mormoopidae", "Mystacinidae", "Myzopodidae", "Natalidae", "Noctilionidae",
    "Nycteridae", "Phyllostomidae", "Pteropodidae", "Rhinolophidae", "Rhinopomatidae",
    "Thyropteridae", "Vespertilionidae", "Miniopteridae", "Cistugidae", "Rhinonycteridae",
}
# EltonTraits column -> short key kept in the output
FOODS = {
    "Diet-Inv": "inv", "Diet-Vend": "vend", "Diet-Vect": "vect", "Diet-Vfish": "fish",
    "Diet-Vunk": "vunk", "Diet-Scav": "scav", "Diet-Fruit": "fruit", "Diet-Nect": "nect",
    "Diet-Seed": "seed", "Diet-PlantO": "plant",
}
GUILD_OF = {
    "inv": "ins", "fruit": "fru", "seed": "fru", "plant": "fru", "nect": "nec",
    "vend": "ver", "vect": "ver", "vunk": "ver", "scav": "ver", "fish": "fis",
}
GUILDS = {
    "ins": "Insects and other invertebrates",
    "fru": "Fruit and other plant parts",
    "nec": "Nectar and pollen",
    "ver": "Land vertebrates",
    "fis": "Fish",
    "blo": "Blood",
}
MIN_SHARE = 30
VAMPIRES = "Desmodontinae"
# how an entry was obtained
BASES = {
    "s": "EltonTraits value for the species",
    "p": "EltonTraits value for the species before it was split",
    "g": "every species of the genus in EltonTraits has this guild",
    "r": "vampire bat (Desmodontinae): blood by rule",
}


def guilds(shares: dict[str, int]) -> list[str]:
    """Every guild with at least MIN_SHARE of the diet, largest share first."""
    totals = Counter()
    for food, share in shares.items():
        totals[GUILD_OF[food]] += share
    return [g for g, share in totals.most_common() if share >= MIN_SHARE]


def main() -> None:
    check_raw(FILES)
    with (RAW / TABLE).open(encoding="latin-1") as handle:
        table = [r for r in csv.DictReader(handle, delimiter="\t") if r["MSWFamilyLatin"] in BAT_FAMILIES]
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))["species"]
    by_id = {s["id"]: s for s in taxonomy}
    splits = {norm(k): v for k, v in SPLIT_ASSIGNMENTS.items()}
    resolver = SizeResolver()

    # every EltonTraits record that lands on an MDD species, with its route
    found: dict[str, list[tuple[dict, str, str]]] = defaultdict(list)
    for record in table:
        shares = {FOODS[c]: int(record[c]) for c in FOODS if record[c] not in ("", "0")}
        if not shares:
            continue
        name = record["Scientific"]
        split = splits.get(norm(name))
        if split:
            for i in split["daughters"]:
                found[i].append((shares, "p", record["Diet-Certainty"]))
            continue
        species, _ = resolver.resolve(name)
        if species:
            found[species["id"]].append((shares, "s", record["Diet-Certainty"]))

    out: dict[str, dict] = {}
    for mdd_id, hits in found.items():
        # a species-level record beats one inherited from a split parent;
        # several records for one species (lumps) are averaged
        own = [h for h in hits if h[1] == "s"] or hits
        merged = Counter()
        for shares, _, _ in own:
            merged.update(shares)
        shares = {k: round(v / len(own)) for k, v in merged.items()}
        out[mdd_id] = {"g": guilds(shares), "b": own[0][1], "c": own[0][2],
                       "sh": dict(sorted(shares.items(), key=lambda kv: -kv[1]))}

    by_genus: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    for mdd_id, entry in out.items():
        by_genus[by_id[mdd_id]["genus"]].add(tuple(sorted(entry["g"])))
    for s in taxonomy:
        if s["id"] not in out and len(by_genus.get(s["genus"], ())) == 1:
            # the genus's guilds, in the order its first listed species gives them
            first = next(e for i, e in out.items() if by_id[i]["genus"] == s["genus"])
            out[s["id"]] = {"g": list(first["g"]), "b": "g"}
    for s in taxonomy:
        if s["subfamily"] == VAMPIRES:
            out.setdefault(s["id"], {})
            out[s["id"]].update(g=["blo"], b="r")

    species = {}
    for s in sorted(taxonomy, key=lambda s: s["sciName"]):
        entry = out.get(s["id"])
        if entry:
            species[s["sciName"].replace("_", " ")] = entry
    result = {
        "_meta": {
            "source": "EltonTraits 1.0 (Wilman et al. 2014), MamFuncDat.txt Diet-* columns",
            "doi": "10.1890/13-1917.1",
            "licence": "CC0-1.0",
            "sha256": FILES[TABLE],
            "rule": f"g lists every food group making up at least {MIN_SHARE}% of the diet, largest share first; "
                    "Desmodontinae are blood-feeders alone by rule.",
            "guilds": GUILDS,
            "bases": BASES,
            "shares": "percent of diet per EltonTraits food type: " + ", ".join(f"{v}={k}" for k, v in FOODS.items()),
            "certainty": "EltonTraits Diet-Certainty: ABC species-level sources, D1 genus, D2 family",
        },
        "species": species,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    counts = Counter(g for e in species.values() for g in e["g"])
    print("  species per number of guilds:", dict(sorted(Counter(len(e["g"]) for e in species.values()).items())))
    bases = Counter(e["b"] for e in species.values())
    print(f"{OUT.name}: {len(species)} of {len(taxonomy)} species")
    print("  guilds:", dict(counts.most_common()))
    print("  routes:", dict(bases.most_common()))
    print(f"  unresolved EltonTraits names: {len(resolver.unresolved)}")


if __name__ == "__main__":
    main()
