"""Import Table 2 from Pham et al. (2021), Vietnamese urban bats.

Run: ``uv run data/build_pham_2021_vietnam_calls.py``.

Only the four rows labelled "This study" are imported.  The other Table 2
rows are explicitly attributed to studies in India, Thailand, Malaysia, and
Nepal, so treating this regional comparison table as new Vietnam observations
would double-count and misplace their evidence.
"""
import hashlib
from pathlib import Path

from call_import_lib import TaxonResolver, report, write_review, write_rows


REFERENCE_ID = "pham-2021-vietnam"
SOURCE = Path(__file__).parent / "raw" / "pham-2021-vietnam.pdf"
SOURCE_SHA256 = "541183622f18e300a7ebf1e314b82d07d8216bdc95fefff299807fe436c59694"

# Species, number of analysed calls, then mean|SD in Table 2 order:
# duration, FmaxE, highest frequency, lowest frequency, start frequency,
# terminal frequency, bandwidth.  Scotophilus kuhlii's printed duration SD is
# retained exactly, despite its implausible magnitude (see quality flag below).
RECORDS = [
    ("Scotophilus kuhlii", 49, "5.48|23.8,45.64|3.32,76.27|6.56,38.94|2.40,60.41|7.21,42.66|3.18,37.32|7.06"),
    ("Taphozous melanopogon", 43, "6.45|1.13,33.07|5.90,59.10|5.11,23.19|1.25,32.70|3.27,31.09|5.12,35.91|5.22"),
    ("Pipistrellus javanicus", 50, "4.78|1.06,50.30|5.09,88.27|3.50,42.27|2.66,68.23|4.05,48.03|3.61,46.00|3.48"),
    ("Myotis hasseltii", 91, "3.86|0.50,50.06|3.09,84.63|5.42,38.82|3.12,67.55|3.75,47.80|2.31,45.81|6.31"),
]
PARAMETERS = (
    ("duration", "ms"), ("peak_frequency", "kHz"), ("max_frequency", "kHz"),
    ("min_frequency", "kHz"), ("start_frequency", "kHz"),
    ("end_frequency", "kHz"), ("bandwidth", "kHz"),
)


def main() -> None:
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise RuntimeError(f"Unexpected source SHA-256: {digest}")

    resolver, rows, species_seen = TaxonResolver(), [], set()
    for number, (name, calls, packed) in enumerate(RECORDS, start=1):
        species, match_method = resolver.resolve(name)
        if species is None:
            continue
        species_seen.add(species["id"])
        for (parameter, unit), printed in zip(PARAMETERS, packed.split(",")):
            value, sd = printed.split("|")
            suspect = name == "Scotophilus kuhlii" and parameter == "duration"
            note = (
                "Table 2, Vietnam row labelled 'This study'; study calls were recorded "
                "from bats flying singly in a 2 x 4 x 2 m tent, with additional "
                "free-flying recordings used for comparison. Table 2 does not assign "
                "each reported summary to a recording condition."
            )
            if suspect:
                note += " The printed duration dispersion is 23.8 ms; retained verbatim and flagged suspect."
            rows.append({
                "observation_id": f"pham2021-table2-{number}", "mdd_id": species["id"],
                "verbatim_taxon_name": name, "taxon_match_method": match_method,
                "reference_id": REFERENCE_ID,
                "locator": f"Table 2, Vietnam / This study row, {parameter} column",
                "method_id": "pham-2021-vietnam-tent-and-free-flight",
                "call_phase": "unspecified", "recording_condition": "unspecified",
                "country": "Vietnam", "n_calls": calls, "parameter": parameter,
                "statistic": "mean", "value": value, "unit": unit,
                "dispersion_type": "sd", "dispersion_value": sd,
                "verbatim_value": f"{value} ± {sd}",
                "quality_flag": "suspect" if suspect else "ok", "notes": note,
            })

    path = write_rows(REFERENCE_ID, rows)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(rows), len(species_seen), resolver)
    print(f"  -> {path}")
    if review:
        print(f"  -> {review} (needs a human decision)")


if __name__ == "__main__":
    main()
