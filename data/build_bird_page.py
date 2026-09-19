"""Build bird-tree.html from chiroptera-tree.html.

Run:  uv run python data/build_bird_page.py

Same arrangement as build_marine_mammal_page.py: chiroptera-tree.html is the
master, and this copies it verbatim -- CSS, markup and every line of
interaction code -- swapping only content: the palette, the data blocks
(build_bird_data_blocks.py), the data-file paths, and the strings that name
the animals. Every replacement is anchored on an exact string and the build
exits loudly if one stops matching.

Birds differ from the two mammal pages in three ways, and each shows up here
as a swap rather than a code change:

  * The source is AviList, not MDD. The species card's MDD link becomes eBird
    and Avibase, and the "no record in MDD" fallback names AviList.
  * AviList has no country checklist, so every country comes from GBIF
    records. The card labels the list that way, and there is no separate
    supplement to merge.
  * There is no call data yet. Nothing is stamped in: the page loads no call
    export, and the card's Call section falls back to the master's own
    "no measurement yet" line -- an empty slot waiting for data.
"""
import os
import re
import sys

import build_bird_data_blocks as data

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "chiroptera-tree.html")
DST = os.path.join(REPO, "bird-tree.html")

html = open(SRC, encoding="utf-8").read()
blocks = data.blocks
FAMILIES = len(data.ORDERED)


def grab(name):
    m = re.search(r"^const %s = .*?^\]?};$" % name, blocks, re.DOTALL | re.MULTILINE)
    if not m:
        sys.exit("generated block not found: " + name)
    return m.group(0)


hits = []
def sub(old, new, count=1):
    global html
    n = html.count(old)
    if n != count:
        sys.exit("ANCHOR MISS (%d, expected %d): %s" % (n, count, old[:90].replace("\n", " ")))
    html = html.replace(old, new)
    hits.append(old[:60].replace("\n", " "))


def swap_const(name, close="\n};"):
    global html
    declaration = "let" if "let %s = {" % name in html else "const"
    i = html.find("%s %s = {" % (declaration, name))
    if i < 0:
        sys.exit("const not found in master: " + name)
    j = html.find(close, i)
    block = grab(name).replace("const %s" % name, "%s %s" % (declaration, name), 1)
    html = html[:i] + block + html[j + len(close):]
    hits.append("const " + name)


# ----------------------------------------------------------------- palette
palette = open(os.path.join(HERE, "bird_palette.css"), encoding="utf-8").read().strip()
START, END = "/* ===== PALETTE ", "/* ===== /PALETTE ==================================================== */"
i, j = html.find(START), html.find(END)
if i < 0 or j < 0:
    sys.exit("palette markers not found in the master")
master_tokens = set(re.findall(r'(--[\w-]+):', html[i:j + len(END)]))
bird_tokens = set(re.findall(r'(--[\w-]+):', palette))
missing = master_tokens - bird_tokens
if missing:
    sys.exit("bird_palette.css is missing tokens the master defines: %s" % sorted(missing))
html = html[:i] + palette + html[j + len(END):]
hits.append("palette region (%d tokens)" % len(bird_tokens))

# ----------------------------------------------------------------- head/chrome
sub("<title>Chiroptera — bat tree and range map</title>",
    "<title>Birds — tree and range map</title>")
sub('<meta name="theme-color" content="#0d140f">',
    '<meta name="theme-color" content="#131020">')
sub("theme === 'light' ? '#f3f0e5' : '#0d140f'",
    "theme === 'light' ? '#f5f1ea' : '#131020'", count=2)

sub('<a class="tb-brand" href="#top">The branching of <em>bats</em></a>',
    '<a class="tb-brand" href="#top">The branching of <em>birds</em></a>')
sub(""".tb-brand{font-size:0;flex:none;width:36px}
  .tb-brand::before{content:"Bats";""",
    """.tb-brand{font-size:0;flex:none;width:auto}
  .tb-brand::before{content:"Birds";""")
# penguins, skuas and sheathbills need Antarctica, which only the marine map draws
sub('<link rel="preload" href="data/world_map.json" as="fetch" type="application/json">',
    '<link rel="preload" href="data/marine_world_map.json" as="fetch" type="application/json">')

sub("""      <a class="ps-opt" href="index.html" aria-current="page">Bats</a>
      <a class="ps-opt" href="marine.html">Marine<span class="ps-long"> mammals</span></a>
      <a class="ps-opt" href="birds.html">Birds</a>""",
    """      <a class="ps-opt" href="index.html">Bats</a>
      <a class="ps-opt" href="marine.html">Marine<span class="ps-long"> mammals</span></a>
      <a class="ps-opt" href="birds.html" aria-current="page">Birds</a>""")

sub('placeholder="Search any bat…"', 'placeholder="Search any bird…"')
sub('aria-label="Show a random bat" title="Random bat"',
    'aria-label="Show a random bird" title="Random bird"')
sub('<nav class="mobile-workspace" aria-label="Browse the bat guide">',
    '<nav class="mobile-workspace" aria-label="Browse the bird guide">')
sub('aria-label="Keep all bats in the tree" title="Keep all bats in the tree"',
    'aria-label="Keep all birds in the tree" title="Keep all birds in the tree"')
sub('aria-label="Show only bats from the selected country" title="Show only bats from the selected country"',
    'aria-label="Show only birds from the selected country" title="Show only birds from the selected country"')
sub("const text = entry ? 'Show only bats from '+entry.name : 'Show only bats from the selected country';",
    "const text = entry ? 'Show only birds from '+entry.name : 'Show only birds from the selected country';")
sub('aria-label="Cladogram of the 21 living bat families"',
    'aria-label="Cladogram of the %d bird families"' % FAMILIES)

sub("""  Source: <a id="mdd-source" href="https://doi.org/10.5281/zenodo.21654811" target="_blank" rel="noopener noreferrer">Mammal Diversity Database v2.5</a>""",
    """  Source: <a id="mdd-source" href="https://doi.org/10.2173/avilist.v2025b" target="_blank" rel="noopener noreferrer">AviList v2025b</a>
  · Countries: <a href="https://www.gbif.org" target="_blank" rel="noopener noreferrer">GBIF</a> records
  · Danish names: <a href="https://www.dof.dk/aktiv-i-dof/grupper-og-udvalg/navnegruppen/publikationer-navnegruppen" target="_blank" rel="noopener noreferrer">DOF</a>""")

# ------------------------------------------------------------------ data blocks
for name in ("F", "ATLAS", "SP"):
    swap_const(name)
swap_const("TREE", close="\n]};")

# the backbone's middle level is an order outside the passerines and a
# suborder, parvorder or superfamily inside them -- never a "superfamily" alone
sub("""famSpecies+' species, superfamily '+r.sf""", """famSpecies+' species, '+r.sf""")

# No call data for birds yet: the slot stays, empty. ESP is species-level bat
# echolocation prose and must not leak across.
if "const ECHO" in html:
    sys.exit("master reintroduced const ECHO; decide what the bird page should do with it")
i = html.find("const ESP = {")
j = html.find("\n};", i)
html = html[:i] + "const ESP = {};" + html[j + len("\n};"):]
hits.append("const ESP -> {}")

# reference links: eBird and Avibase replace MDD; xeno-canto is, if anything,
# more at home here than on the bat page
sub("""  ["Mammal Diversity Database", (n, s) => s && s.id ? "https://www.mammaldiversity.org/taxon/" + encodeURIComponent(s.id) + "/" : "", '<span class="letter-mark" aria-hidden="true">M</span>'],""",
    """  ["eBird and Birds of the World", (n, s) => s && s.ebird ? "https://ebird.org/species/" + encodeURIComponent(s.ebird) : "", '<span class="letter-mark" aria-hidden="true">e</span>'],
  ["Avibase", (n, s) => s && s.avibase ? "https://avibase.bsc-eoc.org/species.jsp?avibaseid=" + encodeURIComponent(s.avibase.replace(/^avibase-/, "")) : "", '<span class="letter-mark" aria-hidden="true">A</span>'],""")

# ------------------------------------------------------------------ the card
sub("""No record under this name in the Mammal Diversity Database export""",
    """No record under this name in the AviList checklist""")
# AviList gives a range description, not realm and continent columns
sub("""        '<dt>Realm</dt><dd>'+luEsc(s.biogeographicRealm||'—')+'</dd>'+
        '<dt>Continents</dt><dd>'+luEsc((s.continentDistribution||'—').replace(/\\|/g,', '))+'</dd>'+
        '<dt>Countries</dt><dd>'+luCountriesHTML(s)+'</dd>'+""",
    """        '<dt>Range</dt><dd>'+luEsc(s.range||'—')+'</dd>'+
        '<dt>Countries</dt><dd>'+luCountriesHTML(s)+'</dd>'+""")
# every bird country is GBIF evidence, so the card says it once for the whole
# list rather than marking each name the way the mammal cards mark additions
sub("""'</dl>'+luCountriesFootnote(s)+'</section>'""",
    """'</dl>'+(s.countryDistribution ? '<p class="lu-src">Countries: GBIF occurrence records, vagrants filtered out</p>' : '')+'</section>'""")
sub("""  if(dk && dk.gbifKey) sources.push('<a href="https://www.gbif.org/species/'+luEsc(dk.gbifKey)+'" target="_blank" rel="noopener">'+luEsc(dk.source)+' via GBIF</a>');""",
    """  if(dk) sources.push('<a href="https://www.dof.dk/aktiv-i-dof/grupper-og-udvalg/navnegruppen/publikationer-navnegruppen" target="_blank" rel="noopener">'+luEsc(dk.source)+'</a>');
  if(s.countryDistribution) sources.push('<a href="https://www.gbif.org/species/search?q='+encodeURIComponent(bin)+'" target="_blank" rel="noopener">GBIF occurrence records</a>');""")

# ------------------------------------------------------------------ data wiring
# No call export, no country supplement (the countries are already in the
# taxonomy) and no image manifest: that snapshot covers mammals only, and
# every bird photo is fetched live from iNaturalist like any uncached mammal.
sub("""Promise.all([
  bundled('d-taxonomy', 'data/chiroptera_taxonomy.json'),
  bundled('d-danish', 'data/danish_names.json'),
  bundled('d-countries', 'data/gbif_country_supplement.json'),
  bundled('d-calls', 'data/calls/exports/calls.json'),
  bundled('d-media', 'data/media-manifest.json')
]).then(([tax, danish, countrySupp, calls, media])=>{
  luState.species = tax.species;
  luBuildDisplayTaxonomy(luState.species);
  luState.danish = danish;
  luState.directCalls = calls.species || {};
  luState.familyInference = calls.familyInference || {};
  luState.genusInference = calls.genusInference || {};
  luState.directCallReferences = calls.references || {};
  luState.media = media.assets || {};
  luMergeCountrySupplement(luState.species, countrySupp);""",
    """Promise.all([
  bundled('d-taxonomy', 'data/bird_taxonomy.json'),
  bundled('d-danish', 'data/bird_danish_names.json')
]).then(([tax, danish])=>{
  luState.species = tax.species;
  luBuildDisplayTaxonomy(luState.species);
  luState.danish = danish;""")
sub("""  luInput.placeholder = 'Search ' + tax._meta.speciesCount.toLocaleString() + ' bats…';""",
    """  luInput.placeholder = 'Search ' + tax._meta.speciesCount.toLocaleString() + ' birds…';""")
sub("bundled('d-worldmap', 'data/world_map.json')",
    "bundled('d-worldmap', 'data/marine_world_map.json')")

open(DST, "w", encoding="utf-8", newline="\n").write(html)

print("applied %d replacements" % len(hits))
print("wrote %s (%d KB)" % (DST, os.path.getsize(DST) / 1024))
