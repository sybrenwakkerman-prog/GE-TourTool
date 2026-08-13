#!/usr/bin/env python3
"""
build_web.py - maakt de twee hostbare versies van tourtool.html.

    python3 build_web.py

Schrijft:

  tourtool-web.html   Zonder eigen <html>/<head>/<body>, want een host zet
                      de pagina in zijn eigen omhulsel. Voor een gedeelde
                      link.

  docs/               Een installeerbare web-app voor GitHub Pages:
                      index.html, manifest.webmanifest en sw.js. Op een
                      iPhone is dit de enige manier om de tool zonder extra
                      app offline te draaien - Safari kan geen file:// en de
                      voorvertoning in Bestanden voert geen scripts uit. Na
                      een keer openen met wifi zet je hem op je beginscherm
                      en werkt hij zonder bereik.

Het gewone tourtool.html blijft het losse bestand voor wie het wel gewoon
kan openen.

Draai make_icons.py als de iconen ontbreken of de route is gewijzigd.
"""

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "tourtool.html")
DST = os.path.join(HERE, "tourtool-web.html")
DOCS = os.path.join(HERE, "docs")

# Wat de service worker vooraf in de kast legt. Alles wat de app nodig
# heeft, want daarna is er geen netwerk meer.
ASSETS = ["./", "./index.html", "./manifest.webmanifest",
          "./icon-180.png", "./icon-192.png", "./icon-512.png"]


def main():
    with open(SRC, encoding="utf-8") as fh:
        html = fh.read()

    head = re.search(r"<head>(.*?)</head>", html, re.DOTALL)
    body = re.search(r"<body>(.*?)</body>", html, re.DOTALL)
    if not head or not body:
        sys.exit("head of body niet gevonden in tourtool.html")

    inner = head.group(1)
    # meta-tags weg: charset en viewport zet de host zelf, en color-scheme
    # staat inmiddels in de CSS
    inner = re.sub(r"\s*<meta[^>]*>", "", inner)

    out = inner.strip() + "\n\n" + body.group(1).strip() + "\n"

    # Controle: geen omhulsel meer over. Op woordgrens, anders struikelt
    # hij over <header> en over de klasse .dayhead.
    for tag in ("!doctype", "html", "head", "body"):
        if re.search(r"</?%s[\s>]" % tag, out, re.IGNORECASE):
            sys.exit("er staat nog een <%s> in het resultaat" % tag)
    if "<title>" not in out:
        sys.exit("de titel is kwijtgeraakt")

    with open(DST, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(
        "Geschreven: %s (%.0f kB, %d scriptblokken)"
        % (DST, os.path.getsize(DST) / 1024, out.count("<script>"))
    )

    bouw_pwa(html)


def bouw_pwa(html):
    """Zet docs/ klaar als installeerbare web-app."""
    os.makedirs(DOCS, exist_ok=True)
    ontbreekt = [a for a in ASSETS
                 if a.endswith(".png") and not os.path.exists(os.path.join(DOCS, a[2:]))]
    if ontbreekt:
        sys.exit("iconen ontbreken (%s) - draai eerst make_icons.py"
                 % ", ".join(a[2:] for a in ontbreekt))

    # iOS kijkt niet naar het manifest voor het beginschermicoon en de
    # volledig-scherm-stand; daar zijn de apple-tags voor nodig.
    kop = """<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Grand Escape">
<meta name="theme-color" content="#0b0d10">
</head>"""
    index = html.replace("</head>", kop, 1)

    # Registratie onderaan. Zonder http werkt een service worker niet, dus
    # openen we docs/index.html rechtstreeks van schijf dan slaan we hem
    # gewoon over - de pagina zelf werkt toch al zonder.
    reg = """<script>
if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("sw.js").catch(function () { /* niet erg */ });
  });
}
</script>
</body>"""
    index = index.replace("</body>", reg, 1)

    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index)

    manifest = {
        "name": "Grand Escape Tourtool",
        "short_name": "Grand Escape",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#0b0d10",
        "theme_color": "#0b0d10",
        "lang": "nl",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    with open(os.path.join(DOCS, "manifest.webmanifest"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)

    # Versie uit de inhoud: wijzigt de app, dan wijzigt de cachenaam en
    # gooit de service worker de oude weg. Zonder dat blijf je na een
    # update de oude versie zien.
    versie = hashlib.sha256(index.encode("utf-8")).hexdigest()[:12]
    sw = '''// Gegenereerd door build_web.py - NIET met de hand aanpassen.
// Legt de hele app in de kast zodat hij zonder bereik opent.
const CACHE = "grand-escape-%s";
const ASSETS = %s;

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(k => Promise.all(k.filter(n => n !== CACHE).map(n => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

// Eerst de kast, dan pas het netwerk. In de bergen is er geen netwerk, en
// wachten op een verbinding die er niet is duurt eindeloos.
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(hit => {
      if (hit) return hit;
      return fetch(e.request).catch(() => caches.match("./index.html"));
    })
  );
});
''' % (versie, json.dumps(ASSETS))
    with open(os.path.join(DOCS, "sw.js"), "w", encoding="utf-8") as fh:
        fh.write(sw)

    print("Geschreven: %s/ (index.html %.0f kB, versie %s)"
          % (DOCS, os.path.getsize(os.path.join(DOCS, "index.html")) / 1024, versie))


if __name__ == "__main__":
    main()
