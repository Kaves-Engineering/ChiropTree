"""The dinosaur data blocks that dinosaur-tree.html is built from.

Imported by build_dinosaur_page.py, which stamps `blocks` into the bat page's
skeleton. Which genus sits in which group, the genus lists, every count, each
group's time span and the countries its fossils come from are all derived from
the Paleobiology Database (dinosaur_taxonomy.json). Hand-authored: the layout
of groups under clade headings, each group's English name, and its natural
history prose. That is the same split the other pages use.

The headings follow the long-standing Ornithischia / Saurischia division, with
Sauropodomorpha and Theropoda as the two saurischian branches. Several
catch-all groups (Theropoda, Sauropoda, Tetanurae, ...) hold genera PBDB places
no deeper than that clade; their prose says so rather than dressing them up as
families. Where current work disagrees -- Megaraptora's position, whether the
silesaurids are the earliest ornithischians -- the prose says that too.
"""
import collections
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
tax = json.load(open(os.path.join(HERE, "dinosaur_taxonomy.json"), encoding="utf-8"))
SPECIES = tax["species"]

# ---------------------------------------------------------------- the cladogram
# heading > block > groups. Headings and blocks are drawn as labelled clades;
# groups are the leaves, opening to genera and species.
TREE_SPEC = [
 ("Early dinosaurs", "Unplaced", [
   ("Dinosauriformes", "Clade", ["Dinosauria"]),
   ("Herrerasaurs and early saurischians", "Grade", ["Herrerasauridae", "Saurischia"]),
 ]),
 ("Ornithischia", "Order", [
   ("Early ornithischians", "Grade", ["Silesauridae", "Ornithischia", "Heterodontosauridae"]),
   ("Thyreophora", "Clade", ["Thyreophora", "Stegosauria", "Ankylosauria", "Nodosauridae", "Ankylosauridae"]),
   ("Neornithischia", "Clade", ["Neornithischia", "Thescelosauridae"]),
   ("Ornithopoda", "Suborder", ["Ornithopoda", "Elasmaria", "Rhabdodontomorpha", "Dryosauridae", "Iguanodontia",
                                "Styracosterna", "Hadrosauroidea", "Hadrosauridae", "Lambeosaurinae"]),
   ("Marginocephalia", "Clade", ["Pachycephalosauria", "Ceratopsia", "Neoceratopsia", "Leptoceratopsidae",
                                 "Protoceratopsidae", "Centrosaurinae", "Chasmosaurinae"]),
 ]),
 ("Sauropodomorpha", "Clade", [
   ("Early sauropodomorphs", "Grade", ["Sauropodomorpha", "Plateosauridae", "Massospondylidae", "Massopoda"]),
   ("Early sauropods", "Grade", ["Sauropoda", "Mamenchisauridae", "Turiasauria"]),
   ("Diplodocoids", "Superfamily", ["Diplodocoidea", "Rebbachisauridae", "Dicraeosauridae", "Diplodocidae"]),
   ("Macronaria", "Clade", ["Macronaria", "Brachiosauridae", "Somphospondyli", "Euhelopodidae"]),
   ("Titanosaurs", "Clade", ["Titanosauria", "Colossosauria", "Lithostrotia", "Saltasauroidea"]),
 ]),
 ("Theropoda", "Clade", [
   ("Early theropods", "Grade", ["Theropoda", "Coelophysoidea"]),
   ("Ceratosauria", "Clade", ["Ceratosauria", "Noasauridae", "Abelisauridae"]),
   ("Early tetanurans", "Grade", ["Tetanurae", "Megalosauroidea", "Spinosauridae", "Allosauroidea",
                                  "Carcharodontosauria", "Megaraptora"]),
   ("Early coelurosaurs", "Grade", ["Coelurosauria", "Tyrannosauroidea", "Tyrannosauridae", "Ornithomimosauria"]),
   ("Maniraptora", "Clade", ["Alvarezsauria", "Therizinosauria", "Oviraptorosauria", "Caenagnathidae",
                             "Oviraptoridae", "Paraves", "Troodontidae", "Dromaeosauridae"]),
 ]),
]

# ---------------------------------------------------------------- group prose
# (English name, description). Range and time span are computed below.
FAM = {
# --- early
"Dinosauria": ("Dinosaurs of uncertain place",
  "Nyasasaurus, from the Middle Triassic of Tanzania, may be the oldest dinosaur known or only a close relative. It is known from an upper arm bone and a few vertebrae, too little to place it on either side of the first split."),
"Herrerasauridae": ("Herrerasaurids",
  "Some of the oldest well-known dinosaurs, from rocks about 230 million years old in Argentina and Brazil. Herrerasaurus was a two-legged predator up to about 6 m long. Whether herrerasaurids are early theropods or sit just outside Saurischia is still argued."),
"Saurischia": ("Early saurischians",
  "Late Triassic dinosaurs that PBDB places in Saurischia without a closer home: small, lightly built animals such as Eodromaeus and Tawa. They sit near the split between the theropod and sauropodomorph lines, and their exact placement often changes with new analyses."),
# --- Ornithischia
"Silesauridae": ("Silesaurids",
  "Slender, four-legged Triassic animals with a beak-like tip to the lower jaw. They were long treated as the closest relatives of dinosaurs. Some recent studies place them at the base of Ornithischia instead, which is where PBDB puts them; that would make them the earliest ornithischians."),
"Ornithischia": ("Early ornithischians",
  "Early members of the 'bird-hipped' line that PBDB places in no smaller group. They include Pisanosaurus and Eocursor from the Triassic and the puzzling Chilesaurus, a plant-eater that some studies place as a theropod."),
"Heterodontosauridae": ("Heterodontosaurids",
  "Small early ornithischians with three kinds of teeth, including canine-like tusks. Tianyulong from China had long filaments along its back, which suggests that some kind of body covering reached back to the base of the ornithischian tree."),
"Thyreophora": ("Early armoured dinosaurs",
  "The first armoured ornithischians, carrying rows of bony plates in the skin before the split into stegosaurs and ankylosaurs. Scelidosaurus, from the Early Jurassic of England, is the best-known, with complete skeletons preserving its armour."),
"Stegosauria": ("Stegosaurs",
  "Four-legged plant-eaters with two rows of plates or spikes along the back and a spiked tail, the thagomizer. The plates were probably for display. Stegosaurus had a small skull but not the tiny brain of legend, and there was never a 'second brain' in its hips."),
"Ankylosauria": ("Early ankylosaurs",
  "Armoured dinosaurs that PBDB does not place in either of the two main families. They include the early Spicomellus, with spikes fused directly to its ribs, and Stegouros from Chile, whose flattened, bladed tail looks like a Mesoamerican war club."),
"Nodosauridae": ("Nodosaurs",
  "Ankylosaurs without a tail club, some with large spikes on the shoulders. Borealopelta, from Alberta, is preserved in three dimensions with its armour and skin in place; pigments in it show the animal was reddish-brown and countershaded."),
"Ankylosauridae": ("Ankylosaurids",
  "Heavily armoured, low-slung plant-eaters, most with a bony club at the end of the tail, driven by stiffened tail vertebrae. Healed injuries on other ankylosaurs suggest they used the club on each other. Most come from the Late Cretaceous of Asia and western North America."),
"Neornithischia": ("Early neornithischians",
  "Small, two-legged plant-eaters near the base of the group that later produced the ornithopods, pachycephalosaurs and ceratopsians. Kulindadromeus, from Siberia, preserves scales on the tail and filaments over much of the body."),
"Thescelosauridae": ("Thescelosaurids",
  "Small to medium two-legged plant-eaters of the Cretaceous. Oryctodromeus was found in a burrow with two juveniles, the first good evidence of burrowing and parental care in dinosaurs. Thescelosaurus lived until the end of the Cretaceous."),
"Ornithopoda": ("Early ornithopods",
  "Ornithopods that PBDB places no deeper. They include Hypsilophodon, a small, fast plant-eater from the Isle of Wight that was long wrongly shown living in trees."),
"Elasmaria": ("Elasmarians",
  "Small, fast ornithopods from the southern continents, especially Argentina, Australia and Antarctica. Leaellynasaura lived within the Antarctic Circle, where it had to cope with long months of polar dark. PBDB also includes the much larger Muttaburrasaurus here."),
"Rhabdodontomorpha": ("Rhabdodontids and Tenontosaurus",
  "Mid-sized ornithopods. The rhabdodontids lived on the islands of Late Cretaceous Europe, and some, such as Zalmoxes in Romania, were dwarfed there. Tenontosaurus, from North America, is often found with teeth of Deinonychus."),
"Dryosauridae": ("Dryosaurids",
  "Lightly built, fast-running ornithopods of the Late Jurassic and Early Cretaceous. Dysalotosaurus, from Tanzania, is known from bonebeds containing hundreds of individuals of all ages."),
"Iguanodontia": ("Iguanodonts",
  "Large plant-eaters that could walk on two legs or four, many with a conical thumb spike. Iguanodon was one of the first dinosaurs named, in 1825, and the Bernissart mine in Belgium produced dozens of complete skeletons. Ouranosaurus had a tall sail or hump on its back."),
"Styracosterna": ("Advanced iguanodonts",
  "Iguanodonts that PBDB places close to the hadrosaur line but in no named family: mostly Early Cretaceous plant-eaters from Europe, North America and Asia."),
"Hadrosauroidea": ("Early hadrosauroids",
  "The forerunners of the duck-billed dinosaurs. These plant-eaters already had batteries of stacked teeth, but most lacked the broad bill and head crests of the later hadrosaurids. Most come from the Cretaceous of Asia."),
"Hadrosauridae": ("Duck-billed dinosaurs",
  "Hadrosaurids without hollow crests: Edmontosaurus, Maiasaura, Saurolophus and their relatives. Their dental batteries held hundreds of teeth for grinding plants. Maiasaura ('good mother lizard') nested in colonies and cared for its young."),
"Lambeosaurinae": ("Crested duck-bills",
  "Hadrosaurids with hollow head crests containing the nasal passages. Parasaurolophus has a long backswept tube, Corythosaurus a helmet. The crests probably worked as resonators for low calls and as visual signals."),
"Pachycephalosauria": ("Dome-headed dinosaurs",
  "Two-legged plant-eaters with thick skull domes, often ringed with knobs and spikes. Whether they butted heads or bodies is debated, and a few 'species' may be growth stages of others. Pachycephalosaurus had a dome up to 25 cm thick."),
"Ceratopsia": ("Early ceratopsians",
  "The first horned-dinosaur line, before real horns: small plant-eaters with a parrot-like beak and a new bone at the tip of the upper jaw. Psittacosaurus, from Asia, is known from hundreds of specimens, one with a pigmented, countershaded body and bristles on the tail."),
"Neoceratopsia": ("Early neoceratopsians",
  "Ceratopsians with the beginnings of a neck frill, in no named family. Most are small plant-eaters from the Early Cretaceous of Asia; Zuniceratops, from New Mexico, already had brow horns."),
"Leptoceratopsidae": ("Leptoceratopsids",
  "Small, stocky horned dinosaurs with a short frill and no real horns, living alongside their giant relatives until the end of the Cretaceous. Their strong jaws had a shearing bite."),
"Protoceratopsidae": ("Protoceratopsids",
  "Sheep-sized ceratopsians of the Mongolian deserts. A Protoceratops was found locked in combat with a Velociraptor, both apparently buried alive by a collapsing dune. Protoceratops skulls may have inspired the griffin legends."),
"Centrosaurinae": ("Centrosaurines",
  "Horned dinosaurs usually with a large nose horn, short brow horns and elaborate spikes on the frill: Centrosaurus, Styracosaurus, Pachyrhinosaurus. Several are known from bonebeds with hundreds of animals, apparently herds killed together. PBDB's few ceratopsids it places in no subfamily are listed here too."),
"Chasmosaurinae": ("Chasmosaurines",
  "Horned dinosaurs usually with long brow horns and a long frill: Triceratops, Torosaurus, Chasmosaurus, Kosmoceratops with fifteen horns. Triceratops lived to the very end of the Cretaceous and is one of the most common dinosaurs in the Hell Creek Formation."),
# --- Sauropodomorpha
"Sauropodomorpha": ("Early sauropodomorphs",
  "The first members of the long-necked line, from the Late Triassic. They were small, two-legged, and some, like Buriolestes and Eoraptor, still had teeth suited to eating animals as well as plants."),
"Plateosauridae": ("Plateosaurids",
  "Plateosaurus, from the Late Triassic of central Europe, is one of the best-known dinosaurs, from more than a hundred skeletons, many from the mud-traps of Trossingen in Germany. It walked on two legs and grew up to about 10 m."),
"Massospondylidae": ("Massospondylids",
  "Early Jurassic sauropodomorphs. Nests of Massospondylus in South Africa hold some of the oldest known dinosaur embryos, about 190 million years old. Glacialisaurus is from Antarctica."),
"Massopoda": ("Sauropodiform grade",
  "Sauropodomorphs close to the origin of sauropods, from the Late Triassic and Early Jurassic, placed here where PBDB gives no family. Some, such as Ledumahadi from South Africa, already weighed around 12 tonnes and walked on four legs."),
"Sauropoda": ("Early sauropods",
  "Sauropods outside the major families: the Late Triassic and Jurassic animals in which the four-legged, long-necked giant body plan was established, such as Shunosaurus, with a tail club, and Cetiosaurus, the first sauropod named."),
"Mamenchisauridae": ("Mamenchisaurids",
  "Jurassic sauropods from East Asia with some of the longest necks relative to body size of any animal, made of up to 19 vertebrae. The neck of Mamenchisaurus sinocanadorum may have reached 15 m."),
"Turiasauria": ("Turiasaurs",
  "A group of sauropods from the Jurassic and Early Cretaceous of Europe, North America and Africa, with heart-shaped teeth. Turiasaurus, from Spain, was one of the largest European dinosaurs."),
"Diplodocoidea": ("Early diplodocoids",
  "Diplodocoids PBDB places in no named family. Lingwulong, from China, showed that the group had reached Asia by the Middle Jurassic, earlier than was thought."),
"Rebbachisauridae": ("Rebbachisaurids",
  "Diplodocoids mostly of the Cretaceous southern continents. Nigersaurus had a broad, shovel-like muzzle with more than 500 teeth replaced about every two weeks, and grazed close to the ground."),
"Dicraeosauridae": ("Dicraeosaurids",
  "Short-necked diplodocoids. Amargasaurus and Bajadasaurus had two rows of tall spines along the neck, possibly supporting sails or horny sheaths."),
"Diplodocidae": ("Diplodocids",
  "Long, whip-tailed sauropods of the Late Jurassic: Diplodocus, Apatosaurus, Brontosaurus, Barosaurus. Brontosaurus was sunk into Apatosaurus in 1903 and reinstated in 2015. Casts of the Carnegie Diplodocus stand in museums around the world."),
"Macronaria": ("Early macronarians",
  "Sauropods with large nasal openings, in no named family, including Camarasaurus, the most common sauropod of the North American Morrison Formation, and Europasaurus, a dwarf sauropod from a Jurassic island in Germany."),
"Brachiosauridae": ("Brachiosaurids",
  "Sauropods with forelimbs longer than hind limbs, holding the neck high. Giraffatitan, from Tanzania, stands mounted in Berlin at about 13 m tall. Brachiosaurus itself is known from far less material."),
"Somphospondyli": ("Somphospondylans",
  "Advanced macronarian sauropods close to the titanosaurs, placed here where PBDB gives no family, among them Sauroposeidon and the Australian Diamantinasaurus and Savannasaurus."),
"Euhelopodidae": ("Euhelopodids",
  "Cretaceous sauropods from East Asia, close relatives of the titanosaurs, several with very long necks. Euhelopus was the first sauropod described from China."),
"Titanosauria": ("Titanosaurs",
  "The last sauropods, found on every continent including Antarctica, and among the largest land animals ever: Argentinosaurus may have weighed 70 tonnes. Many laid eggs in huge nesting grounds, such as Auca Mahuevo in Argentina. Also here are titanosaurs PBDB places in no smaller group, including several genera from Pakistan named from fragmentary material."),
"Colossosauria": ("Colossosaurs",
  "Titanosaurs including some of the largest animals ever to walk on land, such as Futalognkosaurus, Puertasaurus and Notocolossus, most from Argentina and Brazil."),
"Lithostrotia": ("Lithostrotians",
  "Titanosaurs, many of them with bony armour plates (osteoderms) in the skin, a rare feature among sauropods."),
"Saltasauroidea": ("Saltasaurids",
  "Small to mid-sized titanosaurs of the Late Cretaceous. Saltasaurus, from Argentina, was the first sauropod found with armour. Alamosaurus was the last sauropod in North America."),
# --- Theropoda
"Theropoda": ("Early theropods",
  "Theropods placed no deeper than the major clades, including Dilophosaurus from the Early Jurassic of Arizona. It had two thin crests on its head, but not the neck frill or the venom shown in films. Protoavis, a disputed 'Triassic bird', is also here."),
"Coelophysoidea": ("Coelophysoids",
  "Slender, early predators of the Late Triassic and Early Jurassic. At Ghost Ranch in New Mexico, a single bonebed holds hundreds of Coelophysis skeletons. It was the second dinosaur taken into space, as a skull on the Space Shuttle in 1998."),
"Ceratosauria": ("Ceratosaurs",
  "Predators outside the abelisaurid and noasaurid families. Ceratosaurus, from the Morrison Formation, had a blade-like horn on its snout and a row of small bony plates down its back."),
"Noasauridae": ("Noasaurids",
  "Small, slender ceratosaurs. Limusaurus lost its teeth as it grew, from a toothed juvenile to a beaked, probably plant-eating adult. Masiakasaurus, from Madagascar, had forward-pointing front teeth."),
"Abelisauridae": ("Abelisaurids",
  "The top predators of the southern continents in the Late Cretaceous: short, deep skulls, and forelimbs even more reduced than a tyrannosaur's. Carnotaurus had bull-like horns; Majungasaurus, from Madagascar, left tooth marks on bones of its own kind."),
"Tetanurae": ("Early tetanurans",
  "Tetanurans PBDB places in no smaller group, including Cryolophosaurus, the first carnivorous dinosaur named from Antarctica, which had a crest across its head like a comb."),
"Megalosauroidea": ("Megalosauroids",
  "Large Jurassic predators. Megalosaurus, from Oxfordshire, was the first dinosaur to be scientifically named, in 1824. Torvosaurus was among the largest Jurassic predators, and piatnitzkysaurids are here too."),
"Spinosauridae": ("Spinosaurids",
  "Theropods with long, crocodile-like snouts and conical teeth for catching fish. Spinosaurus had a sail on its back, and whether it hunted in open water or waded in the shallows like a heron is still debated. Baryonyx was found with fish scales in its stomach."),
"Allosauroidea": ("Allosauroids",
  "Large Jurassic predators: Allosaurus, the commonest predator of the Morrison Formation, and the metriacanthosaurids of Asia, such as Sinraptor and Yangchuanosaurus. Carcharodontosaurians are drawn as their own group."),
"Carcharodontosauria": ("Carcharodontosaurs",
  "The shark-toothed predators: Giganotosaurus, Carcharodontosaurus and Mapusaurus rivalled Tyrannosaurus in size. Acrocanthosaurus had tall spines along its back. The neovenatorids are included here as PBDB has them."),
"Megaraptora": ("Megaraptorans",
  "Mid-to-large predators from South America, Australia and Asia with long arms and a huge sickle-shaped claw on the first finger. Whether they are allosauroids or early relatives of tyrannosaurs is one of the open questions in theropod evolution."),
"Coelurosauria": ("Early coelurosaurs",
  "Small coelurosaurs PBDB places in no deeper group, including Compsognathus, long the smallest known dinosaur, and Sinosauropteryx, the first non-bird dinosaur found with feathers, which also shows a striped tail."),
"Tyrannosauroidea": ("Early tyrannosauroids",
  "Tyrannosaur relatives outside Tyrannosauridae. Most were small or mid-sized, like the crested Guanlong, but Yutyrannus was about 9 m long and covered in long filaments. The proceratosaurids are included here. Recent work treats Nanotyrannus as a small tyrannosauroid of its own rather than a young Tyrannosaurus, and PBDB places it here."),
"Tyrannosauridae": ("Tyrannosaurids",
  "The giant predators of the last 20 million years of the Cretaceous in Asia and North America: Tyrannosaurus, Tarbosaurus, Albertosaurus, Gorgosaurus, Daspletosaurus. Tyrannosaurus had the strongest bite estimated for any land animal, strong enough to crush bone."),
"Ornithomimosauria": ("Ostrich-mimic dinosaurs",
  "Long-legged, toothless (in most) theropods built for running. Deinocheirus was known for 50 years only from its 2.4 m arms, until complete skeletons showed a humpbacked, duck-billed animal about 11 m long. PBDB includes the ornithomimids and deinocheirids."),
"Alvarezsauria": ("Alvarezsaurs",
  "Small, long-legged theropods whose arms were reduced to a single large claw, probably for breaking into insect nests. Their earliest known members, such as Haplocheirus, still had three-fingered hands."),
"Therizinosauria": ("Therizinosaurs",
  "Pot-bellied, long-necked theropods that turned to eating plants. Therizinosaurus had hand claws up to about 50 cm long, the longest of any animal known. Beipiaosaurus preserves a coat of feathers."),
"Oviraptorosauria": ("Early oviraptorosaurs",
  "Early members of the oviraptorosaur line, placed here where PBDB gives no family. Caudipteryx had true pennaceous feathers on its arms and tail but could not fly."),
"Caenagnathidae": ("Caenagnathids",
  "Beaked, toothless oviraptorosaurs of North America and Asia. Anzu wyliei, nicknamed 'the chicken from hell', had a tall crest. Gigantoraptor, from Inner Mongolia, weighed about two tonnes."),
"Oviraptoridae": ("Oviraptorids",
  "Short-skulled, beaked oviraptorosaurs of the Late Cretaceous of Asia. Oviraptor, 'egg thief', was named for being found on eggs, but the eggs turned out to be its own. Citipati skeletons have been found sitting on their nests in a brooding posture."),
"Paraves": ("Early paravians",
  "Paravians outside the dromaeosaurid and troodontid families. They include the scansoriopterygids Yi and Ambopteryx, which had membranous, bat-like wings held out by a long rod-like bone at the wrist, and Caihong, which had iridescent feathers."),
"Troodontidae": ("Troodontids",
  "Small, big-brained, large-eyed theropods, among the closest relatives of birds. Mei long was found in a sleeping posture like a bird's, head tucked under its arm. Anchiornis, placed here by PBDB, is the first dinosaur whose whole plumage colour was reconstructed from fossil pigment."),
"Dromaeosauridae": ("Raptors",
  "Feathered predators with an enlarged, sickle-shaped claw on the second toe: Velociraptor, Deinonychus, Utahraptor. Velociraptor was about the size of a turkey, much smaller than in films. Microraptor had long feathers on all four limbs and could glide or fly."),
}

# ICS stage boundaries for the page's time span line (Ma, base of each epoch)
EPOCHS = [(251.9, "Early Triassic"), (247.2, "Middle Triassic"), (237.0, "Late Triassic"),
          (201.4, "Early Jurassic"), (174.7, "Middle Jurassic"), (161.5, "Late Jurassic"),
          (143.1, "Early Cretaceous"), (100.5, "Late Cretaceous")]


def epoch(ma: float, start: bool) -> str:
    """The epoch an age falls in. A species' first appearance is the base of
    its oldest stage; nudging inward keeps a boundary age in its own epoch."""
    ma = ma - 0.01 if start else ma + 0.01
    name = EPOCHS[0][1]
    for base, label in EPOCHS:
        if ma <= base:
            name = label
    return name


def esc(s):
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


ORDERED = [f for _, _, blocks in TREE_SPEC for _, _, fams in blocks for f in fams]
groups = set(tax["families"])
missing, extra = groups - set(ORDERED), set(ORDERED) - groups
unwritten = groups - set(FAM)
if missing or extra or unwritten or len(ORDERED) != len(set(ORDERED)):
    raise SystemExit("TREE_SPEC/FAM out of step with the taxonomy: missing %s, extra %s, no prose %s"
                     % (sorted(missing), sorted(extra), sorted(unwritten)))

byfam = collections.OrderedDict((f, collections.OrderedDict()) for f in ORDERED)
for s in sorted(SPECIES, key=lambda s: s["genus"]):
    byfam[s["family"]].setdefault(s["genus"], []).append(s)


def range_line(fam):
    """time span and the countries with the most species, from the data."""
    members = [s for g in byfam[fam].values() for s in g]
    starts = [s["maxMa"] for s in members if s.get("maxMa")]
    ends = [s["minMa"] for s in members if s.get("minMa")]
    span = ""
    if starts and ends:
        first, last = epoch(max(starts), True), epoch(min(ends), False)
        span = first if first == last else f"{first} to {last}"
    places = collections.Counter(c for s in members for c in s.get("countryDistribution", "").split("|") if c)
    top = [c for c, _ in places.most_common(3)]
    more = len(places) - len(top)
    where = ", ".join(top) + (f" and {more} more" if more > 0 else "")
    return " · ".join(x for x in (span, where) if x)


# ---------------------------------------------------------------- F
out = io.StringIO()
out.write("const F = {\n")
for fam in ORDERED:
    genera = byfam[fam]
    nsp = sum(len(v) for v in genera.values())
    common, desc = FAM[fam]
    out.write('  %s:{common:"%s",genera:%d,species:%d,range:"%s",\n    desc:"%s"},\n'
              % (fam, esc(common), len(genera), nsp, esc(range_line(fam)), esc(desc)))
out.write("};\n")
F_JS = out.getvalue()

# ---------------------------------------------------------------- TREE
lines = ['const TREE = {name:"Dinosauria", rank:"Clade", children:[']
for cname, crank, blocks in TREE_SPEC:
    lines.append('  {name:"%s", rank:"%s", children:[' % (cname, crank))
    for bname, brank, fams in blocks:
        leaves = ", ".join('leaf("%s")' % f for f in fams)
        lines.append('    {name:"%s", rank:"%s", children:[ %s ]},' % (bname, brank, leaves))
    lines.append("  ]},")
lines.append("]};")
TREE_JS = "\n".join(lines) + "\n"

# ---------------------------------------------------------------- ATLAS
# what the tree can open before the taxonomy loads; it is rebuilt with
# PBDB's subgroups as rows once dinosaur_taxonomy.json has arrived
out = io.StringIO()
out.write("const ATLAS = {\n")
for fam in ORDERED:
    gl = ",".join('["%s",%d]' % (g, len(v)) for g, v in byfam[fam].items())
    out.write("%s:P([%s]),\n" % (fam, gl))
out.write("};\n")
ATLAS_JS = out.getvalue()

SP_JS = "const SP = {\n};\n"

blocks = "\n".join([F_JS, TREE_JS, ATLAS_JS, SP_JS])

if __name__ == "__main__":
    print("groups %d, genera %d, species %d; F block %d KB, ATLAS block %d KB" % (
        len(ORDERED), len({s["genus"] for s in SPECIES}), len(SPECIES),
        len(F_JS) / 1024, len(ATLAS_JS) / 1024))
    for fam in ORDERED:
        print("  %-22s %s" % (fam, range_line(fam)))
