"""Fetch the open-access papers the call-gap search found, for reading.

Each URL is fetched only if the site's robots.txt allows it for Anthropic's
agents (ClaudeBot, anthropic-ai) and for any agent ("*"); otherwise it is
listed as blocked and left alone. Files are cached under
data/raw/calls/papers/ and never re-fetched.

Run: uv run data/calls/fetch_call_gap_papers.py
"""
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "raw" / "calls" / "papers"
UA = "TreeOfBatLife call-gap search (urllib)"
AGENTS = ("ClaudeBot", "anthropic-ai", "*")

# file stem -> URL of the open copy (from OpenAlex's oa_url, or the DOI)
PAPERS = {
    "saccopteryx-antioquensis-2026": "https://link.springer.com/content/pdf/10.1186/s40693-026-00141-x.pdf",
    "emballonura-semicaudata-2026": "https://zenodo.org/api/records/22134602",
    "thyroptera-devivoi-2020": "https://www.scielo.br/j/bn/a/kvJb7nwynKQfYHJZ5WPQn9n/?lang=en&format=pdf",
    "micronycteris-sanborni-2014": "http://usir.salford.ac.uk/id/eprint/37810/1/L%C3%B3pez-Baucells%20et%20al.%202014.pdf",
    "polillo-2021": "https://philjournalsci.dost.gov.ph/images/pdf/pjs_pdf/vol150no6B/characterization_of_echolocation_calls_from_insectivorous_bats_.pdf",
    "eumops-ferox-2026": "https://theryanotes.mastozoologiamexicana.com/index.php/theryanotes/article/download/699/751",
    "eumops-maurus-2017": "https://www.tandfonline.com/doi/pdf/10.1080/03946975.2017.1382284",
    "myotis-barquezi-2025": "http://hdl.handle.net/11336/276691",
    "myotis-dieteri-2026": "https://preprints.arphahub.com/article/195471/download/pdf/",
    "histiotus-colombiae-2023": "https://mammalogynotes.org/ojs/index.php/mn/article/download/392/537",
    "histiotus-caldasia-2021": "https://revistas.unal.edu.co/index.php/cal/article/download/85424/78456",
    "neoeptesicus-innoxius-2025": "https://revistas.ucr.ac.cr/index.php/rrbt/article/download/704/2948",
    "pharotis-imogene-2026": "https://journals.australian.museum/media/dd/documents/3006_complete.2d29c32.pdf",
    "cynomops-yucatan-2006": "http://www.revmexmastozoologia.unam.mx/ojs/index.php/rmm/article/download/145/138",
    "cynomops-honduras-2015": "https://www.camjol.info/index.php/CEIBA/article/download/2014/1812",
    "mimon-diet-1999": "https://www.scielo.br/j/rbzool/a/rMqwT66szDKn6tkm8tmgwNB/?lang=en&format=pdf",
    "panay-caves-2012": "https://threatenedtaxa.org/JoTT/article/download/800/1434",
    "artibeus-wingbeat-2026": "https://zenodo.org/api/records/22105739",
    "lasiurus-galapagos-2026": "https://bioone.org/journals/acta-chiropterologica/volume-28/issue-2/15081109ACC2026.28.2.023/Seasonal-and-Spatial-Variation-in-Acoustic-Activity-of-Two-Insectivorous/10.3161/15081109ACC2026.28.2.023.pdf",
    "histiotus-magellanicus-ms-2019": "http://hdl.handle.net/11336/106112",
    "carollia-subrufa-ms-2008": "https://academic.oup.com/mspecies/article-pdf/doi/10.1644/823.1/24461013/823.pdf",
    "lonchorhina-marinkellei-ms-2017": "https://academic.oup.com/mspecies/article-pdf/49/950/76/19314969/sex008.pdf",
    "rhinolophus-namuli-2022": "https://bioone.org/journals/acta-chiropterologica/volume-24/issue-1/15081109ACC2022.24.1.002/A-New-Species-of-Horseshoe-Bat-Chiroptera--Rhinolophidae-from/10.3161/15081109ACC2022.24.1.002.pdf",
}

_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


class Blocked(Exception):
    pass


class RobotsRedirect(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to a URL robots.txt allows (checked before the request)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        ok, why = allowed(newurl)
        if not ok:
            raise Blocked(f"redirect to {newurl}: {why}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_plain = urllib.request.build_opener()
_guarded = urllib.request.build_opener(RobotsRedirect)


def opener_get(url: str, guarded: bool = True) -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with (_guarded if guarded else _plain).open(req, timeout=60) as resp:
        return resp.read(), resp.headers.get("Content-Type", ""), resp.geturl()


def allowed(url: str) -> tuple[bool, str]:
    parts = urllib.parse.urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            body, _, _ = opener_get(root + "/robots.txt", guarded=False)
            rp.parse(body.decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                _robots[root] = None          # robots.txt itself refused: treat as disallowed
                return False, f"robots.txt answered {e.code}"
            rp.parse([])                      # no robots.txt: allowed
        except Exception as e:  # noqa: BLE001
            return False, f"robots.txt unreadable ({e})"
        _robots[root] = rp
    rp = _robots[root]
    if rp is None:
        return False, "robots.txt refused"
    for agent in AGENTS:
        if not rp.can_fetch(agent, url):
            return False, f"robots.txt disallows {agent}"
    return True, ""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    for stem, url in PAPERS.items():
        if only and stem not in only:
            continue
        if list(OUT.glob(stem + ".*")):
            print(f"cached   {stem}")
            continue
        ok, why = allowed(url)
        if not ok:
            print(f"BLOCKED  {stem}: {why}")
            continue
        try:
            body, ctype, final = opener_get(url)
        except Blocked as e:
            print(f"BLOCKED  {stem}: {e}")
            continue
        except Exception as e:  # noqa: BLE001
            print(f"FAILED   {stem}: {e}")
            continue
        ext = ".pdf" if body[:4] == b"%PDF" else ".json" if "json" in ctype else ".html"
        (OUT / (stem + ext)).write_bytes(body)
        print(f"fetched  {stem}{ext} ({len(body)} bytes) from {final}")
        time.sleep(1.5)


if __name__ == "__main__":
    main()
