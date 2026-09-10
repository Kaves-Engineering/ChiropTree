# Regional species rosters

Named species lists used by `data/report_regional_call_gaps.py` to compute coverage.
These are **denominators, not measurements** — nothing here enters the call schema.

A roster earns a place here only if it is a published, citable list. A region with
measurements but no checklist stays out, so that coverage is never reported against a
denominator we invented.

| File | Source | Retrieved | Cached raw | SHA-256 of raw |
|---|---|---|---|---|
| `colombia_bats.csv` | Ramírez-Chaves HE et al. (2025). *Mamíferos de Colombia* v1.14. SiB Colombia / GBIF checklist, doi:10.15472/kl1whs. Darwin Core Archive, `taxon.txt`, order = Chiroptera. | 2026-09-09 | `data/raw/rosters/mamiferos-de-colombia-dwca.zip` | `10d2013c6c587477bd05b6bd5a17c9f120a17a1af05dae3ec8e9bc7c0ce3cfe6` |
| `africa_bats.csv` | Monadjem A et al. (2024). African bat database. *Scientific Data* 11:1309. Figshare deposit `10.6084/m9.figshare.26363308`, file *African Bat Database_V2_26 July 2026.csv*. | 2026-09-09 | `data/raw/rosters/african-bat-database-v2.csv` | `9dbf70517a288ae6c40cc6b064394ec07998784b4b8caa0a0fe2e793ee1caa8c` |
| `vietnam_bats.csv` | Győrössy D et al. (2024). The calls of Vietnamese bats. *Scientific Reports* 14:23335, Supplementary Table S1. | 2026-09-09 | `data/raw/gyorossy-2024-vietnam-table-s1.xlsx` | `5c3f860d1b976bc1f821a84c76597fb7c68917ba2361c0eebc525e5f6e971168` |

### Added 2026-09-10, from GBIF

The Asian Bat Call Database datasets (Hungarian NHM + SEABCRU, GBIF-BIFA project
BIFA04-24) are **occurrence records, not measurements** — see the fetch report. What they do
give is a named species list for regions that had none, so they are used only as rosters.
Each is a recording cohort, never a national checklist, and the roster_scope string says so.

| File | GBIF datasets | Species |
|---|---|---|
| `indonesia_bats.csv` | MZB Indonesian bat call library (`10.15468/vytnyb`), Bukit Barisan Selatan (`10.15468/emgg92`), Echolocating bats of West Java (`fa9940cd`) | 51 |
| `malaysia_bats.csv` | Penang Island (`10.15468/tn7zxw`), Langkawi (`c76e7c47`), HNHM Asian Bat Database (`10.15468/zkfx5b`) | 45 |
| `taiwan_bats.csv` | Reference call of insectivorous bats in Taiwan (`7d4b8ea4`) | 17 |

Archives are cached under `data/Fetch/raw/gbif/`. Names are reduced to the binomial: author
strings and subspecies epithets are dropped, and a record whose rank is not species is skipped.

Two country rosters were **deliberately not created**. The same datasets yield only 6 named
species for Cambodia and 26 for China, against real faunas several times larger. A coverage
percentage against a denominator that small says more about the dataset than about the
country, so publishing one would be worse than publishing nothing.

## Decisions made while deriving these

**Colombia** — 222 Chiroptera of 553 mammal taxa, matching the count the checklist itself
advertises. Taken as a national checklist.

**Africa** — the database is an occurrence table, not a checklist, so the roster is its
distinct binomials: 312 names, of which **20 carry an open `cf.` qualifier and are
excluded**, leaving 292. A `cf.` record is an explicit statement of uncertainty about the
identification; counting it as a species would inflate the denominator with names the
authors did not claim. Scope is sub-Saharan Africa, not the continent — North African
faunas are absent from the source.

**Vietnam** — a recording cohort, not a national checklist. Table S1 lists what ChiroVox
holds, so the denominator is "species with a Vietnamese recording in ChiroVox" and the
roster_scope string says so.

## Verified, not added

The Sonozotz Dryad deposit (`data/raw/sonozotz-2020-metadata.xlsx`, SHA-256
`5c0c5e4015aa12441fb4127e96b27e2fa4e999c2f0ae2bff137184a443b89265`) lists exactly the same
69 species as the existing `mexico_sonozotz_species.csv` in the upload archive — no names
in either direction. The archive roster is therefore confirmed against its primary source
and was left as it is.
