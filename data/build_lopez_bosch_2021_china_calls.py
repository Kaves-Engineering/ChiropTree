"""Import the per-study China measurements in Lopez-Bosch et al. Table S1.

This importer parses the official XLSX with only the Python standard library.
That makes the source audit reproducible without an Excel dependency and, more
importantly, uses Excel cell references rather than position in a sparse row.

Run: ``uv run data/build_lopez_bosch_2021_china_calls.py``.
"""
import hashlib
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from call_import_lib import TaxonResolver, report, write_review, write_rows
from calls.parameter_registry import Registry


REFERENCE_ID = "lopez-bosch-2021-china"
SOURCE = Path(__file__).parent / "raw" / "lopez-bosch-2021-china-table-s1.xlsx"
SOURCE_SHA256 = "85284d86a959fb8868933165c1c9c7463d819c75ccef3d2eb38c9d8318af2698"
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
HEADINGS = ("duration", "FmaxE", "max frequency", "min frequency", "start frequency", "end frequency", "bandwidth")
UNITS = ("ms", "kHz", "kHz", "kHz", "kHz", "kHz", "kHz")
NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?")

# One-to-one nomenclatural decisions checked on 2026-09-08.  They are kept
# source-local because they resolve names printed by this review, rather than
# changing the treatment of every future source.  The macrotis *complex* is
# intentionally absent: current work resolves it to several species, so a
# review-table row cannot responsibly be assigned to one of them.
MANUAL_MAP = {
    # MDD v2.5 nominal-names list: Aselliscus wheeleri is a synonym of the
    # current A. stoliczkanus (MDD taxon 1004561).
    "Aselliscus wheeleri": "1004561",
    # BatNames records rouxi as an alternative spelling of R. rouxii; MDD
    # accepts the latter (1004735), making this a spelling, not a split.
    "Rhinolophus rouxi": "1004735",
    # MDD v2.5 treats R. schnitzleri as a synonym of R. rex (1004732).
    "Rhinolophus schnitzleri": "1004732",
    # BatNames and current MDD place Thainycteris aureocollaris in Arielulus
    # (1005569); the species concept itself is unchanged.
    "Thainycteris aureocollaris": "1005569",
}


def column_index(cell_reference: str) -> int:
    number = 0
    for letter in re.match(r"[A-Z]+", cell_reference).group():
        number = number * 26 + ord(letter) - 64
    return number - 1


def xlsx_rows(path: Path):
    with zipfile.ZipFile(path) as archive:
        shared = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        strings = ["".join(item.itertext()) for item in shared.findall("x:si", NS)]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    for xml_row in sheet.findall(".//x:row", NS):
        row_number = int(xml_row.get("r"))
        if row_number < 3:
            continue
        row = [""] * 19
        for cell in xml_row.findall("x:c", NS):
            value = cell.find("x:v", NS)
            if value is None:
                continue
            text = strings[int(value.text)] if cell.get("t") == "s" else value.text
            row[column_index(cell.get("r"))] = text
        yield row_number, row


def parse_measurement(text: str):
    """Return (statistic, value, min, max, sd), never treating a range as a mean."""
    numbers = NUMBER.findall(text)
    if not numbers:
        return None
    if text.lstrip().startswith("("):
        if len(numbers) < 2:
            return None
        return "range", "", numbers[0], numbers[1], ""
    value = numbers[0]
    in_parentheses = re.search(r"\(([^)]*)\)", text)
    range_numbers = NUMBER.findall(in_parentheses.group(1)) if in_parentheses else []
    # The workbook's malformed ± glyph survives as U+FFFD in some cells.
    has_sd = "±" in text or "\ufffd" in text
    sd = numbers[1] if has_sd and len(numbers) > 1 else ""
    return ("mean" if has_sd else "species_summary", value,
            range_numbers[0] if len(range_numbers) >= 2 else "",
            range_numbers[1] if len(range_numbers) >= 2 else "", sd)


def condition(method: str) -> str:
    if method == "Hand-released":
        return "hand_release"
    if method in {"Free-flying", "Emergence"}:
        return "free_flying_wild"
    return "unspecified"


def main() -> None:
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise RuntimeError(f"Unexpected source SHA-256: {digest}")

    registry, resolver = Registry(), TaxonResolver()
    resolver.add_manual(MANUAL_MAP)
    parameters = [registry.resolve(heading) for heading in HEADINGS]
    if any(parameter is None for parameter in parameters):
        raise RuntimeError("A China Table S1 heading is absent from the parameter registry")

    rows, species_seen, skipped = [], set(), 0
    for sheet_row, record in xlsx_rows(SOURCE):
        species, match_method = resolver.resolve(record[1])
        if species is None:
            skipped += 1
            continue
        species_seen.add(species["id"])
        source_name = record[2] or record[1]
        source_note = (
            f"China review Table S1 cites {record[12]} ({record[13]}; {record[14]}). "
            f"Name in the cited study: {source_name}. Detector: {record[11] or 'unstated'}. "
            f"Recording method: {record[16] or 'unstated'}. Sex: {record[15] or 'unstated'}. "
            f"Call type: {record[3] or 'unstated'}."
        )
        for heading, parameter, unit, printed in zip(HEADINGS, parameters, UNITS, record[4:11]):
            measurement = parse_measurement(printed)
            if measurement is None:
                continue
            statistic, value, value_min, value_max, sd = measurement
            rows.append({
                "observation_id": f"lopezbosch2021-s1-{sheet_row}",
                "mdd_id": species["id"],
                "verbatim_taxon_name": record[1],
                "taxon_match_method": match_method,
                "reference_id": REFERENCE_ID,
                "locator": f"Table S1, spreadsheet row {sheet_row}, {heading} column",
                "method_id": "lopez-bosch-2021-china-compiled",
                "call_phase": "unspecified",
                "recording_condition": condition(record[16]),
                "country": "China",
                "locality": record[18],
                "parameter": parameter,
                "statistic": statistic,
                "value": value,
                "value_min": value_min,
                "value_max": value_max,
                "unit": unit,
                "dispersion_type": "sd" if sd else "",
                "dispersion_value": sd,
                "verbatim_value": printed,
                "quality_flag": "definition_unstated",
                "notes": source_note + " Values are a review extraction; this row is not independent corroboration of the cited study.",
            })

    path = write_rows(REFERENCE_ID, rows)
    review = write_review(REFERENCE_ID, resolver.unresolved)
    report(REFERENCE_ID, len(rows), len(species_seen), resolver)
    print(f"  source rows skipped for unresolved taxon: {skipped}")
    print(f"  -> {path}")
    if review:
        print(f"  -> {review} (needs a human decision)")


if __name__ == "__main__":
    main()
