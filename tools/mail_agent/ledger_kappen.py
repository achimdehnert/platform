#!/usr/bin/env python3
"""Den Verlauf eines Vorgangs kappen: das Jüngste bleibt im Ledger, der Rest wandert ins Archiv.

Warum es das gibt (gemessen 2026-08-20, platform#2176 Kriterium 3): Die `notiz`
eines Vorgangs wächst durch Anhängen und wird nie kürzer. Der Ledger stand bei
**119.357 Zeichen**, die größte Einzelnotiz bei **15.553** — und jede Operation am
Ledger, jede Board-Erzeugung, jeder Blick eines Agenten zieht diesen Text mit.
Gelesen wird davon fast immer nur das Ende.

Die Kappung wirft **nichts** weg. Sie verschiebt: das Jüngste bleibt dort, wo es
gebraucht wird, das Ältere zieht in `mail-vorgaenge-archiv.json` daneben. Die
Vorgangsansicht setzt beides wieder zusammen — wer den ganzen Verlauf sehen will,
sieht ihn unverändert.

Idempotent: ein zweiter Lauf ohne neue Einträge verschiebt nichts.

Beide Dateien liegen unter ~/.claude, nie in einem Repo — sie tragen Namen,
Betreffs und Mandantensachen (Charta Art. 2).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
ARCHIV = Path.home() / ".claude" / "mail-vorgaenge-archiv.json"

#: Obergrenze der aktiven Notiz je Vorgang. 2.000 Zeichen sind rund fünf bis acht
#: Einträge — genug, um den laufenden Stand ohne Nachschlagen zu verstehen.
GRENZE = 2000

#: Trenner zwischen zwei Verlaufseinträgen. Historisch gewachsen, deshalb hier
#: benannt statt an sechs Stellen wiederholt.
TRENNER = " | "


def zerlege(notiz: str) -> list[str]:
    return [t.strip() for t in (notiz or "").split(TRENNER) if t.strip()]


def kappe(eintraege: list[str], grenze: int = GRENZE) -> tuple[list[str], list[str]]:
    """→ (bleibt, wandert_ins_archiv), chronologisch, jüngstes zuletzt.

    Gezählt wird von hinten: der jüngste Eintrag bleibt IMMER, auch wenn er allein
    schon über der Grenze liegt — ein Vorgang ohne aktuellen Stand wäre schlimmer
    als ein zu langer.
    """
    if not eintraege:
        return [], []
    bleibt: list[str] = []
    laenge = 0
    for eintrag in reversed(eintraege):
        if bleibt and laenge + len(eintrag) > grenze:
            break
        bleibt.insert(0, eintrag)
        laenge += len(eintrag) + len(TRENNER)
    schnitt = len(eintraege) - len(bleibt)
    return bleibt, eintraege[:schnitt]


def lade(pfad: Path, default: dict) -> dict:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def archiv_key(nr) -> str:
    return str(nr)


def verarbeite(ledger: dict, archiv: dict, grenze: int = GRENZE) -> list[dict]:
    """Kappt alle Vorgänge in-place. → Bericht je verändertem Vorgang."""
    bericht = []
    for v in ledger.get("vorgaenge", []):
        eintraege = zerlege(v.get("notiz", ""))
        bleibt, weg = kappe(eintraege, grenze)
        if not weg:
            continue
        schluessel = archiv_key(v.get("nr"))
        vorhanden = archiv.get(schluessel, [])
        # ALLE verschobenen Eintraege anhaengen, ohne Textvergleich. Der frühere
        # Dublettenfilter (`e not in vorhanden`) hat Daten verloren: steht ein
        # neuer Eintrag zufaellig wortgleich zu einem laengst archivierten — bei
        # wiederkehrenden Zeilen wie "kein neuer Eingang" der Normalfall —, wurde
        # er weder archiviert noch blieb er im Ledger, und der Bericht meldete
        # trotzdem "verschoben". Reproduziert in der Retro 2026-08-21.
        # Idempotenz braucht ihn nicht: was verschoben wurde, steht nicht mehr im
        # Ledger, kann also kein zweites Mal verschoben werden.
        archiv[schluessel] = vorhanden + list(weg)
        vorher = len(v.get("notiz", ""))
        v["notiz"] = TRENNER.join(bleibt)
        bericht.append(
            {
                "nr": v.get("nr"),
                "verschoben": len(weg),
                "vorher": vorher,
                "nachher": len(v["notiz"]),
            }
        )
    return bericht


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--archiv", default=str(ARCHIV))
    ap.add_argument("--grenze", type=int, default=GRENZE)
    ap.add_argument(
        "--apply", action="store_true", help="schreiben (sonst nur Anzeige)"
    )
    args = ap.parse_args()

    lp, ap_ = Path(args.ledger), Path(args.archiv)
    ledger = lade(lp, {"vorgaenge": []})
    archiv = lade(ap_, {})

    vorher_gesamt = sum(len(v.get("notiz", "")) for v in ledger.get("vorgaenge", []))
    bericht = verarbeite(ledger, archiv, args.grenze)
    nachher_gesamt = sum(len(v.get("notiz", "")) for v in ledger.get("vorgaenge", []))

    if not bericht:
        print(f"Nichts zu kappen — Verlauf gesamt {vorher_gesamt} Zeichen.")
        return 0

    for e in bericht:
        print(
            f"  #{e['nr']:>4}  {e['verschoben']:>3} Eintrag/Eintraege ins Archiv  "
            f"{e['vorher']:>6} → {e['nachher']:>5} Zeichen"
        )
    print(
        f"\n{len(bericht)} Vorgang/Vorgaenge gekappt · "
        f"Verlauf im Ledger {vorher_gesamt} → {nachher_gesamt} Zeichen"
    )

    if args.apply:
        lp.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        ap_.write_text(
            json.dumps(archiv, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Geschrieben: {lp.name} + {ap_.name}")
    else:
        print("(Anzeige — mit --apply werden Ledger und Archiv geschrieben.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
