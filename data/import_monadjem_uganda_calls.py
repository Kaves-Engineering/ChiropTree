"""Import taxonomically resolved Table 2 observations from Monadjem et al. (2011)."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "calls" / "monadjem-2011.csv"
FIELDS = "observation_id mdd_id verbatim_taxon_name taxon_match_method reference_id locator method_id call_phase call_variant variant_label signal_direction recording_condition habitat_class country locality date_or_season n_individuals n_calls parameter statistic value value_min value_max unit dispersion_type dispersion_value verbatim_value quality_flag notes".split()
TAXA = [
    ("nycteris-arge-low", "1004833", "Nycteris arge", "exact", "low-frequency sequence", "2", [("min_frequency", 21.55, None), ("max_frequency", 22.11, None), ("characteristic_frequency", 21.88, None), ("knee_frequency", 21.77, None), ("duration", 4.1, None)]),
    ("nycteris-arge-high", "1004833", "Nycteris arge", "exact", "high-frequency sequence", "2", [("min_frequency", 46.43, None), ("max_frequency", 47.83, None), ("characteristic_frequency", 46.93, None), ("knee_frequency", 47.23, None), ("duration", 5.9, None)]),
    ("doryrhina-cyclops", "1004568", "Hipposideros cyclops", "manual", "", "6", [("min_frequency", 51.24, .670), ("max_frequency", 51.54, .389), ("characteristic_frequency", 51.37, .459), ("knee_frequency", 51.51, .395), ("duration", 14.5, 2.02)]),
    ("scotophilus-nux", "1005694", "Scotophilus nux", "exact", "", "1", [("min_frequency", 40.71, None), ("max_frequency", 54.05, None), ("characteristic_frequency", 43.01, None), ("knee_frequency", 45.07, None), ("duration", 2.0, None)]),
]
def main():
    rows=[]
    for slug, mdd, taxon, match, variant, n, values in TAXA:
        for parameter, value, sd in values:
            unit = "ms" if parameter == "duration" else "kHz"
            row={field:"" for field in FIELDS}
            row.update(observation_id=f"monadjem-2011-{slug}", mdd_id=mdd, verbatim_taxon_name=taxon, taxon_match_method=match, reference_id="monadjem-2011", locator=f"Table 2, {taxon} row", method_id="monadjem-2011-anabat", call_phase="unspecified", call_variant=slug.split("-")[-1] if variant else "", variant_label=variant, recording_condition="hand_release", country="Uganda", locality="Kibale Forest National Park / Queen Elizabeth National Park", n_individuals=n, parameter=parameter, statistic="mean", value=str(value), unit=unit, dispersion_type="sd" if sd is not None else "", dispersion_value="" if sd is None else str(sd), verbatim_value=f"{value}" if sd is None else f"{value} ± {sd}", quality_flag="definition_unstated", notes="Manually transcribed from Table 2. Public full text was inspected but could not be cached as source bytes; see reference access note.")
            rows.append(row)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    print(f"Wrote {len(rows)} Monadjem rows")
if __name__ == "__main__": main()
