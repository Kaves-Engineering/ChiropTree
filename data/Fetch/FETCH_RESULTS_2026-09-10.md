# files4.zip — ingest and fetch round, 2026-09-10

`data/echolocation/files4.zip`: 129 files, of which **78 are new and 11 changed** against the
three earlier archives. Working copies of its two checklists are in this directory;
`CLAUDE_CODE_FETCH_CHECKLIST_v2.csv` now carries an outcome for 29 of its 49 items.

## What went into the page

`MASTER_call_records.csv` consolidates the 43 batch worksheets into one schema, so it
supersedes the old per-batch importer. `data/build_master_upload_calls.py` replaces
`import_echolocation_upload.py`, which has been removed.

| | |
|---|---|
| Master rows | 2,857 |
| Admitted as measurements | **1,534**, across **23 references**, 340 species |
| Coverage | 578 → **604 species measured** (38.2% → **39.9%**) |
| Card density | 53 → **65 rich**, 36 basic unchanged |
| Store total | 8,838 → **9,530 rows** from **58 sources** |

**19 new references**, the largest being Barataud et al. 2013 (French Guiana, 246 rows),
McArthur & Khan 2021 (Borneo, 138), Pennay & Lavery 2017 (Solomon Islands, 120) and
Monadjem et al. 2017 (Eswatini, 91). Each has a reference record, a method record and a
stated licence.

## What was refused, and why

The archive carries a great deal that this project should not publish as measurement. The
gates are in `data/master_upload_lib.py`; 1,323 rows were rejected:

- **284** `value_exists_unretrieved` — an acquisition task, not a value.
- **174** traits with no home in the registry, each with a written reason. Source level was
  declined because the archive carries no measurement basis, and a source level without one
  is not comparable.
- **69 + 21 + 12** rows the archive itself marks `join_confidence` exclude / low / genus-only.
- **62** `identification_threshold` — classifier decision boundaries, which the archive's own
  README warns look like measurements and are not.
- **50** `unknown_no_data`, **33** tertiary aggregators (Wikipedia, EoL/ADW, BioNumbers).
- **36** paywalled, **19** heterodyne field-key bands, **18** already-inferred values.

**29 further rows were refused on provenance**, from 11 sources whose citation the archive
itself flags — "resolve to the primary citation before publishing", a bare session URL, a
ResearchGate figure, or a citation whose linked paper is a different paper. A1 requires a
value to resolve to a publication and a place within it. These are the archive's own Tier F.

**308 rows were deferred, not imported.** Six references already have a CSV transcribed from
the primary source with real locators — "Table 2, *Doryrhina camerunensis*, Kakamega forest,
hand-held female" — against a hashed PDF. The archive's locator is a worksheet record id.
Overwriting the first with the second would be a downgrade, so those rows wait in
`data/calls/unresolved/master-upload-deferred.json` for a human merge.

## Three things the consolidation had silently dropped

Caught by comparing the master against the batch worksheets it was built from:

1. **`call_phase`** — present in seven batch files, absent from the master schema. Recovered
   for 893 rows. Without it the whole store fell to `minimal` density.
2. **`call_type_variant`** — populated in five batch files, absent from the master.
3. **Record ids were reassigned** (`BAT01373` where the batch said `NA0001`), so the two
   cannot be joined by id at all. The join is on species + trait + value + unit instead.

One batch records `call_phase = release`, which is a recording context and not a phase. It is
mapped to `unspecified`; the context was already carried separately, and letting it through
would have described the call by how it was recorded.

## Tier A (GBIF) — fetched in full, and it does not contain what the checklist expected

All seven Asian Bat Call Database datasets were retrieved, plus three more found on the parent
project (Taiwan, Belarus, Andaman Islands). **3,582 occurrence records, and not one call
parameter.**

These are occurrence records with ChiroVox media ids (`A001913`), not measurements. Belarus
has a MeasurementOrFact extension, but it holds "number of calls" — an activity count. So
"fixes Indonesia, Cambodia, Yunnan" does not hold: the recordings exist, but the numbers
would have to be measured from the audio.

What they do give is a named species list where there was none. New rosters: **Indonesia 51**,
**Malaysia 45**, **Taiwan 17**. Cambodia (6 named species) and China (26) were deliberately
**not** made into rosters — a coverage percentage against a denominator that small describes
the dataset, not the country.

ChiroVox itself is the common missing piece for Tier A, the Vietnam table and Sonozotz alike.
It has no API: every path returns the same JavaScript shell.

## Coverage audit — now 12 rosters, 1,424 named species

| Region | Named | Measured | Missing |
|---|---:|---:|---:|
| Sub-Saharan Africa | 292 | 131 | 127 |
| Colombia | 222 | 108 | 114 |
| Peru | 189 | 98 | 91 |
| Brazil | 186 | 111 | 75 |
| Ecuador | 171 | 83 | 88 |
| Vietnam | 90 | 54 | 36 |
| Mexico | 69 | 50 | 19 |
| Indonesia *(new)* | 51 | 34 | 8 |
| Europe | 47 | 41 | 6 |
| Malaysia *(new)* | 45 | 41 | 4 |
| North America | 45 | 43 | 2 |
| Taiwan *(new)* | 17 | 9 | 8 |

## A named open item closed

The v2 checklist's Tier G flagged *Thyroptera tricolor* (51 vs 123 kHz) and *T. discifera*
(53 vs 112.5) as "almost certainly an unlabelled fundamental-vs-second-harmonic mismatch."

Confirmed, and now resolved. With Barataud 2013's harmonic-labelled values in, both agree:
tricolor 53.09 vs 51.0 kHz, discifera 53.0 vs 52.5 kHz, both on the fundamental. Because the
archive populates `harmonic_n`, the harmonic-aware expectation check now explains **30**
apparent outliers that way. The genuine unexplained set is unchanged at 16 — the master
ingest introduced no new out-of-range values.

## Also fetched

- `raw/PMC3663840.xml` — *Coelops frithii*, the low-duty-cycle hipposiderid. Full text, not yet mined.
- Six taxonomy synonyms resolved (*Afronycteris nana*, *Neoromicia nana*, *Anoura caudifera*,
  *Eptesicus anatolicus*/*isabellinus*, *Kerivoula papuensis*), recovering 18 rows. Three were
  refused as genuine splits or unsettled synonymies and are recorded with the reason in
  `call_import_lib.py` so a later pass does not "fix" them by guessing.

## Still blocked

| Item | Why |
|---|---|
| Vietnam urban bats (MDPI) | 403 to this IP; needs a real browser |
| Schmieder et al. 2010 | PMC2936139 is not in the Europe PMC open-access subset |
| Phauk et al. 2013 (Cambodia) | no Crossref record; the journal appears not to deposit DOIs |
| Pio 2010, Kofoky 2009 | confirmed genuinely closed, not bot-walled — both belong in Tier E |
| Hackett 2017 | 403 on the only OA copy; correct DOI is 10.1080/09524622.2016.1247386 |
| Tier E (14 items) | institutional access |

## Verified

`build_master_upload_calls.py`, `build_calls.py` (9,530 rows / 58 sources),
`check_expectations.py`, `report_regional_call_gaps.py`, `build_release_manifest.py`,
`validate_release.py`, `sh build.sh` and `smoke_test.py` all pass.

`validate_release.py` caught one real defect on the way: Barataud's URL was `http://`, and the
release rule requires `https://`. The site serves the same PDF over https (2.9 MB, verified),
so the reference was corrected rather than the rule relaxed.
