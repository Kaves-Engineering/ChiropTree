# Claude Code fetch checklist — bat echolocation project

99 blocked or unretrieved sources across 21 regional batches, sorted by **what tool actually unblocks each one**. Machine-readable version: `CLAUDE_CODE_FETCH_CHECKLIST.csv` (has a `status_todo` column to tick off).

Everything here failed for a *mechanical* reason — a binary file format, a bot wall, a paywall, or an unresolved citation — not because the science doesn't exist. None of it can be recovered by re-running the same web fetches.

## How to use this

Work top down. **Tier 1 is where nearly all the value is**: 8 files, mostly a single `curl` + `unzip`/`openpyxl` away, that between them would roughly double this project's measured-species coverage. Tier 5 is 42 items that are mostly just species-count references and can be ignored unless you want completeness.

Rules carried over from the project schema — please keep these:
- Never write a `measured_*` value you haven't actually read. Use `value_exists_unretrieved` if you can see it exists but can't extract it.
- Never write `unknown_no_data` from a family- or review-level statement. It requires a species-name search that returned nothing, plus a `last_searched` date.
- Record `n`, dispersion, `recording_context` and `region` alongside every value. Release calls, hand-held calls and free-flying calls are not interchangeable — this project found ~20-50 kHz discrepancies in the same species traced purely to recording method.
- Keep `verified_by` empty unless a human actually checked it. Every row in the project is currently unverified, and that's honest.

---

## TIER 1 — Binary files (8 items). Highest value, lowest effort.

These are open-access. They failed only because my fetch tool returns `.xlsx`/`.zip`/`.docx` as unparseable bytes. On a desktop these are trivial.

| # | Source | Region | What it unlocks |
|---|---|---|---|
| 1 | **EuroBaTrait 1.0** — figshare `10.6084/m9.figshare.21777161.v2` | Europe | **The single biggest win in the project.** 14 acoustic traits for 46 of 47 European species (98%), from 1.35M calls. Europe currently sits at 32/47 measured. |
| 2 | **South Asia Supp. Material 3** — `threatenedtaxa.org/.../download/9550/10560` | South Asia | Already open and *partially* fetched — my fetch truncated at ~1/3. Needs pagination only. 299 observations, 86 species; only 18 currently have numbers. |
| 3 | **Colombia Darwin Core Archive** — `ipt.biodiversidad.co/sib/archive.do?r=mamiferos_col` | Colombia | 222 species — the world's most bat-diverse country, and the only major region here with a known denominator but **no named species list**, so no coverage audit exists. `unzip`, read `taxon.txt`. |
| 4 | **African bat database** — figshare `10.6084/m9.figshare.26363308.v5`, mirror `github.com/kanead/Bat_database` | All Africa | 266 sub-Saharan species, modern taxonomy. **All six African batches currently lack a named checklist.** GitHub API was rate-limited during the project; a plain clone works. |
| 5 | **Sonozotz Dryad deposit** — `10.5061/dryad.95x69p8g6` | Mexico | 69 Mexican species. The paper was fetched (species + sample sizes already ingested); every parameter value is in this deposit. Converts Mexico from a list into data. |
| 6 | **Vietnam Table S1** — linked from `nature.com/articles/s41598-024-72436-6` | Mainland SE Asia | 88 species already have call-type classification ingested; this adds the full quantitative tables. |
| 7 | **China supplementary S1–S4** — four `.xlsx` on `media.springernature.com`, URLs in `eastasia_sources.csv` | East Asia | 135 species, 64 with published parameters. Article body is paywalled but **these four data files are not**. Would take China from zero numeric values to best-covered in Asia. |
| 8 | **Argentina Supp. 1 (DOCX) + Supp. 3–6 (WAVs)** — `media.springernature.com`, URL in `southamerica_southerncone_sources.csv` | Southern Cone | Article paywalled, supplementary openly hosted. Supp. 1 is very likely the acoustic identification key itself. |

Also worth grabbing while you're in binaries: **Zambia Supplementary S1–S7** (`repository.up.ac.za/bitstreams/6df10c46-.../download`) — quadruples parameter depth for 22 species already in the dataset.

---

## TIER 2 — Needs a real browser (5 items)

Confirmed open access, blocked purely by bot detection (Incapsula/reCAPTCHA) against datacenter IPs. Your browser will load all of these normally.

| Source | Region | Note |
|---|---|---|
| **Pio et al. 2010**, Trinidad, Acta Chiropterologica 12:217–229 | Caribbean | 29 species, 5 families, 12 phyllostomids described for the first time. Likely the richest untapped Caribbean source. *(May be paywalled rather than merely blocked — check.)* |
| **Jennings et al. 2004**, West Indies, Acta Chiropterologica 6:75–90 | Caribbean | Confirmed open on BioOne's own metadata page. Failed 3× (direct, download endpoint, RG mirror). 119 bats, 12 species. |
| **Kofoky et al. 2009**, Madagascar, Acta Chiropterologica 11:375–392 | Madagascar | BioOne bot-blocked + ResearchGate HTTP 429. 15 species, 6 described for the first time. Madagascar's numeric values are almost entirely missing without it. |
| **Hackett et al. 2017**, Arava desert, Bioacoustics 26:217–235 | Middle East | Open author manuscript on Bristol's repository (947 downloads recorded), PDF specifically bot-blocked. 15 species covering a community shared with Jordan, Syria, Saudi Arabia. |
| **Miller & Ossa 2021**, Chile Lucid key — `keys.lucidcentral.org/keys/v4/bats/chile/` | Chile | Interactive JS key, unscrapeable but browsable. Same team's **Honduras** key (`.../bats/honduras/`) is equally relevant to Central America. |

---

## TIER 3 — Institutional access (19 items)

Genuinely paywalled. Needs your library login. Highest-value first:

1. **Obrist, Boesch & Flückiger 2004**, *Mammalia* 68:307–322 — 26 Swiss/European species. Underpins 12 unverified numbers currently in the Europe batch via Wikipedia's triplet.
2. **Russo & Jones 2002**, *J. Zool.* 258:91–103 — 22 Italian species; one of the two foundational European references.
3. **Walters et al. 2012 (iBatsID)**, *J. Appl. Ecol.* 49 — establishes *which European species are not acoustically separable*. Currently used at abstract level only.
4. **Monadjem, Taylor, Cotterill & Schoeman 2020**, *Bats of Southern and Central Africa*, 2nd ed. — cited by **all three** southern African batches as the standard reference. A book.
5. **Russ (ed.) 2021**, *Bat Calls of Britain and Europe* — chs. 8.15/8.16 are the only dedicated accounts for *Myotis crypticus* and *M. escalerai*.
6. **Parsons 1997**, *Can. J. Zool.* 75:1487–1494 — full per-population table for both extant New Zealand species; only anchor values (28/40 kHz) currently held.
7. **Mancina et al. 2012**, *J. Mammal.* 93:1308–1317 — 4 syntopic Cuban mormoopids; abstract only.
8. **Olmedo et al. 2026**, *Mammal Res.* 71:13 — 16 Argentine species + identification key.
9. **Teixeira & Jesus 2009**, *Acta Chiropterologica* 11(1) — only numeric source for *Pipistrellus maderensis*.
10. **Disca, Allegrini & Prié 2014**, *Vespère* 3:209–229 — 16 Moroccan species; the key North African reference.
11. **Ahmim et al. 2020**, *Bioacoustics* 29(5) — "first bioacoustics prospection of the bats of Algeria."

Remaining 8 are in the CSV (Jung & von Helversen 2007 emballonurids, Barclay et al. 1981 *Trachops*, Giménez et al. 2023 Patagonian *Histiotus*, Rodríguez-San Pedro & Simonetti 2013 Chile, Pye 1972, Jones & Rayner, Yovel et al., Iberian *Eptesicus*).

---

## TIER 4 — Resolve the citation first (25 items)

These reached the dataset through ResearchGate figure pages, session URLs, or secondary quotation. **The data may be fine; the provenance isn't.** Each needs its real citation confirmed before publication.

Flagged as actively uncertain:
- **S-BH-EXUMA** (Bahamas) — author, volume and year never resolved; only a ResearchGate ID.
- **S-CU-PHFA** (*Phyllops falcatus*, Cuba) — title confirmed, full citation not.
- **S-PNG-PHIM** (*Pharotis imogene*) — academia.edu hosting only; text truncated mid-value.
- **S-PNG-LP11** (Leary & Pennay 2011) — 8 PNG species whose **identities were never resolved**; recorded as an unnamed placeholder rather than guessed. Fetching the chapter names them.
- **S-NIMBA13**, **S-CM18 Table 2**, **S-AR-HIST23** — values or species assignments marked `medium` confidence.

---

## TIER 5 — Search-first (42 items)

Mostly national species-count references never independently chased (Thailand, Laos, Cambodia, Indonesia, Philippines, Japan, Mongolia, Guyana, Suriname, Venezuela). Low value per item — they refine denominators, not call data. Two exceptions worth doing:

- **Ochoa et al. 2000**, northern Venezuela — the only Venezuelan acoustic source identified; Venezuela (~174 species) contributes **nothing** to the project.
- **Tanshi et al. 2021**, Nigeria, *Acta Chiropterologica* 23:313–343 — ten new country records; likely the richest untapped West African source.

---

## Regions that would change most

| Region | Now | After Tier 1+2 |
|---|---|---|
| Europe | 32/47 measured | ~46/47 |
| China | 0 numeric values | ~64/135 |
| Mexico | 0 numeric values | 69 species |
| Colombia | no species list at all | 222-species audit possible |
| Africa (all) | no species list at all | 266-species audit possible |
| South Asia | 18 of 86 with numbers | ~86 |
| Vietnam | call types only | 87 with full parameters |
| Madagascar | 4 medium/low-confidence values | 15 species |

## Two things to re-run afterwards

1. **`MASTER_AUDIT_REPORT.md`** documents 5 real bugs found and fixed (genus-column corruption, meta-rows in species fields, undated gap claims, an orphaned citation, a coverage-percentage mismatch). Re-run those same checks after any bulk ingest — the meta-row and species-count-drift bugs in particular recurred three separate times during this project.
2. **`GLOBAL_SPECIES_GAP_TALLY.md`** currently reports **407 species confirmed missing across 739 audited** — but only 9 regions have a genuine name-by-name audit. Tier 1 items 3 and 4 (Colombia, Africa) would add ~490 species to the audited denominator and make the global figure meaningful for the first time.
