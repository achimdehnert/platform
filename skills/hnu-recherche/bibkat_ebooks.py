"""HNU-Katalog: nur E-Books ab einem Stichjahr — Themenlauf über mehrere Blöcke.

Der Filter `filter[]=~format:"eBook"` liefert genau die
Titel, die online verfügbar sind. Zusammen mit `sort=year` und einer Jahresgrenze
ergibt das die Menge, aus der die Pflicht- und Vertiefungsliteratur kommt.

Aufruf: python3 bibkat_ebooks.py > ergebnis.txt   (Sitzung vorher: hnu_login.sh)
"""

from __future__ import annotations

import html
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bibkat_suche import hole  # noqa: E402

BASIS = "https://bibkat-hnu-de.ezproxy.hnu.de/vufind/Search/Results"
FILTER = "filter%5B%5D=%7Eformat%3A%22eBook%22"
JAHR_AB = 2023

ABFRAGEN = {
    # Beispielstruktur: je Themenblock mehrere Suchbegriffe, deutsch und englisch.
    # Für einen konkreten Auftrag hier die eigenen Blöcke eintragen.
    "Block A": ["digital strategy", "digitale Transformation Strategie"],
    "Block B": ["business model innovation", "Geschäftsmodell Innovation"],
}


def suche(lookfor: str, limit: int = 20) -> tuple[int, list[dict]]:
    q = urllib.parse.urlencode(
        {"lookfor": lookfor, "type": "AllFields", "limit": limit, "sort": "year"}
    )
    seite = hole(f"{BASIS}?{q}&{FILTER}")
    m = re.search(r"(\d[\d.]*)\s*Treffer", seite)
    gesamt = int(m.group(1).replace(".", "")) if m else 0
    treffer = []
    for block in re.split(r'<div class="result-body">', seite)[1:]:
        block = block[:8000]
        t = re.search(
            r'class="title getFull"[^>]*>\s*<div>\s*(?:<span[^>]*></span>)?\s*(.*?)\s*</div>',
            block,
            re.S,
        )
        j = re.search(r"Veröffentlicht\s*(\d{4})", block)
        rid = re.search(r"Record&#x2F;([A-Za-z0-9.\-]+)", block)
        autoren = re.findall(r'class="result-author">([^<]+)<', block)
        if not (t and j) or int(j.group(1)) < JAHR_AB:
            continue
        treffer.append(
            {
                "jahr": j.group(1),
                "titel": html.unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip(),
                "autoren": [html.unescape(a) for a in autoren],
                "id": rid.group(1) if rid else "",
            }
        )
    return gesamt, treffer


def main() -> None:
    for session, abfragen in ABFRAGEN.items():
        gesehen: set[str] = set()
        zeilen: list[dict] = []
        gesamt_summe = 0
        for a in abfragen:
            gesamt, treffer = suche(a)
            gesamt_summe += gesamt
            for t in treffer:
                schluessel = t["titel"].lower()[:60]
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                zeilen.append(t)
            time.sleep(0.8)
        zeilen.sort(key=lambda t: (-int(t["jahr"]), t["titel"]))
        print(
            f"\n### {session} — {len(zeilen)} E-Books ab {JAHR_AB} (aus {gesamt_summe} Treffern)"
        )
        for t in zeilen[:22]:
            autoren = ", ".join(t["autoren"])[:38] or "—"
            print(f"  {t['jahr']} | {t['titel'][:74]:74} | {autoren:38} | {t['id']}")


if __name__ == "__main__":
    main()
