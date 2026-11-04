"""Carry the body masses already in the call data over into the size data.

Collen (2012, Appendix F) and Castro et al. (2024, Table 3) report one body
mass per species alongside their call measurements. Their importers
(data/build_collen_calls.py, data/build_castro_calls.py) already resolved the
names and wrote the masses to data/calls/<id>.csv as the body_mass covariate,
so this reads those rows rather than parsing the sources a second time.
Castro republishes Collen's EchoBank compilation; build_size.py counts the two
as one source through their shared independence group.

Run after the call importers: uv run data/size/import_call_covariates.py
"""
import csv

from size_lib import DATA, write_rows

SOURCES = {"collen-2012": "Appendix F, pp. 337-392", "castro-2024": "Table 3 (supplementary docx)"}
YEARS = {"collen-2012": "2012", "castro-2024": "2024"}


def main() -> None:
    for reference_id in SOURCES:
        rows = []
        with (DATA / "calls" / f"{reference_id}.csv").open(encoding="utf-8") as handle:
            for record in csv.DictReader(handle):
                if record["parameter"] != "body_mass" or not record["value"]:
                    continue
                # the call data spreads a pre-split name over every daughter
                # species; a body size cannot be assigned that way (size_lib)
                if record["taxon_match_method"] == "split_assigned":
                    continue
                rows.append({
                    "observation_id": record["observation_id"], "mdd_id": record["mdd_id"],
                    "verbatim_taxon_name": record["verbatim_taxon_name"],
                    "taxon_match_method": record["taxon_match_method"], "reference_id": reference_id,
                    "locator": record["locator"] or SOURCES[reference_id], "trait": "body_mass",
                    "basis": "measured", "statistic": "single", "value": record["value"],
                    "value_min": record["value_min"], "value_max": record["value_max"],
                    "range_type": "min_max" if record["value_min"] and record["value_max"] else "",
                    "n": record["n_individuals"], "sex": "pooled", "data_year": YEARS[reference_id],
                    "verbatim_value": record["verbatim_value"], "notes": record["notes"],
                    "upstream_source": "collen-2012" if reference_id == "castro-2024" else "",
                })
        write_rows(reference_id, rows)
        print(f"{reference_id}: {len(rows)} body-mass rows for {len({r['mdd_id'] for r in rows})} species "
              "(names as resolved by the call importer)")


if __name__ == "__main__":
    main()
