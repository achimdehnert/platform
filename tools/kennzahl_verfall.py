#!/usr/bin/env python3
"""kennzahl_verfall.py — rechnet markierte Kennzahlen in Dokumenten nach.

## Warum es das gibt

Am 2026-08-20 stand dieselbe Kennzahl binnen zwei Stunden bei **16**, dann **14**,
dann **15** — jedes Mal korrekt gemessen, jedes Mal aus einem anderen Grund: erst
ein Zaehlfehler, dann seine Korrektur, dann ein neuer Retro-Report, der selbst ein
Vorkommen beisteuerte. Zu diesem Zeitpunkt stand die Zahl bereits in einem
Issue-Titel, einem Handover, einem Memory-Eintrag und zwei PR-Texten.

Keine dieser Zahlen war falsch, als sie geschrieben wurde. Alle waren falsch, kurz
danach. **Wer eine Kennzahl in ein durables Dokument schreibt, schreibt ein
Verfallsdatum mit** — und niemand merkt sich, es zu pruefen.

## Wie es funktioniert

Ein Dokument markiert eine nachrechenbare Zahl mit einem HTML-Kommentar davor:

    Prio 1: **<!--kz:gate-rueckfaellig-->7** von **<!--kz:gate-gesamt-->23** Gates
    sind rueckfaellig.

Der Marker ist beim Rendern unsichtbar. `docs/governance/kennzahlen.json` sagt, wie
jede Kennzahl neu berechnet wird; dieses Werkzeug fuehrt das aus und vergleicht.

## Opt-in ist Absicht, kein Sparzwang

Ein **Stand-Block** SOLL eine Momentaufnahme bleiben — „am 2026-08-20 waren es 8"
ist auch dann richtig, wenn es heute 7 sind. Eine **Prio-Zeile** dagegen behauptet
Gegenwart. Nur die zweite Sorte gehoert markiert. Ein Werkzeug, das jede Zahl in
jedem Dokument pruefen wollte, wuerde Rauschen erzeugen und deshalb abgeschaltet —
dieselbe Mechanik wie bei einem dauerrot laufenden Melder.

## Aufruf

    python3 tools/kennzahl_verfall.py                     # alle bekannten Dokumente
    python3 tools/kennzahl_verfall.py --datei <pfad> …    # gezielt
    python3 tools/kennzahl_verfall.py --kurz              # eine Zeile fuer den Runner
    python3 tools/kennzahl_verfall.py --setzen            # Zahlen im Dokument NACHZIEHEN

`--setzen` schreibt die aktuellen Werte in die markierten Stellen. Bewusst nicht
der Default: eine Zahl stillschweigend zu aendern, waehrend ein Satz sie erklaert
(„acht von zwanzig, also 40 %"), macht das Dokument in sich falsch. Der Mensch
sieht die Abweichung, entscheidet und schreibt den Satz mit.

Exit-Code 0 immer (Report-Werkzeug, Hausform). stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

GATE_HEADER = {
    "slug": "kennzahl-ohne-verfallsdatum",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-20",
    "evidence": "tools/tests/test_kennzahl_verfall.py",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KATALOG = os.path.join(REPO_ROOT, "docs", "governance", "kennzahlen.json")

# Standard-Dokumente: die, die Gegenwart behaupten. Der Stand-Block im Handover
# ist bewusst NICHT dabei — er ist eine Momentaufnahme und darf altern.
STANDARD_DOKUMENTE = ("AGENT_HANDOVER.md",)

# Marker + die erste Zahl danach. Markdown-Auszeichnung (**, `, Leerzeichen) darf
# dazwischenstehen; mehr als 40 Zeichen Abstand ist keine Markierung mehr, sondern
# ein Zufallstreffer.
_MARKER = re.compile(
    r"<!--\s*kz:([a-z0-9][a-z0-9-]*)\s*-->(.{0,40}?)(\d+(?:[.,]\d+)?)", re.S
)


# Enge, ausdrueckliche Freigabe statt `{"__builtins__": {}}`. Der erste Anlauf
# sperrte ALLE Builtins — und damit auch `sum` und `len`, die jeder sinnvolle
# Ausdruck braucht. Ergebnis: jede Kennzahl meldete "nicht berechenbar", der
# Schutzwall hatte das Werkzeug erledigt statt es abzusichern. Hier stehen genau
# die Funktionen, die ein Zaehl-Ausdruck braucht — nichts, was Dateien oeffnet
# oder Prozesse startet.
_EVAL_UMGEBUNG = {
    "__builtins__": {
        "sum": sum,
        "len": len,
        "min": min,
        "max": max,
        "sorted": sorted,
        "abs": abs,
        "round": round,
        "int": int,
        "float": float,
        "bool": bool,
        "any": any,
        "all": all,
        "set": set,
        "list": list,
        "dict": dict,
        "str": str,
    }
}


def lade_katalog(pfad: str = KATALOG) -> dict:
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = json.load(fh)
    except (OSError, ValueError):
        return {}
    return {k["name"]: k for k in daten.get("kennzahlen", []) if k.get("name")}


def berechne(kennzahl: dict, cwd: str = REPO_ROOT) -> float | None:
    """None = nicht berechenbar. NIE als 'stimmt' werten (fetch-failure-is-not-green)."""
    lauf = subprocess.run(
        kennzahl["werkzeug"], capture_output=True, text=True, cwd=cwd, timeout=300
    )
    if lauf.returncode != 0:
        return None
    try:
        d = json.loads(lauf.stdout)
        return float(eval(kennzahl["ausdruck"], _EVAL_UMGEBUNG, {"d": d}))  # noqa: S307
    except Exception:
        return None


def finde_marker(text: str) -> list[tuple[str, str, int]]:
    """(name, roher_zahl_text, position) je Markierung im Dokument."""
    return [(m.group(1), m.group(3), m.start()) for m in _MARKER.finditer(text)]


def pruefe_datei(pfad: str, katalog: dict, werte: dict) -> list[dict]:
    try:
        text = open(pfad, encoding="utf-8").read()
    except OSError:
        return []
    befunde = []
    for name, roh, pos in finde_marker(text):
        zeile = text.count("\n", 0, pos) + 1
        if name not in katalog:
            befunde.append(
                {
                    "datei": pfad,
                    "zeile": zeile,
                    "name": name,
                    "art": "unbekannt",
                    "im_dokument": roh,
                    "aktuell": None,
                }
            )
            continue
        aktuell = werte.get(name)
        if aktuell is None:
            befunde.append(
                {
                    "datei": pfad,
                    "zeile": zeile,
                    "name": name,
                    "art": "nicht-berechenbar",
                    "im_dokument": roh,
                    "aktuell": None,
                }
            )
        elif abs(float(roh.replace(",", ".")) - aktuell) > 1e-9:
            befunde.append(
                {
                    "datei": pfad,
                    "zeile": zeile,
                    "name": name,
                    "art": "veraltet",
                    "im_dokument": roh,
                    "aktuell": aktuell,
                }
            )
    return befunde


def _formatiere(wert: float) -> str:
    return str(int(wert)) if float(wert).is_integer() else str(wert)


def setze(pfad: str, katalog: dict, werte: dict) -> int:
    """Markierte Zahlen im Dokument auf den aktuellen Wert ziehen. Gibt Anzahl zurueck."""
    text = open(pfad, encoding="utf-8").read()
    geaendert = 0

    def ersetze(m: re.Match) -> str:
        nonlocal geaendert
        name, zwischen, roh = m.group(1), m.group(2), m.group(3)
        aktuell = werte.get(name)
        if name not in katalog or aktuell is None:
            return m.group(0)
        neu = _formatiere(aktuell)
        if neu != roh:
            geaendert += 1
        return f"<!--kz:{name}-->{zwischen}{neu}"

    neu_text = _MARKER.sub(ersetze, text)
    if geaendert:
        open(pfad, "w", encoding="utf-8").write(neu_text)
    return geaendert


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--datei", action="append", dest="dateien")
    parser.add_argument("--katalog", default=KATALOG)
    parser.add_argument("--kurz", action="store_true")
    parser.add_argument("--setzen", action="store_true")
    parser.add_argument("--json", action="store_true", dest="als_json")
    args = parser.parse_args()

    katalog = lade_katalog(args.katalog)
    if not katalog:
        if not args.kurz:
            print("Kennzahlen-Katalog nicht lesbar — kein Urteil.", file=sys.stderr)
        return 0

    dateien = args.dateien or [os.path.join(REPO_ROOT, d) for d in STANDARD_DOKUMENTE]
    # Nur Kennzahlen berechnen, die auch wirklich irgendwo markiert sind — sonst
    # laufen bei jedem Aufruf alle Werkzeuge, auch die mit Netzzugriff.
    gebraucht = set()
    for pfad in dateien:
        try:
            gebraucht.update(
                n for n, _, _ in finde_marker(open(pfad, encoding="utf-8").read())
            )
        except OSError:
            continue
    werte = {n: berechne(katalog[n]) for n in gebraucht if n in katalog}

    befunde = [b for pfad in dateien for b in pruefe_datei(pfad, katalog, werte)]

    if args.setzen:
        gesamt = sum(setze(pfad, katalog, werte) for pfad in dateien)
        print(f"{gesamt} Kennzahl(en) nachgezogen.")
        if gesamt:
            print(
                "→ Den erklaerenden Satz danebenlesen: eine Zahl zu aendern, waehrend"
            )
            print("  ein Satz sie deutet, macht das Dokument in sich falsch.")
        return 0

    if args.als_json:
        print(
            json.dumps(
                {"befunde": befunde, "werte": werte}, ensure_ascii=False, indent=2
            )
        )
        return 0

    veraltet = [b for b in befunde if b["art"] == "veraltet"]
    if args.kurz:
        if veraltet:
            spitze = veraltet[0]
            weitere = f" (+{len(veraltet) - 1} weitere)" if len(veraltet) > 1 else ""
            print(
                f"{len(veraltet)} Kennzahl(en) veraltet — {os.path.basename(spitze['datei'])}"
                f":{spitze['zeile']} {spitze['name']}: steht {spitze['im_dokument']}, "
                f"ist {_formatiere(spitze['aktuell'])}{weitere}"
            )
            for b in veraltet[1:5]:
                print(
                    f"  · {os.path.basename(b['datei'])}:{b['zeile']} {b['name']}: "
                    f"steht {b['im_dokument']}, ist {_formatiere(b['aktuell'])}"
                )
        return 0

    print(f"# Kennzahl-Verfall ueber {len(dateien)} Dokument(e)\n")
    if not befunde:
        markiert = sum(
            len(finde_marker(open(p, encoding="utf-8").read()))
            for p in dateien
            if os.path.exists(p)
        )
        print(f"→ Alle {markiert} markierte(n) Kennzahl(en) aktuell.")
        return 0
    for b in befunde:
        if b["art"] == "veraltet":
            print(
                f"🚨 {b['datei']}:{b['zeile']}  {b['name']}: "
                f"im Dokument {b['im_dokument']}, aktuell {_formatiere(b['aktuell'])}"
            )
        elif b["art"] == "unbekannt":
            print(f"❓ {b['datei']}:{b['zeile']}  {b['name']}: nicht im Katalog")
        else:
            print(
                f"◌ {b['datei']}:{b['zeile']}  {b['name']}: NICHT berechenbar — keine Aussage"
            )
    if veraltet:
        print("\n→ Nachziehen: tools/kennzahl_verfall.py --setzen")
        print(
            "  Danach den erklaerenden Satz mitlesen — eine geaenderte Zahl neben einer"
        )
        print("  unveraenderten Deutung ist schlimmer als eine veraltete Zahl.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
