"""Turn the legacy family call guide into explicit evidence-labelled records."""

import json
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = HERE / "echolocation_reference.json"
OUT = HERE / "call-records.json"


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    families = {}
    for name, record in source["families"].items():
        families[name] = {
            **record,
            "evidenceScope": "family-guide",
            "referenceId": "starter-comparative-guide",
        }
    payload = {
        "version": 1,
        "references": {
            "starter-comparative-guide": {
                "citation": "; ".join(source["_meta"]["primary_sources"]),
                "scope": "Comparative family/genus guide. Not species-verified.",
            }
        },
        "families": families,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {len(families)} family call guides")


if __name__ == "__main__":
    main()
