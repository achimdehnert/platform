"""Tests fuer die Deckblatt-Meta-Zeilen (deckblatt_meta.extract_meta).

Der Deckblatt-Filter entfernt Zeilen wie ``**Auftraggeber:** Firma`` aus dem
Fliesstext mit der Begruendung, sie stuenden bereits auf dem Deckblatt. Stimmt
das nicht, verschwindet die Angabe vollstaendig — bei einem Erfassungsbogen an
einen Mandanten also dessen Name. Genau das war der Fall: das Muster kannte nur
die Schreibweise ohne Doppelpunkt (gefunden 2026-08-26 an Erfassungsboegen).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Wie in den Nachbartests: das Modul direkt aus der Datei laden, tools/print_agent ist
# kein Package. deckblatt_meta ist importfrei — print_agent selbst zieht weasyprint/
# litellm, die in der CI-Testumgebung fehlen (#2621).
_MODUL = Path(__file__).resolve().parents[1] / "deckblatt_meta.py"
_spec = importlib.util.spec_from_file_location("deckblatt_meta", _MODUL)
pa = importlib.util.module_from_spec(_spec)
sys.modules["deckblatt_meta"] = pa
_spec.loader.exec_module(pa)


def test_should_read_the_client_written_with_a_colon():
    meta = pa.extract_meta("**Auftraggeber:** Musterwerk Beispiel GmbH & Co. KG\n")
    assert meta["auftraggeber"] == "Musterwerk Beispiel GmbH & Co. KG"


def test_should_still_read_the_client_written_on_the_next_line():
    """Die bisher einzige unterstuetzte Schreibweise darf nicht wegfallen."""
    meta = pa.extract_meta("**Auftraggeber**\nMusterwerk Beispiel GmbH\n")
    assert meta["auftraggeber"] == "Musterwerk Beispiel GmbH"


def test_should_not_strip_a_line_it_cannot_show_on_the_cover():
    """Filter und Muster muessen dieselbe Schreibweise erfassen.

    Was aus dem Fliesstext entfernt wird, muss das Deckblatt aufnehmen — sonst
    ist die Angabe weg. Diese Invariante ist der eigentliche Fund, nicht das
    einzelne Muster.
    """
    zeile = "**Auftraggeber:** Musterwerk Beispiel GmbH & Co. KG"
    entfernt = zeile not in pa.strip_meta_prefix_lines(zeile + "\n")
    aufgenommen = "auftraggeber" in pa.extract_meta(zeile + "\n")
    assert entfernt is aufgenommen
