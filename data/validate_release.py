"""Validate every browser-visible release artifact before deployment."""

import hashlib
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).parent
MAX_IMAGE_BYTES = 60 * 1024 * 1024
ALLOWED_LICENSES = {
    "CC0", "CC-BY", "CC-BY-SA", "CC-BY-NC", "CC-BY-NC-SA",
    "CC-BY-ND", "CC-BY-NC-ND",
}


def load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", value.lower())).strip()


def validate_taxonomy(payload: dict, label: str) -> tuple[set[str], set[str]]:
    species = payload["species"]
    ids = [record["id"] for record in species]
    names = [record["sciName"].replace("_", " ") for record in species]
    assert len(ids) == len(set(ids)), f"{label}: duplicate MDD ID"
    assert len(names) == len(set(names)), f"{label}: duplicate scientific name"
    assert payload["_meta"]["speciesCount"] == len(species), f"{label}: species count mismatch"
    assert payload["_meta"]["familyCount"] == len({record["family"] for record in species}), f"{label}: family count mismatch"
    assert payload["_meta"]["genusCount"] == len({record["genus"] for record in species}), f"{label}: genus count mismatch"
    assert re.fullmatch(r"[0-9a-f]{64}", payload["_meta"]["sourceChecksum"]), f"{label}: invalid source checksum"
    for record in species:
        assert all(record.get(field) for field in ("id", "sciName", "family", "genus")), f"{label}: incomplete taxon"
    return set(ids), set(names)


def validate_names(filename: str, ids: set[str]) -> None:
    for mdd_id, record in load(filename).items():
        assert mdd_id in ids, f"{filename}: unknown MDD ID {mdd_id}"
        assert record.get("mddId") == mdd_id, f"{filename}: mismatched MDD ID {mdd_id}"
        assert record.get("name") and record.get("source") and record.get("gbifKey"), f"{filename}: incomplete name {mdd_id}"


def validate_calls(species_ids: set[str]) -> None:
    calls = load("call-records.json")
    for family, record in calls["families"].items():
        assert record.get("evidenceScope") == "family-guide", f"{family}: invalid evidence scope"
        assert record.get("referenceId") in calls["references"], f"{family}: missing reference"
    direct = load("danish_call_measurements.json")
    for mdd_id, record in direct["species"].items():
        assert mdd_id in species_ids, f"direct calls: unknown MDD ID {mdd_id}"
        assert record.get("summary") and record.get("context"), f"{mdd_id}: incomplete call summary"
        reference = direct["references"].get(record.get("reference"))
        assert reference and reference.get("url", "").startswith("https://"), f"{mdd_id}: invalid citation"


def validate_map(taxonomy: dict, filename: str) -> None:
    index = load(filename)["index"]
    unresolved = set()
    for record in taxonomy["species"]:
        for raw in (record.get("countryDistribution") or "").split("|"):
            country = raw.strip().rstrip("?").strip()
            if country and country != "NA" and norm(country) not in index:
                unresolved.add(country)
    assert not unresolved, f"{filename}: unresolved countries: {', '.join(sorted(unresolved))}"


def validate_media(all_ids: set[str]) -> None:
    assets = load("media-manifest.json")["assets"]
    assert set(assets) == all_ids, "media manifest taxon set mismatch"
    total = 0
    for mdd_id, asset in assets.items():
        assert asset.get("status") in {"available", "unavailable"}, f"{mdd_id}: invalid media status"
        if asset["status"] == "unavailable":
            continue
        assert asset.get("license") in ALLOWED_LICENSES, f"{mdd_id}: disallowed media licence"
        if asset["license"].endswith("-ND"):
            assert asset.get("modified") is False, f"{mdd_id}: ND media was modified"
            assert asset.get("sourceHash") == asset.get("outputHash"), f"{mdd_id}: ND media hash changed"
        assert asset.get("attribution") and asset.get("sourceUrl"), f"{mdd_id}: missing media attribution"
        path = Path(asset["path"])
        assert not path.is_absolute() and path.parts[:1] == ("images",), f"{mdd_id}: unsafe media path"
        absolute = HERE / path
        assert absolute.is_file(), f"{mdd_id}: missing media file"
        content = absolute.read_bytes()
        total += len(content)
        assert hashlib.sha256(content).hexdigest() == asset.get("outputHash"), f"{mdd_id}: media hash mismatch"
    assert total <= MAX_IMAGE_BYTES, f"image pack exceeds 60 MiB: {total} bytes"
    print(f"Validated {len(assets)} media records; image pack {total / 1024 / 1024:.1f} MiB")


def validate_manifest() -> None:
    manifest = load("release.json")
    for name, expected in manifest["files"].items():
        path = HERE / name
        assert path.is_file(), f"release manifest: missing {name}"
        content = path.read_bytes()
        assert len(content) == expected["bytes"], f"release manifest: size mismatch for {name}"
        assert hashlib.sha256(content).hexdigest() == expected["sha256"], f"release manifest: hash mismatch for {name}"


def main() -> None:
    bats = load("chiroptera_taxonomy.json")
    marine = load("marine_mammal_taxonomy.json")
    bat_ids, _ = validate_taxonomy(bats, "bats")
    marine_ids, _ = validate_taxonomy(marine, "marine mammals")
    validate_names("danish_names.json", bat_ids)
    validate_names("marine_mammal_danish_names.json", marine_ids)
    validate_calls(bat_ids)
    validate_map(bats, "world_map.json")
    validate_map(marine, "marine_world_map.json")
    validate_media(bat_ids | marine_ids)
    validate_manifest()
    print("Release validation passed")


if __name__ == "__main__":
    main()
