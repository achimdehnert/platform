#!/usr/bin/env python3
"""handover_byte_cap.py — Byte-Deckel fuer AGENT_HANDOVER.md (platform#2606, Stufe 1).

AGENT_HANDOVER.md ist Pflicht-Lektuere bei JEDEM Session-Start. Am 2026-09-02 war die
Datei 116.548 Byte gross (~35 k Tokens), davon 85 % nie ausgelagerte Historie: die
Sektion „Naechste Schritte (kompakt)" allein trug 91.771 Byte (78,7 %), und daneben
stand ein Block „0. Aktuelle Prioritaeten (2026-07-02 …)" mit zwei Monate altem Datum.
Die Datei-Konvention („nur aktueller + ein vorheriger Stand, Rest ins Archiv") gab es
seit Monaten — sie war nur nirgends durchgesetzt und wuchs deshalb monoton.

Der Deckel ist die Durchsetzung: Er misst genau eine Zahl, und wenn sie reisst, ist die
Antwort **auslagern**, nicht den Deckel anheben. Bewusst kein Zeilen- oder Sektionsmass —
Bytes sind das, was den Kontext kostet, und die einzige Groesse, die man nicht
wegformatieren kann.

Aufruf (lokal identisch zu CI):

    python3 scripts/checks/handover_byte_cap.py                  # AGENT_HANDOVER.md
    python3 scripts/checks/handover_byte_cap.py <datei> [...]    # beliebige Dateien
    python3 scripts/checks/handover_byte_cap.py --limit 20000 <datei>

Exit-Codes: 0 = unter dem Deckel · 1 = Deckel gerissen · 2 = Aufruf-/Dateifehler
(eine fehlende Datei ist ausdruecklich KEIN gruener Zustand — sonst meldet der Check
gruen, wenn jemand den Pfad umbenennt; vgl. feedback_measurement_tool_zero_is_not_absence).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

#: Deckel in Byte. Hergeleitet aus dem Bestand nach der Diaet vom 2026-09-02
#: (16.420 B: Kopf + Zeitanker + ein Stand-Block + 24 offene Faeden + §1–§7 Referenz).
#: ~3,5 kB Luft reichen fuer einen neuen Stand-Block; der uebernaechste zwingt zum
#: Auslagern des dann aeltesten — genau die gewollte Rotation.
DEFAULT_LIMIT = 20_000

#: Ein Pfad, damit der Check ohne Argumente dasselbe misst wie in CI.
DEFAULT_PFADE = ("AGENT_HANDOVER.md",)

MELDUNG = (
    "Handover ist Arbeitsstand, nicht Archiv — "
    "aelteste Sektion nach AGENT_HANDOVER_ARCHIVE.md verschieben"
)


def pruefe(pfad: Path, limit: int) -> tuple[bool, str]:
    """(ok, Meldung) fuer eine Datei. Fehlende Datei ist ein Fehler, kein PASS."""
    if not pfad.is_file():
        raise FileNotFoundError(pfad)
    groesse = pfad.stat().st_size
    if groesse > limit:
        return False, f"{pfad}: {groesse:,} B > {limit:,} B — {MELDUNG}"
    return True, f"{pfad}: {groesse:,} B / {limit:,} B"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pfade", nargs="*", default=list(DEFAULT_PFADE))
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = ap.parse_args(argv)

    pfade = [Path(p) for p in (args.pfade or list(DEFAULT_PFADE))]
    gerissen: list[str] = []
    for pfad in pfade:
        try:
            ok, zeile = pruefe(pfad, args.limit)
        except FileNotFoundError:
            print(f"⛔ {pfad}: Datei nicht gefunden — Pfad pruefen.", file=sys.stderr)
            return 2
        print(("✅ " if ok else "⛔ ") + zeile)
        if not ok:
            gerissen.append(str(pfad))

    if gerissen:
        print(
            f"\n⛔ Gate handover-byte-deckel: {len(gerissen)} Datei(en) ueber dem Deckel.\n"
            f"   {MELDUNG}.\n"
            "   Der Deckel wird NICHT angehoben — siehe Konventionsblock im Dateikopf.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
