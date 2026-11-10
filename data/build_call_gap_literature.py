"""Import call measurements found by the call-gap search (November 2026).

data/calls/search_call_gaps.py listed, for every echolocating bat with no
call in the dataset, the literature that might describe one. Each candidate
was read; this script imports the values that were found, one CSV per source.
Species read but left without a value get their verdict in
data/calls/search_decisions.csv instead.

Every value is read from a cached copy of its source, pinned by sha256:
- Europe PMC full-text XML (data/raw/calls/europepmc/PMC*.xml), fetched by
  the search's triage pass. Tables are parsed from the XML.
- Plazi TreatmentBank XML (data/raw/calls/plazi/*.xml), fetched by the
  search's plazi pass.
- Open-access PDFs (data/raw/calls/papers/*.pdf), fetched by
  data/calls/fetch_call_gap_papers.py where robots.txt allows. Their text is
  read with `pdftotext -layout` (poppler), which must be on PATH.
Each row carries the source's own wording in verbatim_value, and the script
stops if that wording is not found in the cached text. A row read off the
rendered page because the PDF's text layer scrambles the table says so in
its note and is checked against the page by eye only (visual=True).

Two sources were already in the dataset through a supplied worksheet that
covered only part of their tables (Gyorossy et al. 2024, Jung et al. 2014).
Their tables are read here directly, for the gap species only, under
separate reference ids in the same independence group.

Run: uv run data/build_call_gap_literature.py
"""
import hashlib
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from call_import_lib import TaxonResolver, report, write_review, write_rows

RAW = Path(__file__).parent / "raw" / "calls"

# reference_id -> (cached file, method_id, locator prefix); hashes are in PINS
SOURCES = {
    "gyorossy-2024-tables": ("europepmc/PMC11458788.xml", "gyorossy-2024-tables-field", "Tables 1-7"),
    "jung-2014-tables": ("europepmc/PMC3891751.xml", "jung-2014-tables-free-flight", "Table 3"),
    "ramirez-chaves-2023-molossops": ("europepmc/PMC10838178.xml", "ramirez-chaves-2023-molossops-field", "table of pulse parameters"),
    "lopez-cuamatzi-2024-corynorhinus": ("europepmc/PMC10881012.xml", "lopez-cuamatzi-2024-corynorhinus-field", "Table 5"),
    "wang-2025-barbastella": ("europepmc/PMC11862895.xml", "wang-2025-barbastella-field", "table of call features"),
    "luo-2023-plecotus": ("europepmc/PMC10206652.xml", "luo-2023-plecotus-field", "Table 3"),
    "gorfol-2020-mirostrellus": ("europepmc/PMC7236909.xml", "gorfol-2020-mirostrellus-field", "Results, echolocation"),
    "flanders-2022-rwanda": ("europepmc/PMC9848553.xml", "flanders-2022-rwanda-release", "Figure 4 caption"),
    "juste-2023-pseudoromicia": ("europepmc/PMC10075340.xml", "juste-2023-pseudoromicia-field", "species description, echolocation"),
    "weber-2019-sierra-leone": ("europepmc/PMC6592978.xml", "weber-2019-sierra-leone-field", "table of rhinolophid and hipposiderid calls"),
    "rodriguez-herrera-2020-centurio": ("europepmc/PMC7657542.xml", "rodriguez-herrera-2020-centurio-field", "Table 1"),
    "monadjem-2013-miniopterus": ("plazi/104887DAFFE7FFCF80D4FA1BFC6B2316.xml", "monadjem-2013-miniopterus-release", "p. 129, species account; Plazi treatment 104887DAFFE7FFCF80D4FA1BFC6B2316"),
    "monadjem-2019-miniopterus": ("plazi/5A56CD2D6D1E2E0ECA14131957D2C844.xml", "monadjem-2019-miniopterus-release", "p. 245, species account; Plazi treatment 5A56CD2D6D1E2E0ECA14131957D2C844"),
    "srinivasulu-2023-miniopterus": ("plazi/03FAFE07FFCFC00404B9F8F3DAD39643.xml", "srinivasulu-2023-miniopterus-field", "p. 237, species account; Plazi treatment 03FAFE07FFCFC00404B9F8F3DAD39643"),
    "novaes-2022-myotis-lavali": ("plazi/875F8793FFB2FFD9FFF6246330D505E4.xml", "novaes-2022-myotis-lavali-compiled", "Mammalian Species account, Behavior; Plazi treatment 875F8793FFB2FFD9FFF6246330D505E4"),
    "simmons-2021-myotis": ("plazi/867D87BA1B55ED02BEB5FE0517FD5AED.xml", "simmons-2021-myotis-release", "species description, echolocation calls; Plazi treatment 867D87BA1B55ED02BEB5FE0517FD5AED"),
    "saikia-2025-himalaya": ("plazi/03BB87E9FFD02D1BFF6DFA42FC56FB48.xml", "saikia-2025-himalaya-release", "species account; Plazi treatment"),
    "wongwaiyut-2023-hipposideros": ("plazi/E602879BFFD1FFD4FF7AFF4BFBC2FB87.xml", "wongwaiyut-2023-hipposideros-field", "p. 406, species description; Plazi treatment E602879BFFD1FFD4FF7AFF4BFBC2FB87"),
    "soisook-2015-eudiscoderma": ("plazi/03BAD22DF61ED378FF0AB3FEFD8F95D5.xml", "soisook-2015-eudiscoderma-release", "p. 532, species description; Plazi treatment 03BAD22DF61ED378FF0AB3FEFD8F95D5"),
    "rosa-2020-thyroptera": ("papers/thyroptera-devivoi-2020.pdf", "rosa-2020-thyroptera-roost", "p. 5, Table 2"),
    "martinez-2023-histiotus": ("papers/histiotus-colombiae-2023.pdf", "martinez-2023-histiotus-field", "p. 3, Tabla 1"),
    "restrepo-giraldo-2025-neoeptesicus": ("papers/neoeptesicus-innoxius-2025.pdf", "restrepo-giraldo-2025-neoeptesicus-field", "p. 8, Table 1"),
    "woxvold-2026-pharotis": ("papers/pharotis-imogene-2026.pdf", "woxvold-2026-pharotis-release", "p. 74, Table 1"),
    "lopez-cuamatzi-2026-eumops": ("papers/eumops-ferox-2026.pdf", "lopez-cuamatzi-2026-eumops-field", "p. 14, Table 1"),
    "macswiney-2006-cynomops": ("papers/cynomops-yucatan-2006.pdf", "macswiney-2006-cynomops-field", "p. 83, Cuadro 1"),
    "fenton-1999-brazil": ("papers/mimon-diet-1999.pdf", "fenton-1999-brazil-anabat", "p. 1083, Table I"),
}
# Saikia et al. 2025 is one paper split by Plazi into one treatment per
# species; these are the other treatments read.
EXTRA_TEXT = {
    "saikia-2025-himalaya": ["plazi/03BB87E9FFD92D11FF6DF88BFE1EFBD4.xml",   # Pipistrellus babu, p. 50
                             "plazi/03BB87E9FFF42D3FFF6DF953FE52FBD4.xml",   # Hypsugo affinis, p. 29
                             "plazi/03BB87E9FFCB2D08FF6DFDD9FAD8FE78.xml"],  # Myotis himalaicus, p. 36
}
PINS = {
    "europepmc/PMC11458788.xml": "485bc2450adbd6763c8b44e4f75c50b338abae32ce8c9a4e5967957e18c05cde",
    "europepmc/PMC3891751.xml": "e04616d668faf38bcf812584a02d58f87626d920cea636f7574714e31ac44e5b",
    "europepmc/PMC10838178.xml": "154886e24f42614534ea5b236ae9a21a0cd0519e3a3642318a0b6f1b55f58bbe",
    "europepmc/PMC10881012.xml": "6e75d2658b08a8c88afec46eae084d32e4b24b7a4abc486121e15f72853f9ab2",
    "europepmc/PMC11862895.xml": "fc878c02fe40a394d7840fa1f89d115d23824735ea0b0998f191e4c2cce30675",
    "europepmc/PMC10206652.xml": "0e2170750a5f9584be8c2f2b0c21ff10ef7089528a8583dde4d793513498e276",
    "europepmc/PMC7236909.xml": "de4bf97ced66c1c4205c2d4bacf686c60a2346dc563ffc1142e82e0df1f2fbf4",
    "europepmc/PMC9848553.xml": "050c001b9383af2a7e9e078f54804baaf6050f3bcd69fa49015b44c51f764006",
    "europepmc/PMC10075340.xml": "d6ca176c52a240bb893b63af485922bd2d5aab3508832bd51ef17b04e308bcc7",
    "europepmc/PMC6592978.xml": "6a161cb04defd1763c5bcd80f5f161ca0efe2986c96904d33fd16ef0d92cd3f9",
    "europepmc/PMC7657542.xml": "9aa7b36a28e43b56e7391d86dfc9daa4c444955029445333f6e6d692c13cee41",
    "plazi/104887DAFFE7FFCF80D4FA1BFC6B2316.xml": "1f84ae827afd27ebb2f4d764d9c6d7afc17d96aca61a33d589e6e37f77b19640",
    "plazi/5A56CD2D6D1E2E0ECA14131957D2C844.xml": "d4018fd7c6e10c29932a79e26f94cec4c7e264b315a052940a0ad96c6f9e5cd9",
    "plazi/03FAFE07FFCFC00404B9F8F3DAD39643.xml": "8a544bcc346c29831c586f1cdf7e025b5eb88218edb41c35d48b1b1f0cd275f3",
    "plazi/875F8793FFB2FFD9FFF6246330D505E4.xml": "2e0715d4b3d5050d9f150f74c243c3c5475a7a6ae2961d5f9d93900a31159fbc",
    "plazi/867D87BA1B55ED02BEB5FE0517FD5AED.xml": "bf0e7f09286fa20f4d1376990c567bc56c6952577f1df5fb8638c30f990cb100",
    "plazi/03BB87E9FFD02D1BFF6DFA42FC56FB48.xml": "4014ea53b722c0fde57f9c5ef808fdffa96584043c8ac49d6f5d43acdf95ce29",
    "plazi/03BB87E9FFD92D11FF6DF88BFE1EFBD4.xml": "36c86a49b1e591de3cfaf16f73067740245e92bd2da6506108009490407c717b",
    "plazi/03BB87E9FFF42D3FFF6DF953FE52FBD4.xml": "b26991e33c0c7d600e21954f805f2abf33d10efeaa6a0007a5ab966abb7a27a2",
    "plazi/03BB87E9FFCB2D08FF6DFDD9FAD8FE78.xml": "45aabb2c69d78003f6ff76d5175f476ebcef9d1e11ad07fd6b572d4ad13121a3",
    "plazi/E602879BFFD1FFD4FF7AFF4BFBC2FB87.xml": "e352b976b28fa1c904cba125e8a3d8efffb902b2bd4a2322cd36e9b081d97536",
    "plazi/03BAD22DF61ED378FF0AB3FEFD8F95D5.xml": "5361a4abc7cc244bed8b08dc3099e30a01ab08913611348527567660718b151c",
    "papers/thyroptera-devivoi-2020.pdf": "c23a2aa9054add4ee7c3336c7b1350a06283fb87386c27570c688756f14bc997",
    "papers/histiotus-colombiae-2023.pdf": "36ace40fff65c3fb7a7231f605f3f86f609a51fc34956a80a6837472f51fb23b",
    "papers/neoeptesicus-innoxius-2025.pdf": "5c9101aaef8e6d7c7e14a0b7ef56d63b5523418f37528210269516f02fe30866",
    "papers/pharotis-imogene-2026.pdf": "a258ba29a2122e3ffc7d4bbf9ff3cb3c0d62f21c519b8c6ea76f730ee49df7f9",
    "papers/eumops-ferox-2026.pdf": "a705d2a4831ab6f2a58ba679e062947c169372ba8f4ad26367ea9cf919ac15e8",
    "papers/cynomops-yucatan-2006.pdf": "f3d54edfd4c4d356e57cd3d320bdd1d92ef56ab2097f3658e77c9f64764de623",
    "papers/mimon-diet-1999.pdf": "d6aa7aa2479aa3b57754d9d40262478d2f12a513d593448c8d107dad83875423",
}

PK, CF, MX, MN, ST, EN, BW, DU, IP, KN, DC, CFD = (
    "peak_frequency", "cf_frequency", "max_frequency", "min_frequency", "start_frequency",
    "end_frequency", "bandwidth", "duration", "inter_pulse_interval", "knee_frequency",
    "duty_cycle", "cf_duration")
UNITS = {DU: "ms", IP: "ms", CFD: "ms", DC: "percent"}
FREQ = {PK, CF, MX, MN, ST, EN, BW, KN}


def norm_text(s: str) -> str:
    s = s.replace(" ", " ").replace("\xa0", " ").replace("−", "-")
    s = re.sub(r"[‐-―]", "-", s)
    s = re.sub(r"\s*±\s*", " ± ", s)
    return re.sub(r"\s+", " ", s).strip()


def xml_text(rel: str) -> str:
    if rel.endswith(".pdf"):
        out = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(RAW / rel), "-"],
                             capture_output=True, check=True)
        return norm_text(out.stdout.decode("utf-8", "replace"))
    return norm_text(" ".join(ET.parse(RAW / rel).getroot().itertext()))


def r(ref, species, obs, parameter, statistic, value=None, low=None, high=None, *, verbatim,
      sd=None, n="", harmonic="", country="", locality="", condition="unspecified", flag="ok",
      note="", printed="", variant="", variant_label="", locator="", visual=False):
    return dict(ref=ref, species=species, obs=obs, parameter=parameter, statistic=statistic,
                value=value, low=low, high=high, sd=sd, n=n, harmonic=harmonic, country=country,
                locality=locality, condition=condition, flag=flag, verbatim=verbatim, note=note,
                printed=printed, variant=variant, variant_label=variant_label, locator=locator,
                visual=visual)


# --- tables parsed from Europe PMC XML ---------------------------------------

CELL = re.compile(r"^([\d.]+) ?± ?([\d.]+) ([\d.]+) ?- ?([\d.]+) \((\d+)\)$")
GYOROSSY_COLUMNS = {"D (ms)": DU, "IPI (ms)": IP, "FCF (kHz)": CF, "DCF (ms)": CFD,
                    "FmaxE (kHz)": PK, "SF (kHz)": ST, "EF (kHz)": EN, "HF (kHz)": MX,
                    "LF (kHz)": MN, "BW (kHz)": BW}
# FQCF and DQCF (frequency and duration of a quasi-constant part) have no
# registry parameter and are left out.
GYOROSSY_SPECIES = ["Taphozous theobaldi", "Hipposideros poutensis", "Myotis ater", "Myotis montivagus",
                    "Plecotus homochrous", "Murina beelzebub", "Murina eleryi", "Murina fionae",
                    "Hypsugo pulveratus", "Mirostrellus joffrei"]


def table_rows(rel: str):
    root = ET.parse(RAW / rel).getroot()
    for tw in root.iter("table-wrap"):
        label = norm_text(" ".join(tw.find("label").itertext())) if tw.find("label") is not None else ""
        trs = list(tw.iter("tr"))
        header = [norm_text(" ".join(c.itertext())) for c in trs[0]] if trs else []
        for tr in trs[1:]:
            yield label, header, [norm_text(" ".join(c.itertext())) for c in tr]


def gyorossy():
    out = []
    for label, header, cells in table_rows(SOURCES["gyorossy-2024-tables"][0]):
        if not cells or cells[0] not in GYOROSSY_SPECIES:
            continue
        row = dict(zip(header, cells))
        hm = row["HM"]
        for column, parameter in GYOROSSY_COLUMNS.items():
            m = CELL.match(row.get(column, ""))
            if not m:
                continue
            mean, sd, lo, hi, n = (float(x) for x in m.groups())
            # A few cells are internally impossible (a mean outside its own
            # range, an SD wider than the range); they are kept but flagged.
            bad = not (lo <= mean <= hi) or sd > (hi - lo)
            out.append(r("gyorossy-2024-tables", cells[0], f"h{hm}", parameter, "mean", mean, lo, hi, sd=sd,
                         harmonic=hm if parameter in FREQ else "", country="Vietnam",
                         flag="suspect" if bad else "ok", verbatim=f"{cells[0]} ... {row[column]}",
                         locator=f"{label}, {cells[0]}, row HM {hm}, column {column}",
                         note=(f"Measured on harmonic {hm}; n = {int(n)} call sequences."
                               + (" The cell is internally inconsistent (mean outside min-max, or SD wider "
                                  "than the range)." if bad else ""))))
    return out


def jung():
    out, species = [], None
    params = {"SF": ST, "EF": EN, "BW": BW, "CD": DU, "PI": IP}
    for label, header, cells in table_rows(SOURCES["jung-2014-tables"][0]):
        if label != "Table 3":
            continue
        if len(cells) == 1 or (len(cells) > 1 and not any(cells[1:])):
            species = cells[0]
            continue
        if species not in ("Eumops nanus", "Eumops dabbenei") or "/" not in cells[0]:
            continue
        variant = cells[0].split("/")[0].lower()        # low / high
        values = dict(zip(["SF", "EF", "BW"], cells[1].split("/")))
        values.update(zip(["CD", "PI", "D"], cells[2].split("/")))
        values["DC"] = cells[4]
        nc, ns = cells[6].split("/")
        for key, raw in values.items():
            parameter = params.get(key) or (DC if key == "DC" else None)
            if parameter is None:
                continue
            mean, sd = (float(x) for x in raw.split("±"))
            out.append(r("jung-2014-tables", species, variant, parameter, "mean", mean, sd=sd,
                         variant=variant, variant_label=f"{variant.title()} call (alternating pair)",
                         condition="free_flying_wild", verbatim=f"{species} ... {cells[0]} ... {raw}",
                         locator=f"Table 3, {species}, {cells[0]} row",
                         note=f"Search-flight calls; {nc} calls from {ns} sequences."))
    return out


ROWS = gyorossy() + jung()

# --- values read from the text --------------------------------------------------

M = "ramirez-chaves-2023-molossops"
for variant, label, vals in [
        ("ufm", "UFM calls", [(DU, 9.17, 1.0, "9.17 ± 1.0"), (MN, 39.62, 2.7, "39.62 ± 2.7"), (MX, 53.43, 1.5, "53.43 ± 1.5"),
                              (PK, 46.07, 2.5, "46.07 ± 2.5"), (BW, 13.8, 2.5, "13.8 ± 2.5")]),
        ("dfm", "DFM calls", [(DU, 7.28, 1.3, "7.28 ± 1.3"), (MN, 54.67, 2.0, "54.67 ± 2.0"), (MX, 77.71, 9.3, "77.71 ± 9.3"),
                              (PK, 57.81, 1.27, "57.81 ± 1.27"), (BW, 23.04, 10.7, "23.04 ± 10.7")])]:
    for p, v, sd, verb in vals:
        ROWS.append(r(M, "Molossops griseiventer", variant, p, "mean", v, sd=sd, variant=variant, variant_label=label,
                      condition="free_flying_wild", country="Colombia", locality="Magdalena River Basin",
                      verbatim=verb, locator=f"table of pulse parameters, {label}, 'This study' column",
                      note=f"{'137 pulses from 10' if variant == 'ufm' else '37 pulses from 7'} sequences."))

C = "lopez-cuamatzi-2024-corynorhinus"
for variant, n, vals in [("I", 100, [(MN, 21.30, 1.15), (MX, 48.20, 1.32), (PK, 36.40, 0.81), (DU, 3.00, 0.37), (IP, 22.10, 1.27)]),
                         ("II", 23, [(MN, 21.70, 0.73), (MX, 45.70, 1.44), (PK, 35.40, 1.04), (DU, 4.70, 0.73), (IP, 73.80, 23.68)])]:
    for p, v, sd in vals:
        ROWS.append(r(C, "Corynorhinus leonpaniaguae", f"s{variant.lower()}", p, "mean", v, sd=sd, variant=f"sonotype-{variant}",
                      variant_label=f"Sonotype {variant}", country="Mexico", verbatim=f"{v:.2f}",
                      locator=f"Table 5, sonotype {variant}",
                      note=f"n = {n} pulses." + (" FHA, frequency of highest amplitude." if p == PK else "")))

B = "wang-2025-barbastella"
for p, v, lo, hi, sd, verb in [(ST, 33.15, 29.97, 34.63, 1.43, "Initial frequency (kHz) 29.97-34.63 33.15 ± 1.43"),
                               (EN, 29.82, 28.99, 30.19, 0.40, "Terminate frequency (kHz) 28.99-30.19 29.82 ± 0.40"),
                               (BW, 5.79, 4.02, 7.27, 1.04, "Frequency bandwidth (kHz) 4.02-7.27 5.79 ± 1.04"),
                               (PK, 31.48, 31.07, 31.96, 0.40, "Main frequency (kHz) 31.07-31.96 31.48 ± 0.40"),
                               (DU, 2.43, 2.05, 2.74, 0.24, "Duration time (ms) 2.05-2.74 2.43 ± 0.24"),
                               (IP, 246.57, 232.29, 266.43, 9.48, "Interval time (ms) 232.29-266.43 246.57 ± 9.48")]:
    ROWS.append(r(B, "Barbastella caspica", "a", p, "mean", v, lo, hi, sd=sd, condition="free_flying_wild", country="China",
                  locality="Xinjiang", verbatim=verb, locator="table of echolocation call features, free flight",
                  flag="definition_unstated" if p == PK else "ok",
                  note="'Main frequency' read as the frequency of maximum energy." if p == PK else ""))

L = "luo-2023-plecotus"
for p, v, sd, verb in [(ST, 74.0, 2.8, "74.0 ± 2.8 kHz"), (EN, 52.2, 1.9, "52.2 ± 1.9 kHz"),
                       (PK, 58.7, 0.6, "58.7 ± 0.6 kHz"), (DU, 1.5, 0.2, "1.5 ± 0.2 ms")]:
    ROWS.append(r(L, "Plecotus homochrous", "cn", p, "mean", v, sd=sd, n="4", country="China", locality="Guangdong",
                  verbatim=verb, locator="Results, echolocation calls and Table 3, Chinese specimens",
                  note="Four bats (GD-221656 to GD-221659); the Vietnamese means in Table 3 are from another study."))

G = "gorfol-2020-mirostrellus"
for variant, label, cond, vals in [
        ("tent", "FM calls in a flight tent", "flight_room",
         [(PK, 39.0, 2.3, "F maxE ) of 39.0 ± 2.3 kHz"), (DU, 2.7, 1.5, "T dur =2.7 ± 1.5 ms"), (IP, 69.5, 27.5, "PI =69.5 ± 27.5 ms")]),
        ("release", "FMQCF calls on hand release", "hand_release",
         [(PK, 34.6, 1.2, "F maxE =34.6 ± 1.2 kHz"), (DU, 6.4, 2.1, "T dur =6.4 ± 2.1 ms"), (IP, 90.3, 10.8, "PI =90.3 ± 10.8 ms")]),
        ("free-fmqcf", "FMQCF calls in free flight", "free_flying_wild",
         [(PK, 30.5, 0.7, "F maxE =30.5 ± 0.7 kHz"), (DU, 11.8, 1.6, "T dur =11.8 ± 1.6 ms"), (IP, 158.4, 36.9, "PI =158.4 ± 36.9 ms")]),
        ("free-qcf", "QCF calls in free flight", "free_flying_wild",
         [(PK, 28.3, 0.6, "F maxE =28.3 ± 0.6 kHz"), (DU, 13.3, 2.1, "T dur =13.3 ± 2.1 ms"), (IP, 199.8, 36.2, "PI =199.8 ± 36.2 ms")])]:
    for p, v, sd, verb in vals:
        ROWS.append(r(G, "Mirostrellus joffrei", variant, p, "mean", v, sd=sd, variant=variant, variant_label=label,
                      condition=cond, country="Vietnam", verbatim=verb, locator="Results, echolocation calls"))

F = "flanders-2022-rwanda"
for p, v, verb in [(PK, 35.4, "Mean peak frequency 35.4 kHz"), (DU, 49.5, "call duration 49.5 ms"),
                   (IP, 82.25, "interpulse interval 82.25 ms")]:
    ROWS.append(r(F, "Rhinolophus hilli", "a", p, "mean", v, condition="hand_release", country="Rwanda",
                  locality="Nyungwe National Park", verbatim=verb, locator="Figure 4 caption"))

J = "juste-2023-pseudoromicia"
for p, v, sd, lo, hi, verb in [(ST, 55.47, 8.43, 44.75, 74.05, "Start Frequency, 55.47 ± 8.43 (44.75-74.05) kHz"),
                               (EN, 44.71, 1.44, 41.92, 47.83, "End Frequency, 44.71 ± 1.44 (41.92-47.83) kHz"),
                               (PK, 45.69, 1.26, 43.9, 48.3, "Maximum Energy Frequency or Peak Frequency, 45.69 ± 1.26 (43.9-48.3) kHz"),
                               (DU, 5.82, 1.39, 5.32, 9.41, "Duration, 5.82 ± 1.39 (5.32-9.41) ms")]:
    ROWS.append(r(J, "Pseudoromicia principis", "a", p, "mean", v, lo, hi, sd=sd, country="São Tomé and Príncipe",
                  locality="Príncipe", verbatim=verb, locator="species description, echolocation",
                  note="40 call sequences."))

ROWS.append(r("weber-2019-sierra-leone", "Hipposideros abae", "a", CF, "single", 103.0, n="1", condition="hand_release",
              country="Sierra Leone", locality="Bumbuna / Loma Mountains", verbatim="Hipposideros abae 103.0 1 F",
              locator="table of rhinolophid and hipposiderid calls", note="One female."))

H = "rodriguez-herrera-2020-centurio"
for variant, label, vals in [
        ("free", "Free-flying bats", [(PK, 88.6, 1.77, "88.6 (4) ± 1.77"), (ST, 112.7, 3.04, "112.7 (4) ±3.04"), (EN, 76.1, 1.35, "76.1 (4) ±1.35"),
                                      (BW, 36.6, 4.26, "36.6 (4) ± 4.26"), (DU, 1.3, 0.19, "1.3 (4) ± 0.19"), (IP, 54.2, 19.79, "54.2 (4) ±19.79")]),
        ("perch", "Perching bats", [(PK, 91.2, 4.59, "91.2 (7) ± 4.59"), (ST, 116.5, 12.17, "116.5 (7) ± 12.17"), (EN, 76.4, 3.27, "76.4 (7) ± 3.27"),
                                    (BW, 40.1, 9.61, "40.1 (7) ± 9.61"), (DU, 1.3, 0.42, "1.3 (7) ± 0.42"), (IP, 52.0, 12.74, "52.0 (7) ±12.74")])]:
    for p, v, sd, verb in vals:
        ROWS.append(r(H, "Centurio senex", variant, p, "mean", v, sd=sd, variant=variant, variant_label=label,
                      condition="free_flying_wild" if variant == "free" else "unspecified", country="Costa Rica",
                      harmonic="1" if p == PK else "", verbatim=verb, locator="Table 1, echolocation calls",
                      note=("45 calls from 4 passes." if variant == "free" else "Males calling from perches at a lek.")))

# --- Plazi treatments -------------------------------------------------------------

ROWS += [
    r("monadjem-2013-miniopterus", "Miniopterus mossambicus", "a", KN, "species_summary", 55, condition="hand_release",
      verbatim="The frequency of the knee of its echolocation call was 55 kHz"),
    r("monadjem-2019-miniopterus", "Miniopterus nimbae", "a", KN, "mean", 48.4, 47.2, 48.9, n="4", condition="hand_release",
      country="Guinea", locality="Mount Nimba",
      verbatim="The mean frequency of the knee of handreleased M. nimbae captured at Mount Nimba was 48.4 kHz (range: 47.2-48.9 kHz, n = 4)"),
    r("monadjem-2019-miniopterus", "Miniopterus villiersi", "a", KN, "mean", 51.6, 51.1, 52.4, n="5", condition="hand_release",
      country="Guinea", locality="Mount Nimba",
      verbatim="M. villiersi calls (based on hand-released individuals that were captured at Mount Nimba - x = 51.6 kHz, range 51.1-52.4 kHz, n = 5)",
      note="From the M. nimbae account, which compares the two species."),
    *[r("srinivasulu-2023-miniopterus", "Miniopterus srinii", "a", p, "mean", v, lo, hi, sd=sd, country="India",
        locality="Western Ghats", verbatim=verb) for p, v, sd, lo, hi, verb in [
        (PK, 77.62, 7.98, 64.7, 97.2, "FmaxE of 77.62 ± 7.98 kHz (64.7-97.2 kHz)"),
        (ST, 130.00, 11.16, 90, 154, "Fs of 130.00 ± 11.16 kHz (90-154 kHz)"),
        (EN, 58.38, 1.43, 53, 64, "Fe of 58.38 ± 1.43 kHz (53-64 kHz)"),
        (DU, 4.18, 1.16, 2.1, 8.0, "duration of 4.18 ± 1.16 ms (2.1-8.0 ms)")]],
    *[r("novaes-2022-myotis-lavali", "Myotis lavali", "a", p, "mean", v, lo, hi, country="Brazil", verbatim=verb, flag=flag,
        note="The account summarises Arias-Aguilar et al. (2018)." + (" The stated range does not contain the mean." if flag == "suspect" else ""))
      for p, v, lo, hi, verb, flag in [
        (PK, 51.1, 48, 54, "The frequency of maximum energy averages 51.1 kHz (48-54 kHz)", "ok"),
        (MN, 48, 45, 52, "lowest frequency (LF) averages 48 kHz (45-52 kHz)", "ok"),
        (MX, 78.3, 67, 77, "highest frequency (HF) averages 78.3 kHz (67-77 kHz)", "suspect"),
        (BW, 30.2, 6, 67, "bandwidth (BW) averages 30.2 kHz (6-67 kHz)", "ok"),
        (DU, 4.8, 2, 8, "call duration (CD) averages 4.8 ms (2-8 ms)", "ok"),
        (IP, 77.6, 33, 201, "interpulse interval averages 77.6 ms (33-201 ms)", "ok"),
        (DC, 6, 2, 11, "the duty-cycle averages 6% (2-11%", "ok")]],
    *[r("simmons-2021-myotis", "Myotis nimbaensis", "a", p, stat, v, sd=sd, n="1", condition="hand_release", country="Guinea",
        locality="Nimba Mountains", verbatim=verb, note="22 calls from the holotype on release.")
      for p, stat, v, sd, verb in [
        (BW, "mean", 84.1, 13.1, "broad bandwidth (84.1 ± 13.1 kHz"),
        (MX, "species_summary", 104, None, "FMAX: 104 kHz"),
        (MN, "species_summary", 20, None, "FMIN: 20 kHz"),
        (PK, "mean", 42.5, 4.2, "peak frequency of 42.5 kHz (± 4.2 kHz)"),
        (DU, "mean", 3.5, 0.3, "average call duration of 3.5 ms (± 0.3 ms)"),
        (IP, "mean", 113, 5.3, "interpulse interval of 113 ms (± 5.3 ms")]],
    *[r("saikia-2025-himalaya", "Submyotodon caliginosus", "a", p, "species_summary", v, country="India", locality="Western Himalaya",
        verbatim=verb, locator="p. 57, species account; Plazi treatment 03BB87E9FFD02D1BFF6DFA42FC56FB48")
      for p, v, verb in [(BW, 61.41, "bandwidth=61.41 kHz"), (DU, 5.6, "short duration (5.6 ms)"), (EN, 53.6, "ending at 53.6 kHz")]],
    *[r("saikia-2025-himalaya", "Pipistrellus babu", "a", p, "mean", v, n="36", condition="hand_release", country="India",
        locality="Western Himalaya", verbatim=verb, locator="p. 50, species account; Plazi treatment 03BB87E9FFD92D11FF6DF88BFE1EFBD4",
        note="Release calls of 36 bats.")
      for p, v, verb in [(DU, 5.7, "the release calls were 5.7 ms long"), (BW, 47, "average bandwidth of 47 kHz"),
                         (EN, 35, "end frequency of 35 kHz"), (PK, 40, "peak frequency of 40 kHz")]],
    *[r("saikia-2025-himalaya", "Hypsugo affinis", "a", p, "mean", v, sd=sd, n="1", country="India", locality="Western Himalaya",
        verbatim="Hy. affinis 1 66.63 ± 3.88 25.89 ± 0.63 30.51 ± 0.45 40.74 ± 3.81 4.67 ± 0.52",
        locator="Table 6 (call parameters), as printed in the M. himalaicus treatment; Plazi treatment 03BB87E9FFCB2D08FF6DFDD9FAD8FE78",
        note="One bat.") for p, v, sd in [(ST, 66.63, 3.88), (EN, 25.89, 0.63), (PK, 30.51, 0.45), (BW, 40.74, 3.81), (DU, 4.67, 0.52)]],
    *[r("saikia-2025-himalaya", "Murina aurata", "cf", p, "mean", v, sd=sd, n="2", country="India", locality="Western Himalaya",
        flag="taxon_uncertain", printed="Murina aurata",
        verbatim="Mu. cf. aurata 2 159.8 ± 6.7 51.74 ± 11.74 88.91 ± 6.68 108.05 ± 5.16 3.44 ± 2.34",
        locator="Table 6 (call parameters), as printed in the M. himalaicus treatment; Plazi treatment 03BB87E9FFCB2D08FF6DFDD9FAD8FE78",
        note="Printed as 'Mu. cf. aurata': the identification is not certain.")
      for p, v, sd in [(ST, 159.8, 6.7), (EN, 51.74, 11.74), (PK, 88.91, 6.68), (BW, 108.05, 5.16), (DU, 3.44, 2.34)]],
    *[r("saikia-2025-himalaya", "Myotis himalaicus", "a", p, "mean", v, sd=sd, n="4", condition="hand_release", country="India",
        locality="Mandal, Uttarakhand", verbatim=verb,
        locator="p. 36, species account; Plazi treatment 03BB87E9FFCB2D08FF6DFDD9FAD8FE78",
        note="Recordings published by Chakravarty et al. (2020), assigned to this species by its describers.")
      for p, v, sd, verb in [(ST, 96.8, 3.15, "starting at 96.8 ± 3.15 kHz"), (EN, 47.9, 3.13, "ending at 47.9 ± 3.13 kHz"),
                             (PK, 68.0, 3.86, "maximum energy at 68.0 ± 3.86 kHz")]],
    r("wongwaiyut-2023-hipposideros", "Hipposideros kingstonae", "th", PK, "mean", 142.4, 141.0, 143.4, n="3", country="Thailand",
      verbatim="In three individuals recorded from Thailand , the frequency of maximum energy (FmaxE), corresponding to the frequency of the constant element (CF), is 142.4 kHz (141.0-143.4 kHz; n=3)"),
    r("wongwaiyut-2023-hipposideros", "Hipposideros kingstonae", "my", PK, "single", 144.0, n="1", country="Malaysia",
      locality="Krau Wildlife Reserve", verbatim="the FmaxE from Krau Wildlife Reserve is 144.0 kHz (n=1)"),
    r("wongwaiyut-2023-hipposideros", "Hipposideros kingstonae", "bm", PK, "mean", 138.4, 136.6, 141.4, n="5", country="Malaysia",
      locality="Madai caves, Borneo", verbatim="138.4 kHz (136.6-141.4 kHz; n=5 individuals) for males", note="Males."),
    r("wongwaiyut-2023-hipposideros", "Hipposideros kingstonae", "bf", PK, "mean", 137.7, 137.4, 138.2, n="4", country="Malaysia",
      locality="Madai caves, Borneo", verbatim="137.7 kHz (137.4-138.2 kHz; n=4 individuals) for females", note="Females."),
    r("soisook-2015-eudiscoderma", "Eudiscoderma thongareeae", "a", PK, "mean", 54.0, 53.1, 55.1, sd=0.6, harmonic="3",
      country="Thailand", verbatim="peak frequency ( fmaxe ) of 53.1-55.1 kHz (mean± SD: 54.0±0.6 kHz)",
      note="Maximum energy is usually in the third harmonic."),
    r("soisook-2015-eudiscoderma", "Eudiscoderma thongareeae", "a", ST, "mean", 113.9, 107.6, 129.6, sd=7.9, harmonic="6",
      country="Thailand", verbatim="107.6-129.6 kHz (mean± SD: 113.9±7.9 kHz)", note="Start of the sixth (top) harmonic."),
    r("soisook-2015-eudiscoderma", "Eudiscoderma thongareeae", "a", EN, "mean", 12.7, 11.2, 14.0, sd=1.0, harmonic="1",
      country="Thailand", verbatim="11.2-14.0 kHz (mean± SD : 12.7±1.0 kHz)", note="End of the first (bottom) harmonic."),
]


# --- open-access PDFs -------------------------------------------------------------

# Rosa et al. 2020, Table 2: the fundamental (HF) and the next two harmonics
# (H1, H2), each measured separately, from a roost in Maranhão.
for h, n, vals in [
        ("1", 27, [(DU, 2.1, 0.4), (IP, 12.0, 2.3), (ST, 56.2, 3.5), (EN, 46.7, 1.4), (PK, 51.2, 2.3), (BW, 9.5, 3.9)]),
        ("2", 125, [(DU, 2.2, 0.3), (IP, 11.7, 2.4), (ST, 137.6, 3.6), (EN, 116.3, 3.6), (PK, 127.3, 3.0), (BW, 21.4, 4.1)]),
        ("3", 150, [(DU, 2.2, 0.2), (IP, 11.7, 2.4), (ST, 162.1, 6.1), (EN, 136.9, 3.8), (PK, 146.6, 4.6), (BW, 25.2, 5.7)])]:
    for p, v, sd in vals:
        ROWS.append(r("rosa-2020-thyroptera", "Thyroptera devivoi", f"h{h}", p, "mean", v, sd=sd,
                      harmonic=h if p in FREQ else "", condition="roost_emergence", country="Brazil",
                      locality="Chapada das Mesas, Maranhão", verbatim=f"{v} ± {sd}",
                      note=f"Table 2, column {['HF', 'H1', 'H2'][int(h) - 1]} (harmonic {h}); {n} pulses from a colony at its roost."))

for p, v, sd, verb in [(MX, 40.96, 4.0, "Frecuencia máxima 40.96 ± 4.0 kHz"), (MN, 20.36, 0.8, "Frecuencia mínima 20.36 ± 0.8 kHz"),
                       (PK, 26.12, 1.7, "Frecuencia de máxima energía 26.12 ± 1.7 kHz"), (BW, 20.6, None, "Ancho de banda 20.6 kHz"),
                       (DU, 5.01, 1.3, "Duración del pulso 5.01 ± 1.3 ms"), (IP, 175.23, 54.5, "Intervalo entre pulsos 175.23 ± 54.5 ms")]:
    ROWS.append(r("martinez-2023-histiotus", "Histiotus colombiae", "a", p, "mean", v, sd=sd, condition="free_flying_wild",
                  country="Colombia", locality="Guachetá, Cundinamarca", verbatim=verb,
                  note="100 pulses from 7 recordings near a roost; the same recordings are summarised in Rodríguez-Posada et al. (2021)."))

for p, stat, v, sd, verb in [(ST, "mean", 69.33, 7.73, "69.33 ± 49.20 ± 2.64"), (EN, "mean", 49.20, 2.64, "49.20 ± 2.64"),
                             (PK, "mean", 51.99, 1.30, "51.99"), (BW, "mean", 20.13, 8.34, "20.13"),
                             (DU, "mean", 6.82, 0.88, "6.82"), (IP, "median", 93.5, 12.78, "93.5")]:
    ROWS.append(r("restrepo-giraldo-2025-neoeptesicus", "Neoeptesicus innoxius", "a", p, stat, v, sd=sd,
                  country="Ecuador", locality="Isla Santay", verbatim=f"N. innoxius ... {verb}",
                  note="163 search-phase pulses from 11 sequences, hand release and free flight."
                       + (" The table gives the IPI as a median." if p == IP else "")))

for p, v, sd, hi, lo in [(DU, 6.21, 0.50, 6.96, 5.68), (MX, 56.13, 3.48, 59.97, 51.62), (MN, 29.19, 1.56, 31.50, 26.86),
                         (KN, 40.26, 7.08, 52.39, 33.05), ("characteristic_frequency", 34.44, 7.24, 49.17, 30.43)]:
    ROWS.append(r("woxvold-2026-pharotis", "Pharotis imogene", "a", p, "mean", v, lo, hi, sd=sd, n="1",
                  condition="hand_release", country="Papua New Guinea", locality="Kuriva Forestry Station",
                  verbatim=f"Pharotis imogene n = 6 ... {v:.2f}", note="Six pulses of one voucher bat (SCAN'R)."))

for variant, label, flag, n, vals in [
        ("ref", "Reference calls (Oaxaca, with one Cuban mean)", "ok", "25 calls",
         [(MX, 17.79, 1.91), (MN, 13.97, 0.79), (BW, 3.71, 1.09), (PK, 15.56, 1.26), (DU, 15.00, 1.95)]),
        ("tam", "Tamaulipas, identified from the calls (E. cf. ferox)", "taxon_uncertain", "268 calls from 52 passes",
         [(MX, 19.20, 0.95), (MN, 13.57, 0.33), (BW, 5.63, 1.01), (PK, 15.69, 0.39), (DU, 16.23, 1.06)])]:
    for p, v, sd in vals:
        ROWS.append(r("lopez-cuamatzi-2026-eumops", "Eumops ferox", variant, p, "mean", v, sd=sd, variant=variant,
                      variant_label=label, condition="free_flying_wild", country="Mexico", flag=flag,
                      verbatim=f"{v:.2f}", note=f"{n}." + (" The reference set is unpublished Oaxaca data plus a Cuban mean "
                                                           "(Mora & Torres 2008)." if variant == "ref" else
                                                           " Assigned to E. ferox by discriminant analysis; the authors write 'cf.'.")))

for variant, label, n, vals in [
        ("high", "High-frequency call", 4, [(PK, 30.0, 0.8), (MN, 29.8, 0.8), (MX, 30.0, 1.9), (DU, 38.3, 18.4), (IP, 235.0, 70.1)]),
        ("long-low", "Long low-frequency call", 5, [(PK, 23.8, 1.6), (MN, 23.1, 1.4), (MX, 24.7, 1.5), (DU, 65.6, 21), (IP, 182.7, 39.6)]),
        ("short-low", "Short low-frequency call", 4, [(PK, 26.5, 1.0), (MN, 25.1, 1.1), (MX, 27.2, 0.8), (DU, 17.7, 6.2), (IP, 227.8, 160.8)])]:
    for p, v, sd in vals:
        ROWS.append(r("macswiney-2006-cynomops", "Cynomops mexicanus", variant, p, "mean", v, sd=sd, variant=variant,
                      variant_label=label, condition="free_flying_wild", country="Mexico", locality="northern Yucatán",
                      verbatim=f"{v}±{sd}", note=f"{n} sequences, this study's own recordings (Cuadro 1, LIT a); "
                                               "identified from the calls, by comparison with Miller (2003)."))

for p, stat, v, verb in [(MX, "species_summary", 180, "Mimon bennettii 180"), (MN, "species_summary", 35, "35"),
                         (DU, "species_summary", 1, "1")]:
    ROWS.append(r("fenton-1999-brazil", "Mimon bennettii", "a", p, stat, v, country="Brazil", flag="definition_unstated",
                  verbatim=verb, visual=True,
                  note="Anabat zero-crossing 'highest' and 'lowest' kHz. Read from the rendered Table I: the PDF's text "
                       "layer shifts this table's rows by one."))


def num(x) -> str:
    return "" if x is None else (f"{x:g}" if isinstance(x, float) else str(x))


def main() -> None:
    for rel, expected in PINS.items():
        got = hashlib.sha256((RAW / rel).read_bytes()).hexdigest()
        if expected and got != expected:
            raise SystemExit(f"{rel}: sha256 {got} does not match the pinned {expected}")
        if not expected:
            print(f'    "{rel}": "{got}",')
    texts = {}
    for ref, (rel, *_rest) in SOURCES.items():
        texts[ref] = " ".join(xml_text(p) for p in [rel, *EXTRA_TEXT.get(ref, [])])
    resolver = TaxonResolver()
    resolver.add_manual({"Pipistrellus babu": resolver.resolve("Alionoctula babu")[0]["id"]})
    out, seen = {}, {}
    for row in ROWS:
        ref = row["ref"]
        check = [] if row["visual"] else norm_text(row["verbatim"]).split(" ... ")
        missing = [part for part in check if part and part not in texts[ref]]
        if missing:
            raise SystemExit(f"{ref}, {row['species']}: {missing[0]!r} is not in the cached source text")
        species, method = resolver.resolve(row["species"])
        if species is None:
            raise SystemExit(f"{row['species']}: {method}")
        seen.setdefault(ref, set()).add(species["id"])
        _, method_id, prefix = SOURCES[ref]
        out.setdefault(ref, []).append({
            "observation_id": f"{ref}-{species['id']}-{row['obs']}", "mdd_id": species["id"],
            "verbatim_taxon_name": row["printed"] or row["species"], "taxon_match_method": method,
            "reference_id": ref, "locator": row["locator"] or prefix, "method_id": method_id,
            "call_phase": "search" if ref == "jung-2014-tables" else "unspecified",
            "recording_condition": row["condition"],
            "call_variant": row["variant"], "variant_label": row["variant_label"],
            "country": row["country"], "locality": row["locality"], "n_individuals": row["n"],
            "parameter": row["parameter"], "statistic": row["statistic"], "value": num(row["value"]),
            "value_min": num(row["low"]), "value_max": num(row["high"]),
            "unit": UNITS.get(row["parameter"], "kHz"),
            "dispersion_type": "sd" if row["sd"] is not None else "", "dispersion_value": num(row["sd"]),
            "harmonic": row["harmonic"], "verbatim_value": row["verbatim"], "quality_flag": row["flag"],
            "notes": row["note"],
        })
    for ref, rows in out.items():
        write_rows(ref, rows)
        write_review(ref, resolver.unresolved)
        report(ref, len(rows), len(seen[ref]), resolver)


if __name__ == "__main__":
    main()
