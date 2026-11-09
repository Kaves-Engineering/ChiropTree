"""Import Zamora-Gutierrez et al. (2016): per-call SonoBat measurements, 59 species.

Zamora-Gutierrez et al. built acoustic classifiers for Mexican bats and
deposited every call they trained on: 4,685 search-phase calls from 1,378
sequences, each sequence one bat (Dryad doi:10.5061/dryad.760r8, CC0,
Data-All-Classifiers.xlsx, sheet Classifier1). Calls were selected by SonoBat
signal-to-noise, at most 100 per species, and parameterised by SonoBat v.3.
Most were recorded in Mexico in 2012-13 (hand release and zip line, Pettersson
D1000x); the rest were donated, some from other countries (Table S2).

Each species is summarised here, not by the authors, so every row is flagged
'derived': the mean of the per-sequence means, with the SD across sequences,
n_individuals = sequences and n_calls = calls. Pooling calls directly would
let one well-recorded bat dominate. Recordings are summarised per country,
because several names in the deposit (Simmons 2005 taxonomy) have since been
split and only the country tells which daughter the bats belong to.

Names: the deposit gives 6-letter codes; the paper's Table S2 gives the names.
COUNTRY_SPECIES records where MDD v2.5 says only one daughter of a split name
lives in the recording country. A code/country left out of it is resolved by
name or parked for review. Deliberately parked:
- Ptepar in Mexico: P. mesoamericanus and P. mexicanus both occur there;
- Molsin: the authors pooled Molossus alvarezi into M. sinaloae (p. 8);
- Anogeo in Panama, Stulil in French Guiana, Tracir in Brazil: more than one
  daughter of the old name occurs there.

SonoBat columns -> registry: FreqMaxPwr -> peak_frequency ("frequency of the
maximum amplitude of the call", Table S3), Fc -> characteristic_frequency,
HiFreq/LowFreq -> max/min_frequency, StartF/EndF -> start/end_frequency,
FreqKnee -> knee_frequency, CallDuration -> duration.

Fetch (Dryad's file endpoint needs a token; the version download does not):
  curl -L -o z.zip https://datadryad.org/api/v2/versions/20459/download
  unzip z.zip -d data/raw/zamora-gutierrez-2016-mexico/
Run: uv run --with openpyxl data/build_zamora_2016_mexico_calls.py
"""
import hashlib
import statistics
from collections import defaultdict
from pathlib import Path

import openpyxl

from call_import_lib import TaxonResolver, report, write_review, write_rows

REFERENCE_ID = "zamora-gutierrez-2016-mexico"
METHOD_ID = "zamora-gutierrez-2016-mexico-sonobat"
SOURCE = Path(__file__).parent / "raw" / "zamora-gutierrez-2016-mexico" / "Data-All-Classifiers.xlsx"
SOURCE_SHA256 = "45b7ca5fd372d9ee5b5fab26e5f4668865ff1f581c5d69913e8a2b6a5c4d557b"
SHEET = "Classifier1"

# Deposit code -> name in Table S2 (Simmons 2005 taxonomy).
CODES = {
    "Anogeo": "Anoura geoffroyi", "Antpal": "Antrozous pallidus", "Artjam": "Artibeus jamaicensis",
    "Artlit": "Artibeus lituratus", "Balio": "Balantiopteryx io", "Balpli": "Balantiopteryx plicata",
    "Carper": "Carollia perspicillata", "Cormex": "Corynorhinus mexicanus",
    "Cortow": "Corynorhinus townsendii", "Desrot": "Desmodus rotundus",
    "Eptbra": "Eptesicus brasiliensis", "Eptfur": "Eptesicus furinalis", "Eptfus": "Eptesicus fuscus",
    "Eumund": "Eumops underwoodi", "Idiphy": "Idionycteris phyllotis",
    "Lasnoc": "Lasionycteris noctivagans", "Lasblo": "Lasiurus blossevillii",
    "Lasbor": "Lasiurus borealis", "Lascin": "Lasiurus cinereus", "Lasega": "Lasiurus ega",
    "Lasxan": "Lasiurus xanthinus", "Lepyer": "Leptonycteris yerbabuenae",
    "Maccal": "Macrotus californicus", "Molmol": "Molossus molossus", "Molruf": "Molossus rufus",
    "Molsin": "Molossus sinaloae", "Mormeg": "Mormoops megalophylla", "Myoaur": "Myotis auriculus",
    "Myocal": "Myotis californicus", "Myokea": "Myotis keaysi", "Myomel": "Myotis melanorhinus",
    "Myothy": "Myotis thysanodes", "Myovel": "Myotis velifer", "Myovol": "Myotis volans",
    "Myoyum": "Myotis yumanensis", "Natstr": "Natalus stramineus", "Noclep": "Noctilio leporinus",
    "Nychum": "Nycticeius humeralis", "Nycfem": "Nyctinomops femorosaccus",
    "Nyclat": "Nyctinomops laticaudatus", "Nycmac": "Nyctinomops macrotis",
    "Permac": "Peropteryx macrotis", "Piphes": "Pipistrellus hesperus",
    "Pipsub": "Pipistrellus subflavus", "Procen": "Promops centralis",
    "Ptedav": "Pteronotus davyi", "Ptegym": "Pteronotus gymnonotus",
    "Ptepar": "Pteronotus parnellii", "Pteper": "Pteronotus personatus",
    "Rhoaen": "Rhogeessa aeneus", "Rhopar": "Rhogeessa parvula", "Rhynas": "Rhynchonycteris naso",
    "Sacbil": "Saccopteryx bilineata", "Saclep": "Saccopteryx leptura",
    "Stulil": "Sturnira lilium", "Stulud": "Sturnira ludovici", "Tadbra": "Tadarida brasiliensis",
    "Thytri": "Thyroptera tricolor", "Tracir": "Trachops cirrhosus",
}

# (code, country) -> (MDD id, why). Each checked against MDD v2.5
# countryDistribution: the printed name's other daughters do not occur there.
COUNTRY_SPECIES = {
    ("Anogeo", "Mexico"): ("1004898", "A. geoffroyi as now restricted does not occur in Mexico; MDD's Mexican Anoura is A. peruana."),
    ("Ptedav", "Mexico"): ("1004854", "P. davyi as now restricted does not occur in Mexico; Mexican populations are P. fulvus."),
    ("Pteper", "Mexico"): ("1004864", "P. personatus as now restricted does not occur in Mexico; Mexican populations are P. psilotis."),
    ("Molruf", "Mexico"): ("1005203", "M. rufus as now restricted is South American; Mexican populations are M. nigricans."),
    ("Lasblo", "Mexico"): ("1005582", "L. blossevillii as now restricted is South American; Mexican populations are L. frantzii."),
    ("Myokea", "Mexico"): ("1005456", "M. keaysi as now restricted is South American; Mexican populations are M. pilosatibialis."),
    ("Natstr", "Mexico"): ("1005277", "N. stramineus is now restricted to the Lesser Antilles; MDD's only Mexican Natalus is N. mexicanus. The authors treated all Mexican natalids as N. stramineus (p. 8)."),
    ("Stulil", "Mexico"): ("1005089", "S. lilium as now restricted is South American; Mexican populations are S. parvidens."),
    ("Stulil", "Martinique"): ("1005071", "MDD's only Sturnira on Martinique is S. angeli, formerly S. lilium angeli."),
    ("Stulud", "Mexico"): ("1005079", "S. ludovici as now restricted does not occur in Mexico; MDD's Mexican species of that group is S. hondurensis."),
}
PARKED = {
    ("Ptepar", "Mexico"): "split; P. mesoamericanus and P. mexicanus both occur in Mexico and the deposit gives no locality",
    ("Molsin", "Mexico"): "the authors pooled Molossus alvarezi with M. sinaloae (p. 8); both occur in Mexico",
    ("Anogeo", "Panama"): "split; A. peruana and A. cultrata both occur in Panama",
    ("Stulil", "FrenchGuiana"): "split; S. lilium as now restricted does not occur in French Guiana, and two other Sturnira do",
    ("Tracir", "Brazil"): "split; T. cirrhosus and T. ehrhardti both occur in Brazil",
}
COUNTRY_NAMES = {"FrenchGuiana": "French Guiana", "CostaRica": "Costa Rica", "USA": "United States", "Unknown": ""}

PARAMETERS = [  # (registry id, deposit column, unit)
    ("peak_frequency", "FreqMaxPwr", "kHz"), ("characteristic_frequency", "Fc", "kHz"),
    ("max_frequency", "HiFreq", "kHz"), ("min_frequency", "LowFreq", "kHz"),
    ("start_frequency", "StartF", "kHz"), ("end_frequency", "EndF", "kHz"),
    ("knee_frequency", "FreqKnee", "kHz"), ("duration", "CallDuration", "ms"),
]


def fmt(x: float) -> str:
    return f"{x:.2f}"


def main() -> None:
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise SystemExit(f"{SOURCE}: sha256 {digest} does not match the pinned {SOURCE_SHA256}")
    sheet = openpyxl.load_workbook(SOURCE, read_only=True)[SHEET]
    records = sheet.iter_rows(values_only=True)
    header = next(records)
    # (code, country) -> sequence (File) -> list of calls
    groups = defaultdict(lambda: defaultdict(list))
    for values in records:
        call = dict(zip(header, values))
        groups[(call["Spp"], call["Country"])][call["File"]].append(call)

    resolver = TaxonResolver()
    rows, species_seen = [], set()
    for (code, country), sequences in sorted(groups.items()):
        printed = CODES[code]
        note = ""
        if (code, country) in PARKED:
            resolver.unresolved.append((f"{printed} ({country})", PARKED[(code, country)]))
            continue
        if (code, country) in COUNTRY_SPECIES:
            mdd_id, note = COUNTRY_SPECIES[(code, country)]
            species = next(s for s in resolver.accepted.values() if s["id"] == mdd_id)
            method = "manual"
            resolver.matched_manual += 1
        else:
            species, method = resolver.resolve(printed)
            if species is None:
                continue
        # A name that survives a split keeps resolving exactly while its range
        # has shrunk; refuse any recording made outside the current range.
        place = COUNTRY_NAMES.get(country, country)
        countries = {c.rstrip("?") for c in species["countryDistribution"].split("|")}
        if place and place not in countries:
            resolver.unresolved.append((f"{printed} ({country})", f"recorded outside the MDD range of "
                                        f"{species['sciName'].replace('_', ' ')}; the bats may be another species"))
            continue
        species_seen.add(species["id"])
        n_seq = len(sequences)
        n_calls = sum(len(c) for c in sequences.values())
        for parameter, column, unit in PARAMETERS:
            per_seq = [statistics.fmean(float(c[column]) for c in calls)
                       for calls in sequences.values() if all(c[column] is not None for c in calls)]
            if not per_seq:
                continue
            mean = statistics.fmean(per_seq)
            sd = statistics.stdev(per_seq) if len(per_seq) > 1 else None
            rows.append({
                "observation_id": f"zamora2016-{code.lower()}-{country.lower()}", "mdd_id": species["id"],
                "verbatim_taxon_name": printed, "taxon_match_method": method,
                "reference_id": REFERENCE_ID,
                "locator": f"Dryad Data-All-Classifiers.xlsx, sheet {SHEET}, Spp={code}, Country={country}, column {column}",
                "method_id": METHOD_ID, "call_phase": "search", "recording_condition": "unspecified",
                "country": place, "n_individuals": str(len(per_seq)), "n_calls": str(n_calls),
                "parameter": parameter, "statistic": "mean", "value": fmt(mean), "unit": unit,
                "dispersion_type": "sd" if sd is not None else "", "dispersion_value": fmt(sd) if sd is not None else "",
                "verbatim_value": f"{fmt(mean)} (mean of {len(per_seq)} sequence means of SonoBat {column})",
                "quality_flag": "derived",
                "notes": " ".join(filter(None, [
                    f"Summarised by this project from {n_calls} calls in {n_seq} sequences (one bat each): "
                    "the mean of per-sequence means, SD across sequences.", note])),
            })

    path = write_rows(REFERENCE_ID, rows)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(rows), len(species_seen), resolver)
    print(f"  -> {path}")
    if review:
        print(f"  -> {review} (needs a human decision)")


if __name__ == "__main__":
    main()
