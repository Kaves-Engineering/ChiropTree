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
import re, os, sys

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
    m = re.search(r"^const %s = .*?^\]?};$" % name, blocks, re.S | re.M)
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
    i = html.find("const %s = {" % name)
    if i < 0:
        sys.exit("const not found in master: " + name)
    j = html.find(close, i)
    html = html[:i] + grab(name) + html[j + len(close):]
    hits.append("const " + name)

# ----------------------------------------------------------------- head/chrome
sub("<title>Chiroptera — bat tree and range map</title>",
    "<title>Marine mammals — tree and range map</title>")

sub('<a class="tb-brand" href="#top">The branching of <em>bats</em></a>',
    '<a class="tb-brand" href="#top">Back to the <em>sea</em></a>')

# the master carries "Marine mammals ->"; the clone carries the return trip in
# the same nav slot
sub('      <a href="marine-mammal-tree.html">Marine mammals &rarr;</a>',
    '      <a href="chiroptera-tree.html">Bats &rarr;</a>')

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
  bundled('d-echo', 'data/echolocation_reference.json'),
  bundled('d-danish', 'data/danish_names.json')""",
    """Promise.all([
  bundled('d-taxonomy', 'data/marine_mammal_taxonomy.json'),
  bundled('d-danish', 'data/marine_mammal_danish_names.json')""")

sub("]).then(([tax, echo, danish])=>{", "]).then(([tax, danish])=>{")
sub("  luState.echo = echo;", "  luState.echo = null;  // see the ECHO note above")

sub("""  luInput.placeholder = 'Search ' + tax._meta.speciesCount.toLocaleString() + ' bats…';""",
    """  luInput.placeholder = 'Search ' + tax._meta.speciesCount.toLocaleString() + ' marine mammals…';""")

sub("bundled('d-worldmap', 'data/world_map.json')",
    "bundled('d-worldmap', 'data/marine_world_map.json')")

sub("""<script type="application/json" id="d-taxonomy">
INLINE data/chiroptera_taxonomy.json
</script>
<script type="application/json" id="d-echo">
INLINE data/echolocation_reference.json
</script>
<script type="application/json" id="d-danish">
INLINE data/danish_names.json
</script>
<script type="application/json" id="d-worldmap">
INLINE data/world_map.json
</script>""",
    """<script type="application/json" id="d-taxonomy">
INLINE data/marine_mammal_taxonomy.json
</script>
<script type="application/json" id="d-danish">
INLINE data/marine_mammal_danish_names.json
</script>
<script type="application/json" id="d-worldmap">
INLINE data/marine_world_map.json
</script>""")

open(DST, "w", encoding="utf-8", newline="\n").write(html)

# the Promise.all destructuring must lose `echo` along with the fetch
if re.search(r"\.then\(\(\[tax, echo, danish", html):
    sys.exit("d-echo was removed from the fetch list but the destructuring still names it")

print("applied %d replacements" % len(hits))
print("wrote %s (%d KB)" % (DST, os.path.getsize(DST) / 1024))
