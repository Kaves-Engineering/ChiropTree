# /// script
# dependencies = ["pillow"]
# ///
"""Download deterministic, redistributable iNaturalist thumbnails."""

import hashlib
import io
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
MANIFEST = HERE / "media-manifest.json"
ALLOWED = {
    "cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa",
    "cc-by-nd", "cc-by-nc-nd",
}
API_INTERVAL = float(os.environ.get("INAT_API_INTERVAL", "1.05"))
API_RETRIES = int(os.environ.get("INAT_API_RETRIES", "6"))
MAX_WORKERS = int(os.environ.get("MEDIA_WORKERS", "2"))
_api_lock = threading.Lock()
_next_api_request = 0.0


def wait_for_api_slot() -> None:
    """Reserve one globally spaced iNaturalist API request slot."""
    global _next_api_request
    with _api_lock:
        now = time.monotonic()
        delay = max(0.0, _next_api_request - now)
        _next_api_request = max(now, _next_api_request) + API_INTERVAL
    if delay:
        time.sleep(delay)


def retry_delay(error: urllib.error.HTTPError, attempt: int) -> float:
    retry_after = error.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 120.0)
        except ValueError:
            pass
    return min(2**attempt, 60.0)


def read_url(url: str, *, api: bool = False, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "chiroptree-data/1.0"})
    for attempt in range(API_RETRIES + 1):
        if api:
            wait_for_api_slot()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code != 429 and error.code < 500:
                raise
            if attempt == API_RETRIES:
                raise
            delay = retry_delay(error, attempt)
            print(f"HTTP {error.code}; retrying in {delay:g}s")
            time.sleep(delay)
        except (TimeoutError, urllib.error.URLError) as error:
            if attempt == API_RETRIES:
                raise
            delay = min(2**attempt, 60)
            print(f"HTTP {type(error).__name__}; retrying in {delay}s")
            time.sleep(delay)
    raise RuntimeError("unreachable")


def get_json(url: str) -> dict:
    return json.loads(read_url(url, api=True).decode("utf-8"))


def photo_for(name: str) -> dict | None:
    data = get_json("https://api.inaturalist.org/v1/taxa?q=" + urllib.parse.quote(name) + "&rank=species&per_page=10")
    taxon = next((item for item in data.get("results", []) if item.get("name", "").lower() == name.lower()), None)
    photo = taxon and taxon.get("default_photo")
    if photo and (photo.get("license_code") or "").lower() in ALLOWED:
        return {"photo": photo, "sourceUrl": f"https://www.inaturalist.org/taxa/{taxon['id']}", "providerAssetId": str(photo.get("id", ""))}
    query = urllib.parse.urlencode({"taxon_name": name, "quality_grade": "research", "photos": "true", "order_by": "votes", "per_page": 30})
    observations = get_json("https://api.inaturalist.org/v1/observations?" + query)
    for observation in observations.get("results", []):
        for candidate in observation.get("photos", []):
            if (candidate.get("license_code") or "").lower() in ALLOWED:
                return {"photo": candidate, "sourceUrl": f"https://www.inaturalist.org/observations/{observation['id']}", "providerAssetId": str(candidate.get("id", ""))}
    return None


def prepare_image(photo: dict, preserve: bool) -> tuple[bytes, str, str, int, int, str]:
    url = photo["url"].replace("/square.", "/small.") if preserve else photo.get("original_url") or photo["url"]
    source = read_url(url, timeout=60)
    image = Image.open(io.BytesIO(source))
    if preserve:
        suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise ValueError(f"unsupported no-derivatives image format: {suffix}")
        digest = hashlib.sha256(source).hexdigest()
        return source, digest, digest, image.width, image.height, suffix
    image = image.convert("RGB")
    image.thumbnail((320, 320))
    output = io.BytesIO()
    image.save(output, "WEBP", quality=78, method=6)
    content = output.getvalue()
    return content, hashlib.sha256(source).hexdigest(), hashlib.sha256(content).hexdigest(), image.width, image.height, ".webp"


def sync_one(mdd_id: str, record: dict, existing: dict, refresh: bool) -> tuple[str, dict | None]:
    if existing["status"] == "available" and not refresh:
        return mdd_id, None
    choice = photo_for(record["sciName"].replace("_", " "))
    if not choice:
        return mdd_id, None
    photo = choice["photo"]
    if (
        existing.get("status") == "available"
        and existing.get("providerAssetId") != choice["providerAssetId"]
    ):
        return mdd_id, None
    license_code = photo["license_code"].lower()
    preserve = license_code.endswith("-nd")
    content, source_hash, output_hash, width, height, suffix = prepare_image(photo, preserve)
    if existing.get("sourceHash") == source_hash and existing.get("license") == photo["license_code"].upper():
        return mdd_id, None
    relative = f"images/{mdd_id}-{output_hash[:12]}{suffix}"
    path = HERE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    return mdd_id, {
        "status": "available", "path": relative, "sourceUrl": choice["sourceUrl"],
        "providerAssetId": choice["providerAssetId"], "attribution": photo.get("attribution") or "iNaturalist contributor",
        "license": photo["license_code"].upper(), "alt": record["sciName"].replace("_", " "),
        "retrievedAt": datetime.now(UTC).isoformat(), "sourceHash": source_hash,
        "outputHash": output_hash, "width": width, "height": height,
        "modified": not preserve,
    }


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    taxa = {}
    for filename in ("chiroptera_taxonomy.json", "marine_mammal_taxonomy.json"):
        for record in json.loads((HERE / filename).read_text(encoding="utf-8"))["species"]:
            taxa[record["id"]] = record
    queue = sorted(
        taxa.items(),
        key=lambda item: (manifest["assets"][item[0]]["status"] == "available", item[0]),
    )
    saved = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(sync_one, mdd_id, record, manifest["assets"][mdd_id], True): mdd_id
            for mdd_id, record in queue
        }
        for future in as_completed(futures):
            mdd_id = futures[future]
            try:
                _, asset = future.result()
                if asset:
                    manifest["assets"][mdd_id] = asset
                    saved += 1
                    print(f"{mdd_id}: saved")
            except Exception as error:  # noqa: BLE001
                failed += 1
                print(f"{mdd_id}: {error}")
    temporary = MANIFEST.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    temporary.replace(MANIFEST)
    print(f"Media sync complete: {saved} saved, {failed} failed, {len(queue)} checked")


if __name__ == "__main__":
    main()
