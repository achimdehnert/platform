#!/usr/bin/env python3
"""Erledigte Vorgänge aus dem Ledger ins Archiv legen — und Titellose melden.

Warum es das gibt (Owner-Befund 2026-08-21, „nicht mehr benötigte Einträge
entfernen"): Ein geschlossener Vorgang bleibt im Ledger stehen. Die Liste blendet
ihn nach ein paar Tagen aus, aber jede Operation trägt ihn weiter mit, und beim
Lesen des Ledgers steht er zwischen den offenen.

**Entfernt wird nichts.** Der Vorgang zieht nach `mail-vorgaenge-erledigt.json`
daneben — dieselbe Bewegung wie beim Verlauf (`ledger_kappen.py`). Ein
geschlossener Vorgang ist Akte, kein Müll: er trägt die Belege, mit denen später
jemand fragt, wann was gesendet wurde.

**Zweiter Zweck: Titellose finden.** Ein Vorgang ohne `kurz` erscheint in der
Liste als leere Zeile — man sieht, dass etwas da ist, aber nicht was. Das ist
kein Datenfehler, den ein Werkzeug raten sollte, deshalb wird er gemeldet und
nicht gefüllt.

Beide Dateien liegen unter ~/.claude, nie in einem Repo (Charta Art. 2).
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
ARCHIV = Path.home() / ".claude" / "mail-vorgaenge-erledigt.json"

#: Wie lange ein geschlossener Vorgang in der Liste sichtbar bleibt, bevor er
#: umzieht. Drei Tage decken „ich schaue Montag nochmal nach" ab.
KARENZ_TAGE = 3


def _tag(wert) -> date | None:
    try:
        return datetime.strptime(str(wert), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def reif(v: dict, heute: date, karenz: int = KARENZ_TAGE) -> bool:
    """Ist dieser Vorgang alt genug fürs Archiv?

    Ohne `erledigt_am` zählt `letzte_pruefung` — und fehlt beides, bleibt er
    liegen. Ein Vorgang ohne Datum ist kein Fall für eine automatische Bewegung.
    """
    if v.get("bucket") != "erledigt":
        return False
    stand = _tag(v.get("erledigt_am")) or _tag(v.get("letzte_pruefung"))
    if stand is None:
        return False
    return (heute - stand).days >= karenz


def ohne_titel(ledger: dict) -> list[int]:
    """Vorgänge, die in der Liste als leere Zeile erscheinen."""
    return [
        v.get("nr")
        for v in ledger.get("vorgaenge", [])
        if v.get("bucket") != "erledigt" and not (v.get("kurz") or "").strip()
    ]


def teile(ledger: dict, heute: date, karenz: int = KARENZ_TAGE) -> tuple[list, list]:
    """→ (bleibt, wandert)"""
    bleibt, wandert = [], []
    for v in ledger.get("vorgaenge", []):
        (wandert if reif(v, heute, karenz) else bleibt).append(v)
    return bleibt, wandert


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--archiv", default=str(ARCHIV))
    ap.add_argument("--karenz", type=int, default=KARENZ_TAGE)
    ap.add_argument("--heute", default=None)
    ap.add_argument("--apply", action="store_true", help="schreiben (sonst Anzeige)")
    args = ap.parse_args()

    heute = (
        datetime.strptime(args.heute, "%Y-%m-%d").date() if args.heute else date.today()
    )
    lp, ap_ = Path(args.ledger), Path(args.archiv)
    ledger = json.loads(lp.read_text(encoding="utf-8"))
    try:
        archiv = json.loads(ap_.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        archiv = {"vorgaenge": []}

    bleibt, wandert = teile(ledger, heute, args.karenz)
    titellos = ohne_titel(ledger)

    for v in wandert:
        print(
            f"  #{v.get('nr'):>4}  {(v.get('kurz') or '(ohne Titel)')[:48]:<48} "
            f"erledigt {v.get('erledigt_am') or v.get('letzte_pruefung')}"
        )
    if titellos:
        print(
            "\n  Ohne Titel (erscheinen als leere Zeile): "
            + ", ".join(f"#{n}" for n in titellos)
            + "\n  → `kurz` setzen; das Werkzeug raet hier nicht."
        )
    if not wandert:
        print("Nichts zu archivieren.")
        return 0

    print(
        f"\n{len(wandert)} Vorgang/Vorgaenge · Ledger {len(ledger['vorgaenge'])} → {len(bleibt)}"
    )
    if args.apply:
        vorhanden = {v.get("nr") for v in archiv.get("vorgaenge", [])}
        archiv["vorgaenge"] = archiv.get("vorgaenge", []) + [
            v for v in wandert if v.get("nr") not in vorhanden
        ]
        ledger["vorgaenge"] = bleibt
        ap_.write_text(
            json.dumps(archiv, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        lp.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Geschrieben: {lp.name} + {ap_.name}")
    else:
        print("(Anzeige — mit --apply werden Ledger und Archiv geschrieben.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
