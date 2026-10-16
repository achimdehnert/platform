#!/usr/bin/env python3
"""PreToolUse(Bash|mcp__.*|WebFetch|WebSearch) — Kundendaten an Billiganbieter: erst melden, dann sperren.

GATE_HEADER (KONZ-038 D8):
  "slug": "kundendaten-an-billiganbieter"
  "mode": "advisory"
  "owner": "achim"
  "last_drill_pass": "2026-10-16"
  "evidence": "tools/claude-hooks/tests/test_melde_kundendaten_an_billiganbieter.py"

Anlass platform#4049 Punkt 2 (externe Empfehlung Nr. 33): Das Gate
`vertrauliches-verlaesst-ablage` sperrt nur Inhalte MIT Vermerk. Kunden- und
Personendaten ohne Vermerk gingen weiter an die Billiganbieter, an die die
Routing-Regel Zusammenfassen und Einordnen gibt. Dieser Haken findet sie dort
und MELDET sie bis zu einem Stichtag; danach sperrt er. Die Meldewoche misst die
Fehlalarme, bevor eine Sperre Arbeit kostet. Ersatzweg: `tools/lokal_modell.py`.

Regeln stehen in derselben privaten Regeldatei wie die Schranke
(`~/.claude/vertraulich_regeln.json`), drei optionale Felder:
`billig_muster` (Anbieter-Route), `kunden_muster` (Kunden- und Personendaten),
`billig_melden_bis` (ISO-Datum, letzter Meldetag). Fehlt eines der beiden
Muster, ist der Haken aus. Kundennamen stehen nie hier (Repo oeffentlich).

Pruefkern: aus `block_vertrauliches_verlassen` (Dateien im Befehl, Inhalt
gestarteter Python-Skripte) — gleiche Erfassung, kein zweiter Parser.

FAIL-Verhalten: Pruefung wirft ⇒ als `fehler` gezaehlt und gemeldet, nicht
gesperrt (Lehre platform#3862 Fund 5: ein stiller Fehler sieht aus wie „kein
Fund"). Eine kaputte Regeldatei sperrt ohnehin die Schranke (fail-closed).
Protokoll: nur Werkzeug und Index des Musters, nie Inhalt, nie Musterwortlaut.

GRENZEN (bewusst): Daten auf stdin (`-F -`, Pipe aus einem anderen Befehl)
sieht der Haken nicht; Skripte nur als `python <datei>.py`; Personendaten
erkennt er nur, soweit ein Muster sie beschreibt (Namen ohne Muster nicht).
Inhalte mit Vermerk ueberlaesst er der Schranke.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import block_vertrauliches_verlassen as kern  # noqa: E402

SLUG = "kundendaten-an-billiganbieter"
ERSATZ = "tools/lokal_modell.py (GX10, nur localhost)"


class BilligRegeln:
    def __init__(self, roh: dict) -> None:
        self.billig = [
            re.compile(m, re.IGNORECASE) for m in roh.get("billig_muster") or []
        ]
        self.kunden = [re.compile(m) for m in roh.get("kunden_muster") or []]
        self.vermerk = [re.compile(m) for m in roh.get("vermerk_muster") or []]
        bis = roh.get("billig_melden_bis")
        self.melden_bis = date.fromisoformat(bis) if bis else None

    @property
    def aktiv(self) -> bool:
        return bool(self.billig and self.kunden)


def lade(pfad: Path) -> BilligRegeln:
    return BilligRegeln(json.loads(pfad.read_text(encoding="utf-8")))


def _irgendwo(muster: list[re.Pattern], texte: list[str]) -> bool:
    return any(m.search(t) for m in muster for t in texte)


def _texte(daten: dict, r: BilligRegeln) -> list[str] | None:
    """Die Daten, die zum Anbieter gehen — oder None, wenn keine Anbieter-Route."""
    werkzeug = str(daten.get("tool_name") or "")
    eingabe = daten.get("tool_input") or {}
    if werkzeug == "Bash":
        befehl = str(eingabe.get("command") or "")
        cwd = str(daten.get("cwd") or "/")
        if not _irgendwo(r.billig, [befehl, *kern._skript_inhalte(befehl, cwd)]):
            return None
        return [befehl, *(kern._lies(p) for p in kern._dateien_im_befehl(befehl, cwd))]
    if werkzeug.startswith(kern._EINGABE_WERKZEUGE):
        text = json.dumps(eingabe, ensure_ascii=False).replace("\\n", "\n")
        return [text] if _irgendwo(r.billig, [text]) else None
    return None


def befund(daten: dict, r: BilligRegeln) -> int | None:
    """Index des ersten passenden `kunden_muster`, sonst None."""
    texte = _texte(daten, r)
    if not texte or _irgendwo(r.vermerk, texte):
        return None  # keine Route, oder Vermerk: dann sperrt die Schranke
    for i, m in enumerate(r.kunden):
        if any(m.search(t) for t in texte):
            return i
    return None


def sperrt(r: BilligRegeln, heute: date) -> bool:
    return r.melden_bis is not None and heute > r.melden_bis


#: None = Standardprotokoll von gate_hits; Drills setzen eine eigene Datei.
PROTOKOLL: Path | None = None


def _notiere(marker: str, daten: dict, beleg: str, modus: str = "advisory") -> None:
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            marker,
            beleg=f"{daten.get('tool_name') or ''} {beleg}".strip()[:200],
            session=str(daten.get("session_id") or ""),
            modus=modus,
            pfad=PROTOKOLL,
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stoeren
        pass


def _ausgabe(entscheidung: str | None, text: str) -> None:
    spezifisch: dict = {"hookEventName": "PreToolUse"}
    if entscheidung:
        spezifisch |= {
            "permissionDecision": entscheidung,
            "permissionDecisionReason": text,
        }
    else:
        spezifisch["additionalContext"] = text
    print(
        json.dumps(
            {"systemMessage": text, "hookSpecificOutput": spezifisch},
            ensure_ascii=False,
        )
    )


def main(heute: date | None = None) -> int:
    heute = heute or datetime.now(timezone.utc).date()
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        _notiere("fehler", {}, "stdin")
        return 0
    if (
        not kern.erfasst(daten)
        or str(daten.get("tool_name") or "") in kern._DATEI_WERKZEUGE
    ):
        return 0
    pfad = kern.regeln_pfad()
    if not pfad.exists():
        return 0
    try:
        r = lade(pfad)
        if not r.aktiv:
            return 0
        index = befund(daten, r)
    except Exception as exc:  # noqa: BLE001 — zaehlen und melden, nicht still
        _notiere("fehler", daten, type(exc).__name__)
        _ausgabe(
            None,
            f"⚠ {SLUG}: Pruefung fehlgeschlagen ({type(exc).__name__}) — Regeldatei `{pfad}` pruefen.",
        )
        return 0
    if index is None:
        return 0
    beleg = f"kunden_muster[{index}]"
    if sperrt(r, heute):
        _notiere("treffer", daten, beleg, modus="blocking")
        _ausgabe(
            "deny",
            f"⛔ {SLUG}: Aufruf an einen Billiganbieter enthaelt Kunden- oder Personendaten ({beleg}). Ersatz: {ERSATZ}.",
        )
    else:
        _notiere("meldung", daten, beleg)
        _ausgabe(
            None,
            f"📣 {SLUG} (Meldephase bis {r.melden_bis or 'offen'}): Aufruf an einen Billiganbieter enthaelt Kunden- oder Personendaten ({beleg}). Ersatz: {ERSATZ}. Nach dem Stichtag wird gesperrt.",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
