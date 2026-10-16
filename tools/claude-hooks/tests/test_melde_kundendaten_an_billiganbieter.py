"""Drill fuer das Gate `kundendaten-an-billiganbieter` (platform#4049 Punkt 2).

Kunden- und Personendaten ohne Vermerk, die an einen Billiganbieter gehen: bis
zum Stichtag melden (Marker `meldung`), danach sperren (`treffer`). Neben jedem
Fang steht ein Durchlass-Test. Kunde und Muster sind neutral (ACME); die echte
Regeldatei liegt ausserhalb jedes Repos. Gegenprobe: dieselben Aufrufe ohne
Anbieter-Route oder ohne Kundendaten bleiben stumm.
"""

from __future__ import annotations

import io
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import block_vertrauliches_verlassen as kern  # noqa: E402
import melde_kundendaten_an_billiganbieter as hook  # noqa: E402

BEISPIEL = Path(__file__).resolve().parents[1] / "vertraulich_regeln.beispiel.json"
MELDETAG = date(2026, 10, 20)
STICHTAG = date(2026, 10, 23)
NACH_STICHTAG = date(2026, 10, 24)
KUNDE = "Bitte zusammenfassen: Angebot an ACME, Rueckfragen an einkauf@acme.example.\n"
NEUTRAL = "Bitte zusammenfassen: Ablauf der Fahrplanaenderung im Dezember.\n"


@pytest.fixture(autouse=True)
def heim(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    regeln = tmp_path / ".claude" / "vertraulich_regeln.json"
    regeln.parent.mkdir()
    shutil.copy(BEISPIEL, regeln)
    monkeypatch.setenv(kern.REGELN_ENV, str(regeln))
    monkeypatch.setattr(hook, "PROTOKOLL", tmp_path / "gate-hits.jsonl")
    (tmp_path / "scratch").mkdir()
    return tmp_path


def _regeln() -> hook.BilligRegeln:
    return hook.lade(kern.regeln_pfad())


def _befund(werkzeug: str, eingabe: dict, cwd: str = "/") -> int | None:
    return hook.befund({"tool_name": werkzeug, "tool_input": eingabe, "cwd": cwd}, _regeln())


def _lauf(monkeypatch, capsys, werkzeug: str, eingabe: dict, heute: date) -> dict:
    daten = {"tool_name": werkzeug, "tool_input": eingabe, "cwd": "/", "session_id": "s1"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(daten)))
    assert hook.main(heute=heute) == 0
    aus = capsys.readouterr().out.strip()
    return json.loads(aus) if aus else {}


def _protokoll(heim: Path) -> list[dict]:
    datei = heim / "gate-hits.jsonl"
    if not datei.exists():
        return []
    return [json.loads(z) for z in datei.read_text(encoding="utf-8").splitlines()]


def _schreibe(pfad: Path, text: str) -> str:
    pfad.write_text(text, encoding="utf-8")
    return str(pfad)


# --- Fang 1: Bash mit Anbieter im Befehl, Kundendaten in der genannten Datei --


def test_should_melden_bash_route_with_customer_file(heim):
    datei = _schreibe(heim / "scratch" / "mail.txt", KUNDE)
    assert _befund("Bash", {"command": f"llm --anbieter groq --datei {datei}"}) == 0


def test_should_pass_bash_route_with_neutral_file(heim):
    datei = _schreibe(heim / "scratch" / "mail.txt", NEUTRAL)
    assert _befund("Bash", {"command": f"llm --anbieter groq --datei {datei}"}) is None


def test_should_pass_customer_file_without_cheap_route(heim):
    datei = _schreibe(heim / "scratch" / "mail.txt", KUNDE)
    assert _befund("Bash", {"command": f"wc -l {datei}"}) is None


# --- Fang 2: Route steckt im gestarteten Skript ---------------------------


def test_should_melden_script_with_route_and_iban_in_command(heim):
    skript = _schreibe(heim / "scratch" / "zusammenfassen.py", "ANBIETER = 'cerebras'\n")
    befehl = f"python3 {skript} 'Gutschrift auf DE12 3456 7890 1234 5678 90'"
    assert _befund("Bash", {"command": befehl}) == 4


def test_should_pass_local_script_with_iban(heim):
    skript = _schreibe(heim / "scratch" / "zusammenfassen.py", "BASIS = 'http://127.0.0.1:11435'\n")
    befehl = f"python3 {skript} 'Gutschrift auf DE12 3456 7890 1234 5678 90'"
    assert _befund("Bash", {"command": befehl}) is None


# --- Fang 3: MCP und Web ---------------------------------------------------


def test_should_melden_mcp_call_to_cheap_provider_with_phone(heim):
    eingabe = {"anbieter": "together", "text": "Rueckruf unter +49 711 1234567"}
    assert _befund("mcp__llm__complete", eingabe) == 3


def test_should_pass_mcp_call_to_cheap_provider_without_personal_data(heim):
    eingabe = {"anbieter": "together", "text": NEUTRAL}
    assert _befund("mcp__llm__complete", eingabe) is None


# --- Abgrenzung zur Schranke ----------------------------------------------


def test_should_leave_marked_content_to_vault_gate(heim):
    datei = _schreibe(heim / "scratch" / "mail.txt", "ACME Intern\n" + KUNDE)
    assert _befund("Bash", {"command": f"llm --anbieter groq --datei {datei}"}) is None


def test_should_ignore_file_tools(monkeypatch, capsys, heim):
    eingabe = {"file_path": str(heim / "scratch" / "n.md"), "content": "groq " + KUNDE}
    assert _lauf(monkeypatch, capsys, "Write", eingabe, MELDETAG) == {}


# --- Melden bis zum Stichtag, danach sperren ------------------------------


def test_should_report_without_deny_until_cutoff(monkeypatch, capsys, heim):
    eingabe = {"anbieter": "groq", "text": KUNDE}
    for tag in (MELDETAG, STICHTAG):
        aus = _lauf(monkeypatch, capsys, "mcp__llm__complete", eingabe, tag)
        spezifisch = aus["hookSpecificOutput"]
        assert "permissionDecision" not in spezifisch
        assert "kunden_muster[0]" in spezifisch["additionalContext"]
    assert [z["marker"] for z in _protokoll(heim)] == ["meldung", "meldung"]


def test_should_block_after_cutoff(monkeypatch, capsys, heim):
    aus = _lauf(monkeypatch, capsys, "mcp__llm__complete", {"anbieter": "groq", "text": KUNDE}, NACH_STICHTAG)
    assert aus["hookSpecificOutput"]["permissionDecision"] == "deny"
    zeilen = _protokoll(heim)
    assert [(z["marker"], z["modus"]) for z in zeilen] == [("treffer", "blocking")]


def test_should_never_log_content_or_pattern_text(monkeypatch, capsys, heim):
    _lauf(monkeypatch, capsys, "mcp__llm__complete", {"anbieter": "groq", "text": KUNDE}, MELDETAG)
    roh = (heim / "gate-hits.jsonl").read_text(encoding="utf-8")
    assert "ACME" not in roh and "acme.example" not in roh
    assert "kunden_muster[0]" in roh


def test_should_stay_silent_without_cheap_patterns(monkeypatch, capsys, heim):
    regeln = json.loads(BEISPIEL.read_text(encoding="utf-8"))
    del regeln["billig_muster"]
    kern.regeln_pfad().write_text(json.dumps(regeln), encoding="utf-8")
    assert _lauf(monkeypatch, capsys, "mcp__llm__complete", {"anbieter": "groq", "text": KUNDE}, NACH_STICHTAG) == {}
    assert _protokoll(heim) == []


def test_should_count_failures_as_fehler_not_silence(monkeypatch, capsys, heim):
    regeln = json.loads(BEISPIEL.read_text(encoding="utf-8"))
    regeln["kunden_muster"] = ["(kaputt"]
    kern.regeln_pfad().write_text(json.dumps(regeln), encoding="utf-8")
    aus = _lauf(monkeypatch, capsys, "mcp__llm__complete", {"anbieter": "groq", "text": KUNDE}, MELDETAG)
    assert "permissionDecision" not in aus["hookSpecificOutput"]
    assert "fehlgeschlagen" in aus["systemMessage"]
    assert [z["marker"] for z in _protokoll(heim)] == ["fehler"]
