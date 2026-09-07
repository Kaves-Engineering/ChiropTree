"""Import Table 1 of Obrist, Boesch & Flückiger (2004).

Source: "Variability in echolocation call design of 26 Swiss bat species:
consequences, limits and options for automated field identification with a
synergetic pattern recognition approach", Mammalia 68(4):307-322,
DOI 10.1515/mamm.2004.030. Table 1 is on p. 314.

Table 1 is a scanned page with no machine-readable text layer, so the values
below were transcribed by hand from the open-access PDF held by the authors'
institutional repository (DORA WSL). The file's sha256 is recorded in the
reference record so the transcription can be re-checked against the exact
bytes that were read. Decimal commas in the original are written as points.

Two pieces of context that the parameters alone do not convey, both taken
from the paper:

- Recordings were made "mostly when releasing identified bats", so
  recording_condition is hand_release, not free flight. The authors state
  plainly that "recordings made directly after releasing hand-identified bats
  differ from those recorded later in search flight" and that this "leaves
  some insecurity regarding the population variance". Tadarida teniotis is the
  stated exception, recorded in free hunting flight.
- Analysis used a fixed 26 ms window. The table caption marks values that the
  window truncated in italics, which cannot be recovered from the scan; the
  methods do say explicitly that most species fit the window "except
  Rhinolophidae", so those two species' rows are flagged here. See
  TRUNCATION_NOTE.

Run:  uv run data/build_obrist_calls.py
"""
from call_import_lib import TaxonResolver, report, write_review, write_rows

REFERENCE_ID = "obrist-2004"
METHOD_ID = "obrist-2004-canary"

TRUNCATION_NOTE = (
    "Calls of this species exceed the paper's fixed 26 ms analysis window, so "
    "this value is measured on a truncated call. Table 1 marks affected values "
    "in italics, which are not recoverable from the scanned page; the flag here "
    "is applied from the methods statement that Rhinolophidae exceed the window. "
    "Applied to duration and minimum frequency only, since truncation removes "
    "the end of the call: that shortens the measured duration and raises the "
    "measured lowest frequency, while peak and highest frequency sit in the CF "
    "portion present from call onset. That last point is our inference from the "
    "stated mechanism, not the paper's own marking, and should be checked "
    "against a clean copy of the table."
)

# Species, N, then (mean, sd) for DUR ms, LFR kHz, PFR kHz, HFR kHz.
# Column meanings from the caption: call duration (DUR), lowest call frequency
# (LFR), frequency of peak energy (PFR), highest frequency (HFR).
TABLE1 = [
    ("Myotis bechsteinii",        65, (4.3, 0.8), (26.5, 2.9), (48.4, 6.6), (103.5, 12.7)),
    ("Myotis blythii",           100, (3.3, 0.7), (24.5, 4.4), (53.2, 10.9), (106.2, 14.1)),
    ("Myotis brandtii",          100, (4.6, 1.1), (27.5, 3.1), (45.7, 4.9), (103.6, 12.8)),
    ("Myotis capaccinii",        100, (5.2, 1.1), (32.0, 2.6), (45.1, 4.3), (86.8, 8.4)),
    ("Myotis daubentonii",       100, (3.9, 0.9), (27.3, 3.0), (42.7, 3.5), (81.2, 8.0)),
    ("Myotis emarginatus",       100, (3.6, 0.7), (36.3, 2.8), (54.5, 7.4), (113.1, 12.5)),
    ("Myotis myotis",            100, (6.0, 1.7), (22.2, 2.6), (37.1, 4.0), (86.0, 11.3)),
    ("Myotis mystacinus",        100, (3.6, 0.5), (27.9, 3.5), (46.8, 5.6), (99.7, 12.6)),
    ("Myotis nattereri",         100, (4.1, 1.1), (14.0, 4.0), (40.4, 8.8), (108.6, 18.6)),
    ("Barbastella barbastellus", 100, (4.3, 1.0), (25.7, 2.2), (36.0, 4.8), (48.3, 3.9)),
    ("Plecotus auritus",         100, (2.9, 0.6), (22.7, 1.7), (37.7, 5.1), (55.7, 5.6)),
    ("Plecotus austriacus",      100, (5.8, 1.4), (18.0, 2.3), (27.6, 2.5), (45.3, 3.3)),
    ("Hypsugo savii",             72, (7.3, 1.0), (28.8, 0.8), (34.9, 2.0), (48.3, 7.2)),
    ("Pipistrellus kuhlii",      100, (6.3, 0.9), (33.6, 1.3), (39.5, 1.8), (63.6, 12.8)),
    ("Pipistrellus nathusii",    100, (6.9, 1.4), (36.1, 1.1), (41.3, 2.2), (61.5, 13.9)),
    ("Pipistrellus pipistrellus", 100, (6.3, 0.9), (42.6, 1.4), (47.4, 2.0), (73.8, 15.9)),
    ("Pipistrellus pygmaeus",    100, (6.0, 0.9), (51.5, 1.8), (56.2, 2.4), (84.1, 16.5)),
    ("Miniopterus schreibersii", 100, (6.2, 0.8), (47.4, 1.2), (53.9, 3.8), (87.3, 11.0)),
    ("Eptesicus serotinus",      100, (10.9, 2.4), (22.4, 1.2), (26.8, 1.8), (47.2, 7.4)),
    ("Eptesicus nilssonii",      100, (10.7, 1.6), (24.6, 1.1), (29.8, 1.6), (48.2, 8.8)),
    ("Vespertilio murinus",      100, (15.0, 3.8), (20.2, 1.4), (24.6, 2.2), (35.8, 10.5)),
    ("Nyctalus leisleri",         19, (9.3, 3.9), (22.1, 2.1), (27.4, 5.1), (49.4, 14.9)),
    ("Nyctalus noctula",         100, (14.4, 3.4), (17.7, 2.8), (22.1, 3.1), (33.8, 11.6)),
    ("Tadarida teniotis",         42, (16.8, 2.4), (8.0, 0.7), (11.4, 0.8), (15.3, 2.5)),
    ("Rhinolophus hipposideros", 100, (21.6, 4.4), (89.8, 10.9), (107.5, 3.7), (110.6, 1.7)),
    ("Rhinolophus ferrumequinum", 100, (22.7, 4.9), (69.1, 8.1), (79.7, 4.7), (84.1, 0.9)),
]

PARAMETERS = [
    (0, "duration", "ms"),
    (1, "min_frequency", "kHz"),
    (2, "peak_frequency", "kHz"),
    (3, "max_frequency", "kHz"),
]

# Stated in the methods as the one species not recorded after hand release.
FREE_FLYING = {"Tadarida teniotis"}
# Named in the methods as exceeding the 26 ms analysis window.
TRUNCATED_GENERA = {"Rhinolophus"}
# Parameters that truncating the end of a call actually distorts.
TRUNCATION_AFFECTS = {"duration", "min_frequency"}


def main() -> None:
    resolver = TaxonResolver()
    rows = []
    species_seen = set()

    for name, n_calls, *values in TABLE1:
        species, method = resolver.resolve(name)
        if species is None:
            continue
        species_seen.add(species["id"])
        truncated = name.split()[0] in TRUNCATED_GENERA

        context = {
            "observation_id": f"obrist2004-{species['id']}",
            "mdd_id": species["id"],
            "verbatim_taxon_name": name,
            "taxon_match_method": method,
            "reference_id": REFERENCE_ID,
            "locator": "Table 1, p. 314",
            "method_id": METHOD_ID,
            "call_phase": "search",
            "recording_condition": ("free_flying_wild" if name in FREE_FLYING
                                    else "hand_release"),
            "country": "Switzerland",
            "n_calls": str(n_calls),
        }

        for index, parameter, unit in PARAMETERS:
            mean, sd = values[index]
            affected = truncated and parameter in TRUNCATION_AFFECTS
            rows.append({
                **context,
                "parameter": parameter,
                "statistic": "mean",
                "value": f"{mean:g}",
                "unit": unit,
                "dispersion_type": "sd",
                "dispersion_value": f"{sd:g}",
                "verbatim_value": f"{mean:g} ± {sd:g}".replace(".", ","),
                "quality_flag": "suspect" if affected else "ok",
                "notes": TRUNCATION_NOTE if affected else "",
            })

    path = write_rows(REFERENCE_ID, rows)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(rows), len(species_seen), resolver)
    print(f"  -> {path}")
    if review:
        print(f"  -> {review} (needs a human decision)")


if __name__ == "__main__":
    main()
