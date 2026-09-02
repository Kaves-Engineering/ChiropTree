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
