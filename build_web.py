#!/usr/bin/env python3
"""
build_web.py - maakt van tourtool.html een versie om te hosten.

Een gehoste pagina wordt door de host in zijn eigen <html>/<head>/<body>
gezet. Daar mag je die tags dus niet zelf nog eens omheen hebben staan.
Dit script haalt het omhulsel eraf en laat titel, stijl, opmaak en scripts
staan.

    python3 build_web.py

Schrijft tourtool-web.html. Het gewone tourtool.html blijft het bestand dat
je op je telefoon bewaart en offline opent; deze versie is alleen om een
werkende link mee te delen.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "tourtool.html")
DST = os.path.join(HERE, "tourtool-web.html")


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


if __name__ == "__main__":
    main()
