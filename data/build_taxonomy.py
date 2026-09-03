"""Build the Chiroptera taxonomy export from the validated MDD store."""
from pathlib import Path

from taxonomy_store import build_database, export_taxonomy

OUT = Path(__file__).parent / "chiroptera_taxonomy.json"

def main() -> None:
    payload = export_taxonomy(build_database(), OUT, lambda row: row["order"] == "Chiroptera")
    print(
        f"Wrote {payload['_meta']['speciesCount']} Chiroptera species across "
        f"{payload['_meta']['familyCount']} families to {OUT}"
    )


if __name__ == "__main__":
    main()
