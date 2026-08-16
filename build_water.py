#!/usr/bin/env python3
"""
build_water.py - bakt drinkwaterpunten langs de route in.

De data komt uit OpenStreetMap, dezelfde bron waar apps als Watrify op
draaien. Er is geen netwerk nodig om dit script te draaien: je haalt de
export een keer op en dit script rekent hem om.

    1. Open https://overpass-turbo.eu
    2. Plak de query die WATER_QUERY hieronder bevat (of draai
       `python3 build_water.py --query` om hem uit te printen)
    3. Run, dan Export -> download as GeoJSON
    4. python3 build_water.py water.geojson

Het script projecteert elk punt op de route, gooit alles weg wat verder dan
MAX_AFSTAND_M van de route ligt, en schrijft water_data.js. Dat blok wordt
in tourtool.html geplakt tussen de WATER-markers.

Ondersteunt GeoJSON, ruwe Overpass-JSON en GPX met waypoints.
"""

import argparse
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))

# Hoe ver een punt van de route mag liggen om mee te tellen. Een paar honderd
# meter omrijden voor water is prima; een kilometer is een ommetje.
MAX_AFSTAND_M = 350.0

# Punten die dichter dan dit bij elkaar liggen zijn in de praktijk hetzelfde
# tappunt (een plein met drie kranen hoeft niet drie keer in de lijst).
CLUSTER_M = 120.0

WATER_QUERY = """[out:json][timeout:120];
// Drinkwater langs de Grand Escape. Bounding box = de route plus 3 km.
(
  node["amenity"="drinking_water"]({bbox});
  node["man_made"="water_tap"]["drinking_water"!="no"]({bbox});
  node["amenity"="water_point"]({bbox});
  node["amenity"="fountain"]["drinking_water"~"^(yes|treated)$"]({bbox});
  node["natural"="spring"]["drinking_water"="yes"]({bbox});
  node["man_made"="water_well"]["drinking_water"="yes"]({bbox});
);
out body;
"""
BBOX = "45.73,12.92,46.54,14.55"

# ------------------------------------------------------------------ geo

R_EARTH = 6371008.8
DEG = math.pi / 180


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = lat1 * DEG, lat2 * DEG
    dp = p2 - p1
    dl = (lon2 - lon1) * DEG
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(min(1.0, math.sqrt(h)))


# ------------------------------------------------------- route inlezen

def lees_route():
    """ROUTE_PTS uit route_data.js als [(m, lat, lon, ele)]."""
    pad = os.path.join(HERE, "route_data.js")
    if not os.path.exists(pad):
        sys.exit("route_data.js ontbreekt - draai eerst build_route.py")
    src = open(pad, encoding="utf-8").read()
    blok = re.search(r"const ROUTE_PTS = \[(.*?)\n\];", src, re.DOTALL)
    if not blok:
        sys.exit("ROUTE_PTS niet gevonden in route_data.js")
    out = []
    for m in re.finditer(r"\[(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)\]", blok.group(1)):
        out.append(tuple(float(x) for x in m.groups()))
    return out


def projecteer(route, lat, lon):
    """Kortste afstand tot de route, plus de meterstand daar."""
    lat0 = route[0][1] * DEG
    mx = R_EARTH * math.cos(lat0)
    px, py = lon * DEG * mx, lat * DEG * R_EARTH
    best = (1e12, 0.0)
    for i in range(len(route) - 1):
        ax, ay = route[i][2] * DEG * mx, route[i][1] * DEG * R_EARTH
        bx, by = route[i + 1][2] * DEG * mx, route[i + 1][1] * DEG * R_EARTH
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 <= 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        qx, qy = ax + t * dx, ay + t * dy
        d = math.hypot(px - qx, py - qy)
        if d < best[0]:
            best = (d, route[i][0] + (route[i + 1][0] - route[i][0]) * t)
    return best


# ------------------------------------------------------- data inlezen

def lees_punten(pad):
    """Leest GeoJSON, Overpass-JSON of GPX-waypoints tot [(lat, lon, naam, soort)]."""
    tekst = open(pad, encoding="utf-8").read().strip()
    if tekst.startswith("<"):
        return _uit_gpx(tekst)
    data = json.loads(tekst)
    if data.get("type") == "FeatureCollection":
        return _uit_geojson(data)
    if "elements" in data:
        return _uit_overpass(data)
    sys.exit("onbekend formaat: geen GeoJSON, Overpass-JSON of GPX")


def _soort(tags):
    a = tags.get("amenity", "")
    if a == "drinking_water":
        return "kraan"
    if a == "fountain":
        return "fontein"
    if a == "water_point":
        return "tappunt"
    if tags.get("man_made") == "water_tap":
        return "kraan"
    if tags.get("natural") == "spring":
        return "bron"
    if tags.get("man_made") == "water_well":
        return "put"
    return "water"


def _naam(tags):
    for k in ("name", "operator", "description"):
        if tags.get(k):
            return tags[k][:40]
    return ""


def _uit_overpass(data):
    out = []
    for el in data.get("elements", []):
        lat = el.get("lat", (el.get("center") or {}).get("lat"))
        lon = el.get("lon", (el.get("center") or {}).get("lon"))
        if lat is None or lon is None:
            continue
        t = el.get("tags", {})
        out.append((lat, lon, _naam(t), _soort(t)))
    return out


def _uit_geojson(data):
    out = []
    for f in data.get("features", []):
        g = f.get("geometry") or {}
        if g.get("type") != "Point":
            continue
        lon, lat = g["coordinates"][0], g["coordinates"][1]
        t = f.get("properties", {}) or {}
        out.append((lat, lon, _naam(t), _soort(t)))
    return out


def _uit_gpx(tekst):
    root = ET.fromstring(tekst)
    ns = "{http://www.topografix.com/GPX/1/1}"
    out = []
    for w in root.iter(ns + "wpt"):
        naam = w.find(ns + "name")
        out.append((float(w.get("lat")), float(w.get("lon")),
                    (naam.text or "")[:40] if naam is not None else "", "water"))
    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bestand", nargs="?", help="GeoJSON, Overpass-JSON of GPX")
    ap.add_argument("--query", action="store_true", help="print de Overpass-query en stop")
    ap.add_argument("--max", type=float, default=MAX_AFSTAND_M)
    ap.add_argument("--out", default=os.path.join(HERE, "water_data.js"))
    ap.add_argument("--html", default=os.path.join(HERE, "tourtool.html"))
    args = ap.parse_args()

    if args.query or not args.bestand:
        print(WATER_QUERY.replace("{bbox}", BBOX))
        if not args.bestand:
            print("# Draai daarna:  python3 build_water.py water.geojson", file=sys.stderr)
        return

    route = lees_route()
    ruw = lees_punten(args.bestand)
    print("%d punten gelezen uit %s" % (len(ruw), os.path.basename(args.bestand)))

    # projecteren en filteren
    treffers = []
    for lat, lon, naam, soort in ruw:
        d, m = projecteer(route, lat, lon)
        if d <= args.max:
            treffers.append({"m": m, "dist": d, "lat": lat, "lon": lon,
                             "naam": naam, "soort": soort})
    treffers.sort(key=lambda x: x["m"])
    print("%d liggen binnen %.0f m van de route" % (len(treffers), args.max))

    # dubbelingen samenvoegen
    uniek = []
    for t in treffers:
        if uniek and (t["m"] - uniek[-1]["m"]) < CLUSTER_M and \
                haversine(t["lat"], t["lon"], uniek[-1]["lat"], uniek[-1]["lon"]) < CLUSTER_M:
            if t["dist"] < uniek[-1]["dist"]:
                uniek[-1] = t
            continue
        uniek.append(t)
    print("%d over na samenvoegen van punten binnen %.0f m" % (len(uniek), CLUSTER_M))

    # droge stukken
    totaal = route[-1][0]
    grenzen = [0.0] + [t["m"] for t in uniek] + [totaal]
    gaten = []
    for i in range(len(grenzen) - 1):
        gaten.append((grenzen[i + 1] - grenzen[i], grenzen[i], grenzen[i + 1]))
    gaten.sort(reverse=True)
    print("\nlangste stukken zonder water:")
    for lengte, a, b in gaten[:6]:
        print("  %5.1f km  van km %6.1f tot %6.1f" % (lengte / 1000, a / 1000, b / 1000))

    # wegschrijven
    lines = []
    lines.append("// Gegenereerd door build_water.py uit OpenStreetMap-data.")
    lines.append("// %d punten binnen %.0f m van de route." % (len(uniek), args.max))
    lines.append("// [ meters langs route, lat, lon, afstand tot route in m, soort, naam ]")
    lines.append("const DEFAULT_WATER = [")
    for t in uniek:
        lines.append("  [%d,%.5f,%.5f,%d,%s,%s]," % (
            round(t["m"]), t["lat"], t["lon"], round(t["dist"]),
            json.dumps(t["soort"], ensure_ascii=False),
            json.dumps(t["naam"], ensure_ascii=False)))
    if len(lines) > 4:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("];")
    blob = "\n".join(lines) + "\n"

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(blob)
    print("\nGeschreven: %s (%.0f kB)" % (args.out, os.path.getsize(args.out) / 1024))

    # in de HTML plakken
    if os.path.exists(args.html):
        html = open(args.html, encoding="utf-8").read()
        start, eind = "/* === WATER DATA START === */", "/* === WATER DATA END === */"
        if start in html and eind in html:
            html = re.sub(re.escape(start) + ".*?" + re.escape(eind),
                          start + "\n" + blob + eind, html, flags=re.DOTALL)
            open(args.html, "w", encoding="utf-8").write(html)
            print("Ingebakken in %s" % args.html)
        else:
            print("geen WATER-markers in de HTML gevonden")


if __name__ == "__main__":
    main()
