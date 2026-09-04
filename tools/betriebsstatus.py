"""Das Vokabular fuer `betriebsstatus` in infra/ports.yaml — an EINER Stelle.

Warum (2026-09-01, #2586 K5): der Wert stand dreimal im Repo —
`erreichbarkeit_melder.py`, `origin_tls_melder.py` und `waisen_melder.py`
fuehrten je eine eigene Liste. Als das Owner-Urteil den Wert `ruhend` noetig
machte, kannte ihn ein Melder, die anderen beiden nicht, und der Test
`test_should_nur_erlaubte_betriebsstatus_werte_verwenden` wurde rot.

Drei Kopien einer Liste sind drei Gelegenheiten, dass sie auseinanderlaufen.
"""

from __future__ import annotations

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
