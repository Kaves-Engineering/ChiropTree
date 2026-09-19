"""Build dinosaur-tree.html from chiroptera-tree.html.

Run:  uv run python data/build_dinosaur_page.py

Same arrangement as build_marine_mammal_page.py and build_bird_page.py:
chiroptera-tree.html is the master, and this copies it verbatim -- CSS, markup
and every line of interaction code -- swapping only content: the palette, the
data blocks (build_dinosaur_data_blocks.py), the data-file paths, and the
strings that name the animals. Every replacement is anchored on an exact
string and the build exits loudly if one stops matching.

Dinosaurs differ from the other pages in ways that show up here as swaps:

  * The source is the Paleobiology Database. The card's MDD link becomes a
    link to the species' PBDB page, and the source line links PBDB itself
    rather than a DOI (PBDB is a live database, not a versioned release).
  * The card is a fossil record, not a status report: age, diet, the
    countries and rock formations the fossils come from, and the paper that
    named the species replace IUCN status, realm and continents.
  * There is no call section. Birds keep it as an empty slot for data to
    come; nothing will ever fill it for a dinosaur.
  * The picture comes from Wikipedia rather than iNaturalist: the page's live
    photo lookup reads the genus's image from dinosaur_images.json (built by
    build_dinosaur_images.py) instead of querying iNaturalist, and the caption
    credits Wikimedia Commons with the file's own licence.
  * Countries are where fossils were found, so the map and card say that.
"""
import os
import re
import sys

import build_dinosaur_data_blocks as data

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "chiroptera-tree.html")
DST = os.path.join(REPO, "dinosaur-tree.html")

html = open(SRC, encoding="utf-8").read()
blocks = data.blocks
GROUPS = len(data.ORDERED)


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


def swap_function(signature, replacement):
    """replace a whole top-level function, from its signature to the closing
    brace at the start of a line"""
    global html
    i = html.find(signature)
    if i < 0 or html.count(signature) != 1:
        sys.exit("function not found exactly once in master: " + signature)
    j = html.find("\n}\n", i)
    html = html[:i] + replacement + html[j + len("\n}"):]
    hits.append(signature)


# ----------------------------------------------------------------- palette
palette = open(os.path.join(HERE, "dinosaur_palette.css"), encoding="utf-8").read().strip()
START, END = "/* ===== PALETTE ", "/* ===== /PALETTE ==================================================== */"
i, j = html.find(START), html.find(END)
if i < 0 or j < 0:
    sys.exit("palette markers not found in the master")
master_tokens = set(re.findall(r'(--[\w-]+):', html[i:j + len(END)]))
dino_tokens = set(re.findall(r'(--[\w-]+):', palette))
missing = master_tokens - dino_tokens
if missing:
    sys.exit("dinosaur_palette.css is missing tokens the master defines: %s" % sorted(missing))
html = html[:i] + palette + html[j + len(END):]
hits.append("palette region (%d tokens)" % len(dino_tokens))

# ----------------------------------------------------------------- head/chrome
sub("<title>Chiroptera — bat tree and range map</title>",
    "<title>Dinosaurs — tree and fossil map</title>")
sub('<meta name="theme-color" content="#0d140f">',
    '<meta name="theme-color" content="#15110e">')
sub("theme === 'light' ? '#f3f0e5' : '#0d140f'",
    "theme === 'light' ? '#f5efe4' : '#15110e'", count=2)

sub('<a class="tb-brand" href="#top">The branching of <em>bats</em></a>',
    '<a class="tb-brand" href="#top">The branching of <em>dinosaurs</em></a>')
sub(""".tb-brand{font-size:0;flex:none;width:36px}
  .tb-brand::before{content:"Bats";""",
    """.tb-brand{font-size:0;flex:none;width:auto}
  .tb-brand::before{content:"Dinos";""")
# the map that draws Antarctica: Cryolophosaurus, Antarctopelta, Glacialisaurus
sub('<link rel="preload" href="data/world_map.json" as="fetch" type="application/json">',
    '<link rel="preload" href="data/marine_world_map.json" as="fetch" type="application/json">')

sub("""      <a class="ps-opt" href="index.html" aria-current="page">Bats</a>
      <a class="ps-opt" href="marine.html">Marine<span class="ps-long"> mammals</span></a>
      <a class="ps-opt" href="birds.html">Birds</a>
      <a class="ps-opt" href="dinosaurs.html">Dino<span class="ps-long">saurs</span></a>""",
    """      <a class="ps-opt" href="index.html">Bats</a>
      <a class="ps-opt" href="marine.html">Marine<span class="ps-long"> mammals</span></a>
      <a class="ps-opt" href="birds.html">Birds</a>
      <a class="ps-opt" href="dinosaurs.html" aria-current="page">Dino<span class="ps-long">saurs</span></a>""")

sub('placeholder="Search any bat…"', 'placeholder="Search any dinosaur…"')
sub('aria-label="Show a random bat" title="Random bat"',
    'aria-label="Show a random dinosaur" title="Random dinosaur"')
sub('<nav class="mobile-workspace" aria-label="Browse the bat guide">',
    '<nav class="mobile-workspace" aria-label="Browse the dinosaur guide">')
sub('aria-label="Keep all bats in the tree" title="Keep all bats in the tree"',
    'aria-label="Keep all dinosaurs in the tree" title="Keep all dinosaurs in the tree"')
sub('aria-label="Show only bats from the selected country" title="Show only bats from the selected country"',
    'aria-label="Show only dinosaurs found in the selected country" title="Show only dinosaurs found in the selected country"')
sub("const text = entry ? 'Show only bats from '+entry.name : 'Show only bats from the selected country';",
    "const text = entry ? 'Show only dinosaurs found in '+entry.name : 'Show only dinosaurs found in the selected country';")
sub('aria-label="Cladogram of the 21 living bat families"',
    'aria-label="Cladogram of %d dinosaur groups"' % GROUPS)
sub('<h2 class="sr-only" id="map-h">Range map</h2>',
    '<h2 class="sr-only" id="map-h">Where the fossils were found</h2>')

sub("""  Source: <a id="mdd-source" href="https://doi.org/10.5281/zenodo.21654811" target="_blank" rel="noopener noreferrer">Mammal Diversity Database v2.5</a>""",
    """  Source: <a id="mdd-source" href="https://paleobiodb.org" target="_blank" rel="noopener noreferrer">Paleobiology Database</a>
  · Images: <a href="https://commons.wikimedia.org" target="_blank" rel="noopener noreferrer">Wikimedia Commons</a>, via Wikipedia""")

# ------------------------------------------------------------------ data blocks
for name in ("F", "ATLAS", "SP"):
    swap_const(name)
swap_const("TREE", close="\n]};")

# the backbone's middle level is a clade or grade, never a "superfamily" alone
sub("""famSpecies+' species, superfamily '+r.sf""", """famSpecies+' species, '+r.sf""")
# the blocks hold groups, most of which are not families
sub("""b.members.length + (b.members.length===1?' family':' families')""",
    """b.members.length + (b.members.length===1?' group':' groups')""")
# a group's range line is when and where, both from the fossil record
sub("""'<p class="range-line">Range: <b>'+d.range+'</b></p>'""",
    """'<p class="range-line">When and where: <b>'+d.range+'</b></p>'+dinoGroupTimescale(name)""")

# no calls: ESP is species-level bat echolocation prose and must not leak across
if "const ECHO" in html:
    sys.exit("master reintroduced const ECHO; decide what the dinosaur page should do with it")
i = html.find("const ESP = {")
j = html.find("\n};", i)
html = html[:i] + "const ESP = {};" + html[j + len("\n};"):]
hits.append("const ESP -> {}")

# reference links: PBDB replaces MDD; Xeno-canto has nothing to offer
sub("""  ["Mammal Diversity Database", (n, s) => s && s.id ? "https://www.mammaldiversity.org/taxon/" + encodeURIComponent(s.id) + "/" : "", '<span class="letter-mark" aria-hidden="true">M</span>'],
  ["Xeno-canto calls", n => "https://xeno-canto.org/explore?query=" + encodeURIComponent(n), '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h2l2.2-5 3.2 10 3.1-13 3 16 2.2-8H21"/></svg>']""",
    """  ["Paleobiology Database", (n, s) => s && s.pbdb ? "https://paleobiodb.org/classic/basicTaxonInfo?taxon_no=" + encodeURIComponent(s.pbdb) : "", '<span class="letter-mark" aria-hidden="true">P</span>']""")

# ------------------------------------------------------------------ the card
sub("""No record under this name in the Mammal Diversity Database export""",
    """No record under this name in the Paleobiology Database download""")
sub("""'<section class="lu-section"><h4>Taxonomy &amp; status</h4><dl>'""",
    """'<section class="lu-section"><h4>Fossil record</h4><dl>'""")
sub("""        '<dt>IUCN status</dt><dd><span class="lu-status '+luStatusClass(s.iucnStatus)+'">'+(s.iucnStatus||'NA')+'</span></dd>'+
        '<dt>Extinct</dt><dd>'+(s.extinct==='1' ? 'Yes' : 'No')+'</dd>'+
        '<dt>Realm</dt><dd>'+luEsc(s.biogeographicRealm||'—')+'</dd>'+
        '<dt>Continents</dt><dd>'+luEsc((s.continentDistribution||'—').replace(/\\|/g,', '))+'</dd>'+
        '<dt>Countries</dt><dd>'+luCountriesHTML(s)+'</dd>'+
      '</dl>'+luCountriesFootnote(s)+'</section>'+
      '<section class="lu-section"><h4>Call</h4>'+luCallHTML(directCall, callReference, s.family, s.genus, bin)+'</section>'+""",
    """        '<dt>Age</dt><dd>'+luEsc(s.age||'—')+(s.maxMa ? ' · '+(s.maxMa===s.minMa ? s.maxMa : s.maxMa+'–'+s.minMa)+' million years ago' : '')+'</dd>'+
        '<dt>Diet</dt><dd>'+luEsc(s.diet||'—')+'</dd>'+
        '<dt>Found in</dt><dd>'+luCountriesHTML(s)+'</dd>'+
        '<dt>Formations</dt><dd>'+luEsc((s.formations||'—').replace(/\\|/g,', '))+'</dd>'+
        '<dt>Named in</dt><dd>'+luEsc(s.reference||'—')+'</dd>'+
      '</dl>'+(s.occurrences ? '<p class="lu-src">'+s.occurrences+' PBDB occurrence record'+(s.occurrences===1?'':'s')+'; countries are where fossils identified to this species were dug up, on today’s map</p>' : '')+
      dinoSpeciesTimescale(s)+'</section>'+""")
sub("""    '<a href="https://doi.org/'+luEsc(luState.meta.sourceDoi)+'" target="_blank" rel="noopener">'+luEsc(luState.meta.source)+'</a>'
  ];""",
    """    '<a href="https://paleobiodb.org/classic/basicTaxonInfo?taxon_no='+luEsc(s.pbdb)+'" target="_blank" rel="noopener">'+luEsc(luState.meta.source)+'</a>'
  ];
  const image = (luState.images||{})[s.genus];
  if(image) sources.push('<a href="'+luEsc(image.article)+'" target="_blank" rel="noopener">Wikipedia</a> (image)');""")

# ------------------------------------------------------------------ time scale
# A collapsible Mesozoic time axis on both cards: on a group's card one bar per
# genus, from its oldest species' first appearance to its youngest's last, oldest
# first; on a species card the species' own span. The spans are PBDB's
# first/last appearance ages, so a bar is the age of the rocks the fossils are
# from, not a measured lifespan of the lineage. Open or closed is remembered
# (per viewer, in localStorage) so it stays the way the reader left it.
TS_START, TS_END = 252.0, 66.0
PERIODS = [("Triassic", 252.0, 201.4), ("Jurassic", 201.4, 143.1), ("Cretaceous", 143.1, 66.0)]
def pct(ma):
    return round((TS_START - ma) / (TS_START - TS_END) * 100, 2)
jurassic = (pct(201.4), pct(143.1))

sub("</style>", """
/* ---- time scale: bars against the Mesozoic, on group and species cards ---- */
.ts{margin:6px 0 12px;border-top:1px solid var(--line-dim);padding-top:6px}
.ts summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;min-height:32px;
  font-family:var(--mono);font-size:.6875rem;letter-spacing:.08em;text-transform:uppercase;color:var(--ochre)}
.ts summary::-webkit-details-marker{display:none}
.ts summary::before{content:"";flex:none;width:6px;height:6px;margin:0 2px;border-right:1.5px solid currentColor;
  border-bottom:1.5px solid currentColor;transform:rotate(-45deg);transition:transform .15s}
.ts[open] summary::before{transform:rotate(45deg)}
.ts summary:focus-visible{outline:2px solid var(--ochre);outline-offset:2px}
.ts-count{color:var(--muted);letter-spacing:.03em;text-transform:none}
.ts-grid{display:grid;grid-template-columns:minmax(6.5em,32%%) 1fr;column-gap:10px;row-gap:2px;margin:6px 0 2px}
.ts-name{font-size:.75rem;font-style:italic;color:var(--ink-mid);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:16px}
.ts-axis{grid-column:2;position:relative;height:16px}
.ts-period{position:absolute;top:0;height:16px;overflow:hidden;white-space:nowrap;text-align:center;
  font-family:var(--mono);font-size:.625rem;letter-spacing:.06em;text-transform:uppercase;color:var(--line-text)}
.ts-tick{position:absolute;top:1px;font-family:var(--mono);font-size:.625rem;color:var(--ink-faint);white-space:nowrap}
.ts-track{position:relative;height:16px;background:linear-gradient(90deg,
  transparent 0 %(j0)s%%,rgba(var(--hover-rgb),.08) %(j0)s%% %(j1)s%%,transparent %(j1)s%% 100%%)}
.ts-bar{position:absolute;top:4px;bottom:4px;min-width:3px;border-radius:1px;background:var(--rule)}
.ts-bar.hl{background:var(--ochre)}
.ts-note{margin:6px 0 0;font-size:.6875rem;color:var(--muted)}
/* a species card has one bar and already names the species: full width */
.ts-solo{grid-template-columns:1fr}
.ts-solo .ts-axis{grid-column:1}
.ts-short{display:none}
@media (max-width:520px){.ts-long{display:none}.ts-short{display:inline}}
@media (prefers-reduced-motion:reduce){.ts summary::before{transition:none}}
</style>""" % {"j0": jurassic[0], "j1": jurassic[1]})

sub("function luDetailHTML(s, compact){", """const TS_START = %(start)s, TS_END = %(end)s;
const TS_PERIODS = %(periods)s;
let tsOpen = false;
try { tsOpen = localStorage.getItem('dino-timescale-open') === '1'; } catch (_) {}
// 'toggle' does not bubble, so listen in the capture phase for every card's scale
document.addEventListener('toggle', e=>{
  if(!e.target.classList || !e.target.classList.contains('ts')) return;
  tsOpen = e.target.open;
  try { localStorage.setItem('dino-timescale-open', tsOpen ? '1' : '0'); } catch (_) {}
}, true);

function tsPos(ma){ return Math.max(0, Math.min(100, (TS_START-ma)/(TS_START-TS_END)*100)); }
function tsSpan(max, min){ return max===min ? max+' Ma' : max+'–'+min+' Ma'; }

// rows: [[label, maxMa, minMa]], oldest first
function dinoTimescaleHTML(rows, summary, highlight, note){
  if(!rows.length) return '';
  const solo = rows.length===1 && highlight;
  const spacer = solo ? '' : '<div aria-hidden="true"></div>';
  const axis = TS_PERIODS.map(([n,a,b])=>
    '<span class="ts-period" style="left:'+tsPos(a)+'%%;width:'+(tsPos(b)-tsPos(a))+'%%">'+
    '<span class="ts-long">'+n+'</span><span class="ts-short">'+n.slice(0, n==='Cretaceous' ? 4 : 3)+'</span></span>').join('');
  const ticks = [TS_START, 201.4, 143.1, TS_END].map((ma,i,all)=>
    '<span class="ts-tick" style="left:'+tsPos(ma)+'%%;transform:translateX('+(i===0 ? '0' : i===all.length-1 ? '-100%%' : '-50%%')+')">'+
    Math.round(ma)+(i===all.length-1 ? ' Ma' : '')+'</span>').join('');
  const body = rows.map(([label,max,min])=>{
    const left = tsPos(max), width = Math.max(tsPos(min)-left, 0.8);
    return (solo ? '' : '<div class="ts-name" title="'+luEsc(label)+'">'+luEsc(label)+'</div>')+
      '<div class="ts-track" role="img" aria-label="'+luEsc(label)+', '+tsSpan(max,min)+'">'+
      '<span class="ts-bar'+(highlight?' hl':'')+'" style="left:'+left+'%%;width:'+width+'%%"></span></div>';
  }).join('');
  return '<details class="ts"'+(tsOpen?' open':'')+'><summary>Time scale <span class="ts-count">'+luEsc(summary)+'</span></summary>'+
    '<div class="ts-grid'+(solo?' ts-solo':'')+'">'+spacer+'<div class="ts-axis" aria-hidden="true">'+axis+'</div>'+body+
    spacer+'<div class="ts-axis" aria-hidden="true">'+ticks+'</div></div>'+
    (note ? '<p class="ts-note">'+luEsc(note)+'</p>' : '')+'</details>';
}

function dinoGroupTimescale(family){
  if(!luState.ready) return '';
  const spans = new Map(), genera = new Set();
  luState.species.forEach(s=>{
    if(s.family!==family) return;
    genera.add(s.genus);
    if(s.maxMa==null) return;
    const min = s.minMa==null ? s.maxMa : s.minMa, g = spans.get(s.genus);
    spans.set(s.genus, g ? [Math.max(g[0],s.maxMa), Math.min(g[1],min)] : [s.maxMa, min]);
  });
  const rows = [...spans].map(([g,[a,b]])=>[g,a,b]).sort((x,y)=>y[1]-x[1] || y[2]-x[2]);
  if(!rows.length) return '';
  const oldest = Math.max(...rows.map(r=>r[1])), youngest = Math.min(...rows.map(r=>r[2]));
  const undated = genera.size - rows.length;
  return dinoTimescaleHTML(rows, rows.length+' genera · '+tsSpan(oldest, youngest), false,
    (undated ? undated+(undated===1?' genus has':' genera have')+' no age in PBDB. ' : '')+
    'Bars run from first to last appearance in the rocks.');
}

function dinoSpeciesTimescale(s){
  if(s.maxMa==null) return '';
  const min = s.minMa==null ? s.maxMa : s.minMa;
  return dinoTimescaleHTML([[luNiceName(s.sciName), s.maxMa, min]], tsSpan(s.maxMa, min), true, '');
}

function luDetailHTML(s, compact){""" % {"start": TS_START, "end": TS_END,
                                        "periods": [[n, a, b] for n, a, b in PERIODS]})

# ------------------------------------------------------------------ the picture
# No iNaturalist for the extinct: the genus's Wikipedia lead image, resolved
# with its licence at build time, goes through the master's own photo path.
swap_function("async function livePhotoFor(species){", """async function livePhotoFor(species){
  const image = (luState.images||{})[species.genus];
  if(!image) return null;
  return {url:image.url, sourceUrl:image.sourceUrl, attribution:image.attribution,
          license:image.license, licenseUrl:image.licenseUrl || image.sourceUrl,
          provider:'Wikimedia Commons', alt:species.genus+', from its Wikipedia article'};
}""")
sub("""  const licenseUrl = code==='cc0' ? 'https://creativecommons.org/publicdomain/zero/1.0/' : 'https://creativecommons.org/licenses/'+code.replace('cc-','')+'/4.0/';""",
    """  const licenseUrl = asset.licenseUrl || (code==='cc0' ? 'https://creativecommons.org/publicdomain/zero/1.0/' : 'https://creativecommons.org/licenses/'+code.replace('cc-','')+'/4.0/');""")
sub("""+'</a> · iNaturalist'+""", """+'</a> · '+luEsc(asset.provider||'iNaturalist')+""")

# ------------------------------------------------------------------ data wiring
# No call export, no Danish names (dinosaurs have none beyond their Latin
# ones), no country supplement (the countries are in the taxonomy) and no
# image manifest: the pictures are Wikipedia's, listed in dinosaur_images.json.
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
  bundled('d-taxonomy', 'data/dinosaur_taxonomy.json'),
  bundled('d-images', 'data/dinosaur_images.json')
]).then(([tax, images])=>{
  luState.species = tax.species;
  luBuildDisplayTaxonomy(luState.species);
  luState.images = images;""")
sub("""  sourceLink.href = 'https://doi.org/'+tax._meta.sourceDoi;""",
    """  sourceLink.href = tax._meta.sourceUrl;""")
sub("""  luInput.placeholder = 'Search ' + tax._meta.speciesCount.toLocaleString() + ' bats…';""",
    """  luInput.placeholder = 'Search ' + tax._meta.speciesCount.toLocaleString() + ' dinosaurs…';""")
sub("""luState.meta.familyCount+' families</div>';""", """luState.meta.familyCount+' groups</div>';""")
sub("bundled('d-worldmap', 'data/world_map.json')",
    "bundled('d-worldmap', 'data/marine_world_map.json')")

open(DST, "w", encoding="utf-8", newline="\n").write(html)

print("applied %d replacements" % len(hits))
print("wrote %s (%d KB)" % (DST, os.path.getsize(DST) / 1024))
