"""Build the deterministic manifest for browser release artifacts."""

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "release.json"
FILES = (
    "chiroptera_taxonomy.json", "marine_mammal_taxonomy.json", "call-records.json",
    "call_measurements.json", "danish_names.json", "marine_mammal_danish_names.json",
    "gbif_country_supplement.json", "marine_mammal_gbif_country_supplement.json",
    "world_map.json", "marine_world_map.json", "media-manifest.json",
    "calls/exports/calls.json",
)


def canonical_bytes(path: Path) -> bytes:
    """File content as the repository stores it, with LF line endings.

    .gitattributes pins the repo to LF, but a Windows checkout with
    core.autocrlf=true still puts CRLF on disk. Hashing disk bytes directly
    therefore baked CRLF sizes into the committed manifest and broke release
    validation in Linux CI. Normalising here makes the manifest identical
    whichever platform generates it.
    """
    return path.read_bytes().replace(b"\r\n", b"\n")


def digest(path: Path) -> str:
    return hashlib.sha256(canonical_bytes(path)).hexdigest()


def main() -> None:
    bats = json.loads((HERE / "chiroptera_taxonomy.json").read_text(encoding="utf-8"))
    marine = json.loads((HERE / "marine_mammal_taxonomy.json").read_text(encoding="utf-8"))
    source_hash = bats["_meta"]["sourceChecksum"]
    assert source_hash == marine["_meta"]["sourceChecksum"]
    files = {name: {"sha256": digest(HERE / name), "bytes": len(canonical_bytes(HERE / name))}
             for name in FILES}
    payload = {
        "releaseId": f"mdd-v{re.search(r'v([\d.]+)', bats['_meta']['source']).group(1)}-{source_hash[:12]}",
        "source": {"doi": bats["_meta"]["sourceDoi"], "sha256": source_hash},
        "counts": {"bats": bats["_meta"]["speciesCount"], "marineMammals": marine["_meta"]["speciesCount"]},
        "files": files,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote release {payload['releaseId']}")


if __name__ == "__main__":
    main()
