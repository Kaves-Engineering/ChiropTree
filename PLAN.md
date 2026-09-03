# Chiroptree implementation plan

## Scope and decisions

Build a static, offline-capable Chiroptree. Keep the bat page as the master
for shared UI code. The marine page remains a generated derivative and must
keep building at every stage.

Use MDD IDs for all taxon links. Keep the imported source files, curated call
records, and release manifest as reviewable text. Generate SQLite, browser
JSON, image manifest, and site output from those inputs. Do not commit a
binary SQLite database as the only reviewable record.

Use CC0, CC-BY, and CC-BY-SA images only. GitHub Pages is the production
deployment. Limit the optional image pack to 60 MiB.

## 1. Lock down current behaviour

1. Add fixtures for a representative bat from each family, a taxon absent
   from the visual tree, a Danish name, a GBIF country supplement, a
   family-level call guide, and a species note.
2. Make `build.sh` deterministic and test both generated pages. Check that no
   `INLINE` directive remains, expected data is present, and the marine page
   generator still succeeds.
3. Record the current MDD version, source URL, checksum, species, genus, and
   family counts in a machine-readable release manifest.

Done when a clean checkout can build both pages and the checks catch missing
or stale input data.

## 2. Build the data pipeline beside the existing JSON

1. Add one importer that reads a pinned MDD CSV and creates a temporary SQLite
   database. Store MDD ID, accepted name, rank fields, parent links, source
   version, and checksum.
2. Add schema migrations and validators. Treat blank optional ranks as valid.
   Reject duplicate MDD IDs, broken parent/rank links, duplicate display keys,
   unknown map countries, and export/count mismatches.
3. Export the current page-shaped taxonomy JSON from SQLite. Run it beside the
   existing file and compare IDs, ranks, counts, and country distributions.
4. Keep raw downloads out of Git history. A release manifest must identify the
   exact upstream file and checksum, and CI must be able to fetch or restore
   it from a declared release asset.

Done when the generated taxonomy file is equivalent to the current data for
the pinned MDD release. Switch the bat and marine builders only after that
comparison passes.

## 3. Remove duplicated taxonomy state

1. Replace `ATLAS`, `SP`, and handwritten family/genus/species counts with a
   generated display-tree export.
2. Keep a small, explicit display-layout file only for ranks or phylogenetic
   placement MDD does not provide. Validate every imported taxon has a display
   placement. Render a visible unplaced group during development and fail a
   release build if it is non-empty.
3. Make tree navigation, search, cards, counts, and country filtering read
   the same exported records.
4. Update the marine-page generator and its data builder to use the shared
   exporter contract, rather than copying another taxonomy representation.

Done when no handwritten taxon list controls the bat tree and the marine
build passes from the same shared data code.

## 4. Make names and call claims auditable

1. Replace Danish-name lookup keys based on scientific-name strings with MDD
   IDs. Preserve GBIF match key, matched name, fallback method, source,
   retrieval time, and every returned Danish name.
2. Move call data into reviewable records with taxon ID, parameter, range,
   unit, context, evidence scope, and citation locator. Import it into SQLite.
3. Separate direct species measurements from genus and family guides in both
   data and UI. Retain the current hand-written species prose only if it has a
   cited editorial source. Otherwise label it as editorial note or remove it.
4. Add validation that every displayed numeric measurement has a source and
   that inherited values cannot be rendered as species measurements.

Done when each displayed call value links to its evidence, and no Danish name
silently disappears after a successful prior match without being reported.

## 5. Replace live photos with versioned local media

1. Define a deterministic selector for exact accepted-name iNaturalist taxa,
   then eligible research-grade observations. Restrict it to approved
   redistribution licences.
2. Download one bounded WebP thumbnail per eligible species. Record source
   URL, provider asset ID, author, licence, attribution text, retrieval time,
   dimensions, and source and output hashes in a JSON manifest.
3. Add a local placeholder for unavailable images. Remove runtime iNaturalist
   calls as a required dependency, while retaining source links and attribution
   in the card. When no local thumbnail exists and the browser is online,
   optionally fetch an exact-taxon iNaturalist fallback. Accept CC0, CC-BY,
   and CC-BY-SA only. Show its attribution immediately and cache both image and
   metadata for later offline use. Card content must not wait for this request.
4. Retain a valid prior thumbnail if refresh fails. A new release may replace
   it only after validation. Test missing images, invalid licences, corrupt
   files, and interrupted refreshes.

Done when a built page never needs iNaturalist to render a card, and every
published thumbnail has complete attribution.

## 6. Ship a release-aware PWA

1. Stop inlining large release data into one HTML file for the PWA build.
   Publish hashed, versioned assets under a release directory. Keep the
   existing single-file build only if the selected production host still needs
   it, and verify its size remains practical.
2. Add a web manifest and service worker. Precache the shell, core data, map,
   and placeholder. Offer image-pack download as a user action, not a default
   mobile download.
3. Download a new release into a separate cache, verify its manifest, then
   switch the active release. On failure, retain the prior working release.
   Show installed release version and offline-pack state.
4. Test first install, offline restart, incomplete image-pack install, cache
   eviction, first and repeated live-image fallback, rejected licences, and
   update failure with the static server used in CI.

Done when taxonomy, search, map, names, calls, and installed images work with
the network disabled, and a failed update leaves the prior release usable.

## 7. Automate reviewable releases

1. Add a scheduled workflow for the selected production CI. It checks MDD
   release metadata and checksum first, and exits without changes when the
   pinned release is current.
2. On change, run import, reconciliation, derived exports, media validation,
   both page builds, and offline smoke tests in a clean workspace.
3. Produce a text change report covering added, removed, renamed, moved, and
   unresolved taxa; name-match regressions; call-source gaps; image and
   licence changes; output sizes; and validation failures.
4. Create a merge request or pull request. Never publish from the scheduled
   job. Publishing follows an approved merge and tags the data release used by
   the build.

Done when a dry run creates a reviewable proposed release, an unchanged MDD
release changes nothing, and an approved release deploys once.

## Release gates

- MDD source version and checksum match the release manifest.
- Every displayed taxon has one MDD ID and valid display placement.
- Browser exports and SQLite-derived counts agree.
- Map country names resolve.
- Displayed call values have valid units, evidence scope, and citation.
- Cached images have allowed licences, attribution, manifest entries, and
  matching files.
- Bat and marine outputs build, load, and pass offline smoke tests.
- The optional image pack stays within the approved size limit.
