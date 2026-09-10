# African echolocation data audit — 2026-09-08

## Scope

This audit checks every current measurement CSV in `data/calls/` against the
MDD taxonomy included in this repository. A row is African-linked when its MDD
taxon's `continentDistribution` contains `Africa`; this includes species shared
with Asia. The five non-measurement support files are excluded:
`expected_ranges.csv`, `family_call_defaults.csv`, `genus_call_defaults.csv`,
`regional_coverage_summary.csv`, and `regional_missing_species.csv`.

It is a data-integrity and coverage audit. It is not a claim that every
publication table has been visually re-transcribed in this pass; that is a
separate, source-by-source extraction-completeness review.

## Result

- 1,518 African-linked measurement rows
- 132 distinct species whose MDD distribution includes Africa
- 16 source CSVs containing African-linked rows
- 0 rows with a blank or unknown MDD ID
- 0 rows lacking a locator, reference record, or method record
- The structured-data build and release validator pass (6,064 measurement rows
  across all regions, 2026-09-08).

The project's strict Africa-only tracker uses `continentDistribution == Africa`,
not `contains Africa`; it therefore reports 93 structured species of 290 and
197 without records. The difference is shared-range taxa, such as
*Otomops harrisoni* (`Africa|Asia`), not a discrepancy in the CSV audit.

## African-linked source files

| Source CSV | Measurement rows | Observations | Species |
|---|---:|---:|---:|
| `bakwo-fils-2018.csv` | 5 | 1 | 1 |
| `castro-2024.csv` | 455 | 91 | 90 |
| `collen-2012.csv` | 818 | 105 | 104 |
| `denzinger-2001.csv` | 8 | 2 | 1 |
| `goerlitz-2010.csv` | 8 | 2 | 2 |
| `goodman-2011.csv` | 10 | 2 | 2 |
| `grunwald-2024.csv` | 36 | 9 | 9 |
| `ing-2016.csv` | 12 | 2 | 1 |
| `kofoky-2009.csv` | 25 | 5 | 5 |
| `monadjem-2011.csv` | 20 | 4 | 3 |
| `obrist-2004.csv` | 56 | 14 | 14 |
| `patterson-2018-otomops.csv` | 8 | 2 | 1 |
| `patterson-2025.csv` | 6 | 2 | 2 |
| `seibert-2015.csv` | 17 | 2 | 1 |
| `taylor-boyd-2025.csv` | 10 | 1 | 1 |
| `webala-2019.csv` | 24 | 8 | 2 |

## Taxon mapping result

All African-linked rows resolve to a current MDD ID. Non-exact mappings are
retained explicitly as `synonym_via_mdd` or `manual`, rather than silently
rewriting source names. They are concentrated in the broad legacy
compilations (`collen-2012`, `castro-2024`) and in documented modern genus
changes such as *Chaerephon* → *Mops*, *Emballonura* → *Paremballonura*, and
*Hipposideros cyclops* → *Doryrhina cyclops*.

## Follow-up needed

The structural audit does not establish that every numeric row in each source
table is already imported. The next stage is to compare each accessible
source table with its CSV, beginning with the broad source files
`collen-2012.csv` and `castro-2024.csv`, then each African regional study.
