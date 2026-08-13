#!/usr/bin/env python3
"""
make_icons.py - tekent de app-iconen uit het echte hoogteprofiel.

Leest route_data.js en zet het profiel van de lus om in een icoon, met de
top van Vrsic als accent. Draai dit opnieuw als de route wijzigt.

    python3 make_icons.py

Schrijft docs/icon-180.png (iOS beginscherm), icon-192.png en icon-512.png.
Vraagt Pillow.
"""

import json
import os
import re
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Pillow ontbreekt:  pip install pillow")

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")

BG = (11, 13, 16)
LIJN = (56, 189, 248)
VLAK = (30, 74, 100)
TOP = (255, 183, 3)


def lees_profiel():
    """Haalt [(meter, hoogte)] uit de route-constante."""
    with open(os.path.join(HERE, "route_data.js"), encoding="utf-8") as fh:
        src = fh.read()
    blok = re.search(r"const ROUTE_PTS = \[(.*?)\n\];", src, re.DOTALL)
    if not blok:
        sys.exit("ROUTE_PTS niet gevonden - draai eerst build_route.py")
    punten = re.findall(r"\[(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)\]", blok.group(1))
    return [(float(p[0]), float(p[3])) for p in punten]


def teken(profiel, maat):
    # 4x renderen en terugschalen: scheelt kartelranden zonder extra werk
    S = 4
    N = maat * S
    im = Image.new("RGB", (N, N), BG)
    d = ImageDraw.Draw(im)

    marge = int(N * 0.10)
    breed = N - 2 * marge
    hoog = int(N * 0.54)
    grond = int(N * 0.75)

    m0, m1 = profiel[0][0], profiel[-1][0]
    lo = min(p[1] for p in profiel)
    hi = max(p[1] for p in profiel)

    def X(m):
        return marge + (m - m0) / (m1 - m0) * breed

    def Y(e):
        return grond - (e - lo) / (hi - lo) * hoog

    pad = [(X(m), Y(e)) for m, e in profiel]
    d.polygon([(marge, grond)] + pad + [(marge + breed, grond)], fill=VLAK)
    d.line(pad, fill=LIJN, width=max(2, int(N * 0.018)), joint="curve")

    # de top: het hoogste punt van de route
    top = max(profiel, key=lambda p: p[1])
    r = int(N * 0.034)
    d.ellipse([X(top[0]) - r, Y(top[1]) - r, X(top[0]) + r, Y(top[1]) + r], fill=TOP)

    # grondlijn
    d.line([(marge, grond), (marge + breed, grond)], fill=(44, 52, 62), width=max(1, int(N * 0.006)))

    return im.resize((maat, maat), Image.LANCZOS)


def main():
    os.makedirs(DOCS, exist_ok=True)
    profiel = lees_profiel()
    for maat in (180, 192, 512):
        pad = os.path.join(DOCS, "icon-%d.png" % maat)
        teken(profiel, maat).save(pad, optimize=True)
        print("Geschreven: %s (%.1f kB)" % (pad, os.path.getsize(pad) / 1024))


if __name__ == "__main__":
    main()
