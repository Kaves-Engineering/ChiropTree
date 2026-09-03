"""Shared MDD import, validation, and JSON export helpers."""

import csv
import hashlib
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).parent
SOURCE_DOI = "10.5281/zenodo.21654811"
SOURCE_URL = "https://zenodo.org/api/records/21654811/files/MDD_v2.5_6904species.csv/content"
SOURCE_VERSION = "2.5"
RAW = HERE / "raw" / "MDD_v2.5_6904species.csv"
CONCEPT_RECORD = "4139722"

FIELDS = (
    "id", "sciName", "phylosort", "mainCommonName", "otherCommonNames",
    "order", "suborder", "infraorder", "superfamily", "family", "subfamily",
    "tribe", "genus", "subgenus", "specificEpithet", "authoritySpeciesAuthor",
    "authoritySpeciesYear", "countryDistribution", "continentDistribution",
    "biogeographicRealm", "iucnStatus", "extinct", "MSW3_sciName",
)
RANK_FIELDS = (
    "order", "suborder", "infraorder", "superfamily", "family", "subfamily",
    "tribe", "genus", "subgenus",
)


def ensure_raw_csv() -> Path:
    global RAW, SOURCE_DOI, SOURCE_URL, SOURCE_VERSION
    if os.environ.get("MDD_LATEST") == "1":
        query = urllib.parse.urlencode({"q": f"conceptrecid:{CONCEPT_RECORD}", "sort": "mostrecent", "size": 1, "all_versions": "true"})
        request = urllib.request.Request(f"https://zenodo.org/api/records?{query}", headers={"User-Agent": "chiroptree-data/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            release = json.load(response)["hits"]["hits"][0]
        file = next(item for item in release["files"] if re.fullmatch(r"MDD_v[\d.]+_\d+species\.csv", item["key"]))
        SOURCE_DOI = release["doi"]
        SOURCE_URL = file["links"]["self"]
        SOURCE_VERSION = re.search(r"MDD_v([\d.]+)_", file["key"]).group(1)
        RAW = HERE / "raw" / file["key"]
    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading MDD release CSV from {SOURCE_URL} ...")
        urllib.request.urlretrieve(SOURCE_URL, RAW)
    return RAW


def source_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = set(FIELDS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"MDD CSV missing columns: {', '.join(sorted(missing))}")
        return [{field: row[field] for field in FIELDS} for row in reader]


def create_database(rows: list[dict[str, str]], database: Path, checksum: str) -> None:
    database.parent.mkdir(parents=True, exist_ok=True)
    if database.exists():
        database.unlink()
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE release (
                release_id TEXT PRIMARY KEY,
                source_doi TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_checksum TEXT NOT NULL
            );
            CREATE TABLE taxon (
                mdd_id TEXT PRIMARY KEY,
                sci_name TEXT NOT NULL,
                phylosort REAL NOT NULL,
                main_common_name TEXT NOT NULL,
                other_common_names TEXT NOT NULL,
                taxonomy_json TEXT NOT NULL
            );
            CREATE TABLE taxon_rank (
                mdd_id TEXT NOT NULL REFERENCES taxon(mdd_id),
                rank_name TEXT NOT NULL,
                rank_value TEXT NOT NULL,
                PRIMARY KEY (mdd_id, rank_name)
            );
            """
        )
        connection.execute(
            "INSERT INTO release VALUES (?, ?, ?, ?)",
            (SOURCE_DOI, SOURCE_DOI, SOURCE_URL, checksum),
        )
        for row in rows:
            connection.execute(
                "INSERT INTO taxon VALUES (?, ?, ?, ?, ?, ?)",
                (
                    row["id"], row["sciName"], float(row["phylosort"]),
                    row["mainCommonName"], row["otherCommonNames"],
                    json.dumps(row, ensure_ascii=False),
                ),
            )
            connection.executemany(
                "INSERT INTO taxon_rank VALUES (?, ?, ?)",
                (
                    (row["id"], rank, value)
                    for rank in RANK_FIELDS
                    if (value := row[rank]) not in ("", "NA")
                ),
            )


def validate_rows(rows: list[dict[str, str]]) -> None:
    ids = [row["id"] for row in rows]
    names = [row["sciName"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("MDD CSV contains duplicate IDs")
    if len(names) != len(set(names)):
        raise ValueError("MDD CSV contains duplicate scientific names")
    for row in rows:
        if not row["id"] or not row["sciName"] or not row["family"] or not row["genus"]:
            raise ValueError(f"MDD row lacks required ID, name, family, or genus: {row!r}")
        try:
            float(row["phylosort"])
        except ValueError as error:
            raise ValueError(f"Invalid phylosort for {row['sciName']}") from error


def export_taxonomy(
    database: Path,
    output: Path,
    include: Callable[[dict[str, str]], bool],
    extra: Callable[[dict[str, str]], None] | None = None,
) -> dict:
    with sqlite3.connect(database) as connection:
        records = [json.loads(row[0]) for row in connection.execute(
            "SELECT taxonomy_json FROM taxon ORDER BY phylosort"
        )]
        release = connection.execute(
            "SELECT source_doi, source_url, source_checksum FROM release"
        ).fetchone()
    selected = []
    for record in records:
        if not include(record):
            continue
        if extra:
            extra(record)
        selected.append(record)
    if not selected:
        raise ValueError("Taxonomy selection has no species")
    payload = {
        "_meta": {
            "source": f"Mammal Diversity Database v{SOURCE_VERSION}",
            "sourceDoi": release[0],
            "sourceUrl": "https://www.mammaldiversity.org",
            "sourceChecksum": release[2],
            "speciesCount": len(selected),
            "familyCount": len({record["family"] for record in selected}),
            "genusCount": len({record["genus"] for record in selected}),
        },
        "families": sorted({record["family"] for record in selected}),
        "species": selected,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


def build_database() -> Path:
    raw = ensure_raw_csv()
    rows = read_rows(raw)
    validate_rows(rows)
    database = HERE / "build" / "mdd.sqlite"
    create_database(rows, database, source_checksum(raw))
    return database
