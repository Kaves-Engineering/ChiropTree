"""Shared admission policy for the consolidated upload archive.

The supplied archive's `MASTER_call_records.csv` merges 43 batch worksheets into
one schema. It carries far more than this project can honestly publish, so the
gates below decide what becomes a measurement. They are deliberately strict:
everything they reject stays visible in the archive and in the review file.

Gates, in order:

1. `evidence_class` must be `measured_primary` or `measured_compiled`. The
   archive's own README is explicit that `identification_threshold` is a
   classifier decision boundary and not a measurement, that
   `value_exists_unretrieved` is an acquisition task, and that `unknown_no_data`
   is a claim about the literature. None of those are values.
2. The source must be reachable, so a reader can check it. `cited_not_retrieved`
   and `paywalled` rows are values nobody in this project has seen.
3. `join_confidence` must be `high`. Composite multi-species rows, genus-only
   rows and the archive's known `meta_row` bug class cannot be attached to one
   species.
4. The trait must map to a parameter already in the registry. A trait with no
   home is reported, never coerced into a neighbouring parameter.
5. Tertiary aggregators are refused outright: an encyclopaedia entry restating a
   number is not a source for it.
"""

ADMITTED_EVIDENCE = {"measured_primary", "measured_compiled"}
ADMITTED_ACCESS = {"open", "open_via_intermediary"}

# Wikipedia, EoL/ADW, BioNumbers and a monitoring portal's species accounts.
# Each restates numbers from primary work without being checkable itself, and
# the archive's own notes flag the Wikipedia triplet as unverified.
TERTIARY = {"S4", "S18c", "S-BIONUM", "S20"}

# Master trait -> registry parameter. Frequencies that name the same quantity
# under different house styles are merged; anything whose definition differs is
# kept apart. Traits absent here are reported as unmapped and dropped.
TRAITS = {
    "fmaxE_kHz": "peak_frequency",
    "peak_frequency_kHz": "peak_frequency",
    "frequency_of_max_power_kHz": "peak_frequency",
    "freeflying_Fmax_kHz": "peak_frequency",
    "characteristic_frequency_kHz": "characteristic_frequency",
    "start_frequency_kHz": "start_frequency",
    "end_frequency_kHz": "end_frequency",
    "minimum_frequency_kHz": "min_frequency",
    "low_frequency_kHz": "min_frequency",
    "maximum_frequency_kHz": "max_frequency",
    "high_frequency_kHz": "max_frequency",
    "bandwidth_kHz": "bandwidth",
    "frequency_of_knee_kHz": "knee_frequency",
    "frequency_at_knee_kHz": "knee_frequency",
    "CF_frequency_kHz": "cf_frequency",
    "cf_frequency_kHz": "cf_frequency",
    "Fmax_CF_kHz": "cf_frequency",
    "FC_initial_frequency_kHz": "cf_frequency",
    "fmaxE_FC_initial_kHz": "cf_frequency",
    "resting_frequency_kHz": "resting_frequency",
    "resting_CF_frequency_kHz": "resting_frequency",
    "total_slope_kHz_per_ms": "total_slope",
    "call_duration_ms": "duration",
    "interpulse_interval_ms": "inter_pulse_interval",
    "pulse_interval_ms": "inter_pulse_interval",
    "duty_cycle_pct": "duty_cycle",
    "detection_distance_m": "detection_distance",
    "detection_range_m": "detection_distance",
    "beam_half_amplitude_angle_deg": "beam_half_angle",
    "call_type": "signal_type",
    "call_type_grouping": "signal_type",
    "dominant_harmonic": "harmonic_emphasis",
}

# Traits deliberately not mapped, with the reason, so the report can say why
# rather than listing them as unrecognised.
DECLINED_TRAITS = {
    "preceding_interval_ms": "interval before the call, not between calls; not the registry's inter-pulse interval",
    "start_slope_kHz_per_ms": "no start/end slope parameter in the registry; only dominant and total slope",
    "end_slope_kHz_per_ms": "no start/end slope parameter in the registry; only dominant and total slope",
    "ledge_duration_ms": "no ledge-duration parameter in the registry",
    "dietary_guild": "an ecological trait, not a call parameter",
    "frequency_range_kHz": "a span across unstated parameters; not equivalent to bandwidth",
    "source_level_dB_SPL_rms_at_1m": "source level needs its measurement basis on the method record; the archive does not carry one",
    "source_level_dB_peSPL": "source level needs its measurement basis on the method record; the archive does not carry one",
    "source_level_dB_SPL_10cm": "source level needs its measurement basis on the method record; the archive does not carry one",
    "sample_bulgaria_CF": "a single named sample, not a species-level value",
    "start_frequency_kHz_max": "a bound on a start frequency, not a start frequency",
    "end_frequency_kHz_min": "a bound on an end frequency, not an end frequency",
    "DFA_species_accuracy_pct": "classifier performance, not a property of the call",
    "DFA_classification_note": "classifier performance, not a property of the call",
    "acoustic_overlap_group": "an identification statement, not a measurement",
    "acoustic_species_separability": "an identification statement, not a measurement",
    "ecomorphotype_separability": "an identification statement, not a measurement",
    "call_frequency_alternation": "a behavioural description without a controlled vocabulary here",
    "call_shape_description": "free prose; the registry's call_shape_class is a coded vocabulary",
    "call_structure_note": "free prose",
    "social_call_fmaxE_kHz": "a social call, which needs its own call_phase handling before import",
    "richness_by_elevation": "a community metric, not a species measurement",
    "peak_frequency_vs_body_size": "an allometric statement, not a measurement",
}

# Master context_class -> the project's recording_condition vocabulary.
CONTEXT = {
    "free_flying": "free_flying_wild",
    "hand_release": "hand_release",
    "hand_held": "tethered",
    "enclosure": "flight_room",
    "roost_or_cave": "roost_emergence",
    "other_or_unclear": "unspecified",
    "": "unspecified",
}


def admits(row, sources) -> tuple[bool, str]:
    """Return whether one master row may become a measurement, and why not."""
    key = row["source_key"]
    if key in TERTIARY:
        return False, "tertiary_aggregator"
    if row["evidence_class"] not in ADMITTED_EVIDENCE:
        return False, f"evidence_{row['evidence_class']}"
    if sources.get(key, {}).get("access") not in ADMITTED_ACCESS:
        return False, f"access_{sources.get(key, {}).get('access', 'unknown')}"
    if row["join_confidence"] != "high":
        return False, f"join_{row['join_confidence']}"
    if row["name_status"] in {"meta_row", "composite_multi_species", "genus_level_only"}:
        return False, f"name_{row['name_status']}"
    trait = row["trait"]
    if trait in DECLINED_TRAITS:
        return False, "trait_declined"
    if trait not in TRAITS:
        return False, "trait_unmapped"
    return True, ""


# Master source key -> project reference_id, for sources already in the store.
# The master consolidates the same batch worksheets these were built from, so it
# supersedes the older per-batch importer rather than adding a second copy.
EXISTING = {
    "S-YOH20": "yoh-2020",
    "S-AA18": "arias-aguilar-2018",
    "S-SA-REVIEW": "srinivasulu-2025-southasia",
    "S-SB-W": "szewczak-western-2024",
    "S-SB-E": "szewczak-eastern-2022",
    "S-UGA20": "ugarte-nunez-2020",
    "S-KE19": "webala-2019",
    "S-AC24": "arevalo-cortes-2024",
    "S-ZM25": "taylor-boyd-2025",
    "S-JUNG14": "jung-2014",
    "S-CM18": "bakwo-fils-2018",
    "S-NSW04": "pennay-law-reinhold-2004-nsw",
    "S8": "seibert-2015",
}

# New sources whose citation resolves to a specific, retrievable publication.
NEW_REFERENCES = {
    "S-GF13": "barataud-2013-guyane",
    "S-MY-BORNEO": "mcarthur-2021-borneo",
    "S-SI17": "pennay-lavery-2017-solomons",
    "S-SZ17": "monadjem-2017-swaziland",
    "S-TN23": "dalhoumi-2023-tunisia",
    "S2": "van-de-sijpe-2011",
    "S-KR15": "fukui-2015-korea",
    "S-VN24": "gyorossy-2024-vietnam",
    "S-SONO20": "zamora-gutierrez-2020-sonozotz",
    "S5": "lung-mv-ffh-factsheets",
    "S3": "surlykke-2009",
    "S11": "schuchmann-2010",
    "S31": "rehak-2010",
    "S12": "salsamendi-2012",
    "S23": "rydell-arlettaz-1994",
    "S30": "holderied-2005",
    "S-GESS19": "gessinger-2019",
    "S34": "alberdi-garin-2018",
    "S-SURL13": "surlykke-2013-trachops",
}

# Refused on provenance, not on content. A1 requires a value to resolve to a
# publication and a place inside it; each of these fails that test in a way the
# archive's own caveat names. They stay available for a later pass that resolves
# the citation -- which is exactly the archive's own Tier F.
UNRESOLVED_CITATION = {
    "S12b": "no author or year, and the linked paper is about the Carpathian Basin while the citation describes Iranian populations",
    "S22": "the linked record is a different paper; the archive says to resolve the primary citation",
    "S19": "no author or year; a ResearchGate figure, flagged 'resolve before publishing'",
    "S13": "the retrieved link is a bare session URL, flagged 'resolve the exact article URL before publishing'",
    "S25": "a Handbook of the Mammals of the World species account restating other work",
    "S9": "heterodyne tuning frequencies from a society web page; the archive says do not present as measurement",
    "S17": "a ResearchGate figure, flagged 'resolve to the primary citation'",
    "S-NIMBA13": "reached only through a ResearchGate table extract, not the publisher",
    "S21": "no author or year; a ResearchGate figure",
    "S-MORM": "the archive states the numeric peak frequency was not in the retrievable text",
    "S-CARTER": "the archive states the primary citation was not resolved",
}


def reference_for(source_key: str) -> str | None:
    """Project reference_id for a master source key, or None if refused."""
    if source_key in EXISTING:
        return EXISTING[source_key]
    return NEW_REFERENCES.get(source_key)


# Reference -> method record. The archive carries recording context per row but
# no equipment or analysis settings, so new sources get an explicitly "unstated"
# method rather than none: a card that cannot say how a number was produced
# should say so, not leave the question unasked.
METHODS = {
    "yoh-2020": "yoh-2020-release",
    "arias-aguilar-2018": "arias-aguilar-2018-compiled",
    "arevalo-cortes-2024": "arevalo-cortes-2024-em3",
    "ugarte-nunez-2020": "ugarte-nunez-2020-unstated",
    "jung-2014": "jung-2014-free-flight",
    "szewczak-western-2024": "szewczak-western-2024-library",
    "szewczak-eastern-2022": "szewczak-eastern-2022-library",
    "barataud-2013-guyane": "barataud-2013-guyane-unstated",
    "mcarthur-2021-borneo": "mcarthur-2021-borneo-unstated",
    "pennay-lavery-2017-solomons": "pennay-lavery-2017-solomons-unstated",
    "monadjem-2017-swaziland": "monadjem-2017-swaziland-release",
    "dalhoumi-2023-tunisia": "dalhoumi-2023-tunisia-passive",
    "van-de-sijpe-2011": "van-de-sijpe-2011-unstated",
    "fukui-2015-korea": "fukui-2015-korea-unstated",
    "gyorossy-2024-vietnam": "gyorossy-2024-vietnam-unstated",
    "zamora-gutierrez-2020-sonozotz": "zamora-gutierrez-2020-sonozotz-standardised",
    "lung-mv-ffh-factsheets": "lung-mv-ffh-factsheets-unstated",
    "surlykke-2009": "surlykke-2009-array",
    "schuchmann-2010": "schuchmann-2010-unstated",
    "rehak-2010": "rehak-2010-compiled",
    "salsamendi-2012": "salsamendi-2012-unstated",
    "rydell-arlettaz-1994": "rydell-arlettaz-1994-unstated",
    "holderied-2005": "holderied-2005-videogrammetry",
    "gessinger-2019": "gessinger-2019-unstated",
    "alberdi-garin-2018": "alberdi-garin-2018-compiled",
    "surlykke-2013-trachops": "surlykke-2013-trachops-array",
}
