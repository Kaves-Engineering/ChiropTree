# Claude Code checklist v2 — updated after the deep search

**49 actionable items**, replacing the 99-row v1 list. Shorter because it drops the low-value "resolve a national species-count reference" chaff and adds everything the deep search turned up — including the Asian Bat Call Database, which wasn't in v1 at all.

Machine-readable: `CLAUDE_CODE_FETCH_CHECKLIST_v2.csv`, with `status_TODO` / `fetched_by` / `fetched_date` / `result_notes` columns to work through.

Sorted by **what tool unblocks it**, then by species gain. Tiers A–C are ~60% of the total value and need no institutional access at all.

---

## Tier A — GBIF API (8 items). One script, no credentials.

`api.gbif.org` isn't in this container's network allowlist and `www.gbif.org` bot-blocks the fetch tool, so none of this was reachable. From your machine it's `rgbif` or a plain REST call.

The **Asian Bat Call Database** (Hungarian NHM + SEABCRU, GBIF-BIFA project BIFA04-24) has published national bat *call* datasets as Darwin Core records with taxonomy vetted by Gábor Csorba. Their own framing of the problem:

> "call descriptions from over 40% of the 270 echolocating species have been reported in literature, but **none of the recordings are accessible**"

| Dataset | Fills | DOI |
|---|---|---|
| MZB Indonesian bat call library | **Indonesia** — Java, Maluku, Sulawesi, W Papua | `10.15468/vytnyb` |
| Bukit Barisan Selatan | **Indonesia** — Sumatra | `10.15468/emgg92` |
| Echolocating bats of West Java | **Indonesia** | GBIF `fa9940cd-…` |
| HNHM Asian Bat Database | **Cambodia, Yunnan**, Malaysia, Vietnam | `10.15468/zkfx5b` |
| Penang Island | Malaysia | `10.15468/tn7zxw` |
| Langkawi | Malaysia | `bifa04-24-21` |
| NE Vietnam | Vietnam | GBIF `6814e124-…` |

Indonesia (~200+ species) is the project's largest single gap and currently holds **zero** records. Cambodia and Yunnan are also zero. Also check the parent project page for datasets beyond these seven.

## Tier B — Binary files (9 items). Download + parse locally.

All open access; all defeated by file format.

1. **EuroBaTrait 1.0** — figshare `10.6084/m9.figshare.21777161.v2`. **The single highest-value item in the project.** 14 acoustic traits, 46 of 47 European species, 1.35M calls. Europe is currently the *worst-covered major region* (28/47 measured) purely because it was built early from identification keys. This one file takes it from worst to best.
2. **China supplementary S1–S4** — four `.xlsx` openly hosted on `media.springernature.com` even though the article is paywalled. 64/135 species. China currently has zero numeric values.
3. **Colombia Darwin Core ZIP** — `ipt.biodiversidad.co/sib/archive.do?r=mamiferos_col`. 222 species. The only major region with a known denominator but no named list, so it has *no coverage audit at all*.
4. **African bat database** — figshare `10.6084/m9.figshare.26363308.v5`, mirror `github.com/kanead/Bat_database`. 266 species. **All six African batches lack a named checklist.**
5. **South Asia Supp. Material 3** — open, and *partially* fetched: my fetch truncated at ~⅓. Needs pagination only. 86 species, 18 currently have numbers.
6. **Vietnam Table S1** — quantitative tables are image objects; a downloadable spreadsheet is linked on the article page. 88 species already classified by call type.
7. **Sonozotz Dryad** — `10.5061/dryad.95x69p8g6`. All 69 Mexican species are currently `value_exists_unretrieved`.
8. **Zambia Supp. S1–S7** — full 20-parameter dataset vs the 5 currently held.
9. **Argentina Supp. 1 (DOCX)** — article paywalled, supplementary open. Likely *is* the acoustic identification key. The Southern Cone is 100% paywalled; this is its only opening.

## Tier C — Open, simply not fetched (5 items). Fastest wins.

- **Orozco-Lugo et al. 2013**, *Therya* `10.12933/therya-13-103` — **best value-to-effort item on the whole list.** 11 Mexican species with described pulses; Therya is fully open and this project has fetched it before.
- ***Coelops frithii*** (PLoS ONE, PMC3663840) — Taiwan is zero, and this is an ostensibly high-duty-cycle hipposiderid that consistently uses **low** duty cycle (7.7 ± 2.8%): a documented exception to the HDC/LDC split used throughout this project.
- **Schmieder et al. 2010** (Biology Letters, PMC2936139) — *Kerivoula pellucida* buzz calls at 250 kHz, the most broadband and highest-pitched tonal animal vocalization known.
- **Vietnam urban bats** (Diversity `10.3390/d13010018`) — MDPI, fully open.
- **Phauk, Phen & Furey 2013** — Cambodia is zero; the journal is open access.

## Tier D — Needs a real browser (5 items)

Confirmed open or semi-open, blocked by Incapsula/reCAPTCHA against datacenter IPs.

- **Pio et al. 2010** (Trinidad) — 29 species, 12 phyllostomids described for the first time. Richest untapped Caribbean source.
- **Jennings et al. 2004** (West Indies) — BioOne's own metadata page says open access. Failed three ways. Not a paywall, a bot wall.
- **Kofoky et al. 2009** (Madagascar) — 15 species. Madagascar's numeric data is currently 4 medium/low-confidence rows.
- **Hackett et al. 2017** (Arava desert) — open manuscript on Bristol's repository, 947 downloads, PDF specifically blocked. Its abstract reports the only candidate case of **acoustic character displacement** found anywhere in this project.
- **Miller & Ossa Lucid keys** — Chile and Honduras, interactive JS, browsable.

## Tier E — Institutional access (14 items)

Led by the two foundational European references, because Europe needs them most:

1. **Obrist et al. 2004** (26 Swiss species) — underpins 12 currently-unverified European numbers sourced via Wikipedia.
2. **Russo & Jones 2002** (22 Italian species).
3. **Walters et al. 2012, iBatsID** — establishes which European species are *not* separable, directly relevant to Europe's 10 genuine *Myotis*/*Plecotus* gaps.
4. **Ochoa et al. 2000** — Venezuela is zero (~174 species); abstract confirms **30 species identified acoustically**.
5. **Hughes et al. 2011 + 2010** — Thailand is zero; together they cover 19 FM species plus the CF families.
6. **Monadjem et al. 2020**, *Bats of Southern and Central Africa* — cited by all three southern African batches.
7. **Tanshi et al. 2021** (Nigeria) — likely the richest untapped West African source.
8. **Disca et al. 2014** (16 Moroccan species) — Morocco/Algeria/Libya/Egypt contribute nothing to the North Africa batch.

Plus Russ 2021, Parsons 1997, Mancina et al. 2012, Miller et al. 2024, Ahmim et al. 2020.

## Tier F — Resolve the citation (6 items)

Data may be sound; provenance isn't. Four were never resolved at all: the Bahamas Exuma paper, *Phyllops falcatus*, *Pharotis imogene*, and Leary & Pennay 2011 — whose **8 PNG species identities were never determined**, recorded as an unnamed placeholder rather than guessed. Fetching it names them.

## Tier G — Verify known errors (2 items)

**North America.** All 239 records are `measured_compiled` from **one author's two tables** — zero `measured_primary`. Broadest coverage in the project, narrowest evidence base. Seven records carry suspected-error flags, and an independent cross-check found *Nyctinomops macrotis* at 13.4 kHz (SonoBat) vs 17.43 kHz (Peru) — a 4 kHz gap in a species already flagged twice. *Corynorhinus rafinesquii* is effectively n=1: its ranges collapse to 40–40, 22–22, 33–33, yet a mean and SD are printed alongside.

**South America.** Of the six species in `CONFLICT_REGISTER.csv`, *Thyroptera tricolor* (51 vs 123 kHz) and *T. discifera* (53 vs 112.5) both sit near a 1:2 ratio — almost certainly an unlabelled fundamental-vs-second-harmonic mismatch. Probably fixable by just identifying which harmonic each source reported.

---

## If you only do five things

1. EuroBaTrait (Tier B1) — fixes the worst-covered region
2. The seven ABCD GBIF datasets (Tier A) — fixes Indonesia, Cambodia, Yunnan
3. Orozco-Lugo 2013 (Tier C1) — first real Mexican numbers, near-zero effort
4. Colombia DwC-A + African database (Tier B3, B4) — makes coverage auditing possible for ~490 species
5. South Asia Supp. 3 pagination (Tier B5) — completes a batch that's already ⅔ done

## Rules to carry over

- Never write a `measured_*` value you haven't read. Use `value_exists_unretrieved` when you can see it exists but can't extract it.
- Never write `unknown_no_data` from a family- or review-level statement. It needs a species-name search that returned nothing, plus a `last_searched` date. **This bug recurred three times in this project.**
- Record `harmonic_n` (fundamental = 1) explicitly. Three sources used three incompatible conventions and it caused 44 of 50 apparent conflicts.
- Record `context_class` — release vs hand-held vs free-flying calls differ by 20–50 kHz in the same species.
- Keep `verified_by` empty unless a human checked it. All 2,857 rows are currently unverified, and that's honest.
