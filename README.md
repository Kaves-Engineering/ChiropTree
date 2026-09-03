# Tree of Bat Life

A lightweight, static tree and range map for bat (Chiroptera) taxonomy,
phylogenetic placement, and echolocation call characteristics. Built for lab
use, with no backend required.

Live site (GitLab Pages): https://chiroptree-911c6f.pages.sdu.dk/

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
  every species record: Robinson-projected, simplified SVG path strings plus
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

## The marine mammal pages

A parallel set of pages covering marine mammals, built from the same MDD
release by the same mechanisms. They are separate files throughout — nothing
here changes what the bat pages show.

- **`marine-mammal-tree.html`** — **generated, do not edit by hand.**
  `chiroptera-tree.html` is the master; this page is stamped out of it by
  `data/build_marine_mammal_page.py`, which copies the skeleton verbatim —
  CSS, markup and every line of interaction code — and swaps only content:
  the data blocks, the data-file paths, and the strings that name the animals.
  The two pages link to each other from the top nav. Change the bat page,
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

`build.sh` bundles the JSON into one self-contained HTML file:

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

The bundling exists because the site is published behind GitLab Pages access
control: the page itself loads after sign-in, but a `fetch()` for a data file
can be bounced to the cross-origin sign-in flow and fail, leaving the page up
with no data. With the data inside the HTML there is nothing left to fetch.

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
