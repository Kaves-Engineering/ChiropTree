"""The marine-mammal data blocks that marine-mammal-tree.html is built from.

Imported by build_marine_mammal_page.py, which stamps `blocks` into the bat
page's skeleton. Everything structural -- which genus sits in which subfamily
or tribe, the species lists, every count -- is derived from MDD here. Only the
natural history prose and the coarse ecology tags are hand-authored, the same
split the master page itself uses.
"""
import json, collections, io, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
tax = json.load(open(os.path.join(HERE, "marine_mammal_taxonomy.json"), encoding="utf-8"))
SPECIES = tax["species"]

# ---------------------------------------------------------------- family prose
FAM = {
"Balaenidae": dict(common="Right and bowhead whales", range="Arctic, and temperate waters of both hemispheres",
  desc="Enormously thick blubber, no throat grooves and no dorsal fin. They feed by skimming — swimming forward, mouth open, straining copepods through baleen up to three metres long. Slow, fat and floating when dead, which is precisely why whalers named them the \u201cright\u201d whales to kill, and why three of the four species are still recovering."),
"Balaenopteridae": dict(common="Rorquals, including the blue and grey whales", range="All oceans",
  desc="The lunge feeders. Pleated throat grooves let the mouth balloon out around a volume of water larger than the whale itself, which is then forced back out through the baleen. The group holds the largest animal that has ever lived, and — since MDD folded Eschrichtius in — the grey whale, whose bottom-ploughing for amphipods is unlike anything else here."),
"Cetotheriidae": dict(common="Pygmy right whale", range="Cool temperate waters of the Southern Ocean",
  desc="One living species, and for a long time it sat alone in its own family. Fossil work then matched it to the cetotheres, a group everyone had assumed died out millions of years ago, making Caperea the last of a lineage rather than an offshoot of the right whales it was named for. It is rarely seen alive and much of its biology is simply unknown."),
"Delphinidae": dict(common="Oceanic dolphins", range="All oceans, plus some tropical rivers and estuaries",
  desc="The largest and most varied cetacean family, and the youngest — most of it radiated within the last ten million years. It runs from the five-foot Hector's dolphin to the killer whale, and includes the most socially complex animals in the sea, with matrilineal groups, learned hunting traditions that differ between neighbouring populations, and signature whistles that work like names."),
"Monodontidae": dict(common="Beluga and narwhal", range="Arctic and subarctic",
  desc="Two Arctic specialists with no dorsal fin — an advantage under pack ice — and unfused neck vertebrae, so unlike other whales they can turn their heads. The narwhal's tusk is a single spiralled left canine, grown through the lip, packed with nerve endings and now thought to be as much a sensory organ and social signal as a weapon."),
"Phocoenidae": dict(common="Porpoises", range="Temperate and cold coastal waters, plus Asian rivers",
  desc="Small, blunt-headed and spade-toothed rather than cone-toothed, and quite separate from the dolphins they are often confused with. They echolocate with narrow-band high-frequency clicks pitched above the hearing of killer whales, which appears to be a way of staying inaudible to their main predator. The family holds the most endangered marine mammal on Earth."),
"Iniidae": dict(common="Amazon river dolphins", range="The Amazon and Orinoco basins",
  desc="Pink, loose-necked and nearly blind, navigating turbid floodwater almost entirely by sonar. In the wet season they swim out of the river channels and hunt among the trunks of flooded forest. Fused neck vertebrae have been lost here too, so the head swings freely — useful in a habitat full of obstacles."),
"Pontoporiidae": dict(common="Franciscana", range="Coastal south-western Atlantic, from Brazil to Argentina",
  desc="A river dolphin that does not live in a river. It is the franciscana's ancestors that were riverine; this one has moved out into shallow coastal water, keeping the long thin beak — the longest relative to body size of any cetacean — and the murky-water sonar. Bycatch in gillnets is the pressing threat."),
"Lipotidae": dict(common="Baiji, Yangtze river dolphin", range="The Yangtze river, China",
  desc="A family of one, and almost certainly a family of none. A dedicated survey in 2006 failed to find a single animal and declared it functionally extinct — the first cetacean driven out by humans, not by hunting but by the accumulated weight of dam building, boat traffic, fishing gear and pollution along the world's busiest river."),
"Kogiidae": dict(common="Pygmy and dwarf sperm whales", range="Deep tropical and temperate waters worldwide",
  desc="Small relatives of the sperm whale with the same spermaceti apparatus at a fraction of the size. When startled they release a cloud of reddish-brown intestinal fluid and vanish behind it, the only cetaceans known to use a squid's trick. Rarely seen at sea; most of what is known comes from strandings."),
"Physeteridae": dict(common="Sperm whale", range="All deep oceans",
  desc="The largest toothed predator alive and the deepest-diving mammal, working the sea floor two kilometres down in total darkness for an hour at a time. The huge nose is an acoustic instrument: it generates the loudest sound produced by any animal, a directional click used to find squid. Females and young live in lasting matrilineal groups with dialects of their own."),
"Platanistidae": dict(common="South Asian river dolphins", range="The Ganges, Brahmaputra and Indus river systems",
  desc="Effectively blind — the eye has no lens and registers little more than direction of light — and they swim on one side, trailing a flipper along the bottom while scanning with sonar. They are the most distinctive of the river dolphins and among the most threatened, cut into isolated populations by barrages and dams."),
"Ziphiidae": dict(common="Beaked whales", range="Deep water in all oceans",
  desc="The least known large animals on Earth. They are deep-diving squid specialists — a Cuvier's beaked whale holds the mammal record at nearly four hours submerged — and several species have never been seen alive, being known only from skulls washed ashore. Most males carry a single pair of tusks used for fighting each other, and the females are toothless."),
"Dugongidae": dict(common="Dugong and the Steller's sea cow", range="Indo-Pacific coasts; the sea cow, the north Pacific",
  desc="Seagrass grazers of the shallows, with a downturned snout for cropping the plants at the root. The family also holds the largest sirenian ever recorded, Steller's sea cow — a nine-metre north Pacific animal described in 1741 and hunted out within 27 years of its discovery."),
"Trichechidae": dict(common="Manatees", range="Caribbean and Atlantic coasts, the Amazon, and West Africa",
  desc="Slow herbivores of warm shallow water, distinguished from the dugong by a rounded, paddle-shaped tail. Their teeth march forward through the jaw and are replaced from behind throughout life, an adaptation to a diet of abrasive vegetation. All three species are vulnerable to cold, to boat strikes, and to the loss of the warm-water refuges they need in winter."),
"Odobenidae": dict(common="Walrus", range="Arctic and subarctic coasts",
  desc="A family of one, and the only pinniped that feeds mainly on bottom-dwelling molluscs, which it finds in the dark with a dense array of stiff whiskers and takes by suction rather than by biting. Both sexes grow tusks, used for hauling out onto ice and for status. It needs shallow water and sea ice over it, which is a difficult combination to keep."),
"Otariidae": dict(common="Eared seals, sea lions and fur seals", range="Pacific, Southern Ocean and southern Atlantic coasts",
  desc="The pinnipeds that still work well on land: visible external ear flaps, hind flippers that rotate forward, and a gait that is close to walking. They swim with the fore flippers, like birds flying underwater, rather than sculling with the rear. Breeding is loud, crowded and strongly polygynous, with the largest bulls holding territory against everything that approaches."),
"Phocidae": dict(common="True or earless seals", range="Both polar regions, plus temperate and a few tropical coasts",
  desc="No ear flaps, and hind flippers that cannot turn forward, so on land they hump along on their bellies — the price of being the better divers. They swim by sculling with the hind flippers, pup fast on ice or beach, and include the deepest and longest-diving pinnipeds. The family spans both poles, and the two monk seal genera are the only members left in warm water."),
}

# --------------------------------------------------------- subfamily/tribe notes
SUBNOTE = {
("Dugongidae","Dugonginae"): "The one surviving dugong lineage, tied to Indo-Pacific seagrass meadows.",
("Dugongidae","Hydrodamalinae"): "Steller\u2019s sea cow alone: a cold-water giant with no teeth, described by naturalists on a shipwrecked expedition in 1741 and gone by 1768.",
("Trichechidae","Trichechinae"): "The manatees. One lineage, split between the Caribbean, the Amazon and West Africa.",
("Odobenidae","Odobeninae"): "A single living genus at the end of a family that was once far more varied.",
("Phocidae","Monachinae"): "The southern seals: monk seals in warm water, elephant seals in the temperate south, and the four Antarctic ice seals.",
("Phocidae","Phocinae"): "The northern seals, all of them tied to the Arctic and the north Atlantic and Pacific.",
("Cetotheriidae","Neobalaeninae"): "The pygmy right whale, and with it the last of the cetotheres.",
("Delphinidae","Delphininae"): "The typical beaked dolphins \u2014 bottlenose, common, spotted and humpback dolphins.",
("Delphinidae","Globicephalinae"): "The blackfish: pilot whales, false killer whale, melon-headed and pygmy killer whales, plus Risso\u2019s dolphin and the snubfin dolphins.",
("Delphinidae","Lissodelphininae"): "Southern-cool-water dolphins \u2014 the finless right whale dolphins and the Cephalorhynchus group.",
("Delphinidae","incertae sedis"): "Genera whose position inside the family is not settled \u2014 including Orcinus, the killer whale, which sits awkwardly wherever it is put.",
("Ziphiidae","Berardiinae"): "Baird\u2019s and Arnoux\u2019s beaked whales, the largest of the family.",
("Ziphiidae","Hyperoodontinae"): "The bottlenose whales and Mesoplodon \u2014 sixteen species, several known from almost nothing.",
("Ziphiidae","Ziphiinae"): "Cuvier\u2019s beaked whale, the most widespread and most often stranded of the family.",
("Ziphiidae","incertae sedis"): "Shepherd\u2019s beaked whale, the one member of the family with a full set of functional teeth.",
("Kogiidae","Kogiinae"): "The two small sperm whales.",
}

# ------------------------------------------------------------------ ecology tags
# r = water it lives in, d = what it eats, ro = where it rests or breeds,
# e = how it finds prey. Coarse by necessity, exactly as on the bat page.
FAM_TAGS = {
"Balaenidae":       dict(r="arc atl pac",     d="kri",         ro="sea",      e="none"),
"Balaenopteridae":  dict(r="glob",            d="kri fis",     ro="sea",      e="none"),
"Cetotheriidae":    dict(r="sou",             d="kri",         ro="sea",      e="none"),
"Delphinidae":      dict(r="glob",            d="fis squ",     ro="sea",      e="bio"),
"Monodontidae":     dict(r="arc",             d="fis squ",     ro="sea",      e="bio"),
"Phocoenidae":      dict(r="atl pac",         d="fis",         ro="sea",      e="bio"),
"Iniidae":          dict(r="riv",             d="fis",         ro="riv",      e="bio"),
"Pontoporiidae":    dict(r="atl",             d="fis squ",     ro="sea",      e="bio"),
"Lipotidae":        dict(r="riv",             d="fis",         ro="riv",      e="bio"),
"Kogiidae":         dict(r="glob",            d="squ fis",     ro="sea",      e="bio"),
"Physeteridae":     dict(r="glob",            d="squ",         ro="sea",      e="bio"),
"Platanistidae":    dict(r="riv",             d="fis",         ro="riv",      e="bio"),
"Ziphiidae":        dict(r="glob",            d="squ fis",     ro="sea",      e="bio"),
"Dugongidae":       dict(r="ind pac",         d="veg",         ro="sea",      e="none"),
"Trichechidae":     dict(r="atl riv",         d="veg",         ro="sea riv",  e="none"),
"Odobenidae":       dict(r="arc",             d="ben",         ro="ice land", e="none"),
"Otariidae":        dict(r="pac sou atl",     d="fis squ",     ro="land",     e="none"),
"Phocidae":         dict(r="arc sou atl pac", d="fis squ",     ro="ice land", e="none"),
}
GENUS_TAGS = {
# cetaceans with a diet or range worth separating from the family default
"Orcinus":       dict(r="glob", d="ver fis squ", ro="sea", e="bio"),
"Pseudorca":     dict(d="fis squ ver"),
"Globicephala":  dict(d="squ fis"),
"Grampus":       dict(d="squ"),
"Orcaella":      dict(r="ind pac riv", d="fis squ"),
"Sotalia":       dict(r="atl riv", d="fis squ"),
"Sousa":         dict(r="ind atl pac", d="fis"),
"Neophocaena":   dict(r="pac ind riv", d="fis squ"),
"Delphinapterus":dict(r="arc", d="fis squ ben"),
"Eschrichtius":  dict(r="pac", d="ben", ro="sea"),
"Megaptera":     dict(r="glob", d="kri fis"),
"Eubalaena":     dict(r="atl pac", d="kri"),
"Balaena":       dict(r="arc", d="kri"),
# pinnipeds
"Hydrurga":      dict(r="sou", d="ver kri fis", ro="ice"),
"Lobodon":       dict(r="sou", d="kri", ro="ice"),
"Ommatophoca":   dict(r="sou", d="squ fis", ro="ice"),
"Leptonychotes": dict(r="sou", d="fis squ", ro="ice"),
"Mirounga":      dict(r="sou pac", d="squ fis", ro="land"),
"Monachus":      dict(r="atl", d="fis squ", ro="land"),
"Neomonachus":   dict(r="atl pac", d="fis squ", ro="land"),
"Erignathus":    dict(r="arc", d="ben fis", ro="ice"),
"Pusa":          dict(r="arc", d="fis kri", ro="ice"),
"Pagophilus":    dict(r="arc atl", d="fis kri", ro="ice"),
"Histriophoca":  dict(r="arc pac", d="fis ben", ro="ice"),
"Cystophora":    dict(r="arc atl", d="fis squ", ro="ice"),
"Halichoerus":   dict(r="atl", d="fis", ro="land ice"),
"Phoca":         dict(r="arc atl pac", d="fis", ro="land ice"),
"Odobenus":      dict(r="arc", d="ben", ro="ice land"),
# sirenians
"Trichechus":    dict(r="atl riv", d="veg", ro="sea riv"),
"Dugong":        dict(r="ind pac", d="veg", ro="sea"),
"Hydrodamalis":  dict(r="pac", d="veg", ro="sea"),
}

# ----------------------------------------------------------------- the cladogram
# Two levels below the top, exactly like the bat page: lineage > superfamily >
# family. MDD's own infraorder/superfamily columns supply every grouping here.
TREE_SPEC = [
 ("Mysticeti", "Parvorder", [
   ("Balaenoidea",     ["Balaenidae"]),
   ("Balaenopteroidea",["Balaenopteridae"]),
   ("Cetotherioidea",  ["Cetotheriidae"]),
 ]),
 ("Odontoceti", "Parvorder", [
   ("Physeteroidea",   ["Physeteridae", "Kogiidae"]),
   ("Platanistoidea",  ["Platanistidae"]),
   ("Lipotoidea",      ["Lipotidae"]),
   ("Inioidea",        ["Iniidae", "Pontoporiidae"]),
   ("Ziphioidea",      ["Ziphiidae"]),
   ("Delphinoidea",    ["Monodontidae", "Phocoenidae", "Delphinidae"]),
 ]),
 ("Sirenia", "Order", [
   ("Trichechoidea",   ["Trichechidae"]),
   ("Dugongoidea",     ["Dugongidae"]),
 ]),
 ("Pinnipedia", "Clade in Carnivora", [
   ("Otarioidea",      ["Otariidae", "Odobenidae"]),
   ("Phocoidea",       ["Phocidae"]),
 ]),
]

# ------------------------------------------------------------------- derive data
def esc(s):
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')

byfam = collections.OrderedDict()
for s in SPECIES:
    byfam.setdefault(s["family"], collections.OrderedDict()) \
         .setdefault((s.get("subfamily") or "", s.get("tribe") or ""), collections.OrderedDict()) \
         .setdefault(s["genus"], []).append(s)

def clean(v):
    return "" if not v or v in ("NA", "incertae sedis") else v

# --- F: family info
out = io.StringIO()
out.write("const F = {\n")
for fam in [f for _, _, sfs in TREE_SPEC for _, fams in sfs for f in fams]:
    groups = byfam[fam]
    genera = {g for grp in groups.values() for g in grp}
    nsp = sum(len(v) for grp in groups.values() for v in grp.values())
    m = FAM[fam]
    out.write('  %s:{common:"%s",genera:%d,species:%d,range:"%s",\n    desc:"%s"},\n'
              % (fam, esc(m["common"]), len(genera), nsp, esc(m["range"]), esc(m["desc"])))
out.write("};\n")
F_JS = out.getvalue()

# --- TREE
lines = ["const TREE = {name:null, rank:\"Marine mammals\", children:["]
for lname, lrank, sfs in TREE_SPEC:
    lines.append('  {name:"%s", rank:"%s", children:[' % (lname, lrank))
    for sfname, fams in sfs:
        leaves = ", ".join('leaf("%s")' % f for f in fams)
        lines.append('    {name:"%s", rank:"Superfamily", children:[ %s ]},' % (sfname, leaves))
    lines.append("  ]},")
lines.append("]};")
TREE_JS = "\n".join(lines) + "\n"

# --- ATLAS
out = io.StringIO()
out.write("const ATLAS = {\n")
for fam in [f for _, _, sfs in TREE_SPEC for _, fams in sfs for f in fams]:
    groups = byfam[fam]
    # group by subfamily, keeping tribes under it
    subs = collections.OrderedDict()
    for (sub, tribe), genera in groups.items():
        subs.setdefault(clean(sub), []).append((clean(tribe), genera))
    subblocks = []
    for sub, tribes in subs.items():
        note = SUBNOTE.get((fam, sub)) or SUBNOTE.get((fam, "incertae sedis")) if sub == "" else SUBNOTE.get((fam, sub))
        raw_sub = None
        for (s0, _t0) in groups:
            if clean(s0) == sub and s0 not in ("", "NA"):
                raw_sub = s0
        if sub == "" and raw_sub:
            note = SUBNOTE.get((fam, raw_sub))
        tparts = []
        for tribe, genera in tribes:
            gl = ", ".join('["%s",%d]' % (g, len(v)) for g, v in genera.items())
            tparts.append('T(%s,[%s])' % ('"%s"' % tribe if tribe else "null", gl))
        subname = '"%s"' % raw_sub if raw_sub else "null"
        notestr = '"%s"' % esc(note) if note else "null"
        subblocks.append("  S(%s,%s,[%s])" % (subname, notestr, ",".join(tparts)))
    out.write("%s:[\n%s],\n" % (fam, ",\n".join(subblocks)))
out.write("};\n")
ATLAS_JS = out.getvalue()

# --- SP: every genus complete, since 144 species fit comfortably
out = io.StringIO()
out.write("const SP = {\n")
for lname, _lrank, sfs in TREE_SPEC:
    out.write("// --- %s\n" % lname)
    for _sfname, fams in sfs:
        for fam in fams:
            for (_sub, _tribe), genera in byfam[fam].items():
                for g, rows in genera.items():
                    items = ", ".join('["%s","%s"]' % (r["specificEpithet"], esc(r.get("mainCommonName") or ""))
                                      for r in sorted(rows, key=lambda r: r["specificEpithet"]))
                    out.write("%s:[1,[%s]],\n" % (g, items))
out.write("};\n")
SP_JS = out.getvalue()

# --- TRAW ecology tags per genus: "regions|diet|haul-out", the master's own
# three-field shape, so genusMatches() needs no change. Biosonar is a
# family-level fact and rides in ETAG, exactly where the master reads it from.
out = io.StringIO()
out.write("const TRAW = {\n")
for lname, _lrank, sfs in TREE_SPEC:
    for _sfname, fams in sfs:
        for fam in fams:
            gs = [g for grp in byfam[fam].values() for g in grp]
            row = []
            for g in gs:
                t = dict(FAM_TAGS[fam])
                t.update(GENUS_TAGS.get(g, {}))
                row.append('%s:"%s|%s|%s"' % (g, t["r"], t["d"], t["ro"]))
            out.write("  " + ", ".join(row) + ",\n")
out.write("};\n")
TRAW_JS = out.getvalue()

# --- ETAG: whether the family hunts with active biosonar. A qualitative,
# well-established fact per lineage -- no invented call parameters.
out = io.StringIO()
out.write("const ETAG = {\n")
for lname, _lrank, sfs in TREE_SPEC:
    for _sfname, fams in sfs:
        for fam in fams:
            out.write('%s:["%s"], ' % (fam, FAM_TAGS[fam]["e"]))
    out.write("\n")
out.write("};\n")
ETAG_JS = out.getvalue()

blocks = "\n".join([F_JS, TREE_JS, ATLAS_JS, SP_JS, TRAW_JS, ETAG_JS])

if __name__ == "__main__":
    print("families %d, genera %d, species %d" % (
        len({s["family"] for s in SPECIES}),
        len({s["genus"] for s in SPECIES}), len(SPECIES)))
