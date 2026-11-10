"""Place a call recording among the species of a split, by where it was made.

A source that recorded bats under a name the current taxonomy has since split
recorded *some* of the daughter species, and the name alone cannot say which.
Where it was recorded often can: if every country the source names lies inside
exactly one candidate's range under MDD, and outside every other candidate's,
the recording can only be of that species.

This module only answers that question. build_calls.py decides what to do with
the answer, and every row it moves keeps quality_flag taxon_uncertain and a
note naming the printed name, the countries and the ranges that decided it.

The rule is deliberately strict:
  - every country the row names must parse; a region ("Europe", "Central
    America") or an unparseable place leaves the row where it is;
  - the target must be recorded present in each country (a "?" in MDD's
    country list is not enough);
  - every other candidate must be absent from each country, where a "?" counts
    as possibly present and so blocks the move.
"""
import re
import unicodedata

# ISO 3166 alpha-2 codes the sources print. "CA" and "SA" are left out on
# purpose: in these sources they mean Central and South America as often as
# Canada and Saudi Arabia.
ISO2 = {
    "BE": "Belgium", "BR": "Brazil", "CZ": "Czech Republic", "DE": "Germany",
    "DM": "Dominica", "ES": "Spain", "FR": "France", "GB": "United Kingdom",
    "GR": "Greece", "IT": "Italy", "MX": "Mexico", "NL": "Netherlands",
    "PA": "Panama", "PR": "Puerto Rico", "PT": "Portugal", "UK": "United Kingdom",
    "US": "United States", "VC": "Saint Vincent and the Grenadines",
    "CH": "Switzerland",
}

# Spellings in the sources that differ from MDD's. Islands MDD lists on their
# own (Canary Islands, Madeira, Azores) map to that entry, not to the state.
ALIASES = {
    "unitedkingdom": "United Kingdom",
    "uk": "United Kingdom",
    "swaziland": "Eswatini",
    "spain-tenerife": "Canary Islands",
    "tenerife": "Canary Islands",
    "portugal-madeira": "Madeira",
    "portugal-são miguel": "Azores",
    "malaysian borneo": "Malaysia",
    "sarawak": "Malaysia",
    "usa": "United States",
    "ivory coast": "Cote d'Ivoire",
    "dr congo": "Democratic Republic of the Congo",
}

# Whole strings that name a pair of countries with a slash.
PAIRS = {"US/CA": {"United States", "Canada"}, "BE/NL": {"Belgium", "Netherlands"}}


def _one(part: str, known: set[str], trailing: bool = False) -> str | None:
    """One place name -> an MDD country, or None if it is not a country.

    trailing=True also accepts free text ending in a country name
    ("Narino Department, SW Colombia").
    """
    text = unicodedata.normalize("NFC", part).strip().strip(".")
    text = re.sub(r"^(also|north-eastern|north-western|south-eastern|south-western|"
                  r"northern|southern|eastern|western|central|ne|nw|se|sw)\s+", "",
                  text, flags=re.I)
    text = re.sub(r"\s*\(.*\)$", "", text).strip()
    if text in known:
        return text
    if text.upper() in ISO2 and len(text) == 2:
        return ISO2[text.upper()]
    if text.lower() in ALIASES:
        return ALIASES[text.lower()]
    if trailing:
        for country in known:
            if re.search(rf"\b{re.escape(country)}$", text):
                return country
    return None


def countries(value: str, known: set[str]) -> set[str] | None:
    """Every country a source's country field names, or None if any part is
    not a country (a region, a code we do not trust, free text)."""
    value = re.sub(r"\s*\([^)]*\)", "", value or "").strip()  # glosses in parentheses
    if not value:
        return None
    if value.split(" | ")[0].strip() in PAIRS:
        return set(PAIRS[value.split(" | ")[0].strip()])
    # " | " separates the country from a free-text gloss ("BR | Central
    # Brazilian Amazon"), in either order. A gloss that names no country is
    # ignored; one that does ("GR | also Iran") adds to the set.
    found: set[str] = set()
    for chunk in (c.strip() for c in value.split(" | ")):
        parts = [p for p in re.split(r"\s*[,;|]\s*", chunk) if p]
        resolved = [_one(p, known) for p in parts]
        if all(resolved):
            found.update(resolved)  # "Croatia, France, Spain"
            continue
        whole = _one(chunk, known)  # "Sarawak, Malaysian Borneo"
        if whole:
            found.add(whole)
        elif not any(resolved[:-1]) and _one(parts[-1], known, trailing=True):
            found.add(_one(parts[-1], known, trailing=True))  # "Narino Department, SW Colombia"
        elif any(resolved):
            return None  # a list mixing countries and regions: cannot trust it
    return found or None


def range_of(species: dict) -> tuple[set[str], set[str]]:
    """(countries where present, countries where presence is queried)."""
    present, queried = set(), set()
    for entry in (species.get("countryDistribution") or "").split("|"):
        entry = entry.strip()
        if not entry or entry == "NA":
            continue
        if entry.endswith("?"):
            queried.add(entry[:-1])
        else:
            present.add(entry)
    return present, queried


def known_countries(taxonomy: list[dict]) -> set[str]:
    known = set()
    for species in taxonomy:
        present, queried = range_of(species)
        known |= present | queried
    return known


def place(where: set[str], candidates: list[dict]) -> dict | None:
    """The one candidate the recording countries allow, or None."""
    fits = []
    for species in candidates:
        present, queried = range_of(species)
        if where <= present:
            fits.append(species)
        elif where & (present | queried):
            return None  # another candidate may occur there: ambiguous
    return fits[0] if len(fits) == 1 else None
