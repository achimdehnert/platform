#!/usr/bin/env python3
"""melder_ergebnis.py — gemeinsame Ablageform fuer Melder-Ergebnisse (platform#2944).

## Warum es das gibt

Vier Melder messen Dinge, die der Future-Readiness-Erheber braucht (Erreichbarkeit,
Alarmweg, Backup-Frische, shared-ci-Band, kopierte Standards). Gemessen am
2026-09-07: **drei von vier hinterlassen kein maschinenlesbares Ergebnis** — kein
Artefakt, kein Commit, keine Datei. Sie melden und verschwinden; der vierte
schreibt Fliesstext in ein Issue.

„Anschliessen statt neu erheben" setzt aber voraus, dass es etwas zum Anschliessen
GIBT. Dieses Modul ist diese eine Form — bewusst klein, damit vier Melder sie
uebernehmen koennen, ohne dass jeder eine eigene erfindet.

## Die Frische-Grenze ist der eigentliche Punkt

Ein Melder-Ergebnis von vorletzter Woche darf keine heutige Bewertung tragen.
Ohne diese Regel waere der Anschluss **schlimmer als die Luecke**: er saehe aus
wie Evidenz und waere veraltet.

`lies()` gibt deshalb `None` zurueck, sobald das Ergebnis aelter ist als
`max_alter_tage` — und der Aufrufer faellt damit auf `unverified` zurueck,
NICHT auf rot. Ein fehlender Beleg ist kein Mangelbefund.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = "melder-ergebnis/1"
# 7 Tage: der langsamste angeschlossene Melder laeuft woechentlich (alarmweg-probe,
# montags). Ein Fenster kleiner als sein Takt wuerde ihn dauerhaft als abgelaufen
# fuehren; ein deutlich groesseres liesse zwei verpasste Laeufe unbemerkt.
MAX_ALTER_TAGE = 7


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def schreibe(
    pfad: Path,
    melder: str,
    ergebnis: Any,
    *,
    werkzeug_version: str = "",
    gemessen_am: datetime | None = None,
) -> dict:
    """Ergebnis in der gemeinsamen Huelle ablegen und zurueckgeben.

    `ergebnis` bleibt absichtlich beliebig: jeder Melder misst etwas anderes.
    Die Huelle drumherum ist das Gemeinsame — wer liest, prueft immer dieselben
    drei Felder, egal von welchem Melder die Datei kommt.
    """
    daten = {
        "schema": SCHEMA,
        "melder": melder,
        "gemessen_am": (gemessen_am or _jetzt())
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "werkzeug_version": werkzeug_version,
        "ergebnis": ergebnis,
    }
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(
        json.dumps(daten, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return daten


def lies(
    pfad: Path,
    *,
    max_alter_tage: int = MAX_ALTER_TAGE,
    jetzt: datetime | None = None,
) -> dict | None:
    """Ergebnis lesen — oder `None`, wenn es fehlt, kaputt oder zu alt ist.

    Alle drei Faelle geben dasselbe zurueck, und das ist Absicht: fuer den
    Aufrufer sind sie identisch. Er hat keinen frischen Beleg und muss die Frage
    offen lassen. Ein kaputtes Ergebnis als "rot" zu werten waere schlimmer als
    es zu ignorieren — es wuerde einen Mangel behaupten, den niemand gemessen hat.
    """
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(daten, dict) or daten.get("schema") != SCHEMA:
        return None
    roh = daten.get("gemessen_am")
    if not isinstance(roh, str):
        return None
    try:
        gemessen = datetime.fromisoformat(roh.replace("Z", "+00:00"))
    except ValueError:
        return None
    if gemessen.tzinfo is None:
        gemessen = gemessen.replace(tzinfo=timezone.utc)
    if (jetzt or _jetzt()) - gemessen > timedelta(days=max_alter_tage):
        return None
    return daten
