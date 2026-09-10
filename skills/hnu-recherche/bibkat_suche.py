"""HNU-Bibliothekskatalog (VuFind) über ezproxy durchsuchen — Titel, Autor, Jahr, Format, Volltext.

Cookie-Jar aus dem SAML-Login (hnu-cookies.txt). Keine Zugangsdaten hier.
Aufruf: python3 bibkat_suche.py <ausgabe.json>   — Abfragen stehen unten je Session.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

S = Path(__file__).parent
BASIS = "https://bibkat-hnu-de.ezproxy.hnu.de/vufind/Search/Results"

ABFRAGEN = {
    # Beispielstruktur; für einen konkreten Auftrag die eigenen Blöcke eintragen.
    "Block A": [
        ("digital strategy", "AllFields"),
        ("Digital Business Strategy", "Title"),
    ],
}


def hole(url: str) -> str:
    r = subprocess.run(
        [
            "curl",
            "-s",
            "-L",
            "-b",
            str(S / "hnu-cookies.txt"),
            "-c",
            str(S / "hnu-cookies.txt"),
            url,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return r.stdout


def parse(seite: str) -> tuple[int, list[dict]]:
    m = re.search(r"(\d[\d.]*)\s*Treffer", seite)
    gesamt = int(m.group(1).replace(".", "")) if m else 0
    treffer = []
    for blk in re.split(r'<div class="result-body">', seite)[1:]:
        blk = blk[:6000]
        t = re.search(
            r'class="title getFull"[^>]*>\s*<div>\s*(?:<span[^>]*></span>)?\s*(.*?)\s*</div>',
            blk,
            re.S,
        )
        rid = re.search(r"Record&#x2F;([A-Za-z0-9.\-]+)", blk)
        autoren = re.findall(r'class="result-author">([^<]+)<', blk)
        jahr = re.search(r"Veröffentlicht\s*(\d{4})", blk)
        formate = re.findall(
            r'class="[^"]*(?:format|label)[^"]*"[^>]*>\s*([^<]{2,40})<', blk
        )
        volltext = 'class="fulltext' in blk
        treffer.append(
            {
                "id": rid.group(1) if rid else "",
                "titel": html.unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip()
                if t
                else "",
                "autoren": [html.unescape(a) for a in autoren],
                "jahr": jahr.group(1) if jahr else "",
                "formate": sorted(
                    {html.unescape(f).strip() for f in formate if f.strip()}
                ),
                "volltext": volltext,
            }
        )
    return gesamt, treffer


def main(ausgabe: str) -> None:
    ergebnis = {}
    for session, abfragen in ABFRAGEN.items():
        ergebnis[session] = []
        for lookfor, typ in abfragen:
            url = f"{BASIS}?{urllib.parse.urlencode({'lookfor': lookfor, 'type': typ, 'limit': 20, 'sort': 'year'})}"
            gesamt, treffer = parse(hole(url))
            ergebnis[session].append(
                {"abfrage": lookfor, "typ": typ, "gesamt": gesamt, "treffer": treffer}
            )
            print(
                f"{session[:4]} | {lookfor:45} | {gesamt:5} Treffer | {len(treffer):2} geparst | Volltext {sum(t['volltext'] for t in treffer):2}"
            )
            time.sleep(1.0)
    Path(ausgabe).write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8"
    )


if __name__ == "__main__":
    main(sys.argv[1])
