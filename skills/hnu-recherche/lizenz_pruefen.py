"""Prueft je Katalog-Titel, ob die HNU den Volltext oeffnen kann.

Ein Datensatz fuehrt oft mehrere Volltext-Wege; einer genuegt. Das Urteil kommt
von der Zielseite, nicht vom Pfad — und jede Plattform sagt es anders. Deshalb
drei Ausgaenge: HNU (belegt), FREMD (alle Wege gehoeren anderen Haeusern),
UNGEKLAERT (Seite laedt nach, z. B. EBSCO — von Hand ansehen).

Aufruf: python3 lizenz_pruefen.py <cookie-datei> "DE-604.BV...=Kurzname" ...
Sitzung vorher mit hnu_login.sh anlegen.
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
import urllib.parse

KATALOG = "https://bibkat-hnu-de.ezproxy.hnu.de/vufind/Record/"
PROXY = "https://ezproxy.hnu.de/login?qurl="

FREMD = re.compile(r"ebookcentral\.proquest\.com/lib/([a-z0-9-]+)/", re.I)
UNGEKLAERT = re.compile(r"ebscohost\.com|research-ebsco", re.I)
JA = [
    re.compile(r"Access provided by[^<]{0,80}Neu-Ulm", re.I),  # Springer
    re.compile(r"itemNotAuthorized[^>]*d-none", re.I),  # De Gruyter
    re.compile(r"wiso-net|kohlhammer|beck-online", re.I),  # Verlagsplattformen
]


def _curl(url: str, cookies: str, folgen: bool = True) -> str:
    ruf = ["curl", "-s", "-b", cookies, "-c", cookies, "--max-time", "40"]
    if folgen:
        ruf.append("-L")
    return subprocess.run([*ruf, url], capture_output=True, text=True).stdout


def ziele(rid: str, cookies: str) -> list[str]:
    seite = html.unescape(_curl(KATALOG + rid, cookies, folgen=False))
    gefunden: list[str] = []
    for roh in re.findall(r'qurl=([^"&\s]+)', seite):
        ziel = urllib.parse.unquote(roh)
        if ziel not in gefunden:
            gefunden.append(ziel)
    return gefunden


def urteil(rid: str, cookies: str) -> tuple[str, str]:
    wege = ziele(rid, cookies)
    if not wege:
        return "KEIN VOLLTEXT", ""
    offen = ""
    for ziel in wege:
        wirt = re.sub(r"^https?://", "", ziel).split("/")[0]
        if FREMD.search(ziel):
            continue
        seite = _curl(PROXY + urllib.parse.quote(ziel, safe=""), cookies)
        if any(p.search(seite) for p in JA):
            return "HNU", wirt
        if UNGEKLAERT.search(ziel) or UNGEKLAERT.search(seite[:4000]):
            offen = offen or wirt
    fremde = {m.group(1) for z in wege for m in [FREMD.search(z)] if m}
    if len(fremde) and all(FREMD.search(z) for z in wege):
        return "FREMD", ", ".join(sorted(fremde))[:40]
    if offen:
        return "UNGEKLAERT", offen
    return "UNGEKLAERT", ", ".join(
        sorted(
            {
                re.sub(r"^https?://", "", z).split("/")[0]
                for z in wege
                if not FREMD.search(z)
            }
        )
    )[:46]


def main() -> None:
    cookies, *titel = sys.argv[1:]
    for eintrag in titel:
        rid, _, name = eintrag.partition("=")
        wert, wirt = urteil(rid, cookies)
        print(f"{name or rid:24} {rid:20} {wert:13} {wirt}")


if __name__ == "__main__":
    main()
