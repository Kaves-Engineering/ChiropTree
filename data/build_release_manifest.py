"""Build the deterministic manifest for browser release artifacts."""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "release.json"
FILES = (
    "chiroptera_taxonomy.json", "marine_mammal_taxonomy.json", "call-records.json",
    "danish_call_measurements.json", "danish_names.json", "marine_mammal_danish_names.json",
    "gbif_country_supplement.json", "marine_mammal_gbif_country_supplement.json",
    "world_map.json", "marine_world_map.json", "media-manifest.json",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    bats = json.loads((HERE / "chiroptera_taxonomy.json").read_text(encoding="utf-8"))
    marine = json.loads((HERE / "marine_mammal_taxonomy.json").read_text(encoding="utf-8"))
    source_hash = bats["_meta"]["sourceChecksum"]
    assert source_hash == marine["_meta"]["sourceChecksum"]
    files = {name: {"sha256": digest(HERE / name), "bytes": (HERE / name).stat().st_size} for name in FILES}
    payload = {
        "releaseId": f"mdd-v2.5-{source_hash[:12]}",
        "source": {"doi": bats["_meta"]["sourceDoi"], "sha256": source_hash},
        "counts": {"bats": bats["_meta"]["speciesCount"], "marineMammals": marine["_meta"]["speciesCount"]},
        "files": files,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote release {payload['releaseId']}")


if __name__ == "__main__":
    main()
