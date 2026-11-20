"""Fetch every species account of Handbook of the Mammals of the World vol. 9
(Bats, Wilson & Mittermeier 2019) from Plazi TreatmentBank.

Plazi publishes HMW 9 as one master document per family chapter, each holding
one treatment per species (plus genus and family treatments). This script
lists the treatments of every chapter from its TreatmentBank summary page,
downloads each treatment's XML to the gitignored cache data/raw/size/plazi/
(reusing copies the other importers already cached there or under
data/raw/calls/plazi/), and writes the tracked manifest
data/size/hmw-2019-sources.json: docId -> account title, family and the
sha256 that import_hmw.py pins.

Plazi is slow and answers HTTP 500 under load, so requests run two at a
time with retries. A re-run only fetches what is missing.

Run:  uv run data/size/fetch_hmw.py
"""
import hashlib
import json
import re
import shutil
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE.parent
CACHE = DATA / "raw" / "size" / "plazi"
OTHER_CACHE = DATA / "raw" / "calls" / "plazi"
MANIFEST = HERE / "hmw-2019-sources.json"
SERVER = "https://tb.plazi.org/GgServer"
USER_AGENT = "TreeOfBatLife-size-import/1.0 (bat trait research; low request rate)"
WORKERS = 2
RETRIES = 5

# family chapter -> Plazi masterDocId of the HMW 9 chapter
CHAPTERS = {
    "Pteropodidae": "FF94FF82FFC4F62A891E341CFFA5FF9B",
    "Rhinopomatidae": "7A37B03C5717FFECFFB6FFB0B83CFFE1",
    "Craseonycteridae": "266F372FFF8AAC35E341FFE0FFDF183D",
    "Megadermatidae": "3D066E39FF8DFFE2FFD7FF8AFF916A04",
    "Rhinonycteridae": "FFBA5C272223977C8E73F509FFB1FFD0",
    "Hipposideridae": "FF84FFDAC676A204FFF8FF9AFFEF4346",
    "Rhinolophidae": "7461FFDAFFCF8A29FFCCFFA1FF85D963",
    "Emballonuridae": "FFECFF8AFFCF4C04FFA53577FFF8FFE9",
    "Nycteridae": "FFB45E34754FD70B851AFFEF527EFFBD",
    "Myzopodidae": "FF89C47E2413FFD5FF87EA47FF90FFC9",
    "Mystacinidae": "9D2D4E5EC159FFE7FF80F125FF8DFFFF",
    "Phyllostomidae": "FF9FFFC4FFB1FFB1133CFFBAFFE0F244",
    "Mormoopidae": "FF9F4F3B9157FFEBE472C9232F51A072",
    "Noctilionidae": "FFE3C632FFE0FFA057444405FFA9C95B",
    "Furipteridae": "FFA8FFD45C3E2A53F03609113F64FFC4",
    "Thyropteridae": "9B2B7A11A43AE04DFFE6FFC7FF89FFD6",
    "Natalidae": "D53EFF87FFA41873FFBA9505EB7B3516",
    "Molossidae": "E57BFFB1FFBCBA10B412F760B226FFCE",
    "Miniopteridae": "1471FF81FFD6D6580A4AFFEC112F3619",
    "Cistugidae": "8E35BD5DFFF94548ED13FF8F634AFFED",
    "Vespertilionidae": "B004FF90FFFB6A44FFFC96591E00BB32",
}


def get(url: str) -> bytes:
    for attempt in range(RETRIES):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=180) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == RETRIES - 1:
                raise
            wait = 10 * (attempt + 1)
            print(f"  {url}: {error}; retrying in {wait}s")
            time.sleep(wait)
    raise AssertionError("unreachable")


def chapter_treatments(master: str) -> list[str]:
    html = get(f"{SERVER}/summary/{master}").decode("utf-8", errors="replace")
    return sorted(set(re.findall(r"GgServer/html/([0-9A-F]{32})", html)))


def cached(doc: str) -> Path:
    path = CACHE / f"{doc}.xml"
    if not path.exists() and (OTHER_CACHE / f"{doc}.xml").exists():
        shutil.copyfile(OTHER_CACHE / f"{doc}.xml", path)
    if not path.exists():
        path.write_bytes(get(f"{SERVER}/xml/{doc}"))
    return path


def header(path: Path) -> dict:
    with path.open(encoding="utf-8", errors="replace") as handle:
        head = handle.read(4000)
    tag = re.search(r"<document [^>]*>", head)
    if not tag:
        raise SystemExit(f"{path}: no <document> element; delete it and re-run")
    return dict(re.findall(r'(\w[\w.-]*)="([^"]*)"', tag.group(0)))


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    for family, master in CHAPTERS.items():
        docs = [d for d in chapter_treatments(master) if d != master]
        with ThreadPoolExecutor(WORKERS) as pool:
            paths = list(pool.map(cached, docs))
        kept = 0
        for doc, path in zip(docs, paths):
            meta = header(path)
            if meta.get("masterDocId") != master:
                continue  # a summary page can link to other documents
            manifest[doc] = {
                "title": meta.get("docTitle", ""), "family": family,
                "page": meta.get("pageNumber", ""),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            kept += 1
        print(f"{family}: {kept} treatments")
    MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"manifest: {len(manifest)} treatments in {MANIFEST.relative_to(DATA.parent)}")


if __name__ == "__main__":
    main()
