"""Import publicly table-verified Saudi call values from Al Obaid et al. (2026).

The publisher blocks automated source-file retrieval. This intentionally small
transcription therefore contains only cells exposed in the public Table 2, 3,
4 and 7 renderings, each with a precise locator. It must not be expanded from
search snippets or inferred rows.
"""
from call_import_lib import TaxonResolver, report, write_review, write_rows


REFERENCE_ID = "al-obaid-2026-saudi"
PARAMETERS = (("start_frequency", "kHz"), ("end_frequency", "kHz"),
              ("peak_frequency", "kHz"), ("duration", "ms"))

# Taxon, locality, calls, standardized condition, then mean|SD|min|max values
# ordered as SF, EF, Fmax, Dur.  Values are verbatim Table 3/4 transcriptions.
RECORDS = [
    ("Table 2", "Rhinopoma cystops", "As Saqeed Island", 164, "unspecified", "38.4|2.1|35.1|42.1,31.9|6.9|13.6|41.2,36.5|5.5|18.8|42.1,6.6|3.6|1.2|15.7"),
    ("Table 2", "Rhinopoma cystops", "Biljarashi", 46, "unspecified", "36.5|0.6|36.0|38.1,31.1|3.9|24.9|36.0,35.7|1.7|30.8|38.1,4.2|1.8|3.9|7.3"),
    ("Table 2", "Rhinopoma cystops", "Al Buseerah", 127, "unspecified", "34.2|0.7|32.3|36.0,32.9|0.6|31.3|34.2,34.8|0.7|32.3|36.0,5.6|3.2|1.1|14.9"),
    ("Table 3", "Triaenops persicus", "As Saqeed Island", 36, "unspecified", "75|1.71|72.7|78.4,70.3|3.4|66.7|78.4,75.9|1.1|74.1|78.4,7.17|1.2|5.7|9.4"),
    ("Table 3", "Asellia patrizii", "As Saqeed Island", 290, "unspecified", "134.6|3.2|129.0|138.3,121.5|12.8|108.1|114.3,135.2|2.4|133|139,4.9|2.9|1.6|10.7"),
    ("Table 3", "Asellia tridens", "Ben Rasheed cave", 321, "unspecified", "117.2|2.8|105.3|121.1,104.3|6.4|100|121.2,116.7|3.8|100|121.2,5.9|2.9|1.4|11.1"),
    ("Table 3", "Asellia tridens", "Luga cave", 1725, "unspecified", "111.1|2.9|100.0|121.2,108.1|4.2|100|121.2,111.2|2.7|102.6|117.7,5.11|2.5|1.07|11.8"),
    ("Table 3", "Asellia tridens", "Al Summan", 37, "unspecified", "113.53|1.9|111.1|117.6,108.6|5.1|100.0|117.7,113.5|16|111.1|117.6,5.6|1.8|1.35|9.9"),
    ("Table 3", "Asellia tridens", "Al Madinah", 13, "unspecified", "118.2|1.9|114.3|121.2,114.1|5.9|105.3|121.2,116.6|5.0|105.3|121.2,5.1|2.6|1.2|9.6"),
    ("Table 4", "Rhinolophus clivosus", "Ben Rasheed cave", 33, "free_flying_wild", "81.7|5.1|74.7|90.3,75.3|4.4|71.2|90.3,90.2|0.3|71.2|90.3,47.9|5.1|34|51.6"),
    ("Table 4", "Rhinolophus clivosus", "Bani Malik", 177, "unspecified", "89.9|3.3|81.6|95.2,82.7|8.3|71.4|95.2,91.7|1.4|86.9|93.0,22.2|7.2|10.0|38.5"),
    ("Table 4", "Rhinolophus clivosus", "Wadi Al Menshar", 27, "free_flying_wild", "87.8|3.2|78.4|90.9,86.7|4.6|74.0|90.9,88.6|0.9|86.9|91.9,12.1|8.9|1.6|28"),
    # Table 7 cells are publicly rendered by the article landing page.  The
    # study says these calls were recorded while bats were flying, but does not
    # distinguish a release recording from an unmanipulated pass for each row.
    ("Table 7", "Rhyneptesicus nasutus", "Unayzah", 357, "unspecified", "43.9|2.2|38.8|55.6,42.0|0.9|9.2|46.5,43.5|1.5|40.0|48.2,7.5|2.5|1.1|11.9"),
    ("Table 7", "Rhyneptesicus nasutus", "Al Oqdah Water Falls", 88, "unspecified", "47.1|2.1|43.9|54.8,45.8|1.3|44.0|50.0,46.7|1.3|43.9|52.6,5.0|2.4|1.1|14.2"),
]


def main() -> None:
    resolver, rows, species_seen = TaxonResolver(), [], set()
    for number, (table, name, locality, calls, condition, packed) in enumerate(RECORDS, start=1):
        species, match_method = resolver.resolve(name)
        if species is None:
            continue
        species_seen.add(species["id"])
        for (parameter, unit), printed in zip(PARAMETERS, packed.split(",")):
            value, sd, low, high = printed.split("|")
            suspect = ((name == "Asellia patrizii" and parameter == "end_frequency")
                       or (name == "Rhyneptesicus nasutus" and locality == "Unayzah"
                           and parameter == "end_frequency"))
            note = table
            note += f", {name} at {locality}; reported n={calls} calls."
            if name == "Asellia patrizii" and parameter == "end_frequency":
                note += " Source table prints EF mean 121.5 with range 108.1-114.3, an internal inconsistency retained verbatim and flagged suspect."
            if name == "Rhyneptesicus nasutus" and locality == "Unayzah" and parameter == "end_frequency":
                note += " Source table prints EF range 9.2-46.5; retained verbatim and flagged suspect because its lower bound is unusually distant from the reported mean."
            rows.append({
                "observation_id": f"alobaid2026-{number}", "mdd_id": species["id"],
                "verbatim_taxon_name": name, "taxon_match_method": match_method,
                "reference_id": REFERENCE_ID, "locator": f"{note.split(';')[0]}, {parameter} column",
                "method_id": "al-obaid-2026-saudi-anabat", "call_phase": "unspecified",
                "recording_condition": condition, "country": "Saudi Arabia", "locality": locality,
                "n_calls": calls, "parameter": parameter, "statistic": "mean", "value": value,
                "value_min": low, "value_max": high, "unit": unit, "dispersion_type": "sd",
                "dispersion_value": sd, "verbatim_value": f"{value} ± {sd} ({low}-{high})",
                "quality_flag": "suspect" if suspect else "definition_unstated", "notes": note,
            })
    path = write_rows(REFERENCE_ID, rows)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(rows), len(species_seen), resolver)
    print(f"  -> {path}")
    if review:
        print(f"  -> {review} (needs a human decision)")


if __name__ == "__main__":
    main()
