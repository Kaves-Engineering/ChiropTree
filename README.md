# Tree of Bat Life

A lightweight, static tree and range map for bat (Chiroptera) taxonomy,
phylogenetic placement, and echolocation call characteristics. Built for lab
use, with no backend required.

Published with GitHub Pages.

## What's here

- **`chiroptera-tree.html`** — the main page: an expandable bat taxonomy tree,
  species search with licensed iNaturalist photos, and a clickable country
  range map. Deployed as the site's homepage.
- **`data/chiroptera_taxonomy.json`** — generated taxonomy data, Chiroptera
  subset of the [Mammal Diversity Database](https://www.mammaldiversity.org)
  (MDD) v2.5 release ([doi:10.5281/zenodo.21654811](https://doi.org/10.5281/zenodo.21654811)).
- **`data/echolocation_reference.json`** — a **starter** family/genus-level
  reference of echolocation call type, duty cycle, and peak frequency, hand
  compiled from standard comparative literature (Jones & Holderied 2007;
  Fenton & Simmons 2015; Neuweiler 2000; see `_meta.primary_sources` in the
  file itself). This is illustrative, not exhaustive or species-verified —
  treat it as a starting point to expand, not a citable primary source.
- **`data/build_taxonomy.py`** — regenerates `chiroptera_taxonomy.json` from
  the MDD release CSV (auto-downloads it into `data/raw/`, which is
  gitignored).
- **`data/danish_names.json`** — genuine Danish common names, fetched from
  [GBIF](https://www.gbif.org)'s vernacular-name records (mainly Denmark's
  National Checklist and Catalogue of Life). Danish names for bats barely
  exist outside the ~17 species found in Denmark — species without a
  recorded name are simply absent from this file rather than given an
  invented one.
- **`data/world_map.json`** — country outlines for the range map drawn in
  every species record: Equal Earth-projected, simplified SVG path strings plus
  centre points for the small islands the 110m outlines are too coarse to
  show, and a name index that resolves all 224 country spellings the MDD
  export uses. Built from [Natural Earth](https://www.naturalearthdata.com)
  (public domain).
- **`data/build_world_map.py`** — regenerates `world_map.json` from two
  Natural Earth GeoJSON files (auto-fetch commands are in the script's
  docstring; they land in the gitignored `data/raw/`). It reports any country
  name in the taxonomy it cannot place — that count should stay at zero. It
  also re-attributes Crimea from Russia's polygon to Ukraine's (Natural
  Earth's default draws it as Russian, which reflects control, not recognised
  sovereignty), using Shapely for that one boolean cut — declared as an inline
  `uv run` script dependency, so `uv run data/build_world_map.py` picks it up
  without adding it to the project's own dependencies.
- **`data/build_danish_names.py`** — regenerates `danish_names.json` by
  querying GBIF's species-match and vernacular-name APIs for every species
  in `chiroptera_taxonomy.json` (falls back to each species' MSW3-era name
  when MDD's current genus placement is ahead of GBIF's backbone, e.g. the
  *Eptesicus* → *Cnephaeus* split). Takes a few minutes; re-run after
  regenerating the taxonomy from a new MDD release.
- **`data/gbif_country_supplement.json`** — countries GBIF has real
  occurrence records for that MDD's own `countryDistribution` column omits
  (MDD's country list is a checklist column that lags real-world records —
  e.g. it was missing 4 of Denmark's 17 established species). Built from
  [GBIF](https://www.gbif.org) occurrence data by
  `data/build_country_distribution.py`; a country only counts if it has at
  least 3 non-fossil, non-captive, present-status records, to filter out
  vagrants/escapes/misidentifications. Merged into `countryDistribution`
  client-side at page load (see `luMergeCountrySupplement` in either page) —
  additive only, never removes or overrides an MDD-asserted country, and
  untouched by re-running `build_taxonomy.py` against a new MDD release.
- **`data/build_country_distribution.py`** — regenerates
  `gbif_country_supplement.json`. Caches per-species GBIF results in
  `data/raw/gbif_country_cache.json` (gitignored) so an interrupted run
  resumes cheaply; takes roughly 10–20 minutes for the full species list.

## Comparing species

Every species record has a **Compare** toggle. Picked species collect in a
tray along the bottom of the page (up to 10, set by `CMP_MAX`), and the tray
opens a side-by-side table: photos, names, every rank, the rank all of them
share, the countries they are recorded in together, and the page's own fields,
with an "only differences" filter. On the bat page a chart puts each species'
call frequency range on one kHz axis, with inferred ranges drawn as outlines;
the dinosaur page shows its Mesozoic time scale there instead. The picks are
remembered per page in `localStorage`, and an open comparison is mirrored into
the URL as `#compare=Genus_species,...`, so it can be shared as a link.

The feature lives in the master page. The clone pages inherit it. Their
content rows are `COMPARE_ROWS` and the chart is `compareChartHTML`, which
`build_dinosaur_page.py` swaps for fossil-record rows and the time scale. The
bird and marine pages keep the master's rows, and any row with no values for
the picked species is left out.

## The marine mammal pages

A parallel set of pages covering marine mammals, built from the same MDD
release by the same mechanisms. They are separate files throughout — nothing
here changes what the bat pages show.

- **`marine-mammal-tree.html`** — **generated, do not edit by hand.**
  `chiroptera-tree.html` is the master; this page is stamped out of it by
  `data/build_marine_mammal_page.py`, which copies the skeleton verbatim —
  CSS, markup and every line of interaction code — and swaps only content:
  the data blocks, the data-file paths, and the strings that name the animals.
  The pages link to each other from the top nav. Change the bat page,
  re-run the script, and the marine page inherits the change; every swap is
  anchored on an exact string and the build exits loudly if one stops
  matching, so the two cannot silently drift apart. Deployed as
  `/marine.html`.

  That guard rail has already earned its keep once: the "unified explorer"
  rewrite of the bat page removed three of its five sections, and the next
  run of this script stopped on the first anchor rather than emitting a page
  half-built from a master that no longer existed. Re-pointing the anchors is
  the maintenance cost of the arrangement, and it is the cost that keeps the
  two pages the same page.
- **`data/build_marine_mammal_page.py`** — does that stamping, and
  **`data/build_marine_mammal_data_blocks.py`** — holds what it stamps in.
  Everything structural in there (which genus sits in which subfamily or
  tribe, the species lists, every count) is derived from MDD; only the
  natural history prose and the coarse ecology tags are hand-authored, which
  is the same split the master page uses.
- **`data/marine_palette.css`** — the marine page's colour palette. Every
  colour in `chiroptera-tree.html` resolves through one delimited region
  (`/* ===== PALETTE ===== */` ... `/* ===== /PALETTE ===== */`) of named
  tokens — surface, ink, map, and status colours, in both themes — and
  nothing outside that region names a colour directly. The build script lifts
  that region out of the master and drops this file in, after checking every
  token the master defines is also defined here; a palette missing one fails
  the build instead of silently painting an element transparent. The bat page
  reads as a cave at night: dark leaf-litter ground, lichen green for
  structure, one warm lamplit accent. This is that same system moved into
  cold water — deep sea and glacial blue for ground and structure — with the
  accent kept warm on purpose, since that is what a marine mammal actually
  is: a warm body in a cold ocean.
- The two pages also share a **page switch** in the top bar (next to the
  title, where "The branching of bats" / "Three ways into water" sits) —
  both destinations always visible, the current one held down. It replaces
  what was a one-way arrow link, and is itself part of the master/clone
  split: one `.pageswitch` block, `aria-current` swapped by the build script
  to mark whichever page it's rendering.
- **`marine-mammal-lookup.html`** — **not currently published.** It mirrored
  `index.html`, the standalone lookup, which the unified-explorer rewrite
  deleted; with no counterpart left on the bat side it is out of `build.sh`
  and kept only pending a decision to revive or delete it.
- **`data/marine_mammal_taxonomy.json`** — 144 species, 18 families, 67
  genera, built by **`data/build_marine_mammal_taxonomy.py`**. Unlike
  Chiroptera, marine mammals are not a clade: the file is the union of
  Cetacea (102 spp., which MDD v2.5 nests inside Artiodactyla), Sirenia
  (5 spp.) and the pinniped families Otariidae/Phocidae/Odobenidae within
  Carnivora (37 spp.). Every species record carries a `lineage` field, and
  the three lineages are counted separately in `_meta`. The pages lead with
  that polyphyly rather than papering over it.
- **`data/marine_mammal_danish_names.json`** / **`..._gbif_country_supplement.json`**
  — same GBIF sources and same client-side merge as the bat data, built by the
  matching `build_marine_mammal_*.py` scripts. The supplement matters more
  here than it does for bats: MDD's country column never names Svalbard, so
  without it the walrus, bowhead, and ringed and bearded seals have no Arctic
  presence on the map at all. It is worth 11 clickable places, Antarctica 22
  species → 28, and Svalbard 0 → 19.
- **`data/marine_world_map.json`** — the range map. Built by the *same*
  `data/build_world_map.py` with `--marine`, which differs in one respect:
  it draws Antarctica instead of cropping it at 57°S. Species range there —
  blue, fin and minke whales, the Weddell, crabeater, leopard and Ross seals,
  the southern elephant seal — so the bat map's crop would silently swallow a
  large share of the ranges. The map is correspondingly taller (viewBox
  height 405.8 vs 344.9); the page reads the height from the data, so nothing
  hardcodes it.

There is deliberately **no** marine equivalent of
`echolocation_reference.json`. Odontocetes are formidable echolocators, but no
comparable per-family reference was compiled, and inventing call parameters to
fill the same card would have produced numbers that look citable and are not.
`ECHO` and `ESP` are therefore stamped in as empty objects: every code path is
the master's and simply renders nothing, and the species drawer falls back to
the master's own "no reference data" wording.

Building the marine data (the bat commands are unchanged):

```
uv run python data/build_marine_mammal_taxonomy.py
uv run data/build_world_map.py --marine
uv run python data/build_marine_mammal_danish_names.py
uv run python data/build_marine_mammal_country_distribution.py
```

## The bird pages

A third tree, for birds, built the same way as the marine page: it is stamped
out of the bat page, and none of it changes what the bat page shows. The page
switch in the top bar has a **Birds** option on all three pages; on phones,
"Marine mammals" shortens to "Marine" so the three options fit.

- **`bird-tree.html`** — **generated, do not edit by hand.** Stamped out of
  `chiroptera-tree.html` by `data/build_bird_page.py`: the same guard rails as
  the marine build (every swap anchored on an exact string, loud failure on a
  miss, palette token check). Deployed as `/birds.html`.
- **`data/bird_taxonomy.json`** — 11,131 species, 2,376 genera, 252 families,
  46 orders, from [AviList](https://www.avilist.org) v2025b
  ([doi:10.2173/avilist.v2025b](https://doi.org/10.2173/avilist.v2025b),
  CC BY 4.0), the 2025 global checklist that unified Clements/eBird and
  BirdLife/HBW. Built by **`data/build_bird_taxonomy.py`**, which keeps MDD's
  record shape so the master's lookup, card and map code read it unchanged.
  AviList adds a range description (the species row's, or its subspecies'
  joined), an eBird species code (also the record id) and an Avibase ID; the
  card's MDD link becomes eBird and Avibase links, and Xeno-canto stays.
- **`data/bird_gbif_countries.json`** — AviList has no country column, so every
  bird country comes from GBIF occurrence records, built by
  **`data/build_bird_country_distribution.py`** and merged into the taxonomy.
  eBird dominates bird records and logs every twitched rarity hundreds of
  times, so the mammal scripts' flat 3-record floor would paint half of Europe
  for any vagrant. A country is kept only with at least 5 records *and* either
  a meaningful share of all bird records in that country or 5% of the
  species' own records (the docstring explains the thresholds and the species
  they were checked against). The card labels these countries as GBIF
  evidence, not a checklist: established introductions appear too. Not
  published — the page reads the merged taxonomy.
- **`data/bird_danish_names.json`** — Danish names for 99.6% of species, from
  DOF's *Navne på alverdens fugle* (Navnegruppen; IOC 12.1 base), built by
  **`data/build_bird_danish_names.py`**. The list follows IOC 12.1 and the
  page follows AviList, so each name records how it was matched: exact
  binomial, a DOF subspecies AviList has raised to species, or an identical
  English name (genus moves).
- **`data/build_bird_data_blocks.py`** — the tree the page draws. Counts,
  genera and family English names come from AviList; the clade headings
  (Palaeognathae, Galloanserae, Columbaves, Strisores, Afroaves, Australaves,
  and suborders and superfamilies within Passeriformes) and each family's
  range line and description are hand-authored. The Hoatzin sits under
  "Neoaves incertae sedis" because the phylogenomic studies still disagree
  about where it goes.
- **`data/bird_palette.css`** — the sky before dawn: dusk violet and heather
  for ground and structure, with the accent the first warm light.
- The range map is `marine_world_map.json`, the one that draws Antarctica
  (penguins, skuas, sheathbills).
- **No call data yet.** The page loads no call export, and the card's Call
  section shows the master's "no measurement yet" line: an empty slot to
  fill later. Species photos come live from iNaturalist; the offline image
  snapshot covers mammals only.

Building the bird data (downloads land in the gitignored `data/raw/`):

```
uv run data/build_bird_taxonomy.py
uv run data/build_bird_country_distribution.py   # ~2 h first time; cached
uv run data/build_bird_taxonomy.py               # merges the countries in
uv run data/build_bird_danish_names.py
uv run python data/build_bird_page.py
```

The weekly data-sync workflow follows MDD releases only. AviList publishes
about once a year, and picking up a new version means updating
`SOURCE_URL`/`SOURCE_VERSION` in `build_bird_taxonomy.py` and re-running the
steps above.

## The dinosaur pages

A fourth tree, for the non-avian dinosaurs, stamped out of the bat page like
the marine and bird pages; none of it changes what the other pages show. The
page switch gains a **Dinosaurs** option on all four pages ("Dino" on phones).

- **`dinosaur-tree.html`** — **generated, do not edit by hand.** Stamped out of
  `chiroptera-tree.html` by `data/build_dinosaur_page.py`, with the same guard
  rails as the other builds. Deployed as `/dinosaurs.html`.
- **`data/dinosaur_taxonomy.json`** — 1,435 species in 1,279 genera, from the
  [Paleobiology Database](https://paleobiodb.org) (PBDB, CC BY 4.0), pulled
  from its public API by **`data/build_dinosaur_taxonomy.py`**: one call for
  every accepted taxon under Dinosauria, one for every fossil occurrence.
  Accepted names only (no junior synonyms), body fossils only (no footprint or
  egg taxa), and no birds: everything under PBDB's Avialae and Aves is cut,
  Archaeopteryx included. Records keep MDD's shape and add the fossil fields
  the card shows: age (stages and millions of years), diet, the rock formations
  the species comes from, and the paper that named it.
- **The groups the tree draws.** PBDB's hierarchy is uneven (about half the
  genera have no family, and it keeps some families few workers use), so the
  script's `GROUPS` names 71 groups by the PBDB taxa each absorbs, and every
  genus lands in the group of its nearest named ancestor. That is the only
  editorial layer; membership is PBDB's. Groups such as *Theropoda* or
  *Sauropoda* are catch-alls for genera PBDB places no deeper, and their text
  says so. The build fails if a genus lands nowhere or a group ends up empty.
- **Countries** are where fossils identified to the species were found, on
  today's map. They come from PBDB occurrences, are spelled the way MDD spells
  them, and are drawn on `marine_world_map.json`, since Antarctica has
  dinosaurs too.
- **`data/dinosaur_images.json`** — one image per genus (1,081 of 1,279): the
  lead image of the genus's English Wikipedia article (a skeleton, fossil or
  life restoration), with author and licence read from Wikimedia Commons.
  Built by **`data/build_dinosaur_images.py`**. Only public-domain, CC0,
  CC BY, CC BY-SA and GFDL images are kept, and an article counts only if its
  title is the genus itself. A redirect to another genus is Wikipedia sinking
  the name as a synonym, and the picture would show a different animal. The
  page reads this file in place of the iNaturalist lookup; nothing is fetched
  from Wikipedia at runtime except the image itself.
- **`data/build_dinosaur_data_blocks.py`** — the cladogram layout (early
  dinosaurs, Ornithischia, Sauropodomorpha, Theropoda) and each group's
  English name and description. Each group's time span and top countries are
  computed from the data.
- **`data/dinosaur_palette.css`** — the badlands: basalt ground, sandstone and
  bone for structure, iron-red strata for rules, and the first cool accent,
  vivianite blue.
- **Time scale.** Group and species cards have a collapsible time scale set
  against the whole Mesozoic (Triassic, Jurassic, Cretaceous, 252–66 Ma). A
  group's card has one bar per genus, oldest first. A species card has its
  own bar. Bars run from first to last appearance in the rocks (PBDB's
  ages), which is not the same as how long the lineage lived. Open or closed
  is remembered per viewer. Phones show no group cards, so there the scale
  appears on species records only.
- No Danish names (dinosaurs have none beyond their Latin ones) and no call
  section.

Building the dinosaur data (downloads cached in the gitignored `data/raw/`):

```
uv run python data/build_dinosaur_taxonomy.py   # --refresh to re-download from PBDB
uv run python data/build_dinosaur_images.py     # --refresh to re-query Wikipedia
uv run python data/build_dinosaur_page.py
```

PBDB is a live database, not a versioned release, so the release manifest
records the checksum of the two API downloads in place of a version. Picking
up new dinosaurs means re-running the steps above with `--refresh`.

## Updating the taxonomy data

MDD publishes new releases periodically. To pick up a new one:

1. Find the current release at the MDD concept DOI (always resolves to
   latest): https://doi.org/10.5281/zenodo.4139722
2. Update `SOURCE_DOI` / `SOURCE_URL` in `data/build_taxonomy.py` to point at
   the new release's species CSV file.
3. Delete `data/raw/` and run:

   ```
   uv run python data/build_taxonomy.py
   ```

## Running locally

### Install on Android

The published site is an installable web app named **Chiroptree**, with a
gold-and-green cladogram icon. All four animal groups stay inside the same app.

1. Publish the changes through the existing GitHub Pages workflow (a push to
   `master` builds and deploys the site).
2. On the phone, open the published **HTTPS** address in Chrome.
3. Tap **Install app** in the page footer when available, or open Chrome's
   **⋮** menu and choose **Add to home screen → Install**.
4. Launch **Chiroptree** from the home screen or app drawer.

Installation does not require a Play Store listing or an APK. Chrome controls
when it offers installation; the footer button appears only when a native
install prompt is available. See [Chrome's Android instructions](https://support.google.com/chrome/answer/9658361?co=GENIE.Platform%3DAndroid&hl=en).

Keep the app online for its first visit so the offline cache can finish.
The trees and core data then work offline. **Save images offline** downloads
the available image pack separately; live photos and external links still
need a connection. The app receives updates when reopened online (a further
reopen may be needed to display an update).

Phone installation requires HTTPS; a plain HTTP address on your home network
is not sufficient. The local development server intentionally skips the
service worker to avoid stale edits, so verify offline behavior on the built
site served over HTTPS.

The editable icon is `icons/icon.svg`. Regenerate its committed PNG exports
with `uv run python data/build_app_icons.py` after changing the mark. The
icon URL version in `manifest.webmanifest` and its matching entries in
`service-worker.js` must also change: Chrome 144+ detects icon updates from
changed manifest icon URLs or metadata, not changed image bytes alone.
Chrome may ask installed users to approve the new icon.
The
manifest includes 192px, 512px and Android maskable icons; build smoke checks
validate their dimensions and the offline asset paths.

`build.sh` writes the GitHub Pages site and its cacheable data files:

```
sh build.sh          # writes public/index.html
```

On Windows, open the bundled tree page directly without starting a local
server:

```
powershell -ExecutionPolicy Bypass -File .\open-tree.ps1
```

To keep the `http://localhost:8000/chiroptera-tree.html` URL available after
restarts, install the current-user Windows startup shortcut:

```
powershell -ExecutionPolicy Bypass -File .\install-startup-shortcut.ps1
```

The unbuilt `chiroptera-tree.html` in the repo root loads its data via
`fetch()`, so it needs to be served over HTTP. Opening it as a `file://` URL
fails silently on most browsers:

```
uv run python -m http.server 8000
```

Then open http://localhost:8000/chiroptera-tree.html.

GitHub Pages serves the data files directly. The service worker precaches the
application shell and core data after first visit, so the explorer works
offline without parsing a multi-megabyte HTML document at startup.

## Map performance checks

The map keeps its SVG geometry between selections, updates country/range
classes in place, and batches pan/zoom writes with `requestAnimationFrame`.
The frame callback runs only when the view changes; there is no idle render
loop. All four pages inherit this behavior from `chiroptera-tree.html`.

With the local HTTP server running on port 8000 and Playwright plus Chromium
available, run `node data/test_map_browser.cjs`. If Playwright is installed
outside the project, set `PLAYWRIGHT_MODULE` to its module directory. This
checks country filtering, species ranges, preserved geometry, island markers,
dragging, zoom controls, wheel zoom, and narrow-screen selection on every page.

## Extending the echolocation data

`data/echolocation_reference.json` is keyed by family, with optional
per-species/genus overrides under each family's `genusExamples`. To add or
correct an entry, add a key there (either a full species binomial like
`"Myotis lucifugus"` or a bare genus name) with `callType`, `dutyCycle`,
`peakFrequencyKHz`, and a `foragingNote`, and cite the source.

## License / attribution

Taxonomy data is © the Mammal Diversity Database contributors (ASM
Biodiversity Committee), used under their stated terms for downstream reuse —
retain attribution to MDD and its DOI when sharing derived data.

Bird taxonomy is from AviList (AviList Core Team. 2025. *AviList: The Global
Avian Checklist*, v2025b. https://doi.org/10.2173/avilist.v2025b), licensed
CC BY 4.0. Danish bird names are from Dansk Ornitologisk Forening's
Navnegruppen, *Navne på alverdens fugle*. Country presence for birds is derived
from GBIF-mediated occurrence data.

Dinosaur taxonomy, ages, diets and fossil occurrences are from the
Paleobiology Database (https://paleobiodb.org), licensed CC BY 4.0. Dinosaur
images are from Wikimedia Commons; each is credited on the card with its
author and its own licence.
