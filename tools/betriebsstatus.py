"""Das Vokabular fuer `betriebsstatus` in infra/ports.yaml — an EINER Stelle.

Warum (2026-09-01, #2586 K5): der Wert stand dreimal im Repo —
`erreichbarkeit_melder.py`, `origin_tls_melder.py` und `waisen_melder.py`
fuehrten je eine eigene Liste. Als das Owner-Urteil den Wert `ruhend` noetig
machte, kannte ihn ein Melder, die anderen beiden nicht, und der Test
`test_should_nur_erlaubte_betriebsstatus_werte_verwenden` wurde rot.

Drei Kopien einer Liste sind drei Gelegenheiten, dass sie auseinanderlaufen.

Ablauf (2026-09-24, #3507 — V2-Rest von #3495):
    Ein `betriebsstatus` ungleich `aktiv` ist eine Ausnahme: die Melder schweigen
    ueber den Dienst. Bis #3507 war sie unbefristet — `blockiert` seit Wochen sah
    genauso aus wie `blockiert` seit gestern. Jetzt gilt die Ausnahme nur, solange
    in `governance/deklarationen.json` eine gueltige Deklaration der Art
    `betriebsstatus` fuer den Dienst steht (gelesen ueber
    ``befund_journal.deklarationen_fuer``).

    Entwurfsentscheidung — Wert und Grund bleiben in ports.yaml, die Deklaration
    traegt NUR den Ablauf:
      * Das Vokabular gehoert an eine Stelle (dieses Modul). Wanderte der Wert in
        die Deklaration, laesen `deploy_preflight.py`, `flottenbild.py` und
        `iil_assist_katalog.py` ihn entweder aus einer zweiten Quelle oder muessten
        alle mitwandern — fuer ein Feld, das dort kein Befund-Schalter ist.
      * `betriebsstatus_grund` bleibt der fachliche Grund; der `grund` der
        Deklaration sagt, warum GERADE dieses Ablaufdatum (Wiedervorlage-Anlass).
        Kein Wert steht doppelt.
    ``wirksamer_status()`` ist die eine Stelle, die beides zusammenfuehrt.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import befund_journal  # noqa: E402 — Deklarationen, #3507

# Werte, die in infra/ports.yaml stehen duerfen. Alles daneben ist ein Befund,
# keine Variante — sonst faellt ein Tippfehler als "stumme Ausnahme" durch.
STATUS_ERLAUBT: tuple[str, ...] = (
    "aktiv",  # laeuft und soll laufen
    "stillgelegt",  # endgueltig ausser Betrieb
    "blockiert",  # etwas haelt den Betrieb auf (Auflage, Entscheidung, Defekt)
    "ruhend",  # nicht in Betrieb, kann jederzeit wieder anlaufen
)

# Teilmenge: bei diesen Werten ist ein FEHLENDER Container erklaert und kein
# Befund. `aktiv` gehoert ausdruecklich nicht dazu.
ERKLAERT: tuple[str, ...] = tuple(s for s in STATUS_ERLAUBT if s != "aktiv")


def wirksamer_status(
    dienst: str, cfg: dict | None, heute: str | date | None = None
) -> str:
    """Der Status, nach dem ein Melder urteilt.

    * ``aktiv`` oder ein unbekannter Wert -> unveraendert (ein Tippfehler bleibt
      fuer `erreichbarkeit_melder` sichtbar, statt still zu `aktiv` zu werden).
    * ein ``ERKLAERT``-Wert MIT gueltiger ``betriebsstatus``-Deklaration -> der Wert.
    * ein ``ERKLAERT``-Wert OHNE (fehlend, abgelaufen, ungueltig) -> ``aktiv``:
      die Ausnahme wirkt nicht, der Melder meldet den Dienst wieder.
    """
    status = str((cfg or {}).get("betriebsstatus", "aktiv"))
    if status not in ERKLAERT:
        return status
    if befund_journal.deklarationen_fuer(dienst, heute, "betriebsstatus"):
        return status
    return "aktiv"
