# Fetch results — 2026-09-09

Attempted every Tier 1 and Tier 2 item in `CLAUDE_CODE_FETCH_CHECKLIST.csv`. Raw bytes are in `raw/`.
`status_todo` in the CSV now carries the per-item outcome.

## Retrieved

| Item | File | Content |
|---|---|---|
| S-SSA-FIGSHARE (Africa DB) | `raw/africa_bat_db_v2.csv` (3.2 MB) | 18,409 occurrence records, **312 species**, 12 families. Derived: `raw/africa_bat_checklist.csv` (family, species, n_records, countries). Figshare REST API worked where the DOI landing page did not. |
| S-CO-DWCA (Colombia) | `raw/colombia_dwca.zip` (extracted to `raw/colombia/`) | Darwin Core Archive, 553 mammal taxa. Derived: `raw/colombia_bat_checklist.csv` — **222 Chiroptera**, exactly the expected denominator. |
| S-VN24-TABLES1 (Vietnam) | `raw/vn24_TableS1.xlsx` | 1,042 recordings, **90 species**. |
| S-SONOZOTZ-DRYAD (Mexico) | `raw/sonozotz/Metadata_Sonozotz.xlsx` | 2,323 recordings, **69 species**. Dryad's file endpoint 401s and the web download is behind an Anubis proof-of-work wall; `/api/v2/versions/68177/download` returns the zip unauthenticated. |
| S-JENN04 (West Indies) | `raw/jennings04.pdf` | Full 17-page paper. Bronze OA on BioOne; a browser User-Agent + `Referer: bioone.org` is sufficient. |
| S-AR25 (Argentina) | `raw/ar25_supp1.docx` | Supplementary 1, retrieved — but see correction below. |

## Two corrections to the checklist's expectations

**1. Vietnam S1 and Sonozotz are recording metadata, not measurement tables.**
Neither file contains a single frequency, bandwidth or duration column.

- Vietnam S1 columns: ChiroVoxUID, family, species, locality, territory, country, method, call type, recording type, device manufacturer/model, recorded by.
- Sonozotz columns (58): collector/library/locality/date/UTM, family/genus/species, sex, age, forearm, weight, ID certainty, voucher, and a full recording-method block (technique, environment, flight height, sampling rate, detector, microphone).

The numeric parameters are not in these deposits. For Vietnam they sit in ChiroVox against the UIDs listed here; for Mexico they are in the Sonozotz library itself, not the Dryad metadata sheet. So "converts Mexico from a list into data" does not hold as written — this deposit converts Mexico into a list *with method provenance*.

That said, the method provenance is worth having on its own terms. Per the design doc's insistence that `recording_condition` never be null-by-default, both files pin it down species by species:

- Vietnam: Enclosure 489, Hand held 345, Hand release 119, **Free fly 46**, Container 29, Emergence 8.
- Sonozotz: Hand release 1,476, Zip-lining 694, Inside the bag 116, Flight cage 23.

Almost none of either corpus is free-flying wild. Any value later ingested from these two libraries should carry that flag — this is precisely the ~20–50 kHz confound the project has already been bitten by.

**2. Argentina Supp. 1 is not the identification key.**
It contains Table S1 (9 sampling sites), Table S2 (linear discriminant coefficients), and Tables S3–S4 (DA classification matrices). The per-species parameter table remains in the paywalled article body. Supp. 3–6 are four WAV files. Still a Tier 3 library-login item for the actual numbers.

## Still blocked

| Item | Why |
|---|---|
| S-IL-HACKETT17 (Arava desert) | The Bristol repository PDF is the only OA copy anywhere (confirmed via Unpaywall) and returns 403 from this IP under every UA/Referer combination. Needs a real browser. **The checklist's DOI was wrong**: correct DOI is `10.1080/09524622.2016.1247386`. |
| S-TT-PIO10 (Trinidad) | Not bot-blocked — **genuinely closed**. OpenAlex and Unpaywall both report `oa_status: closed`, no repository copy. Reclassify Tier 2 → Tier 3 (library login). |
| S-MG09 (Kofoky, Madagascar) | Same: confirmed `closed`, no repository copy. Reclassify Tier 2 → Tier 3. Existing `kofoky-2009.csv` stands as-is. |

## Already done before this pass

`S-EUROBATRAIT`, `S-SA-SUPP3`, `S-CN21` and `S-ZM25-SUPPL-2` are already ingested as
`eurobatrait-2023.csv` (1,264 rows), `srinivasulu-2025-southasia.csv` (181), `lopez-bosch-2021-china.csv` (909)
and `taylor-boyd-2025.csv` (10). No re-fetch needed.

## Not yet done

Nothing here has been ingested into the call schema — these are raw fetches plus two derived checklists.
The two checklists are directly usable now for the coverage audit that Tier 1 items 3 and 4 existed to enable:
Colombia 222 and Africa 312 named species, against which `report_regional_call_gaps.py` can run for the first time.
Tiers 3–5 were not attempted; Tier 3 needs your library login and Tier 4 needs citation resolution rather than fetching.

---

# Coverage audit — first run for Colombia and Africa

`data/report_regional_call_gaps.py` now reads rosters from two sources: the upload archive as
before, plus `data/calls/rosters/` for lists derived from separately fetched checklists.
Added `colombia_bats.csv` (222) and `africa_bats.csv` (292; the 20 `cf.` records are excluded —
they are uncertainty flags, not species claims).

| Region | Named | Measured | No laryngeal echo. | Still missing | Unresolved |
|---|---|---|---|---|---|
| **Colombia** *(new)* | 222 | 104 (47%) | 0 | **118** | 8 |
| **Sub-Saharan Africa** *(new)* | 292 | 130 (45%) | 34 | **128** | 4 |
| Brazil | 186 | 105 | 0 | 81 | 4 |
| Ecuador | 171 | 82 | 0 | 89 | 18 |
| Peru | 189 | 94 | 0 | 95 | 19 |
| Europe | 47 | 41 | 0 | 6 | 6 |
| North America | 45 | 43 | 0 | 2 | 0 |
| Mexico | 69 | 50 | 0 | 19 | 6 |

Audited denominator rises from 707 to **1,221 named species**; 572 named gaps across 8 rosters.
Europe also moved 35 → 41 measured, reflecting the EuroBaTrait ingest since the last run.

## A5 fix made while running this

Africa's first pass reported 162 missing, of which **35 were Pteropodidae**. But
`family_call_defaults.csv` already asserts, with sources, that Pteropodidae have no laryngeal
echolocation — design-doc A5 makes that a positive claim, not missing data. Counting it as a
coverage gap overstated the Africa deficit by more than a fifth.

The reporter now reads `laryngeal_echolocation` from the family defaults and `echolocation_mode ==
non_laryngeal_clicks` from the genus defaults, and emits a distinct `no_laryngeal_echolocation`
status in its own summary column. *Rousettus* is correctly excluded from the exemption and remains
a genuine gap. Africa's real deficit is **128, not 162**. No other region contains pteropodids, so
nothing else moved.

## Where the remaining gaps are

- **Colombia** — Phyllostomidae 84 of 118. The gap is overwhelmingly one family, and phyllostomid
  calls are low-intensity and under-recorded, so this will not close from general acoustic surveys.
- **Africa** — Vespertilionidae 56, Molossidae 22, Rhinolophidae 18, Miniopteridae 11.

## Taxonomy names that did not resolve to MDD

Small enough to fix by hand; these are mapping gaps, not data gaps.

- Colombia (8): *Molossops temmincki*, *Dermanura gnoma*, *Lophostoma occidentalis*,
  *Platyrrhinus chocoensis*, *Platyrrhinus nigellus*, *Vampyressa sinchi*, *Vampyriscus nymphaea*,
  *Eptesicus miradorensis*
- Africa (4): *Mops leonis*, *Rhinolophus gorongosae*, *Rhinolophus rhodesiae*, *Scotophilus damarensis*
  (*Epomophorus minimus* also fails to resolve but is now covered by the Pteropodidae assertion)

Several look like orthographic variants or recent splits — *Molossops temmincki* vs MDD
*temminckii* is almost certainly just a spelling difference.

## Note

`check_expectations.py` still reports the same 18 pre-existing out-of-range values
(`data/calls/checks/out-of-range.md`). Unrelated to this work — no measurements were added.

---

# Ingestion — Jennings 2004 is in the page

## What landed

`jennings-2004` is now a measurement source: **139 rows, 14 taxa, 14 MDD species**, built by
`data/build_jennings_2004_calls.py` from Table 1 of the cached PDF (SHA-256 pinned).

- Export: 575 -> **578 species measured**, 38.0% -> **38.2%** coverage.
- Card density: 42 -> **53 rich**, 17 -> 19 detailed.
- Eleven of the fourteen already had data, so most of the gain is depth and a second
  independent source rather than new species.

Every value carries its locator (`Table 1, pp. 79-80, <taxon> (<harmonic>)`), n bats, the
verbatim printed string, and `recording_condition = hand_release` — the bats were released
from the hand and recorded in free flight ~10 m away, which is not free-flying wild.

### Taxonomy

The paper uses 2004 trinomials. Four of its subspecies are accepted species in MDD today,
so each trinomial maps to exactly one current species — the authors identified to
subspecies precisely because *A. jamaicensis* subspecies differ in size and call frequency:

| Printed | Now |
|---|---|
| *P. parnellii portoricensis* | *Pteronotus portoricensis* |
| *A. jamaicensis schwartzi* | *Artibeus schwartzi* |
| *S. lilium angeli* | *Sturnira angeli* |
| *S. lilium paulsoni* | *Sturnira paulsoni* |
| *M. blainvillii* | *Mormoops blainvillei* (respelling) |

## The `harmonic` field, and what it fixed

§3.3 of the design doc specifies a per-measurement `harmonic`; it had never been
implemented. It is now a real column, validated as a positive integer with the fundamental
as 1, and it is part of both the duplicate key and the comparability key — so a frequency
read off the second harmonic no longer competes with the fundamental's, and the two can
never be silently averaged or flagged as divergent. It renders on the card as a small label
beside the parameter name: *Peak frequency · 2nd harmonic*.

Three things fell out of adding it:

**`yoh-2020` was encoding harmonics as fake call variants.** 324 of its 326 rows carried
`call_variant = "harmonic 3"` and so on, which made the card show four invented named calls
per species. `import_echolocation_upload.py` now writes the real column instead, and those
324 phantom variants are gone. `arias-aguilar-2018` picked up the same fix for 7 rows.

**`FIELDS` in the upload importer had drifted from `COLUMNS`.** It was a second hand-kept
copy of the same 29-column contract. It now imports `COLUMNS`, so a future column cannot be
added in one place and missed in the other.

**`check_expectations.py` was reporting harmonic artefacts as suspect data.** Its own
docstring lists "a harmonic confusion" as something it exists to catch, but it had no way to
tell one. It now rescales against the stated harmonic and separates those cases out:

- 5 new Jennings fundamentals (e.g. *Mormoops blainvillei* 27.5 kHz against a family band of
  45–95 kHz, which is 55 kHz on the second harmonic) are reported as explained, not suspect.
- 2 **pre-existing** false alarms — *Mesophylla macconnelli* and *Phyllostomus hastatus*,
  both `yoh-2020` — were cleared for the same reason.
- Genuine unexplained values: **18 -> 16**.

A cosmetic fix went in alongside: a `count` unit no longer prints, so it is "Dominant
harmonic 2", not "2 count" (27 pre-existing rows were affected).

## Rosters

`data/calls/rosters/` now holds Colombia (222), Sub-Saharan Africa (292) and Vietnam (90),
with `SOURCES.md` recording each list's citation, retrieval date, cached raw file and
SHA-256. Vietnam is a ChiroVox recording cohort, not a national checklist, and its
roster_scope says so.

**Mexico verified, not changed.** The Sonozotz Dryad deposit lists exactly the same 69
species as the `mexico_sonozotz_species.csv` already in the upload archive — no differences
in either direction. The existing roster is confirmed against its primary source.

Audit now covers **9 rosters / 1,311 named species**, 615 named gaps.

## Verified

`build_calls.py` (8,838 rows, 42 sources), `check_expectations.py`, `report_regional_call_gaps.py`,
`build_release_manifest.py`, `validate_release.py`, `smoke_test.py`, and `sh build.sh` all pass.
`public/data/calls/exports/calls.json` carries the new data, all six of the page's fetches
return 200, and the page's own `luCallFactHTML` was run against the built export — 42 facts
rendered without error, producing e.g.
`End frequency (fundamental) 10.0–17.0 kHz [Jennings et al. 2004] n=2`.

I could not drive a real browser (no Playwright in this environment), so the rendering check
exercises the page's actual fact-rendering function against the actual built data rather than
a live page.

## Still not ingested

- **Vietnam / Sonozotz** — metadata only; the numbers need ChiroVox (JS-rendered on
  OpenBioMaps, so it needs that backend API) and the Sonozotz library itself.
- **Argentina** — per-species values are in the paywalled article body.
- **Hackett 2017, Pio 2010, Kofoky 2009** — see the blocked table above.
- **Jennings Table 2** (mass, forearm, aspect ratio, wing loading for 300 bats) was left
  alone. `body_mass` and `forearm_length` are registry parameters, so it could be imported,
  but two taxa are split by sex there and it is morphology rather than call data.
