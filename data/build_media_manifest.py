"""Keep one explicit local-media status for every published species."""

import json
from pathlib import Path

HERE = Path(__file__).parent
MANIFEST = HERE / "media-manifest.json"
TAXONOMIES = (HERE / "chiroptera_taxonomy.json", HERE / "marine_mammal_taxonomy.json")
REQUIRED = {"path", "sourceUrl", "attribution", "license", "alt"}


def main() -> None:
    existing = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"assets": {}}
    species = {}
    for taxonomy in TAXONOMIES:
        for record in json.loads(taxonomy.read_text(encoding="utf-8"))["species"]:
            species[record["id"]] = record

    assets = {}
    for mdd_id, record in sorted(species.items()):
        asset = existing.get("assets", {}).get(mdd_id, {"status": "unavailable"})
        if asset.get("status") == "available":
            missing = REQUIRED - set(asset)
            if missing:
                raise ValueError(f"{mdd_id}: available media lacks {', '.join(sorted(missing))}")
            path = Path(asset["path"])
            if path.is_absolute() or path.parts[:1] != ("images",) or not (HERE / path).is_file():
                raise ValueError(f"{mdd_id}: invalid or missing local media path {asset['path']!r}")
        elif asset.get("status") != "unavailable":
            raise ValueError(f"{mdd_id}: invalid media status {asset.get('status')!r}")
        assets[mdd_id] = asset

    MANIFEST.write_text(
        json.dumps({"version": 1, "assets": assets}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    available = sum(asset["status"] == "available" for asset in assets.values())
    print(f"Wrote {len(assets)} media records, {available} available")


if __name__ == "__main__":
    main()
