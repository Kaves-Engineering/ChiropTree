"""Import the directly tabulated Table 1 call means from Hughes et al. (2011).

The article is embedded in the open Thai Research Fund report cached at
``data/raw/hughes-2011-thailand.pdf``.  The compact transcription below stores
only individual factual measurements, not the copyrighted source table.

Run: ``uv run data/build_hughes_2011_thailand_calls.py``.
"""
import hashlib
from pathlib import Path

from call_import_lib import TaxonResolver, report, write_review, write_rows
from calls.parameter_registry import Registry


REFERENCE_ID = "hughes-2011-thailand"
SOURCE = Path(__file__).parent / "raw" / "hughes-2011-thailand.pdf"
SOURCE_SHA256 = "891dd55308fd08c5e86273c5ee4d016ff8c7ca6e05efeef684755aa676e00327"

# Each record is taxon, calls, then d/FMAXE/hf/lf/sf/tf/fr/pi as mean|SD.
# It is a transcription of Table 1, pp. 448-449 of the embedded article.
TABLE = [
    ("Coelops frithii", 17, "8.18|3.48,119.5|8.89,154.59|17.18,105.29|3.37,151.24|19.29,105.29|3.37,49.29|11.77,11.83|3.69"),
    ("Eudiscopus denticulus", 2, "6.54|0.23,53.45|0.49,135.5|16.26,46|1.41,101|1.14,51.5|3.55,89.5|17.68,78.5|5.52"),
    ("Kerivoula hardwickii", 88, "3.15|2.67,118.25|11.87,173.39|29.87,89.93|7.03,169.57|28.80,90.73|8.15,83.47|30.05,15.55|4.92"),
    ("Murina cyclotis", 28, "1.78|1.2,93.81|7.63,122.59|44.88,53.42|23.54,121.38|44.58,57.35|25.87,69.17|28.15,44.28|21.92"),
    ("Murina suilla", 34, "2.91|1.90,101.93|10.95,146.56|13.56,73.95|11.36,142.62|23.99,82.42|17.99,72.61|11.22,49.78|16.75"),
    ("Murina turbinares", 2, "2.88|0.11,88.7|0.28,132.00|0,69.50|20.51,132|0,55.5|0.71,62.5|20.51,25.13|0"),
    ("Myotis muricola", 49, "5.21|2.5,82.27|16.63,137.14|12.79,55.33|6.81,117.98|17.10,55.58|10.13,81.80|16.10,59.44|14.73"),
    ("Myotis horsfieldii", 8, "3.17|2.60,56.93|7.98,134.25|9.60,38.38|3.46,87.25|13.56,39.63|5.93,95.88|6.34,30.44|24.1"),
    ("Myotis siligorensis", 44, "3.58|1.61,73.16|4.64,141.12|31.7,62.5|4.06,122.84|21.93,63.1|4.26,78.65|33.45,54.35|21.55"),
    ("Miniopterus magnater", 10, "4.35|1.52,47.36|2.48,122.2|23.89,36.2|2.97,85.3|9.89,42.3|17.02,86|22.83,65.21|18.93"),
    ("Miniopterus australis", 5, "4.42|1.03,61.46|18.15,131.6|5.68,47.2|8.98,95.4|18.22,47.2|8.98,84.4|14.54,57.96|0.9"),
    ("Miniopterus medius", 6, "1.73|0.84,61.23|3.09,158.17|17.7,61|16.71,107.5|18.25,68.83|20.39,97.17|27.56,50.42|15.35"),
    ("Miniopterus pusillus", 11, "4.65|3.17,62.85|3.56,109.73|17.74,52.28|7.7,106.17|12.51,52.28|7.7,57.45|18.99,47.75|16.03"),
    ("Tylonycteris pachypus", 5, "1.56|0.8,50.46|13.05,134.4|6.69,39.4|4.39,95.2|3.96,39.8|4.87,95|7.9,26.77|12.15"),
    ("Tylonycteris robustula", 4, "3.3|2.7,51.03|5.57,137.25|8.26,39.75|5.38,93.75|3.77,41|4.32,97.5|3.42,12.84|3.81"),
    ("Emballonura monticola", 17, "5.42|2.88,51.24|7.82,118.46|27.17,34.54|18.99,53.55|13.98,38.91|15.91,64.18|51.41,53.79|28.7"),
    ("Saccolaimus saccolaimus", 4, "3.85|2.11,32.03|8.85,60.25|12.09,17.75|0.98,36.75|1.89,26.75|18,42.5|11.93,46.8|0"),
    ("Taphozous longimanus", 11, "4.95|0.33,30.83|1.58,96.91|6.99,8.73|2.33,32.27|0.9,8.36|2.06,88.18|8.11,30.45|1.19"),
    ("Taphozous melanopogon", 33, "6.02|3.4,29.71|2.67,76.15|20.18,20.37|6.2,36.6|10.44,22.58|5.58,55.78|20.32,89.78|16.18"),
    ("Megaderma spasma", 44, "2.69|1.39,72.99|12.52,108.93|8.24,20.8|12.44,73.92|17.8,30.65|15.03,79.13|16.08,30.53|13.69"),
    ("Megaderma lyra", 1, "1.8|,62.10|,106.00|,35.00|,66.00|,35.00|,71.00|,71.80|"),
    ("Nycteris tragata", 16, "2.87|0.88,97.64|10.02,120.63|5.4,69.63|11.05,111.88|18.11,71.13|11.99,51|10.11,36.66|20.41"),
]

SOURCE_HEADINGS = ("duration", "FmaxE", "max frequency", "min frequency", "start frequency", "end frequency", "bandwidth", "inter-pulse interval")
UNITS = ("ms", "kHz", "kHz", "kHz", "kHz", "kHz", "kHz", "ms")


def main() -> None:
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise RuntimeError(f"Unexpected source SHA-256: {digest}")

    registry, resolver = Registry(), TaxonResolver()
    # The Table 1 spelling is inconsistent with the methods' M. tubinaris.
    resolver.add_manual({"Murina turbinares": "1005354"})
    parameters = [registry.resolve(heading) for heading in SOURCE_HEADINGS]
    if any(parameter is None for parameter in parameters):
        raise RuntimeError("A Hughes Table 1 heading is absent from the parameter registry")

    rows, seen = [], set()
    for row_number, (printed_name, calls, packed) in enumerate(TABLE, start=1):
        species, match_method = resolver.resolve(printed_name)
        if species is None:
            continue
        seen.add(species["id"])
        values = [cell.split("|", 1) for cell in packed.split(",")]
        for heading, parameter, unit, (mean, sd) in zip(SOURCE_HEADINGS, parameters, UNITS, values):
            rows.append({
                "observation_id": f"hughes2011-table1-{row_number}",
                "mdd_id": species["id"],
                "verbatim_taxon_name": printed_name,
                "taxon_match_method": match_method,
                "reference_id": REFERENCE_ID,
                "locator": f"Table 1, {printed_name} row, {heading} column",
                "method_id": "hughes-2011-thailand-time-expansion",
                "call_phase": "unspecified",
                "recording_condition": "hand_release",
                "country": "Thailand",
                "locality": "primarily southern Thai peninsula; range of Thailand localities",
                "n_calls": calls,
                "parameter": parameter,
                "statistic": "mean",
                "value": mean,
                "unit": unit,
                "dispersion_type": "sd" if sd else "",
                "dispersion_value": sd,
                "verbatim_value": mean if not sd else f"{mean} ± {sd}",
                "quality_flag": "definition_unstated",
                "notes": "Table 1 mean and SD. The paper explicitly defines pi as start-to-start pulse interval; it warns that start/end values depend on the background-noise boundary. The reported free flight follows hand release in relatively cluttered surroundings.",
            })

    path = write_rows(REFERENCE_ID, rows)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(rows), len(seen), resolver)
    print(f"  -> {path}")
    if review:
        print(f"  -> {review} (needs a human decision)")


if __name__ == "__main__":
    main()
