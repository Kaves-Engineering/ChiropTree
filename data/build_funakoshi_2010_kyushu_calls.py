"""Import Tables 2 and 3 of Funakoshi (2010): scanning calls of 13 Kyushu bats.

Funakoshi K (2010) Acoustic identification of thirteen insectivorous bat
species from the Kyushu District, Japan. Mammalian Science 50(2): 165-175
(in Japanese, English tables). Open on J-STAGE.

Both tables give, per species (Table 2: per species and locality), the number
of bats and the mean ± SD (min-max) of per-bat means for peak frequency (PF),
end frequency (EF, Table 3 only) and duration (D) of "scanning" calls (精査音).
The methods (p. 166) define these as calls recorded at roost emergence more
than 10 m from the roost, from bats passing along forest roads, after release,
while perched on branches or in caves, and while circling in a net enclosure,
so recording_condition is 'unspecified'. Table 4 (search-phase calls of six
species) is not imported: its second row per species is not labelled.

Names, checked against MDD v2.5 ranges for Japan:
- "Rhinolophus ferrumequinum" in Japan is R. nippon;
- "Myotis nattereri" in Japan is M. bombinus;
- "Murina leucogaster" in Japan is M. hilgendorfi;
- Pipistrellus abramus resolves through MDD's MSW3 name to Alionoctula abramus.

Fetch: https://www.jstage.jst.go.jp/article/mammalianscience/50/2/50_2_165/_pdf
to data/raw/funakoshi-2010-kyushu.pdf.
Run: uv run data/build_funakoshi_2010_kyushu_calls.py
"""
import hashlib
from pathlib import Path

from call_import_lib import TaxonResolver, report, write_review, write_rows

REFERENCE_ID = "funakoshi-2010-kyushu"
METHOD_ID = "funakoshi-2010-kyushu-scanning"
SOURCE = Path(__file__).parent / "raw" / "funakoshi-2010-kyushu.pdf"
SOURCE_SHA256 = "630bbaf61e2bb284569453a016555cd1a371aff7ef724bd5a7d505e9dd4d8c3f"

# printed name -> (MDD id, why), for names whose Japanese bats MDD now places elsewhere
JAPAN = {
    "Rhinolophus ferrumequinum": ("1004722", "Japanese populations of R. ferrumequinum are R. nippon in MDD v2.5."),
    "Myotis nattereri": ("1005378", "Japanese populations of M. nattereri are M. bombinus in MDD v2.5."),
    "Murina leucogaster": ("1005335", "Japanese populations of M. leucogaster are M. hilgendorfi in MDD v2.5."),
}

# (table, species as printed, locality, n bats, PF "mean|sd|min|max", EF or None, D)
ROWS = [
    ("2", "Rhinolophus ferrumequinum", "Kagoshima (Shibushi)", 10, "69.7|0.33|69.3|70.3", None, "47.9|8.8|36.3|65.0"),
    ("2", "Rhinolophus ferrumequinum", "Ooita (Notsuharu)", 10, "68.5|0.19|68.3|68.8", None, "44.8|5.0|39.5|55.0"),
    ("2", "Rhinolophus cornutus", "Kagoshima (Shibushi)", 10, "109.6|0.63|108.7|110.8", None, "45.0|6.0|34.0|52.3"),
    ("2", "Rhinolophus cornutus", "Kumamoto (Kumamura)", 7, "108.2|0.49|107.1|108.8", None, "43.7|3.2|38.3|48.0"),
    ("2", "Rhinolophus cornutus", "Ooita (Notsuharu)", 10, "108.3|0.59|107.3|109.0", None, "44.8|5.2|38.5|54.0"),
    ("2", "Rhinolophus cornutus", "Fukuoka (Saigawa)", 10, "107.7|0.38|107.1|108.1", None, "44.9|4.4|38.4|51.2"),
    ("3", "Myotis nattereri", "Kagoshima and Kumamoto", 10, "36.4|2.34|32.6|40.1", "29.3|0.63|28.2|30.3", "2.4|0.48|2.4|2.5"),
    ("3", "Myotis macrodactylus", "Kagoshima and Kumamoto", 10, "49.5|2.31|47.4|53.7", "38.4|2.83|35.4|45.3", "3.4|0.38|3.0|4.1"),
    ("3", "Myotis pruinosus", "Miyazaki (Aya) and Kumamoto (Yamato)", 10, "52.4|1.73|49.7|54.7", "38.7|2.47|33.0|41.8", "2.8|0.16|2.6|3.0"),
    ("3", "Pipistrellus abramus", "Kagoshima", 10, "46.2|2.64|39.3|48.7", "40.9|0.34|40.1|41.3", "3.2|0.15|2.9|3.4"),
    ("3", "Miniopterus fuliginosus", "Kagoshima and Kumamoto", 10, "51.9|1.40|48.1|52.8", "49.9|1.21|46.6|50.8", "4.5|0.16|4.3|4.7"),
    ("3", "Murina ussuriensis", "Miyazaki", 10, "62.2|2.36|58.4|65.7", "47.9|5.11|40.7|59.6", "1.9|0.16|1.7|2.2"),
    ("3", "Murina ryukyuana", "Amami-Oshima and Tokunoshima", 6, "58.3|3.05|54.4|62.3", "43.6|1.52|41.2|45.9", "1.8|0.10|1.6|1.9"),
    ("3", "Murina leucogaster", "Miyazaki", 10, "49.6|4.13|44.0|54.7", "27.4|1.38|25.3|29.4", "2.5|0.97|2.3|2.6"),
    ("3", "Vespertilio sinensis", "Fukuoka (sea cave, Nishi-ku)", 10, "33.2|5.41|24.5|41.0", "21.6|1.41|19.5|23.5", "3.2|1.03|2.4|5.8"),
    ("3", "Nyctalus aviator", "Kagoshima (Soo)", 10, "19.7|0.39|19.0|20.3", "15.8|1.60|13.4|17.7", "8.6|0.57|7.9|9.5"),
    ("3", "Tadarida insignis", "Miyazaki (Biroujima)", 10, "15.4|0.73|14.1|16.5", "9.7|1.66|8.2|12.6", "13.6|1.31|11.8|15.8"),
]
PARAMS = (("peak_frequency", 4, "kHz", "PF"), ("end_frequency", 5, "kHz", "EF"), ("duration", 6, "ms", "D"))


def main() -> None:
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise SystemExit(f"{SOURCE}: sha256 {digest} does not match the pinned {SOURCE_SHA256}")
    resolver = TaxonResolver()
    by_id = {s["id"]: s for s in resolver.accepted.values()}
    rows, seen = [], set()
    for number, record in enumerate(ROWS, start=1):
        table, name, locality, n_bats = record[:4]
        note = ""
        if name in JAPAN:
            mdd_id, note = JAPAN[name]
            species, method = by_id[mdd_id], "manual"
            resolver.matched_manual += 1
        else:
            species, method = resolver.resolve(name)
            if species is None:
                continue
        if "Japan" not in species["countryDistribution"]:
            raise SystemExit(f"{name} resolved to {species['sciName']}, which MDD does not list for Japan")
        seen.add(species["id"])
        for parameter, index, unit, label in PARAMS:
            if record[index] is None:
                continue
            mean, sd, low, high = record[index].split("|")
            rows.append({
                "observation_id": f"funakoshi2010-t{table}-{number}", "mdd_id": species["id"],
                "verbatim_taxon_name": name, "taxon_match_method": method, "reference_id": REFERENCE_ID,
                "locator": f"Table {table}, {name}, {locality}, {label} column", "method_id": METHOD_ID,
                "call_phase": "unspecified", "recording_condition": "unspecified",
                "country": "Japan", "locality": locality, "n_individuals": str(n_bats),
                "parameter": parameter, "statistic": "mean", "value": mean,
                "value_min": low, "value_max": high, "unit": unit,
                "dispersion_type": "sd", "dispersion_value": sd,
                "verbatim_value": f"{mean}±{sd} ({low}–{high})", "quality_flag": "ok",
                "notes": " ".join(filter(None, [
                    "Scanning calls (精査音): emergence, passing, release, perched and enclosure recordings pooled; "
                    "mean of per-bat means.", note])),
            })
    path = write_rows(REFERENCE_ID, rows)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(rows), len(seen), resolver)
    print(f"  -> {path}")
    if review:
        print(f"  -> {review} (needs a human decision)")


if __name__ == "__main__":
    main()
