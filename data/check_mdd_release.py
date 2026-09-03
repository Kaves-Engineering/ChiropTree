"""Report whether Zenodo has a newer MDD release."""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

CONCEPT_RECORD = "4139722"
HERE = Path(__file__).parent


def main() -> None:
    query = urllib.parse.urlencode(
        {"q": f"conceptrecid:{CONCEPT_RECORD}", "sort": "mostrecent", "size": 1, "all_versions": "true"}
    )
    request = urllib.request.Request(
        f"https://zenodo.org/api/records?{query}", headers={"User-Agent": "chiroptree-data/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        latest = json.load(response)["hits"]["hits"][0]["doi"]
    current = json.loads((HERE / "release.json").read_text(encoding="utf-8"))["source"]["doi"]
    changed = str(latest != current).lower()
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"changed={changed}\nlatest={latest}\n")
    print(f"MDD current={current} latest={latest} changed={changed}")


if __name__ == "__main__":
    main()
