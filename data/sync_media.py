# /// script
# dependencies = ["pillow"]
# ///
"""Download deterministic, redistributable iNaturalist thumbnails."""

import hashlib
import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
MANIFEST = HERE / "media-manifest.json"
ALLOWED = {"cc0", "cc-by", "cc-by-sa"}


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "chiroptree-data/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def photo_for(name: str) -> dict | None:
    data = get_json("https://api.inaturalist.org/v1/taxa?q=" + urllib.parse.quote(name) + "&rank=species&per_page=10")
    taxon = next((item for item in data.get("results", []) if item.get("name", "").lower() == name.lower()), None)
    photo = taxon and taxon.get("default_photo")
    if not photo or (photo.get("license_code") or "").lower() not in ALLOWED:
        return None
    return {"photo": photo, "sourceUrl": f"https://www.inaturalist.org/taxa/{taxon['id']}"}


def save_image(mdd_id: str, photo: dict) -> tuple[str, int, int]:
    url = photo.get("original_url") or photo["url"]
    with urllib.request.urlopen(url, timeout=60) as response:
        source = response.read()
    image = Image.open(io.BytesIO(source)).convert("RGB")
    image.thumbnail((320, 320))
    path = HERE / "images" / f"{mdd_id}.webp"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "WEBP", quality=78, method=6)
    return hashlib.sha256(source).hexdigest(), image.width, image.height


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    taxa = {}
    for filename in ("chiroptera_taxonomy.json", "marine_mammal_taxonomy.json"):
        for record in json.loads((HERE / filename).read_text(encoding="utf-8"))["species"]:
            taxa[record["id"]] = record
    for mdd_id, record in taxa.items():
        if manifest["assets"][mdd_id]["status"] == "available":
            continue
        try:
            choice = photo_for(record["sciName"].replace("_", " "))
            if not choice:
                continue
            photo = choice["photo"]
            source_hash, width, height = save_image(mdd_id, photo)
            manifest["assets"][mdd_id] = {
                "status": "available", "path": f"images/{mdd_id}.webp", "sourceUrl": choice["sourceUrl"],
                "attribution": photo.get("attribution") or "iNaturalist contributor",
                "license": photo["license_code"].upper(), "alt": record["sciName"].replace("_", " "),
                "sourceHash": source_hash, "width": width, "height": height,
            }
            print(f"{mdd_id}: saved")
        except Exception as error:  # noqa: BLE001
            print(f"{mdd_id}: {error}")
        finally:
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            time.sleep(0.15)


if __name__ == "__main__":
    main()
