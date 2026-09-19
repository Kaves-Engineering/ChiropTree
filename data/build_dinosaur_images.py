"""Build data/dinosaur_images.json: one freely licensed image per genus.

Run:  uv run python data/build_dinosaur_images.py   (after build_dinosaur_taxonomy.py)

The mammal and bird cards show a photograph from iNaturalist. Nobody has
photographed a living dinosaur, so iNaturalist has nothing to show. The image
here is the lead image of the genus's English Wikipedia article: a skeleton,
a fossil or a life restoration, hosted on Wikimedia Commons.

Two public APIs, 50 titles per request:

  en.wikipedia.org  prop=pageimages|description  the article's lead image,
                    and its short description to check the article is the
                    animal (Wikipedia has a "Minmi" and a "Kol" that are not
                    dinosaurs). The "<Genus> (dinosaur)" title is tried when
                    the plain title is some other subject.
  commons           prop=imageinfo&iiprop=extmetadata  author and licence

Only public-domain, CC0, CC BY and CC BY-SA images are kept, and the card
credits the author and links the licence and the Commons file page, as those
licences require. Images are per genus, because Wikipedia writes about genera:
every species of a genus shows the same picture.

The page reads the result as data; nothing is fetched from Wikipedia at
runtime except the image itself. Results are cached in
data/raw/dinosaur_wikipedia_cache.json; --refresh starts over.
"""
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
TAXONOMY = HERE / "dinosaur_taxonomy.json"
CACHE = HERE / "raw" / "dinosaur_wikipedia_cache.json"
OUT = HERE / "dinosaur_images.json"

WIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia throttles anonymous-looking clients; its policy asks for a contact URL
USER_AGENT = "chiroptree-data/1.0 (https://github.com/Kaves-Engineering/ChiropTree) python-urllib"
THUMB_WIDTH = 800

# the article is about an extinct reptile, not a town, a band or a moth
ABOUT_DINOSAUR = re.compile(
    r"dinosaur|saur|theropod|sauropod|ornithopod|ceratops|ceratopsian|ankylosaur|stegosaur|"
    r"hadrosaur|iguanodont|reptile|archosaur|ornithischian|saurischian|titanosaur", re.I)
NOT_DINOSAUR = re.compile(r"squamate|mosasaur|plesiosaur|pterosaur|crocodyl|ichthyosaur|turtle|lizard", re.I)
FREE = re.compile(r"^(public domain|pd\b|cc0|cc[ -]by(-sa)?\b|gfdl|copyrighted free use|no restrictions)", re.I)


def api(base: str, params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    url = base + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read())
        except Exception as error:                     # throttled or dropped: back off
            if attempt == 4:
                raise
            wait = 5 * 2 ** attempt
            retry_after = getattr(error, "headers", None) and error.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait = max(wait, int(retry_after))
            print(f"  {error}; waiting {wait}s", flush=True)
            time.sleep(wait)
    return {}


def chunks(items, n=50):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def lead_images(titles: list[str]) -> dict:
    """title asked for -> {title, image, description} (image may be absent)."""
    found = {}
    for batch in chunks(titles):
        data = api(WIKI_API, {"action": "query", "titles": "|".join(batch), "redirects": 1,
                              "prop": "pageimages|description", "piprop": "name"})
        query = data.get("query", {})
        # follow normalisation and redirects back to the title we asked for
        back = {}
        for step in query.get("normalized", []) + query.get("redirects", []):
            back[step["to"]] = back.get(step["from"], step["from"])
        for page in query.get("pages", []):
            if page.get("missing"):
                continue
            asked = back.get(page["title"], page["title"])
            asked = back.get(asked, asked)
            found[asked] = {"title": page["title"], "image": page.get("pageimage"),
                            "description": page.get("description", "")}
        time.sleep(1)
    return found


def licences(files: list[str]) -> dict:
    """file name -> {thumb, page, artist, licence, licenceUrl}."""
    found = {}
    for batch in chunks(files):
        data = api(COMMONS_API, {"action": "query", "titles": "|".join("File:" + f for f in batch),
                                 "prop": "imageinfo", "iiprop": "url|extmetadata",
                                 "iiurlwidth": THUMB_WIDTH,
                                 "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|Credit"})
        query = data.get("query", {})
        back = {n["to"]: n["from"] for n in query.get("normalized", [])}
        for page in query.get("pages", []):
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            name = back.get(page["title"], page["title"]).removeprefix("File:")
            artist = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", ""))
            found[name] = {
                "thumb": info.get("thumburl") or info.get("url"),
                "page": info.get("descriptionurl"),
                "artist": re.sub(r"\s+", " ", html.unescape(artist)).strip(),
                "licence": (meta.get("LicenseShortName") or {}).get("value", ""),
                "licenceUrl": (meta.get("LicenseUrl") or {}).get("value", ""),
            }
        time.sleep(1)
    return found


def about(genus: str, hit: dict | None) -> bool:
    """The article is this genus: its title is the genus, a species of it, or
    a disambiguated "Genus (dinosaur)". A redirect to another genus means
    Wikipedia sinks it as a synonym (Rubeosaurus -> Styracosaurus), and its
    picture would be of a different animal."""
    if not hit or not re.match(re.escape(genus) + r"( |$)", hit["title"]):
        return False
    return bool(ABOUT_DINOSAUR.search(hit["description"])) and not NOT_DINOSAUR.search(hit["description"])


def clean_url(url: str) -> str:
    # the APIs append analytics parameters; the file resolves without them
    return re.sub(r"\?utm_[^#]*$", "", url or "")


def main():
    tax = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    genera = sorted({s["genus"] for s in tax["species"]})
    cache = {} if "--refresh" in sys.argv or not CACHE.exists() else \
        json.loads(CACHE.read_text(encoding="utf-8"))

    todo = [g for g in genera if g not in cache.get("articles", {})]
    if todo:
        print(f"Looking up {len(todo)} genera on Wikipedia ...", flush=True)
        articles = cache.setdefault("articles", {})
        plain = lead_images(todo)
        retry = []
        for g in todo:
            hit = plain.get(g)
            if about(g, hit):
                articles[g] = hit
            else:
                retry.append(g)
        qualified = lead_images([f"{g} (dinosaur)" for g in retry])
        for g in retry:
            hit = qualified.get(f"{g} (dinosaur)")
            articles[g] = hit if about(g, hit) else None
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    files = sorted({a["image"] for a in cache["articles"].values() if a and a.get("image")})
    files_cache = cache.setdefault("files", {})
    missing = [f for f in files if f not in files_cache]
    if missing:
        print(f"Reading licences for {len(missing)} Commons files ...", flush=True)
        files_cache.update(licences(missing))
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    out, no_article, no_image, not_free = {}, 0, 0, []
    for g in genera:
        article = cache["articles"].get(g)
        if not article:
            no_article += 1
            continue
        info = files_cache.get(article.get("image") or "")
        if not info or not info.get("thumb"):
            no_image += 1
            continue
        if not FREE.search(info["licence"]):
            not_free.append(f"{g}: {info['licence'] or 'no licence'}")
            continue
        out[g] = {
            "url": clean_url(info["thumb"]),
            "sourceUrl": info["page"],
            "attribution": info["artist"] or "Wikimedia Commons contributor",
            "license": info["licence"],
            "licenseUrl": info["licenceUrl"],
            "article": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(article["title"].replace(" ", "_")),
        }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    print(f"Wrote {OUT}: images for {len(out)} of {len(genera)} genera; {no_article} without a "
          f"matching article, {no_image} whose article has no lead image, {len(not_free)} not freely licensed")
    for line in not_free:
        print("   ", line)


if __name__ == "__main__":
    main()
