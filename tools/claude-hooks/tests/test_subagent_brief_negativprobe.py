"""Drill fuer subagent_brief_negativprobe.py (Slug check-ohne-positivkontrolle).

Realfall: Retro `docs/retros/session-retro-2026-09-17-meiki-hub-8185e1.md`
Befund #1 — der Brief post-hub#22 Ziel 3 verlangte "Projektion strikt auf die
Vertragsfelder; alles andere wird verworfen und nie geloggt", der Subagent
baute `raw.update(fachlich)` (post-hub#23 `be10bda`) und meldete "alle sechs
Ziele erfuellt". Gefangen nur durch Review (`9a3c085`), nicht durch einen
eigenen Test des Subagenten — genau die Luecke, die dieser Hook schliessen
soll: ein Schutz-Kriterium im Brief OHNE vorgeschriebene Negativ-Probe.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location(
    "subagent_brief_negativprobe", _DIR / "subagent_brief_negativprobe.py"
)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

MODUL = _DIR / "subagent_brief_negativprobe.py"


# --- Positivkontrolle (Pflicht): der Realfall aus post-hub#22 Ziel 3 -------

REALFALL_OHNE_PROBE = (
    "Ziel 3: Projektion strikt auf die Vertragsfelder; alles andere wird "
    "verworfen und nie geloggt."
)

REALFALL_MIT_PROBE = REALFALL_OHNE_PROBE + (
    "\nTest: ein geschwätziger Parser mit Fremdfeld und zweitem tenant_id "
    "— nichts davon kommt an."
)


def test_should_flag_realfall_criterion_without_negativprobe() -> None:
    """probe: ohne_negativprobe — der wortwoertliche Realfall-Ausschnitt OHNE
    Negativ-Probe muss melden."""
    grund = scanner.entscheide(REALFALL_OHNE_PROBE)
    assert grund is not None
    assert "check-ohne-positivkontrolle" in grund
    assert "Negativ-Probe" in grund


def test_should_not_flag_realfall_criterion_with_negativprobe() -> None:
    """Dieselbe Zeile MIT einer Negativ-Probe-Zeile darf nicht melden."""
    assert scanner.entscheide(REALFALL_MIT_PROBE) is None


# --- Zweiter Positivfall: kein Schreibzugriff + DELETE/PUT/PATCH-Probe -----

KEIN_SCHREIBZUGRIFF_MIT_PROBE = (
    "Der Leser hat kein Schreibzugriff auf den Ziel-DB.\n"
    "Test belegt, dass keine DELETE/PUT/PATCH abgesetzt werden."
)


def test_should_not_flag_write_ban_with_delete_put_patch_probe() -> None:
    assert scanner.entscheide(KEIN_SCHREIBZUGRIFF_MIT_PROBE) is None


def test_should_flag_write_ban_without_probe() -> None:
    ohne_probe = "Der Leser hat kein Schreibzugriff auf den Ziel-DB."
    grund = scanner.entscheide(ohne_probe)
    assert grund is not None


# --- Fail-open: Lese-Agenten werden nicht geprueft --------------------------


def test_should_ignore_read_only_agent_even_with_schutz_woertern() -> None:
    """probe: lese_agent — Explore-Subagent wird nicht geprueft (fail-open)."""
    res = subprocess.run(
        [str(MODUL)],
        input=json.dumps(
            {
                "tool_name": "Agent",
                "tool_input": {
                    "subagent_type": "Explore",
                    "prompt": REALFALL_OHNE_PROBE,
                },
            }
        ),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0
    assert res.stdout.strip() == ""


# --- Brief ohne Schutz-Kriterien --------------------------------------------


def test_should_not_flag_brief_without_schutz_kriterien() -> None:
    brief = "Behebe den Tippfehler in der README, Zeile 12."
    assert scanner.entscheide(brief) is None


def test_should_return_empty_list_when_no_schutz_kriterium_present() -> None:
    assert scanner.finde_schutz_kriterien("Behebe den Tippfehler.") == []


# --- Kaputtes JSON / leere Eingabe: Exit 0, keine Meldung -------------------


def test_should_exit_zero_on_broken_json() -> None:
    res = subprocess.run(
        [str(MODUL)],
        input="{kaputt",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_should_exit_zero_on_empty_stdin() -> None:
    res = subprocess.run(
        [str(MODUL)], input="{}", capture_output=True, text=True, timeout=30
    )
    assert res.returncode == 0


def test_should_ignore_non_agent_tool_calls() -> None:
    res = subprocess.run(
        [str(MODUL)],
        input=json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": REALFALL_OHNE_PROBE}}
        ),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0
    assert res.stdout.strip() == ""


# --- Hook-Vertrag: echte Delegation feuert, Exit 0 --------------------------


def test_should_exit_zero_and_print_hint_for_unflagged_criterion() -> None:
    res = subprocess.run(
        [str(MODUL)],
        input=json.dumps(
            {
                "tool_name": "Agent",
                "tool_input": {
                    "subagent_type": "general-purpose",
                    "prompt": REALFALL_OHNE_PROBE,
                },
            }
        ),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0
    assert "check-ohne-positivkontrolle" in res.stdout


def test_should_exit_zero_and_print_nothing_when_probe_present() -> None:
    res = subprocess.run(
        [str(MODUL)],
        input=json.dumps(
            {
                "tool_name": "Agent",
                "tool_input": {
                    "subagent_type": "general-purpose",
                    "prompt": REALFALL_MIT_PROBE,
                },
            }
        ),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_should_never_use_hookspecificoutput_json_pretooluse_has_no_additionalcontext() -> (
    None
):
    """PreToolUse kennt additionalContext nicht — Klartext ist der belegte Weg
    (wie cd_fehlschlag_ketten_scanner.py / tools/hooks/foreign_clone_check.sh).
    Geprueft per AST, damit die Erklaerung im Docstring hierueber nicht selbst
    durchfaellt."""
    import ast

    baum = ast.parse(MODUL.read_text(encoding="utf-8"), filename=str(MODUL))
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Dict):
            continue
        for schluessel in knoten.keys:
            assert not (
                isinstance(schluessel, ast.Constant)
                and schluessel.value == "hookSpecificOutput"
            ), "subagent_brief_negativprobe.py darf kein hookSpecificOutput senden"


# --- Mutationstest: belegt, dass die Verneinungs-Erkennung wirklich traegt -


def test_should_flag_good_case_when_negation_detection_is_disabled_mutation(
    monkeypatch,
) -> None:
    """Ohne Verneinungs-Muster-Erkennung MUSS derselbe gute Fall durchfallen —
    sonst haengt das "keine Meldung" oben an etwas anderem als der Verneinung
    (z.B. daran, dass irgendein Wort 'Test' vorkommt)."""
    kaputtes_muster = re.compile(r"(?!)")  # matcht nie irgendetwas
    monkeypatch.setattr(scanner, "NEGATIVPROBE_MUSTER", kaputtes_muster)
    grund = scanner.entscheide(REALFALL_MIT_PROBE)
    assert grund is not None, (
        "Mutationstest fehlgeschlagen: der gute Fall (Realfall MIT Negativ-Probe) "
        "wird auch ohne Verneinungs-Erkennung nicht gemeldet — die 'keine "
        "Meldung' haengt dann an etwas anderem als NEGATIVPROBE_MUSTER."
    )
