# Tree of Bat Life

A lightweight, static lookup tool for bat (Chiroptera) taxonomy, phylogenetic
placement, and echolocation call characteristics — built for lab use, no
backend required.

## What's here

- **`index.html`** — the lookup tool. Search/filter across all 1,514 currently
  recognized bat species; each entry shows its taxonomic chain (order →
  suborder → family → genus), IUCN status, distribution, and echolocation
  call parameters where known.
- **`chiroptera-tree.html`** — a standalone illustrated essay on bat taxonomy
  and evolution (companion piece, not required by the lookup tool).
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

The page loads its data via `fetch()`, so it needs to be served over HTTP —
opening `index.html` directly as a `file://` URL will fail silently on most
browsers.

```
uv run python -m http.server 8000
```

Then open http://localhost:8000/index.html.

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
