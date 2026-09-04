#!/usr/bin/env python3
"""Step 2a Pfad-Modus: Breitensuche ueber interne Links, klick-only, je Station Messung.

Aufruf: python3 ux_pfad.py --basis http://127.0.0.1:8197 --login /l/... --max-seiten 60 --out pfad.json
Klick-only: jede neue Station wird per echtem Klick auf den Anker erreicht; zum Elternknoten
zurueck geht es per page.goto auf eine bereits per Klick erreichte Seite (kein neuer Weg).
Nicht geklickt (notiert): Abmelden, Loeschen, /admin/, externe Links, Formular-Submits/hx-post.
"""

import argparse
import json
import re
import time
from collections import deque
from urllib.parse import urlparse

SKIP = re.compile(r"abmelden|logout|/admin/|delete|loeschen|löschen|/l/", re.I)
ID = re.compile(r"[0-9a-f]{8}-[0-9a-f-]{27}|(?<=/)\d+(?=/|$)")


def norm(path: str) -> str:
    return ID.sub("<id>", path.split("?")[0].split("#")[0])


def messen(page):
    return page.evaluate("""() => {
      const t=[...document.querySelectorAll('[hx-get],[hx-post],[hx-delete],[hx-put],[hx-patch]')];
      const miss=t.filter(e=>!(e.hasAttribute('hx-target')&&e.hasAttribute('hx-swap')&&e.hasAttribute('hx-indicator'))).length;
      const links=[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href'));
      const knoepfe=[...document.querySelectorAll('button, [hx-post], form')].length;
      const json=[...document.querySelectorAll('script[type="application/json"]')].map(s=>{try{JSON.parse(s.textContent);return 1}catch(e){return 0}});
      const leer=/keine .* vorhanden|noch keine|leer/i.test(document.body.innerText);
      return {h1:(document.querySelector('h1')||{}).innerText||'', title:document.title, htmx:t.length, triade_fehlt:miss,
              links, knoepfe, json_ok:json.filter(x=>x).length, json_fehler:json.filter(x=>!x).length,
              text_len:document.body.innerText.length, leerhinweis:leer}; }""")


def main():
    from playwright.sync_api import sync_playwright  # noqa: PLC0415 — nur der Lauf braucht den Browser

    ap = argparse.ArgumentParser()
    ap.add_argument("--basis", required=True)
    ap.add_argument("--login", required=True)
    ap.add_argument("--max-seiten", type=int, default=60)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    host = urlparse(a.basis).netloc
    stationen, notiert, queue = {}, set(), deque()
    konsole, netz = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context()
        page = ctx.new_page()
        page.on(
            "console",
            lambda m: (
                konsole.append((page.url, m.type, m.text))
                if m.type in ("error", "warning")
                else None
            ),
        )
        page.on(
            "response",
            lambda r: netz.append((r.url, r.status)) if r.status >= 400 else None,
        )
        page.goto(a.basis + a.login, wait_until="load")
        start = norm(urlparse(page.url).path)

        def station(pfad_norm, eltern, url):
            m = messen(page)
            ke = [k for k in konsole if norm(urlparse(k[0]).path) == pfad_norm]
            ne = [
                n
                for n in netz
                if host in n[0]
                and norm(urlparse(n[0]).path) == pfad_norm
                or (eltern and n[1] >= 500)
            ]
            stationen[pfad_norm] = {
                "url": url,
                "eltern": eltern,
                "h1": m["h1"],
                "title": m["title"],
                "htmx": m["htmx"],
                "triade_fehlt": m["triade_fehlt"],
                "knoepfe": m["knoepfe"],
                "json_ok": m["json_ok"],
                "json_fehler": m["json_fehler"],
                "text_len": m["text_len"],
                "leerhinweis": m["leerhinweis"],
                "konsole": [k[1] + ": " + k[2][:160] for k in ke][:5],
                "netz_4xx5xx": [(norm(urlparse(u).path), s) for u, s in ne][:5],
            }
            for href in m["links"]:
                if not href or href.startswith(("#", "mailto:", "javascript:")):
                    continue
                u = urlparse(href)
                if u.netloc and u.netloc != host:
                    notiert.add("extern " + href[:60])
                    continue
                if SKIP.search(u.path):
                    notiert.add("uebersprungen " + u.path[:60])
                    continue
                n = norm(u.path)
                if n not in stationen and all(q[0] != n for q in queue):
                    queue.append((n, pfad_norm, href))

        station(start, None, page.url)
        while queue and len(stationen) < a.max_seiten:
            n, eltern, href = queue.popleft()
            if n in stationen:
                continue
            if norm(urlparse(page.url).path) != eltern:
                page.goto(
                    stationen[eltern]["url"], wait_until="load"
                )  # Elternseite: per Klick bereits erreicht
            try:
                loc = page.locator(f'a[href="{href}"]').first
                loc.click(timeout=8000)
                page.wait_for_load_state("load", timeout=15000)
            except Exception as e:  # noqa: BLE001
                stationen[n] = {
                    "url": None,
                    "eltern": eltern,
                    "zustand": "blind",
                    "grund": f"Klick fehlgeschlagen: {str(e)[:100]}",
                }
                continue
            station(n, eltern, page.url)
        rest = [q[0] for q in queue]
        b.close()
    out = {
        "basis": a.basis,
        "max_seiten": a.max_seiten,
        "besucht": len(stationen),
        "stationen": stationen,
        "unbesucht_seitenbudget": rest,
        "notiert": sorted(notiert),
        "geprueft_am": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(
        f"besucht {len(stationen)} · unbesucht (Seitenbudget) {len(rest)} · notiert {len(notiert)}"
    )


if __name__ == "__main__":
    main()
