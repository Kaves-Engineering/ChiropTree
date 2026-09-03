"""Build marine-mammal-tree.html from chiroptera-tree.html.

Run:  uv run python data/build_marine_mammal_page.py

chiroptera-tree.html is the master. This copies it verbatim -- CSS, markup and
every line of interaction code -- and swaps only content: the four data blocks
(generated from MDD by build_marine_mammal_data_blocks.py), the data-file
paths, and the strings that name the animals.

Every replacement is anchored on an exact string and the build exits loudly if
one stops matching, so the two pages cannot silently drift apart. When the
master is redesigned, this script is what fails first and tells you where.
"""
import os
import re
import sys

import build_marine_mammal_data_blocks as data

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "chiroptera-tree.html")
DST = os.path.join(REPO, "marine-mammal-tree.html")

html = open(SRC, encoding="utf-8").read()
blocks = data.blocks

def grab(name):
    """Pull one generated const block out of the generated text.

    TREE is an array literal and closes on "]};" rather than "};" -- without
    that alternative the non-greedy match runs past it and swallows the next
    block whole.
    """
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
    """Replace a whole `const NAME = {...};` block with the generated one."""
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
# The whole palette is one delimited region in the master, so the clone can
# carry a different one without touching a single structural rule. Both files
# must name the same tokens: a token used by the sheet but missing from the
# marine palette would fall back to nothing and paint an element transparent,
# so check before swapping rather than after rendering.
palette = open(os.path.join(HERE, "marine_palette.css"), encoding="utf-8").read().strip()
START, END = "/* ===== PALETTE ", "/* ===== /PALETTE ==================================================== */"
i, j = html.find(START), html.find(END)
if i < 0 or j < 0:
    sys.exit("palette markers not found in the master")
master_palette = html[i:j + len(END)]
master_tokens = set(re.findall(r'(--[\w-]+):', master_palette))
marine_tokens = set(re.findall(r'(--[\w-]+):', palette))
missing = master_tokens - marine_tokens
if missing:
    sys.exit("marine_palette.css is missing tokens the master defines: %s" % sorted(missing))
html = html[:i] + palette + html[j + len(END):]
hits.append("palette region (%d tokens)" % len(marine_tokens))

# ----------------------------------------------------------------- head/chrome
sub("<title>Chiroptera — bat tree and range map</title>",
    "<title>Marine mammals — tree and range map</title>")

# the browser chrome colour is set from markup and from JS, and has to track
# --abyss in both themes
sub('<meta name="theme-color" content="#0d140f">',
    '<meta name="theme-color" content="#08161e">')
sub("theme === 'light' ? '#f3f0e5' : '#0d140f'",
    "theme === 'light' ? '#eef3f7' : '#08161e'", count=2)

# Chiroptera is one clade and the title can say so. These three lineages
# entered the water separately, so the marine title counts the entrances
# instead of naming a branch.
sub('<a class="tb-brand" href="#top">The branching of <em>bats</em></a>',
    '<a class="tb-brand" href="#top">Three ways into <em>water</em></a>')
sub('<link rel="preload" href="data/world_map.json" as="fetch" type="application/json">',
    '<link rel="preload" href="data/marine_world_map.json" as="fetch" type="application/json">')

# the switch keeps both destinations; only which one is held down changes
sub("""      <a class="ps-opt" href="index.html" aria-current="page">Bats</a>
      <a class="ps-opt" href="marine.html">Marine mammals</a>""",
    """      <a class="ps-opt" href="index.html">Bats</a>
      <a class="ps-opt" href="marine.html" aria-current="page">Marine mammals</a>""")

sub('placeholder="Search any bat…"', 'placeholder="Search any marine mammal…"')
sub('aria-label="Show a random bat" title="Random bat"',
    'aria-label="Show a random marine mammal" title="Random marine mammal"')
sub('aria-label="Keep all bats in the tree" title="Keep all bats in the tree"',
    'aria-label="Keep all marine mammals in the tree" title="Keep all marine mammals in the tree"')
sub('aria-label="Show only bats from the selected country" title="Show only bats from the selected country"',
    'aria-label="Show only marine mammals from the selected country" title="Show only marine mammals from the selected country"')
sub('aria-label="Cladogram of the 21 living bat families"',
    'aria-label="Cladogram of the 18 living marine mammal families"')

# ------------------------------------------------------------------ data blocks
for name in ("F", "ATLAS", "SP"):
    swap_const(name)
swap_const("TREE", close="\n]};")

# Echolocation stays empty on purpose. No marine equivalent of the bat page's
# per-family reference was compiled, and inventing call figures would produce
# numbers that look citable and are not. Every code path below is the master's
# and simply renders nothing; the drawer already has an honest fallback.
i = html.find("const ECHO = {")
j = html.find("\n};", i)
html = html[:i] + "const ECHO = {};" + html[j + len("\n};"):]
hits.append("const ECHO -> {}")

i = html.find("const ESP = {")
j = html.find("\n};", i)
html = html[:i] + "const ESP = {};" + html[j + len("\n};"):]
hits.append("const ESP -> {}")

# xeno-canto is a bird/bat call archive and does not cover marine mammals;
# GBIF occurrence records do, and the icon carries over unchanged
sub("""  ["Xeno-canto calls", n => "https://xeno-canto.org/explore?query=" + encodeURIComponent(n), '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h2l2.2-5 3.2 10 3.1-13 3 16 2.2-8H21"/></svg>']""",
    """  ["GBIF records", n => "https://www.gbif.org/species/search?q=" + encodeURIComponent(n), '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h2l2.2-5 3.2 10 3.1-13 3 16 2.2-8H21"/></svg>']""")

# ------------------------------------------------------------------ data wiring
sub("""Promise.all([
  bundled('d-taxonomy', 'data/chiroptera_taxonomy.json'),
  bundled('d-calls', 'data/call-records.json'),
  bundled('d-danish', 'data/danish_names.json'),
  bundled('d-countries', 'data/gbif_country_supplement.json'),
  bundled('d-danish-calls', 'data/danish_call_measurements.json'),
  bundled('d-media', 'data/media-manifest.json')""",
    """Promise.all([
  bundled('d-taxonomy', 'data/marine_mammal_taxonomy.json'),
  bundled('d-danish', 'data/marine_mammal_danish_names.json'),
  bundled('d-countries', 'data/marine_mammal_gbif_country_supplement.json'),
  bundled('d-media', 'data/media-manifest.json')""")

sub("]).then(([tax, calls, danish, countrySupp, danishCalls, media])=>{", "]).then(([tax, danish, countrySupp, media])=>{")

# the supplement matters more here than on the bat page: MDD's country column
# never names Svalbard, so without this the walrus, bowhead and ringed and
# bearded seals have no Arctic presence on the map at all
sub("""// it misses 4 of Denmark's 17 established bat species. Additive only -- it""",
    """// it misses Svalbard entirely -- no walrus, no bowhead. Additive only -- it""")
sub("  luState.echo = calls;", "  luState.echo = null;  // see the ECHO note above")
sub("  luState.directCalls = danishCalls.species || {};", "  luState.directCalls = {};")
sub("  luState.directCallReferences = danishCalls.references || {};", "  luState.directCallReferences = {};")

sub("""  luInput.placeholder = 'Search ' + tax._meta.speciesCount.toLocaleString() + ' bats…';""",
    """  luInput.placeholder = 'Search ' + tax._meta.speciesCount.toLocaleString() + ' marine mammals…';""")

sub("bundled('d-worldmap', 'data/world_map.json')",
    "bundled('d-worldmap', 'data/marine_world_map.json')")

open(DST, "w", encoding="utf-8", newline="\n").write(html)

# the Promise.all destructuring must lose `calls` along with the fetch
if re.search(r"\.then\(\(\[tax, calls, danish", html):
    sys.exit("d-calls was removed from the fetch list but the destructuring still names it")

print("applied %d replacements" % len(hits))
print("wrote %s (%d KB)" % (DST, os.path.getsize(DST) / 1024))
