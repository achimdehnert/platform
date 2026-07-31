"""Der Wächter, gemessen an den Sätzen, an denen er versagt hat.

Am 2026-07-31 gingen an einem Tag fünf prüfbare Behauptungen falsch oder ungeprüft
raus. Der Scanner lief die ganze Zeit — er fing **eine**. Die vier anderen sind hier
wörtlich als Fixture hinterlegt, damit „ich achte künftig darauf" durch etwas ersetzt
wird, das beim nächsten Mal von selbst anschlägt.

Wichtig für die Bewertung dieser Datei: ein Test, der nur die neu gebauten Muster
bestätigt, wäre zirkulär. Deshalb stehen die **Nicht-Treffer** gleichberechtigt
daneben — Redewendungen, die dieselben Wörter tragen, aber nichts Prüfbares behaupten.
Ein Wächter, der bei „ich habe keine Zeit" anschlägt, wird abgeschaltet und schützt
dann gar nichts mehr.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_QUELLE = Path(__file__).resolve().parents[1] / "evidence_claim_scanner.py"
_spec = importlib.util.spec_from_file_location("evidence_claim_scanner", _QUELLE)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)


def _klassen(satz: str) -> set[str]:
    return {label for muster, label in scanner.CLAIM_PATTERNS if muster.search(satz)}


# --- Die realen Fehlsätze vom 2026-07-31, wörtlich -------------------------------

@pytest.mark.parametrize(
    "satz, erwartet",
    [
        # Gelesen waren 100 von 140 Zeilen; alle drei Meter-Jobs trugen den Zweig.
        ("Kein einziger dieser Jobs fragt steps.meter.outcome ab.", "universal-claim"),
        ("Keiner der drei Melder prüft das outcome.", "universal-claim"),
        # Belegt war der Vortag, behauptet die Gegenwart.
        ("Der Megatest läuft weiterhin nicht.", "function-negation"),
        ("Das Gate greift nicht.", "function-negation"),
        # Aus dem Gedächtnis geschrieben, falsch: 29.07. vs. 30.07.
        ("Das war das zweite Mal am selben Tag.", "temporal-claim"),
        ("Der Check schlägt seit 14 Tagen fehl.", "temporal-claim"),
        # Vermutung im Gewand eines Befunds; geprüft waren es null.
        ("Viele dieser Issues sind längst erledigt und wurden nur nie geschlossen.",
         "soft-quantifier-claim"),
        ("Die meisten der Repos haben den Scan schon aktiv.", "soft-quantifier-claim"),
    ],
)
def test_should_erkennen_die_realen_fehlsaetze(satz: str, erwartet: str) -> None:
    assert erwartet in _klassen(satz), f"{satz!r} rutscht weiterhin durch"


# --- Redewendungen: gleiche Wörter, keine prüfbare Behauptung ---------------------

@pytest.mark.parametrize(
    "satz",
    [
        "Ich habe keine Zeit, das heute noch zu prüfen.",
        "Das läuft nicht auf einen Rewrite hinaus.",
        "Es gibt keinen Grund, das jetzt zu entscheiden.",
        "Der Fix funktioniert nicht nur hier, sondern überall.",
        "Wir sollten das nicht zwingend heute klären.",
        "Viele Wege führen nach Rom.",
        "Das kostet viele Stunden Arbeit.",
    ],
)
def test_should_redewendungen_in_ruhe_lassen(satz: str) -> None:
    treffer = _klassen(satz) & {"universal-claim", "function-negation", "temporal-claim", "soft-quantifier-claim"}
    assert not treffer, f"Falschalarm auf {satz!r}: {treffer}"


# --- Beleg-Strenge: der falsche Beleg darf nicht durchgehen ----------------------

def test_should_diff_nicht_als_beleg_fuer_gegenwart_akzeptieren() -> None:
    """`git show` zeigt Code, nicht Verhalten.

    Genau dieser Fehlschluss trug den Megatest-Satz: die Workflow-Datei war
    unverändert, also „läuft weiterhin nicht" — ohne den heutigen Lauf anzusehen.
    """
    assert not scanner.RUN_EVIDENCE_TOKENS.search("git show origin/main:.github/workflows/megatest.yml")
    assert scanner.RUN_EVIDENCE_TOKENS.search("gh run view 30610979756 --log")


def test_should_stichprobe_nicht_als_beleg_fuer_allaussage_akzeptieren() -> None:
    """Ein gezielter Datei-Read deckt keine Aussage über eine ganze Menge."""
    assert not scanner.ABSENCE_EVIDENCE_TOKENS.search("Read .github/workflows/megatest.yml limit=100")
    assert scanner.ABSENCE_EVIDENCE_TOKENS.search("grep -rn 'steps.meter.outcome' .github/workflows/")
