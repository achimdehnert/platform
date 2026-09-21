#!/usr/bin/env python3
"""schliess_bezug_check.py — nennt ein PR ein Issue, ohne es zu schliessen?

Owner-Ziel 2026-09-21: Issues und PRs sollen so schnell wie moeglich geschlossen
werden und verschwinden. Gemessen war an dem Tag das Gegenteil:

  * Zufluss 69 Issues je Woche, Abfluss 41 — netto +28, hochgerechnet +1436/Jahr.
  * **Ein** einziges von 445 offenen Issues hatte einen verknuepften PR.
  * Von 120 gemergten PRs nannten 53 % die Nummer nackt (`#3337`), 17 %
    schrieben `Refs #3337`, und nur 22 % ein schliessendes Schluesselwort.

Nackte Nummern und `Refs` erzeugen bei GitHub keine Verknuepfung und schliessen
nichts. Erledigte Arbeit bleibt danach als offenes Issue stehen — nicht weil
jemand sie fuer offen haelt, sondern weil niemand das Wort geschrieben hat.

Dieses Werkzeug liest einen PR-Text und meldet jede Issue-Nummer, die ohne
schliessendes Schluesselwort dasteht. Es ist KEIN Vorwurf: ein PR darf ein
Issue nennen, ohne es zu erledigen. Dann erwartet der Check aber einen Grund
in derselben Zeile wie die Nummer; welche Begleitmarker gelten, steht in
`_BEGRUENDET_RE` weiter unten.

(Die Marker sind hier bewusst NICHT ausgeschrieben: der Aufschub-Anker-Gate
liest diesen Docstring und hielt die Aufzaehlung fuer eine angekuendigte
Auslassung — ein Werkzeug, das ein Muster dokumentiert, loest den Melder fuer
genau dieses Muster aus.)

Aufruf:
  python3 tools/schliess_bezug_check.py --text-datei pr.md
  python3 tools/schliess_bezug_check.py --pr 3344 --repo achimdehnert/platform
  ... --kurz     eine Zeile statt Bericht
  ... --json     maschinenlesbar

Exit 0 = nichts zu melden · Exit 1 = mindestens eine unbegleitete Nummer.
stdlib-only ausser `gh` fuer --pr.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

#: GitHubs eigene Liste. Wer eines dieser Woerter vor die Nummer setzt, bekommt
#: beim Merge die Schliessung geschenkt — das ist der ganze Hebel.
SCHLIESSEND = (
    "close",
    "closes",
    "closed",
    "fix",
    "fixes",
    "fixed",
    "resolve",
    "resolves",
    "resolved",
)

_SCHLIESS_RE = re.compile(
    r"\b(?:" + "|".join(SCHLIESSEND) + r")\s+#(\d+)\b", re.IGNORECASE
)
_NUMMER_RE = re.compile(r"(?<![\w/])#(\d+)\b")

#: Begleitsaetze, die eine offene Nummer rechtfertigen. Bewusst grosszuegig:
#: das Ziel ist ein bewusster Satz, keine Formelsprache.
_BEGRUENDET_RE = re.compile(
    r"\b(bleibt offen|teil von|teilschritt|folge-?issue|vorarbeit|"
    r"refs?\s+#\d+\s*[—–-]\s*\w|zwischenstand|dazu geh(oe|ö)rt|"
    r"weiterer schritt|noch offen|nicht abschliessend|nicht abschließend)\b",
    re.IGNORECASE,
)


def _ohne_rauschen(text: str) -> str:
    """Codebloecke und HTML-Kommentare raus — dort stehen Beispiele, keine Absicht."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"https?://\S*?/(?:issues|pull)/\d+", " ", text)
    return text


def offene_nummern(nummern: list[int], repo: str | None) -> set[int]:
    """Welche dieser Nummern sind offene Issues?

    Ohne diesen Filter meldet der Check jede historische Zitatstelle: ein PR,
    der einen geschlossenen Vorgang als Beleg in einer Tabelle nennt, kann ihn
    nicht schliessen — die Forderung waere sinnlos und der Melder eine Plage.
    Realfall am Tag des Baus: platform#3332 zitierte #1904/#2380/#3073, alle
    drei CLOSED, als Beweis dafuer, dass zwei Handover-Zeilen ins Archiv
    gehoeren. Ohne Filter waren das drei Befunde, alle falsch.

    Nicht ermittelbar (kein `gh`, kein Netz) -> alle gelten als offen. Ein
    Melder, der bei Netzfehlern schweigt, ist schlimmer als einer, der fragt.
    """
    if not nummern:
        return set()
    offen: set[int] = set()
    for n in nummern:
        befehl = ["gh", "issue", "view", str(n), "--json", "state"]
        if repo:
            befehl += ["--repo", repo]
        try:
            fertig = subprocess.run(befehl, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return set(nummern)
        if fertig.returncode != 0:
            # Nummer ist womoeglich ein PR, kein Issue — dann ist nichts zu
            # schliessen und die Erwaehnung ist in Ordnung.
            continue
        try:
            if json.loads(fertig.stdout).get("state") == "OPEN":
                offen.add(n)
        except json.JSONDecodeError:
            offen.add(n)
    return offen


def pruefe(text: str, repo: str | None = None, zustand_pruefen: bool = False) -> dict:
    """{schliesst: [n], unbegleitet: [n], begruendet: [n]} aus einem PR-Text."""
    sauber = _ohne_rauschen(text)
    schliesst = sorted({int(n) for n in _SCHLIESS_RE.findall(sauber)})
    alle = sorted({int(n) for n in _NUMMER_RE.findall(sauber)})

    unbegleitet: list[int] = []
    begruendet: list[int] = []
    for nummer in alle:
        if nummer in schliesst:
            continue
        # Der Satz um die Nummer herum entscheidet, nicht das ganze Dokument:
        # sonst entschuldigt ein einziges "bleibt offen" jede weitere Nummer.
        zeilen = [z for z in sauber.splitlines() if f"#{nummer}" in z]
        if any(_BEGRUENDET_RE.search(z) for z in zeilen):
            begruendet.append(nummer)
        else:
            unbegleitet.append(nummer)

    if zustand_pruefen:
        noch_offen = offene_nummern(unbegleitet, repo)
        geschlossen = [n for n in unbegleitet if n not in noch_offen]
        unbegleitet = [n for n in unbegleitet if n in noch_offen]
    else:
        geschlossen = []

    return {
        "bereits_geschlossen": geschlossen,
        "schliesst": schliesst,
        "unbegleitet": unbegleitet,
        "begruendet": begruendet,
    }


def hole_pr_text(pr: str, repo: str | None) -> str:
    befehl = ["gh", "pr", "view", pr, "--json", "title,body"]
    if repo:
        befehl += ["--repo", repo]
    fertig = subprocess.run(befehl, capture_output=True, text=True, timeout=60)
    if fertig.returncode != 0:
        raise SystemExit(f"gh pr view fehlgeschlagen: {fertig.stderr.strip()}")
    d = json.loads(fertig.stdout)
    return f"{d.get('title', '')}\n\n{d.get('body') or ''}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--text-datei")
    p.add_argument("--pr")
    p.add_argument("--repo")
    p.add_argument("--kurz", action="store_true")
    p.add_argument("--json", action="store_true", dest="als_json")
    p.add_argument(
        "--ohne-zustand",
        action="store_true",
        help="Nummern nicht gegen GitHub pruefen (offline, meldet mehr)",
    )
    a = p.parse_args(argv)

    if a.text_datei:
        text = open(a.text_datei, encoding="utf-8").read()
    elif a.pr:
        text = hole_pr_text(a.pr, a.repo)
    else:
        text = sys.stdin.read()

    ergebnis = pruefe(text, repo=a.repo, zustand_pruefen=not a.ohne_zustand)
    offen = ergebnis["unbegleitet"]

    if a.als_json:
        print(json.dumps(ergebnis))
        return 1 if offen else 0

    if a.kurz:
        teile = [f"schliesst {len(ergebnis['schliesst'])}"]
        if ergebnis["begruendet"]:
            teile.append(f"begruendet offen {len(ergebnis['begruendet'])}")
        if offen:
            teile.append("unbegleitet " + ", ".join(f"#{n}" for n in offen))
        print("schliess-bezug: " + " · ".join(teile))
        return 1 if offen else 0

    print("Schliess-Bezug (Owner-Ziel: Issues sollen verschwinden)")
    print(
        f"  schliessend genannt : {', '.join(f'#{n}' for n in ergebnis['schliesst']) or '—'}"
    )
    print(
        f"  offen, mit Grund    : {', '.join(f'#{n}' for n in ergebnis['begruendet']) or '—'}"
    )
    print(f"  offen, ohne Grund   : {', '.join(f'#{n}' for n in offen) or '—'}")
    if ergebnis["bereits_geschlossen"]:
        zitate = ", ".join(f"#{n}" for n in ergebnis["bereits_geschlossen"])
        print(f"  nur zitiert (zu)    : {zitate}")
    if offen:
        print()
        print("  Dieser PR nennt Issues, schliesst sie nicht und sagt nicht warum.")
        print(
            "  Erledigt er sie? Dann `Closes #N` schreiben — GitHub schliesst beim Merge."
        )
        print("  Erledigt er sie nicht? Dann einen Satz dazu, z.B.")
        print("      Refs #N — Teil von; der Rest haengt an <…>.")
    return 1 if offen else 0


if __name__ == "__main__":
    raise SystemExit(main())
