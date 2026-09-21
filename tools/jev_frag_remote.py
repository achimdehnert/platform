#!/usr/bin/env python3
"""Eine Textdatei zeilenweise durch kev schicken — laeuft AUF der GPU-Box.

Der kev-Dienst lauscht dort nur auf 127.0.0.1; dieses Skript wird von
`jev_messreihe.py` vor jedem Lauf dorthin ausgeliefert (platform#3337).
Es gehoert ins Repo, damit die Frageform versioniert ist und eine spaetere
Messung mit einer frueheren vergleichbar bleibt.


  python3 /root/frag.py /root/texte.txt                 # Fragen aus /root/fragen.json
  python3 /root/frag.py /root/texte.txt meine_fragen.json
  python3 /root/frag.py /root/texte.txt --json           # Rohantworten statt Tabelle

Leerzeilen und Zeilen ab '#' werden uebersprungen.
"""

import json
import sys
import time
import urllib.request

URL = "http://127.0.0.1:8009/v1/systemone"


def frag(state, fragen):
    daten = json.dumps({"state": state, "model": "kev-latest", "questions": fragen})
    req = urllib.request.Request(
        URL, data=daten.encode(), headers={"content-type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def wert(a):
    """Eine Antwort auf eine Zahl und ein Etikett bringen."""
    if a["type"] == "noul":
        return a["noul"], ""
    if a["type"] == "choice":
        return a.get("confidence", 0.0), a.get("choice", "")
    return a.get("score", 0.0), ""


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    roh = "--json" in argv
    if not args:
        print(__doc__)
        return 2
    texte = [
        z.strip()
        for z in open(args[0], encoding="utf-8")
        if z.strip() and not z.lstrip().startswith("#")
    ]
    fragen = json.load(
        open(args[1] if len(args) > 1 else "/root/fragen.json", encoding="utf-8")
    )
    if not texte:
        print("Keine Textzeilen gefunden.")
        return 1

    namen = list(fragen)
    breite = max(28, min(52, max(len(t) for t in texte)))
    if not roh:
        kopf = (
            f"{'Text':<{breite}} "
            + " ".join(f"{n[:14]:>14}" for n in namen)
            + f" {'ms':>6}"
        )
        print(kopf)
        print("-" * len(kopf))
    gesamt = 0.0
    for t in texte:
        t0 = time.time()
        antwort = frag(t, fragen)
        gesamt += time.time() - t0
        if roh:
            print(json.dumps({"state": t, **antwort}, ensure_ascii=False))
            continue
        kurz = t if len(t) <= breite else t[: breite - 1] + "…"
        zellen = []
        for n in namen:
            p, etikett = wert(antwort["answers"][n])
            zellen.append(f"{etikett + ' ' if etikett else ''}{p:.2f}"[:14].rjust(14))
        print(
            f"{kurz:<{breite}} " + " ".join(zellen) + f" {antwort['latency_ms']:>6.0f}"
        )
    if not roh:
        print(
            f"\n{len(texte)} Zeilen in {gesamt:.1f}s ({gesamt / len(texte) * 1000:.0f} ms je Zeile)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
