#!/usr/bin/env python3
"""
build_route.py - bakt de referentieroute in tot een JS-constante.

Leest de dag-GPX'en uit gpx/, ketent ze aan elkaar tot een doorlopende lus,
downsamplet naar ~2000 punten en schrijft route_data.js. Dat bestand wordt
inline in tourtool.html geplakt (zie inject_route.py, of handmatig plakken
tussen de ROUTE-markers).

Draai opnieuw als de route wijzigt:

    python3 build_route.py

Geen dependencies buiten de stdlib.
"""

import argparse
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

GPX_NS = "http://www.topografix.com/GPX/1/1"
HERE = os.path.dirname(os.path.abspath(__file__))

# Dagbestanden in volgorde. De lus sluit: eind van dag 4 == start van dag 1.
DAY_FILES = [
    ("Dag 1", "gpx/dag1.gpx"),
    ("Dag 2", "gpx/dag2.gpx"),
    ("Dag 3", "gpx/dag3.gpx"),
    ("Dag 4", "gpx/dag4.gpx"),
]

# Downsample-doel. ~250 m interval over 579 km geeft ~2300 punten; de
# Douglas-Peucker-pass daarna knijpt dat terug richting TARGET_POINTS.
RESAMPLE_M = 250.0
TARGET_POINTS = 2000

# Hoeveel klimmen er in het bergklassement meedoen. We detecteren ruim en
# houden de zwaarste over, zodat dit getal een keuze is en niet de uitkomst
# van twee drempels die je net zo lang bijstelt tot het toevallig klopt.
TARGET_CLIMBS = 26

# Namen voor gedetecteerde klimmen: (naam, lat top, lon top, radius m).
# Alleen cols waarvan de positie vaststaat. Klimmen die hier niet in de buurt
# van liggen krijgen "Klim km X" - hernoem die met de hand in DEFAULT_SEGMENTS
# als je een betere naam weet.
LANDMARKS = [
    ("Vrsic", 46.43287, 13.74640, 2500),
    ("Predel", 46.41775, 13.57880, 2000),
    ("Predel-aanloop", 46.45740, 13.57440, 2000),
    ("Rakitna", 45.90680, 14.43100, 2500),
]

# ---------------------------------------------------------------- geo helpers

R_EARTH = 6371008.8


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(min(1.0, math.sqrt(h)))


# ------------------------------------------------------------------- parsing


def parse_gpx(path):
    """Alle trkpt uit een GPX als [(lat, lon, ele)]."""
    tree = ET.parse(path)
    pts = []
    for p in tree.getroot().iter("{%s}trkpt" % GPX_NS):
        lat = float(p.get("lat"))
        lon = float(p.get("lon"))
        ele_el = p.find("{%s}ele" % GPX_NS)
        ele = float(ele_el.text) if ele_el is not None and ele_el.text else 0.0
        pts.append((lat, lon, ele))
    if not pts:
        raise SystemExit("geen trkpt gevonden in %s" % path)
    return pts


def chain_days(day_files):
    """Ketent de dagbestanden. Geeft (punten, dagsplits in meters)."""
    chained = []
    splits = []
    for label, rel in day_files:
        path = os.path.join(HERE, rel)
        if not os.path.exists(path):
            raise SystemExit("ontbrekend bestand: %s" % path)
        pts = parse_gpx(path)
        if chained:
            gap = haversine(chained[-1][0], chained[-1][1], pts[0][0], pts[0][1])
            if gap > 500:
                print(
                    "  ! LET OP: gat van %.0f m tussen %s en de vorige dag"
                    % (gap, label),
                    file=sys.stderr,
                )
            # Eerste punt overlapt met het laatste van de vorige dag: overslaan.
            if gap < 50:
                pts = pts[1:]
        start_m = cumulative(chained)[-1] if chained else 0.0
        chained.extend(pts)
        splits.append({"label": label, "file": os.path.basename(rel), "start_m": start_m})
    # eind-km per dag invullen
    total = cumulative(chained)[-1]
    for i, s in enumerate(splits):
        s["end_m"] = splits[i + 1]["start_m"] if i + 1 < len(splits) else total
    return chained, splits


def cumulative(pts):
    """Cumulatieve afstand in meters per punt."""
    if not pts:
        return [0.0]
    out = [0.0]
    for i in range(1, len(pts)):
        out.append(out[-1] + haversine(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]))
    return out


# ------------------------------------------------------------------ smoothing


def smooth_ele(eles, dists, window_m=200.0):
    """Voortschrijdend gemiddelde over een venster in meters.

    Komoot-hoogtes zitten vol trapjes; ongefilterd tellen die op tot honderden
    valse hoogtemeters.

    Let op het woord gemiddelde: dat is een gemiddelde over de AFSTAND, niet
    over de punten. Komoot zet punten neer waar de weg draait, dus in een
    haarspeld liggen ze vijf meter uit elkaar en op een recht stuk tachtig.
    Middel je dan gewoon de puntwaardes, dan trekt zo'n cluster het
    gemiddelde naar zich toe en wordt de klim steiler dan hij is - op Vrsic
    scheelde dat 22% waar 15% de werkelijkheid was.

    We integreren daarom het lijnstuk-profiel over het venster en delen door
    de lengte. Met een prefixsom van de trapezia kost dat O(1) per punt.
    """
    n = len(eles)
    if n < 2:
        return list(eles)

    # opp[i] = oppervlak onder het profiel van dists[0] tot dists[i]
    opp = [0.0] * n
    for i in range(1, n):
        opp[i] = opp[i - 1] + (dists[i] - dists[i - 1]) * (eles[i] + eles[i - 1]) / 2

    def integraal(a, b):
        """Oppervlak onder het profiel tussen meterstand a en b."""
        return _opp_tot(dists, eles, opp, b) - _opp_tot(dists, eles, opp, a)

    out = [0.0] * n
    for i in range(n):
        a = max(dists[0], dists[i] - window_m)
        b = min(dists[-1], dists[i] + window_m)
        span = b - a
        out[i] = eles[i] if span <= 0 else integraal(a, b) / span
    return out


def _opp_tot(dists, eles, opp, m):
    """Oppervlak onder het profiel van het begin tot meterstand m."""
    if m <= dists[0]:
        return 0.0
    if m >= dists[-1]:
        return opp[-1]
    lo, hi = 0, len(dists) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if dists[mid] <= m:
            lo = mid
        else:
            hi = mid
    seg = dists[hi] - dists[lo]
    f = 0.0 if seg <= 0 else (m - dists[lo]) / seg
    e = eles[lo] + (eles[hi] - eles[lo]) * f
    return opp[lo] + (m - dists[lo]) * (eles[lo] + e) / 2


def total_gain(eles, threshold=2.0):
    """Hoogtemeters met een dode zone, zodat ruis niet meetelt."""
    gain = 0.0
    ref = eles[0]
    for e in eles[1:]:
        if e > ref + threshold:
            gain += e - ref
            ref = e
        elif e < ref:
            ref = e
    return gain


# ---------------------------------------------------------------- downsample


def resample(pts, dists, step_m):
    """Lineair interpoleren naar een vast afstandsinterval."""
    out = []
    total = dists[-1]
    j = 0
    d = 0.0
    while d <= total:
        while j < len(dists) - 2 and dists[j + 1] < d:
            j += 1
        seg = dists[j + 1] - dists[j]
        f = 0.0 if seg <= 0 else (d - dists[j]) / seg
        a, b = pts[j], pts[j + 1]
        out.append(
            (
                a[0] + (b[0] - a[0]) * f,
                a[1] + (b[1] - a[1]) * f,
                a[2] + (b[2] - a[2]) * f,
                d,
            )
        )
        d += step_m
    last = pts[-1]
    if out[-1][3] < total - 1:
        out.append((last[0], last[1], last[2], total))
    return out


def rdp_indices(points, epsilon, breaks=()):
    """Douglas-Peucker, iteratief (2000+ punten recursief overloopt de stack).

    breaks zijn indices die altijd behouden blijven en de reeks opknippen.
    Nodig voor de plattegrond: de route is een lus, dus zonder knip vallen
    het eerste en laatste punt samen, is de basislijn ontaard en houdt RDP
    niets over.
    """
    n = len(points)
    keep = [False] * n
    keep[0] = keep[n - 1] = True
    anchors = sorted({0, n - 1} | {b for b in breaks if 0 < b < n - 1})
    for b in anchors:
        keep[b] = True
    stack = [(anchors[i], anchors[i + 1]) for i in range(len(anchors) - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        x1, y1 = points[first]
        x2, y2 = points[last]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1.0
        dmax, index = 0.0, first
        for i in range(first + 1, last):
            x0, y0 = points[i]
            d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / norm
            if d > dmax:
                dmax, index = d, i
        if dmax > epsilon:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    return [i for i, k in enumerate(keep) if k]


def downsample(res_pts, target, breaks=()):
    """Downsample op geometrie en hoogteprofiel tegelijk.

    Twee RDP-passes waarvan we de behouden punten samenvoegen. Alleen op het
    profiel simplificeren snijdt bochten af: een stuk dat vlak is in hoogte
    kan in het platte vlak een haarspeld zijn, en dan projecteren de sporen
    straks honderden meters verkeerd. We zoeken een schaal waarbij de unie
    net onder target punten blijft; de hoogte-epsilon loopt op de helft van
    de geometrie-epsilon mee.
    """
    # lat/lon naar lokale meters, zodat epsilon in meters klopt
    lat0 = math.radians(res_pts[0][0])
    mx = R_EARTH * math.cos(lat0)
    plan = [(math.radians(p[1]) * mx, math.radians(p[0]) * R_EARTH) for p in res_pts]
    # x in meters, niet in km: anders zit de loodrechte afstand in gemengde
    # eenheden en vlakt RDP scherpe toppen af (Vrsic verloor zo 20 hoogtemeter)
    prof = [(p[3], p[2]) for p in res_pts]

    lo, hi = 0.5, 200.0
    best = sorted(set(range(len(res_pts))))
    for _ in range(40):
        mid = (lo + hi) / 2
        union = set(rdp_indices(plan, mid, breaks)) | set(
            rdp_indices(prof, mid / 3, breaks)
        )
        if len(union) > target:
            lo = mid
        else:
            best = sorted(union)
            hi = mid
        if hi - lo < 0.05:
            break
    return best


# ------------------------------------------------------------ klimdetectie


def detect_climbs(dists, eles, min_gain=40.0, min_grade=2.0):
    """Vindt aaneengesloten klimmen in het gesmoothde profiel.

    Werkwijze: markeer stijgende stukken over een 400 m-venster, plak stukken
    aan elkaar die minder dan 1 km uit elkaar liggen en er tussenin niet meer
    dan 40 m verliezen, en houd alles over met genoeg hoogtewinst.

    De drempel ligt laag met opzet: een klimmetje van honderd hoogtemeters
    mag ook punten opleveren.
    """
    n = len(dists)
    win = 400.0
    rising = [False] * n
    j = 0
    for i in range(n):
        while j < n - 1 and dists[j] - dists[i] < win:
            j += 1
        run = dists[j] - dists[i]
        if run > 0 and (eles[j] - eles[i]) / run * 100 >= min_grade:
            rising[i] = True

    runs = []
    i = 0
    while i < n:
        if rising[i]:
            k = i
            while k < n and rising[k]:
                k += 1
            # het venster kijkt vooruit, dus het echte einde ligt win verder
            end = k
            while end < n - 1 and dists[end] - dists[k] < win:
                end += 1
            runs.append([i, end])
            i = k
        else:
            i += 1

    merged = []
    for r in runs:
        if merged:
            prev = merged[-1]
            gap = dists[r[0]] - dists[prev[1]]
            dip = eles[prev[1]] - min(eles[prev[1] : r[0] + 1] or [eles[prev[1]]])
            if gap < 1000 and dip < 40:
                prev[1] = r[1]
                continue
        merged.append(r)

    climbs = []
    for a, b in merged:
        gain = total_gain(eles[a : b + 1], threshold=0.5)
        length = dists[b] - dists[a]
        if gain >= min_gain and length > 500:
            climbs.append(
                {
                    "start_m": dists[a],
                    "end_m": dists[b],
                    "length_m": length,
                    "gain_m": gain,
                    "grade": gain / length * 100,
                    "top_m": max(eles[a : b + 1]),
                    "i0": a,
                    "i1": b,
                }
            )
    return climbs


def fiets_index(gain_m, length_m):
    """Zwaarte van een klim: hoogtewinst in het kwadraat gedeeld door de
    lengte. Zo weegt steil veel zwaarder dan lang, wat overeenkomt met hoe
    een klim aanvoelt. Vrsic komt op ruim 7 uit, een vlakke oprit op 0,3.
    """
    if length_m <= 0:
        return 0.0
    return gain_m * gain_m / (length_m * 10.0)


# Ondergrens van de zwaarte-index per categorie.
#
# Bewust laag afgesteld: liever veel klimmetjes waar wat te pakken valt dan
# drie beslissende bergen. Een bult van honderd hoogtemeters telt gewoon mee.
CATS = [
    (5.0, "HC"),
    (2.0, "1"),
    (1.05, "2"),
    (0.50, "3"),
    (0.25, "4"),
    (0.0, "5"),
]


def categorie(index):
    for grens, naam in CATS:
        if index >= grens:
            return naam
    return None


def find_sprints(dists, eles, splits, per_dag=2):
    """Zoekt vlakke plekken voor tussensprints.

    Een sprint hoort op vlak terrein: bergop is het gewoon klimmen, bergaf
    is het rollen. We zoeken per dag de vlakste punten rond een derde en
    twee derde van de dag, gemeten over de laatste twee kilometer ervoor.
    """
    out = []
    for s in splits:
        d0, d1 = s["start_m"], s["end_m"]
        for k in range(1, per_dag + 1):
            doel = d0 + (d1 - d0) * k / (per_dag + 1)
            beste, beste_score = None, 1e9
            # een venster van 12 km rond het doel aftasten
            m = max(d0 + 3000, doel - 6000)
            while m < min(d1 - 500, doel + 6000):
                aanloop = 2000.0
                if m - aanloop < d0:
                    m += 250
                    continue
                e0 = ele_at(dists, eles, m - aanloop)
                e1 = ele_at(dists, eles, m)
                # gemiddelde steilheid over de aanloop, plus de ruwheid
                helling = abs(e1 - e0) / aanloop * 100
                ruw = 0.0
                stappen = 8
                for j in range(stappen):
                    a = ele_at(dists, eles, m - aanloop + aanloop * j / stappen)
                    b = ele_at(dists, eles, m - aanloop + aanloop * (j + 1) / stappen)
                    ruw += abs(b - a)
                score = helling * 3 + ruw / aanloop * 100
                # niet te dicht op een eerdere sprint
                if any(abs(m - p["m"]) < 8000 for p in out):
                    score += 50
                if score < beste_score:
                    beste_score, beste = score, m
                m += 250
            if beste is not None:
                out.append({"m": beste, "dag": s["label"], "vlakheid": beste_score})
    return out


def ele_at(dists, eles, m):
    """Hoogte op meterstand m, lineair tussen twee rasterpunten."""
    if m <= dists[0]:
        return eles[0]
    if m >= dists[-1]:
        return eles[-1]
    lo, hi = 0, len(dists) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if dists[mid] <= m:
            lo = mid
        else:
            hi = mid
    span = dists[hi] - dists[lo]
    f = 0.0 if span <= 0 else (m - dists[lo]) / span
    return eles[lo] + (eles[hi] - eles[lo]) * f


def name_climb(pts, i0, i1):
    """Noemt een klim naar de dichtstbijzijnde bekende landmark bij de top."""
    seg = pts[i0 : i1 + 1]
    top = max(seg, key=lambda p: p[2])
    best, bestd = None, 1e9
    for nm, lat, lon, rad in LANDMARKS:
        d = haversine(top[0], top[1], lat, lon)
        if d < rad and d < bestd:
            best, bestd = nm, d
    return best


# ------------------------------------------------------------------- output


def js_number(x, digits):
    s = ("%." + str(digits) + "f") % x
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def emit_js(route, splits, climbs, sprints, meta):
    """Schrijft de JS-constante. Coordinaten op 5 decimalen (~1 m)."""
    lines = []
    lines.append("// Gegenereerd door build_route.py - NIET met de hand aanpassen.")
    lines.append("// Bron: %s" % ", ".join(m for m in meta["sources"]))
    lines.append(
        "// %s punten, %.1f km, +%.0f hm, top %.0f m"
        % (len(route), meta["total_m"] / 1000, meta["gain_m"], meta["max_ele"])
    )
    lines.append("const ROUTE_META = %s;" % json.dumps(meta["short"], ensure_ascii=False))
    lines.append("")
    lines.append("// [ cumulatieve meters, lat, lon, hoogte m ] per punt")
    lines.append("const ROUTE_PTS = [")
    chunk = []
    for p in route:
        chunk.append(
            "[%s,%s,%s,%s]"
            % (
                js_number(p[3], 0),
                js_number(p[0], 5),
                js_number(p[1], 5),
                js_number(p[2], 0),
            )
        )
    for i in range(0, len(chunk), 8):
        lines.append(" " + ",".join(chunk[i : i + 8]) + ",")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("];")
    lines.append("")
    lines.append("// Dagsplits uit de losse dag-GPX'en. Instelbaar in de UI.")
    lines.append(
        "const DEFAULT_DAYS = %s;"
        % json.dumps(
            [
                {
                    "label": s["label"],
                    "startKm": round(s["start_m"] / 1000, 1),
                    "endKm": round(s["end_m"] / 1000, 1),
                }
                for s in splits
            ],
            ensure_ascii=False,
        )
    )
    lines.append("")
    lines.append("// Alle klimmen uit het profiel, met categorie voor het")
    lines.append("// bergklassement. cat HC is het zwaarst, 4 het lichtst.")
    lines.append("const DEFAULT_CLIMBS = [")
    for c in climbs:
        lines.append(
            '  {name:%s, day:%s, cat:%s, index:%s, startKm:%s, endKm:%s, lengthKm:%s, gainM:%s, grade:%s, topM:%s},'
            % (
                json.dumps(c["name"], ensure_ascii=False),
                json.dumps(c.get("day", ""), ensure_ascii=False),
                json.dumps(c["cat"], ensure_ascii=False),
                js_number(c["index"], 2),
                js_number(c["start_m"] / 1000, 1),
                js_number(c["end_m"] / 1000, 1),
                js_number(c["length_m"] / 1000, 1),
                js_number(c["gain_m"], 0),
                js_number(c["grade"], 1),
                js_number(c["top_m"], 0),
            )
        )
    lines.append("];")
    lines.append("")
    lines.append("// Tussensprints op de vlakste plekken van elke dag. De")
    lines.append("// dagfinish telt daarnaast altijd mee voor het sprintklassement.")
    lines.append("const DEFAULT_SPRINTS = [")
    for s in sprints:
        lines.append(
            '  {name:%s, day:%s, km:%s},'
            % (
                json.dumps(s["name"], ensure_ascii=False),
                json.dumps(s["dag"], ensure_ascii=False),
                js_number(s["m"] / 1000, 1),
            )
        )
    lines.append("];")
    lines.append("")
    return "\n".join(lines)


def inject(html_path, js_blob):
    """Vervangt het blok tussen de ROUTE-markers in tourtool.html."""
    if not os.path.exists(html_path):
        return False
    with open(html_path, encoding="utf-8") as fh:
        html = fh.read()
    start = "/* === ROUTE DATA START === */"
    end = "/* === ROUTE DATA END === */"
    if start not in html or end not in html:
        return False
    pattern = re.compile(
        re.escape(start) + ".*?" + re.escape(end), re.DOTALL
    )
    html = pattern.sub(start + "\n" + js_blob + end, html)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return True


# --------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(HERE, "route_data.js"))
    ap.add_argument("--html", default=os.path.join(HERE, "tourtool.html"))
    ap.add_argument("--points", type=int, default=TARGET_POINTS)
    ap.add_argument("--no-inject", action="store_true")
    args = ap.parse_args()

    print("GPX inlezen en aan elkaar ketenen")
    pts, splits = chain_days(DAY_FILES)
    dists = cumulative(pts)
    raw_eles = [p[2] for p in pts]
    sm = smooth_ele(raw_eles, dists)
    pts = [(p[0], p[1], sm[i]) for i, p in enumerate(pts)]

    total_m = dists[-1]
    gain = total_gain(sm)
    print(
        "  %d ruwe punten, %.1f km, +%.0f hm, hoogte %.0f..%.0f m"
        % (len(pts), total_m / 1000, gain, min(sm), max(sm))
    )
    loop_gap = haversine(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1])
    print("  lus sluit op %.0f m" % loop_gap)

    print("Downsamplen")
    res = resample(pts, dists, RESAMPLE_M)
    # dagovergangen als vaste knikpunten: ze knippen de lus open en blijven
    # zo gegarandeerd als vertex in de route staan
    breaks = []
    for s in splits[1:]:
        breaks.append(min(range(len(res)), key=lambda i: abs(res[i][3] - s["start_m"])))
    idx = downsample(res, args.points, breaks)
    route = [res[i] for i in idx]
    print("  %d -> %d -> %d punten" % (len(pts), len(res), len(route)))

    rd = [p[3] for p in route]
    re_ = [p[2] for p in route]
    # Echte fout meten: het gedownsamplede profiel lineair uitlezen op elk
    # resample-punt, en de loodrechte afstand tot de vereenvoudigde polyline.
    err = 0.0
    geo_err = 0.0
    k = 0
    lat0 = math.radians(route[0][0])
    mx = R_EARTH * math.cos(lat0)
    xy = [(math.radians(p[1]) * mx, math.radians(p[0]) * R_EARTH) for p in route]
    for p in res:
        while k < len(rd) - 2 and rd[k + 1] < p[3]:
            k += 1
        span = rd[k + 1] - rd[k]
        f = 0.0 if span <= 0 else (p[3] - rd[k]) / span
        err = max(err, abs(re_[k] + (re_[k + 1] - re_[k]) * f - p[2]))
        px, py = math.radians(p[1]) * mx, math.radians(p[0]) * R_EARTH
        (ax, ay), (bx, by) = xy[k], xy[k + 1]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 <= 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        geo_err = max(geo_err, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    print(
        "  na downsample: %.1f km, +%.0f hm (max hoogtefout %.1f m, max lijnfout %.0f m)"
        % (rd[-1] / 1000, total_gain(re_), err, geo_err)
    )

    print("Klimmen detecteren")
    climbs = detect_climbs(rd, re_)
    for c in climbs:
        c["name"] = name_climb(route, c["i0"], c["i1"]) or "km %.0f" % (
            c["start_m"] / 1000
        )
    # dubbele namen uniek maken
    seen = {}
    for c in climbs:
        seen[c["name"]] = seen.get(c["name"], 0) + 1
        if seen[c["name"]] > 1:
            c["name"] = "%s %d" % (c["name"], seen[c["name"]])
    # De zwaarste TARGET_CLIMBS houden, daarna weer op volgorde van de route.
    for c in climbs:
        c["index"] = fiets_index(c["gain_m"], c["length_m"])
    gevonden = len(climbs)
    climbs = sorted(climbs, key=lambda c: -c["index"])[:TARGET_CLIMBS]
    climbs.sort(key=lambda c: c["start_m"])
    for c in climbs:
        c["cat"] = categorie(c["index"])
        mid = (c["start_m"] + c["end_m"]) / 2
        c["day"] = next(
            (s["label"] for s in splits if s["start_m"] <= mid < s["end_m"]), ""
        )
    print("  %d gevonden, de %d zwaarste doen mee" % (gevonden, len(climbs)))

    print("  %-20s %-6s %5s %7s %8s %6s %6s %5s"
          % ("klim", "dag", "cat", "van km", "tot km", "km", "hm", "gem%"))
    for c in climbs:
        print(
            "  %-20s %-6s %5s %7.1f %8.1f %6.1f %6.0f %5.1f   index %.2f"
            % (c["name"], c["day"], c["cat"], c["start_m"] / 1000, c["end_m"] / 1000,
               c["length_m"] / 1000, c["gain_m"], c["grade"], c["index"])
        )

    print("Tussensprints zoeken")
    sprints = find_sprints(rd, re_, splits)
    for i, sp in enumerate(sprints):
        # naam naar de dichtstbijzijnde klim of gewoon de kilometer
        sp["name"] = "Sprint km %.0f" % (sp["m"] / 1000)
        print("  %-16s %-6s km %7.1f   vlakheid %.2f"
              % (sp["name"], sp["dag"], sp["m"] / 1000, sp["vlakheid"]))

    meta = {
        "sources": [f for _, f in DAY_FILES],
        "total_m": rd[-1],
        "gain_m": total_gain(re_),
        "max_ele": max(re_),
        "short": {
            "totalKm": round(rd[-1] / 1000, 1),
            "gainM": round(total_gain(re_)),
            "maxEleM": round(max(re_)),
            "startLat": round(route[0][0], 5),
            "startLon": round(route[0][1], 5),
            "points": len(route),
        },
    }

    blob = emit_js(route, splits, climbs, sprints, meta)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(blob)
    print("Geschreven: %s (%.0f kB)" % (args.out, os.path.getsize(args.out) / 1024))

    if not args.no_inject:
        if inject(args.html, blob):
            print("Ingebakken in %s" % args.html)
        else:
            print("tourtool.html nog niet aanwezig of geen markers - alleen route_data.js")


if __name__ == "__main__":
    main()
