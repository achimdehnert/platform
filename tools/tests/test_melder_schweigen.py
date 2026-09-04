"""Ein Melder, der nicht messen konnte, darf nicht wie ein sauberer Befund aussehen.

Die drei Gate-Melder werden im Sitzungsstart als `--kurz ... 2>/dev/null`
aufgerufen, und der Runner entscheidet allein an der Laenge der Ausgabe:

    if [ -n "$DECKUNG_OUT" ]; then record WARN ... else record PASS "keine offene Gate-Pflicht"

Beide Unterdrueckungen zugleich — `--kurz` schrieb die Fehlerzeile gar nicht,
und im Nicht-kurz-Fall ging sie nach stderr — machten aus einer unlesbaren
Registry ein gruenes PASS mit einem positiven Satz ueber Gates, die niemand
gelesen hatte (platform#2278). Dieselbe Klasse wie der `check_c`-Befund aus
platform#2264: das Werkzeug meldete `0`, und `0` sah aus wie Gesundheit.

Diese Datei prueft die drei Werkzeuge GEMEINSAM. Der Fix ist in jedem einzeln
eingetragen; ohne einen Test ueber alle drei laeuft beim naechsten Anfassen
genau einer davon wieder auseinander — die Fehlerklasse
`partial-fix-not-generalized-to-sibling-artifacts`, die seit dem 2026-07 dreimal
in den Retros steht.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
WURZEL = TOOLS.parent

# Werkzeug -> die PASS-Behauptung, die der Runner bei leerer Ausgabe druckt.
MELDER = {
    "gate_deckung.py": "keine offene Gate-Pflicht",
    "gate_wirkung.py": "kein Gate rueckfaellig",
    "gate_namensdeckung.py": "kein Gate nennt einen ungedrillten Fall",
}


def _lauf(werkzeug: str, registry: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS / werkzeug), "--kurz", "--registry", str(registry)],
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize("werkzeug", sorted(MELDER))
def test_should_speak_up_when_the_registry_is_missing(werkzeug, tmp_path):
    lauf = _lauf(werkzeug, tmp_path / "gibtsnicht.json")
    assert lauf.stdout.strip(), (
        f"{werkzeug} schweigt bei fehlender Registry — der Runner macht daraus "
        f"PASS mit der Behauptung '{MELDER[werkzeug]}'"
    )
    assert "misst nichts" in lauf.stdout


@pytest.mark.parametrize("werkzeug", sorted(MELDER))
def test_should_speak_up_when_the_registry_is_corrupt(werkzeug, tmp_path):
    """Der realistische Fall: die Registry wird von Hand editiert.

    Eine fehlende Datei ist selten, ein abgeschnittenes oder syntaktisch kaputtes
    JSON nach einer Handaenderung nicht — `gate-registry.json` waechst mit jeder
    Retro.
    """
    kaputt = tmp_path / "halb.json"
    echte = WURZEL / "docs" / "governance" / "gate-registry.json"
    kaputt.write_text(echte.read_text(encoding="utf-8")[:400], encoding="utf-8")
    lauf = _lauf(werkzeug, kaputt)
    assert "misst nichts" in lauf.stdout


@pytest.mark.parametrize("werkzeug", sorted(MELDER))
def test_should_stay_fail_open_and_not_block_the_session_start(werkzeug, tmp_path):
    """Reden ja, blockieren nein — der Exit-Code-Vertrag bleibt unveraendert.

    Ein Melder, der den Sitzungsstart aufhaelt, wird abgeschaltet und meldet
    danach gar nichts mehr. Das war der Grund fuer Fail-open und bleibt richtig;
    falsch war nur das Schweigen.
    """
    assert _lauf(werkzeug, tmp_path / "gibtsnicht.json").returncode == 0


@pytest.mark.parametrize("werkzeug", sorted(MELDER))
def test_should_not_cry_wolf_on_the_real_registry(werkzeug):
    """Positivkontrolle in der Gegenrichtung: mit echter Registry keine Blind-Zeile.

    Ohne diesen Test wuerde ein Werkzeug, das die Zeile IMMER druckt, alle Tests
    oben bestehen — und der Sitzungsstart haette drei Dauer-WARNs.
    """
    lauf = _lauf(werkzeug, WURZEL / "docs" / "governance" / "gate-registry.json")
    assert "misst nichts" not in lauf.stdout


def test_should_keep_the_runner_reading_stdout_for_these_phases():
    """Der Vertrag hat zwei Enden — dies ist das andere.

    Die Werkzeuge reden jetzt auf stdout. Wirksam ist das nur, solange der Runner
    genau daran PASS und WARN unterscheidet. Wuerde eine Phase auf einen
    Exit-Code oder ein Schluesselwort umgestellt, waere der Fix oben still
    wirkungslos — `melder-ohne-leser`, nur andersherum.
    """
    runner = (TOOLS / "session_start_checks.sh").read_text(encoding="utf-8")
    for variable in ("DECKUNG_OUT", "WIRKUNG_OUT", "NAMDECK_OUT"):
        assert f'if [ -n "${variable}" ]' in runner, variable
        assert f"{variable}=$(" in runner.replace("timeout 60 ", "")
