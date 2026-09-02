# Tree of Bat Life

A lightweight, static lookup tool for bat (Chiroptera) taxonomy, phylogenetic
placement, and echolocation call characteristics — built for lab use, no
backend required.

Live site (GitLab Pages): https://chiroptree-911c6f.pages.sdu.dk/ — this
serves `chiroptera-tree.html` as the homepage, with the standalone lookup
available at `/lookup.html`.

## What's here

- **`chiroptera-tree.html`** — the main page: an illustrated essay on bat
  taxonomy and evolution, a genus-by-genus browser, a species lookup in the
  search bar and drawer, and a clickable world map that lists every species
  confirmed present in whichever country you click. Deployed as the site's
  homepage.
- **`index.html`** — a standalone version of just the lookup tool. Search/
  filter across all 1,514 currently recognized bat species; each entry shows
  its taxonomic chain (order → suborder → family → genus), IUCN status,
  distribution, and echolocation call parameters where known. Deployed at
  `/lookup.html` on the live site.
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
  client-side at page load (see `luMergeCountrySupplement`/
  `mergeCountrySupplement` in the two pages) — additive only, never removes
  or overrides an MDD-asserted country, and untouched by re-running
  `build_taxonomy.py` against a new MDD release.
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
  the prose, the data blocks, and the data-file paths. The two pages link to
  each other from the top nav. Change the bat page, re-run the script, and
  the marine page inherits the change; every swap is anchored on an exact
  string and the build exits loudly if one stops matching, so the two cannot
  silently drift apart. Deployed as `/marine.html`.
- **`data/build_marine_mammal_page.py`** — does that stamping, and
  **`data/build_marine_mammal_data_blocks.py`** — holds what it stamps in.
  Everything structural in there (which genus sits in which subfamily or
  tribe, the species lists, every count) is derived from MDD; only the
  natural history prose and the coarse ecology tags are hand-authored, which
  is the same split the master page uses.
- **`marine-mammal-lookup.html`** — the lookup tool, mirroring `index.html`.
  Deployed as `/marine-lookup.html`.
- **`data/marine_mammal_taxonomy.json`** — 144 species, 18 families, 67
  genera, built by **`data/build_marine_mammal_taxonomy.py`**. Unlike
  Chiroptera, marine mammals are not a clade: the file is the union of
  Cetacea (102 spp., which MDD v2.5 nests inside Artiodactyla), Sirenia
  (5 spp.) and the pinniped families Otariidae/Phocidae/Odobenidae within
  Carnivora (37 spp.). Every species record carries a `lineage` field, and
  the three lineages are counted separately in `_meta`. The pages lead with
  that polyphyly rather than papering over it.
- **`data/marine_mammal_danish_names.json`** / **`..._gbif_country_supplement.json`**
  — same GBIF sources and same client-side merge as the bat pages, built by
  the matching `build_marine_mammal_*.py` scripts.
- **`data/marine_world_map.json`** — the range map. Built by the *same*
  `data/build_world_map.py` with `--marine`, which differs in one respect:
  it draws Antarctica instead of cropping it at 57°S. 28 of these species
  range there — blue, fin and minke whales, the Weddell, crabeater, leopard
  and Ross seals, the southern elephant seal — so the bat map's crop would
  silently swallow a quarter of the ranges. The map is correspondingly
  taller (viewBox height 405.8 vs 344.9); the page reads the height from the
  data, so nothing hardcodes it.

There is deliberately **no** marine equivalent of
`echolocation_reference.json`. Odontocetes do echolocate, and the essay says
so, but no comparable per-family reference was compiled — inventing call
parameters to fill the same card would have produced numbers that look
citable and are not.

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

`build.sh` bundles the JSON into the pages, so the built site is two
self-contained HTML files and needs no server:

```
sh build.sh          # writes public/index.html and public/lookup.html
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

The unbuilt `chiroptera-tree.html` / `index.html` in the repo root still load
their data via `fetch()`, so those need to be served over HTTP — opening them
as a `file://` URL fails silently on most browsers:

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
