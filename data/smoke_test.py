"""Fast release and built-site smoke checks."""

import json
import re
from pathlib import Path

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
    worker = (ROOT / "public/service-worker.js").read_text(encoding="utf-8")

    assert "INLINE data/" not in bat_html + marine_html + bird_html
    assert "__RELEASE__" not in worker
    assert all(family in bat_html for family in bats["families"])
    assert all(family in marine_html for family in marine["families"])
    assert all(family in bird_html for family in birds["families"])
    assert all('href="birds.html"' in page for page in (bat_html, marine_html, bird_html))
    assert set(direct["species"]) <= {item["id"] for item in bats["species"]}
    assert set(names) <= {item["id"] for item in bats["species"]}
    assert supplement and all(value for value in supplement.values())
    assert re.search(r"chiroptree-core-[0-9a-f]{16}", worker)
    print("Offline build smoke test passed")


if __name__ == "__main__":
    main()
