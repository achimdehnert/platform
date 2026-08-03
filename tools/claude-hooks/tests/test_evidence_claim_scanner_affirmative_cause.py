"""Bejahende Ursachenbehauptung — der Marker, den `over-diagnosis` nicht abdeckte.

`evidence-discipline.md` nennt „root-cause label" ausdruecklich als ausloesenden
Marker. Der Scanner setzte davon bis 2026-08-03 nur die **abwehrende** Haelfte um
(`pre-existing`, `konfabuliert`, `infra-smell`, `not my code`). Eine **bejahende**
Diagnose — „die Ursache ist X", „das liegt an X" — trug keinen dieser Marker.

Realfall (Retro 928b64): Ein `403 CSRF Failed` wurde als „veraltetes Plaetzchen"
festgestellt und in ein durables Memory geschrieben, bevor ein Befund das stuetzte.
Der Scanner lief dabei im blocking-Modus und schwieg. Widerlegt wurde die Diagnose
erst durch eine Gegenprobe, die in der bereits gelesenen Memory-Datei woertlich
vorgeschlagen war.

Die Faelle unten sind die echten Saetze dieser Sitzung, nicht erfundene Beispiele.

Run: `python3 -m pytest tools/claude-hooks/tests/test_evidence_claim_scanner_affirmative_cause.py -q`
"""

import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "evidence_claim_scanner.py"
_spec = importlib.util.spec_from_file_location("scanner", _SRC)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)


# Ungehedgte Ursachen-FESTSTELLUNGEN — muessen feuern.
FEUERT = [
    "Das ist ein bekanntes Muster aus dem doc-hub-Aufbau, nicht ein neuer Defekt.",
    "Die Ursache ist ein veraltetes Plaetzchen im Tab.",
    "Der Fehler liegt an der Cookie-Domain.",
    "Root cause: stale service worker.",
    "Das Verhalten wird verursacht durch die Middleware-Reihenfolge.",
    "The failure is caused by a stale cookie.",
]

# Als Hypothese gekennzeichnet ODER gar keine Ursachenaussage — muessen schweigen.
SCHWEIGT = [
    "Meine Leithypothese: die Ursache ist ein Doppel-Cookie.",
    "Hypothese: das Problem liegt an der Edge.",
    "Nicht verifiziert: die Ursache ist der Service Worker.",
    "Vermutlich liegt es an einem veralteten Service Worker.",
    "Das koennte an der Cookie-Domain liegen.",
    "Die Ursache ist noch nicht belegt.",
    "Ich habe den nginx-vhost gelesen und die Konfiguration geprueft.",
    "Verifiziert: Schreibpfad intakt, 201 mit Token.",
]


@pytest.mark.parametrize("satz", FEUERT)
def test_should_flag_unhedged_cause_assertion(satz):
    assert scanner._affirmative_cause_fires(satz), (
        "Ursachen-Feststellung ohne Hedge muss feuern"
    )


@pytest.mark.parametrize("satz", SCHWEIGT)
def test_should_stay_silent_on_hedged_or_causeless_text(satz):
    assert not scanner._affirmative_cause_fires(satz), (
        "Als Hypothese gekennzeichnete oder ursachenlose Aussage darf NICHT feuern"
    )


def test_should_not_split_hedge_from_claim_at_colon():
    """Regressionsschutz fuer den einzigen Fehlalarm des Kalibrierlaufs.

    Mit ":" im Satz-Splitter landete „Leithypothese:" in einem anderen Segment als
    „die Ursache ist X" — der Hedge verfehlte den Treffer und der Satz feuerte.
    """
    assert not scanner._affirmative_cause_fires(
        "Meine Leithypothese: die Ursache ist ein Doppel-Cookie."
    )


def test_should_keep_hedge_scoped_to_its_own_sentence():
    """Ein Hedge darf NICHT den ganzen Turn entwaffnen — sonst genuegte ein
    beilaeufiges „vermutlich" irgendwo, um jede spaetere Feststellung zu decken."""
    text = (
        "Vermutlich haengt das mit dem Umbau zusammen.\n"
        "Die Ursache ist ein veraltetes Plaetzchen im Tab."
    )
    assert scanner._affirmative_cause_fires(text)


def test_should_register_label_in_claim_patterns():
    """Positivkontrolle: ohne Eintrag in CLAIM_PATTERNS laeuft der Zweig nie an."""
    labels = [label for _pat, label in scanner.CLAIM_PATTERNS]
    assert "affirmative-cause" in labels
