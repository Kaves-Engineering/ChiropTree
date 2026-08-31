"""Build data/world_map.json — the country outlines the species panel draws.

Two Natural Earth sources (public domain), both re-fetchable into data/raw/,
which is gitignored:

  ne_110m_admin_0_countries.geojson    the polygons actually drawn
  ne_50m_admin_0_map_subunits.geojson  only used to place dots for the small
                                       islands 110m leaves out (Fiji, Comoros,
                                       Guadeloupe, the Andamans and ~130 more)

  curl -o data/raw/ne_110m_admin_0_countries.geojson \
    https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson
  curl -o data/raw/ne_50m_admin_0_map_subunits.geojson \
    https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_map_subunits.geojson

The build prints any country name in the taxonomy it cannot place; that count
should stay at zero.

Everything is projected (Robinson), simplified and rounded here, so the page
ships flat SVG path strings and does no geometry work at runtime.

Natural Earth draws Crimea as part of Russia's polygon (their documented
de-facto-control editorial choice). That is not the internationally
recognised position — the UN General Assembly affirmed Ukraine's territorial
integrity within its recognised borders, including Crimea, in resolution
68/262 — so `fix_crimea()` below cuts the peninsula out of Russia's shape and
merges it into Ukraine's before anything is projected or simplified. That
step needs Shapely for the polygon boolean ops; `uv run` picks it up from the
inline metadata block just below without touching the project's own
dependencies.

Run:  uv run data/build_world_map.py
"""
# /// script
# dependencies = ["shapely"]
# ///

import io
import json
import math
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "world_map.json")

W = 800.0            # projected width in px
EPS = 0.40           # Douglas-Peucker tolerance, px
MIN_RING_AREA = 1.2  # drop projected rings smaller than this, px^2
LAT_MIN = -57.0      # crop Antarctica; no bats there

# Robinson interpolation table, latitude 0..90 in 5 degree steps
RX = [1.0000, 0.9986, 0.9954, 0.9900, 0.9822, 0.9730, 0.9600, 0.9427, 0.9216,
      0.8962, 0.8679, 0.8350, 0.7986, 0.7597, 0.7186, 0.6732, 0.6213, 0.5722, 0.5322]
RY = [0.0000, 0.0620, 0.1240, 0.1860, 0.2480, 0.3100, 0.3720, 0.4340, 0.4958,
      0.5571, 0.6176, 0.6769, 0.7346, 0.7903, 0.8435, 0.8936, 0.9394, 0.9761, 1.0000]


def robinson(lon, lat):
    """Return unscaled Robinson coordinates; y grows northwards."""
    lat = max(-90.0, min(90.0, lat))
    a = abs(lat) / 5.0
    i = min(int(a), 17)
    t = a - i
    x = (RX[i] + (RX[i + 1] - RX[i]) * t) * 0.8487 * math.radians(lon)
    y = (RY[i] + (RY[i + 1] - RY[i]) * t) * 1.3523
    return x, (y if lat >= 0 else -y)


# world extent, so the projection can be scaled into the viewBox
_X0, _ = robinson(-180, 0)
_X1, _ = robinson(180, 0)
_, _Y1 = robinson(0, 90)
_, _Y0 = robinson(0, LAT_MIN)
SCALE = W / (_X1 - _X0)
H = round((_Y1 - _Y0) * SCALE, 1)


def project(lon, lat):
    x, y = robinson(lon, lat)
    return ((x - _X0) * SCALE, (_Y1 - y) * SCALE)


def norm(s):
    """Accent- and punctuation-insensitive key for name matching."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def ring_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def simplify(pts, eps):
    """Iterative Douglas-Peucker."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi <= lo + 1:
            continue
        ax, ay = pts[lo]
        bx, by = pts[hi]
        dx, dy = bx - ax, by - ay
        den = math.hypot(dx, dy)
        far, fd = -1, eps
        for i in range(lo + 1, hi):
            px, py = pts[i]
            d = (abs(dx * (ay - py) - (ax - px) * dy) / den) if den else math.hypot(px - ax, py - ay)
            if d > fd:
                far, fd = i, d
        if far > 0:
            keep[far] = True
            stack.append((lo, far))
            stack.append((far, hi))
    return [p for p, k in zip(pts, keep) if k]


def polys(geom):
    """Yield each outer/inner ring of a (Multi)Polygon as a list of lon/lat."""
    if not geom:
        return
    if geom["type"] == "Polygon":
        for ring in geom["coordinates"]:
            yield ring
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            for ring in poly:
                yield ring


def to_path(geom):
    """Project, simplify and serialise one feature's geometry."""
    out, box = [], None
    for ring in polys(geom):
        pts = []
        for lon, lat in ring:
            if lat < LAT_MIN:
                lat = LAT_MIN
            pts.append(project(lon, lat))
        if len(pts) < 4:
            continue
        pts = simplify(pts, EPS)
        if len(pts) < 4 or ring_area(pts) < MIN_RING_AREA:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        b = (min(xs), min(ys), max(xs), max(ys))
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]),
                                     max(box[2], b[2]), max(box[3], b[3]))
        d = "M" + " L".join("%.1f %.1f" % p for p in pts) + "Z"
        out.append(d)
    return ("".join(out), box)


def centroid(geom):
    """Area-weighted centroid of the largest ring, projected."""
    best, best_a = None, -1.0
    for ring in polys(geom):
        pts = [project(lon, max(lat, LAT_MIN)) for lon, lat in ring]
        if len(pts) < 3:
            continue
        a = ring_area(pts)
        if a > best_a:
            best_a, best = a, pts
    if not best:
        return None
    n = len(best)
    return (round(sum(p[0] for p in best) / n, 1), round(sum(p[1] for p in best) / n, 1))


NAME_KEYS = ("ADMIN", "NAME", "NAME_LONG", "NAME_EN", "BRK_NAME", "FORMAL_EN",
             "SUBUNIT", "GEOUNIT", "ISO_A3", "ISO_A3_EH")

# SOVEREIGNT is deliberately not in NAME_KEYS: a dependency's SOVEREIGNT is its
# parent state's name (e.g. Greenland's SOVEREIGNT is "Denmark"), and if that
# alias were registered in the same pass as everyone's own name, a dependency
# processed before its sovereign could steal "denmark" -> GRL and leave Denmark
# itself unmatched. It is added in a second pass below, setdefault-only, so a
# country's own polygon always wins its own name.

# for the dot pass: names that identify the island itself, never its parent state
DOT_KEYS = ("SUBUNIT", "NAME", "NAME_LONG", "NAME_EN", "BRK_NAME")

# MDD spellings with no Natural Earth counterpart at any scale. The three BES
# islands are specks a few tens of km from the island they borrow here, which is
# under a pixel at this scale.
ALIASES = {
    "bonaire": "Curacao",
    "saba": "Sint Maarten",
    "sint eustatius": "Sint Maarten",
    "northern marianas": "Northern Mariana Islands",
    "andaman and nicobar islands": "Andaman Is.",
    "antigua and barbuda": "Antigua",
    "sao tome and principe": "Sao Tome",
    "micronesia": "Federated States of Micronesia",
    "cocos islands": "Cocos Is.",
    "galapagos islands": "Galapagos Islands",
}


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


# lon/lat box around the Crimean peninsula, tight enough to stop short of the
# Kerch Strait so it doesn't also bite into Russia's Taman Peninsula opposite
CRIMEA_BOX = (32.4, 44.0, 36.6, 46.3)


def fix_crimea(features):
    """Move Crimea from Russia's polygon to Ukraine's, in place.

    Natural Earth's 110m countries file draws Crimea as Russian; this reflects
    military control, not recognised sovereignty. Cut unconditionally — if a
    future Natural Earth release already draws Crimea as Ukrainian, the
    intersection/difference below are simply no-ops.
    """
    import shapely.geometry as sg

    russia = ukraine = None
    for f in features:
        admin = f["properties"].get("ADMIN")
        if admin == "Russia":
            russia = f
        elif admin == "Ukraine":
            ukraine = f
    if not russia or not ukraine:
        print("  fix_crimea: Russia and/or Ukraine feature not found, skipped")
        return

    box = sg.box(*CRIMEA_BOX)
    rus_geom = sg.shape(russia["geometry"]).buffer(0)
    ukr_geom = sg.shape(ukraine["geometry"]).buffer(0)
    crimea = rus_geom.intersection(box)
    if crimea.is_empty:
        return  # already not part of Russia's shape

    russia["geometry"] = sg.mapping(rus_geom.difference(box))
    ukraine["geometry"] = sg.mapping(ukr_geom.union(crimea))


def main():
    c110 = load(os.path.join(RAW, "ne_110m_admin_0_countries.geojson"))
    s50 = load(os.path.join(RAW, "ne_50m_admin_0_map_subunits.geojson"))
    fix_crimea(c110["features"])

    shapes, small, index, cent = {}, [], {}, {}

    def add_names(feat_props, key, keys=NAME_KEYS):
        for k in keys:
            v = feat_props.get(k)
            if v and v != "-99" and len(str(v)) > 2:
                index.setdefault(norm(str(v)), key)

    # 1. the polygons that actually get drawn
    for f in c110["features"]:
        p = f["properties"]
        if p.get("ADMIN") == "Antarctica":
            continue
        key = p.get("ISO_A3_EH") or p.get("ISO_A3") or p.get("ADMIN")
        if not key or key == "-99":
            key = norm(p.get("ADMIN", ""))[:8].upper()
        d, box = to_path(f.get("geometry"))
        if not d:
            continue
        shapes[key] = d
        cent[key] = centroid(f.get("geometry"))
        if box and (box[2] - box[0] < 5 or box[3] - box[1] < 5):
            small.append(key)
        add_names(p, key)

    # 1b. SOVEREIGNT as a fallback alias only, once every feature's own name is in
    for f in c110["features"]:
        p = f["properties"]
        key = p.get("ISO_A3_EH") or p.get("ISO_A3") or p.get("ADMIN")
        sov = p.get("SOVEREIGNT")
        if key and sov and sov != "-99" and len(str(sov)) > 2:
            index.setdefault(norm(str(sov)), key)

    # 2. dots for everything 110m is too coarse to show
    dots = {}
    for f in s50["features"]:
        p = f["properties"]
        own = [norm(str(p.get(k))) for k in DOT_KEYS if p.get(k) and p.get(k) != "-99"]
        if any(n in index for n in own):
            continue                      # this place is already a polygon
        c = centroid(f.get("geometry"))
        if not c:
            continue
        key = "d:" + (p.get("SUBUNIT") or p.get("NAME") or "?")
        dots[key] = c
        add_names(p, key, DOT_KEYS)

    # 3. hand-written spellings
    for a, target in ALIASES.items():
        k = index.get(norm(target))
        if k:
            index.setdefault(norm(a), k)
        else:
            print("  alias target not found: %s" % target)

    payload = {
        "_meta": {
            "source": "Natural Earth 110m admin-0 countries (outlines) and 50m map subunits (island dots)",
            "sourceUrl": "https://www.naturalearthdata.com",
            "projection": "Robinson, cropped at %g degrees south" % LAT_MIN,
            "license": "public domain",
        },
        "w": round(W, 1),
        "h": H,
        "shapes": shapes,
        "dots": dots,
        "cent": cent,
        "small": sorted(set(small)),
        "index": index,
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        # indent=1 keeps every line short: build.sh inlines this file with awk,
        # which reads line by line, and matches the other data files here
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)

    print("viewBox 0 0 %g %g" % (W, H))
    print("%d polygons, %d dots, %d name aliases" % (len(shapes), len(dots), len(index)))
    print("%.0f KB" % (os.path.getsize(OUT) / 1024.0))

    # coverage report against the taxonomy the page ships
    tax = load(os.path.join(HERE, "chiroptera_taxonomy.json"))
    seen, miss = set(), set()
    for s in tax["species"]:
        v = (s.get("countryDistribution") or "").strip()
        if not v or v == "NA":
            continue
        for n in v.split("|"):
            n = n.strip().rstrip("?").strip()
            if not n:
                continue
            seen.add(n)
            if norm(n) not in index:
                miss.add(n)
    print("countries used by the taxonomy: %d, unmatched: %d" % (len(seen), len(miss)))
    for n in sorted(miss):
        print("   unmatched: %s" % n)


if __name__ == "__main__":
    main()
