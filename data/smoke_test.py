"""Fast release and built-site smoke checks."""

import json
import re
import struct
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main() -> None:
    bats = load("chiroptera_taxonomy.json")
    marine = load("marine_mammal_taxonomy.json")
    direct = load("call_measurements.json")
    names = load("danish_names.json")
    supplement = load("gbif_country_supplement.json")
    bat_html = (ROOT / "public/index.html").read_text(encoding="utf-8")
    marine_html = (ROOT / "public/marine.html").read_text(encoding="utf-8")
    birds = load("bird_taxonomy.json")
    bird_html = (ROOT / "public/birds.html").read_text(encoding="utf-8")
    dinosaurs = load("dinosaur_taxonomy.json")
    dino_html = (ROOT / "public/dinosaurs.html").read_text(encoding="utf-8")
    worker = (ROOT / "public/service-worker.js").read_text(encoding="utf-8")

    pages = (bat_html, marine_html, bird_html, dino_html)
    assert "INLINE data/" not in "".join(pages)
    assert "__RELEASE__" not in worker
    assert all(family in bat_html for family in bats["families"])
    assert all(family in marine_html for family in marine["families"])
    assert all(family in bird_html for family in birds["families"])
    assert all(family in dino_html for family in dinosaurs["families"])
    assert all('href="birds.html"' in page and 'href="dinosaurs.html"' in page for page in pages)
    assert set(direct["species"]) <= {item["id"] for item in bats["species"]}
    assert set(names) <= {item["id"] for item in bats["species"]}
    assert supplement and all(value for value in supplement.values())
    assert re.search(r"chiroptree-core-[0-9a-f]{16}", worker)
    manifest = json.loads((ROOT / "public/manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["display"] == "standalone"
    assert manifest["scope"] == "./" and manifest["id"] == manifest["start_url"] == "./index.html"
    assert {"192x192", "512x512"} <= {icon["sizes"] for icon in manifest["icons"] if icon["purpose"] == "any"}
    assert any(icon["purpose"] == "maskable" for icon in manifest["icons"])
    for icon in manifest["icons"]:
        png = (ROOT / "public" / urlsplit(icon["src"]).path).read_bytes()
        assert f"'./{icon['src']}'" in worker, "Manifest icon must be precached at its exact URL"
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        width, height = struct.unpack(">II", png[16:24])
        assert icon["sizes"] == f"{width}x{height}"
    for page in pages:
        assert 'rel="manifest" href="manifest.webmanifest"' in page
        assert 'src="app-install.js"' in page and 'id="install-app"' in page
    core = re.search(r"const CORE = \[(.*?)\];", worker, re.S).group(1)
    for path in re.findall(r"'\./([^']*)'", core):
        assert (ROOT / "public" / urlsplit(path).path).exists(), f"Missing offline asset: {path}"
    print("Offline build smoke test passed")


if __name__ == "__main__":
    main()
