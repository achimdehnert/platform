"""Drill fuer tools/gpu_leerlauf.py (platform#3352).

Die beiden teuersten Faelle stammen aus dem Bau am 2026-09-21 und sind beide
real aufgetreten:

1. `test_should_flag_a_service_that_was_never_called` — vLLM hielt 37,5 GB und
   hatte im Journal keine einzige Anfrage. Ein Melder, der „keine Anfrage" als
   „unklar, lieber schweigen" liest, ist fuer genau diesen Fall blind.
2. `test_should_not_count_a_shutdown_line_as_a_request` — beim Herunterfahren
   schreibt vLLM „[shutdown] EngineCore: request processing complete". Ein loses
   `processing` im Muster machte daraus eine frische Anfrage; der Melder meldete
   dann nichts, obwohl der Dienst seit 13 Tagen still war. Gefunden nur, weil
   die Positivkontrolle lief — ohne sie waere der Melder gruen und wertlos gewesen.

Kein Netz: `messe_knoten` ist die einzige Funktion mit Aussenkontakt und wird
hier nicht gerufen. Der echte Pfad ist einmal belegt (beide Knoten gemessen,
vLLM als 37,2 GB / 13 Tage still gemeldet).
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gpu_leerlauf as gl  # noqa: E402

HEUTE = date(2026, 9, 21)
FERN = Path(__file__).resolve().parents[1] / "gpu_leerlauf_remote.sh"


def _proc(mib: int, letzte: str = "", unit: str = "vllm.service") -> dict:
    return {"pid": 1, "mib": mib, "unit": unit, "cmd": "x", "letzte_anfrage": letzte}


# ── Wann ist ein Dienst im Leerlauf? ────────────────────────────────────────


def test_should_flag_a_service_that_was_never_called() -> None:
    """Keine Anfrage im Journal ist der SCHWERE Fall, nicht der unklare."""
    b = gl.beurteile([_proc(38000)], 4.0, 3, HEUTE)

    assert len(b) == 1
    assert b[0]["stille_tage"] is None
    assert b[0]["gb"] == 37.1


def test_should_flag_a_service_silent_longer_than_the_threshold() -> None:
    b = gl.beurteile([_proc(38000, "2026-09-08T10:00:00+02:00")], 4.0, 3, HEUTE)

    assert b[0]["stille_tage"] == 13


def test_should_not_flag_a_service_called_today() -> None:
    """kev hielt 18 GB und war in Benutzung — das ist Bereitschaft, kein Leerlauf."""
    b = gl.beurteile(
        [_proc(18198, "2026-09-21T18:13:35+02:00", "kev.service")], 4.0, 3, HEUTE
    )

    assert b == []


def test_should_ignore_small_consumers_even_when_silent() -> None:
    """whisper hielt 2 GB. Ein Melder, der Kleinkram meldet, wird ueberlesen."""
    b = gl.beurteile([_proc(2070, "", "whisper.service")], 4.0, 3, HEUTE)

    assert b == []


@pytest.mark.parametrize("tage", [3, 4, 30])
def test_should_flag_at_and_above_the_threshold(tage: int) -> None:
    tag = date.fromordinal(HEUTE.toordinal() - tage).isoformat()
    b = gl.beurteile([_proc(38000, f"{tag}T10:00:00+02:00")], 4.0, 3, HEUTE)

    assert len(b) == 1, f"{tage} Tage Stille muessen melden"


def test_should_stay_quiet_just_below_the_threshold() -> None:
    b = gl.beurteile([_proc(38000, "2026-09-19T10:00:00+02:00")], 4.0, 3, HEUTE)

    assert b == []


# ── Stille rechnen ─────────────────────────────────────────────────────────


def test_should_return_none_for_an_unparsable_timestamp() -> None:
    """Lieber „nie gerufen" als eine erfundene Zahl."""
    assert gl.stille_tage("kein Datum", HEUTE) is None


def test_should_handle_utc_suffix() -> None:
    assert gl.stille_tage("2026-09-18T10:00:00Z", HEUTE) == 3


# ── Das Fernskript: was zaehlt als Anfrage? ────────────────────────────────


def _filter(zeilen: list[str]) -> list[str]:
    """Genau die beiden grep-Stufen des Fernskripts, gegen echte Journal-Zeilen."""
    quelle = FERN.read_text(encoding="utf-8")
    nehmen = quelle.split("grep -aE ")[1].split("\n")[0].strip().strip('"')
    lassen = quelle.split("grep -avE ")[1].split("|\n")[0].strip().strip("'")
    text = "\n".join(zeilen)
    a = subprocess.run(
        ["grep", "-aE", nehmen], input=text, capture_output=True, text=True
    ).stdout
    b = subprocess.run(
        ["grep", "-avE", lassen], input=a, capture_output=True, text=True
    ).stdout
    return [z for z in b.splitlines() if z.strip()]


def test_should_not_count_a_shutdown_line_as_a_request() -> None:
    """Der Realfall, der den Melder blind machte."""
    zeile = (
        "2026-09-21T19:29:28+02:00 gx10 vllm[3588]: (EngineCore pid=3588) "
        "INFO [core.py:1496] [shutdown] EngineCore: request processing complete"
    )

    assert _filter([zeile]) == []


def test_should_not_count_the_route_listing_at_startup() -> None:
    zeile = (
        "2026-09-15T04:41:03+02:00 gx10 vllm[2411]: INFO [launcher.py:60] Route: /infer"
    )

    assert _filter([zeile]) == []


def test_should_count_a_real_http_request() -> None:
    """Positivkontrolle zum Filter: er MUSS etwas finden koennen."""
    zeile = (
        "2026-09-15T11:01:03+02:00 gx10 ollama[7293]: [GIN] | 200 | POST /api/generate"
    )

    assert len(_filter([zeile])) == 1


def test_should_count_whisper_processing_a_file() -> None:
    """whisper meldet echte Arbeit mit Anfuehrungszeichen — das unterscheidet
    sie von der Abschaltzeile, die ebenfalls `processing` enthaelt."""
    zeile = (
        "2026-09-17T11:08:30+02:00 gx10 whisper-server[2412]: "
        "operator(): processing 'plaud_pub_fbb136bd.wav'"
    )

    assert len(_filter([zeile])) == 1
