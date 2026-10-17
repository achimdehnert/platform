"""Drill fuer kuerzel_ohne_gegenzeile_scanner.py (Slug kuerzel-ohne-artefakt-bezug).

Realfall (Retro 835f30 Befund 18, platform#4062): „MA go“ und „FR go“ blieben
ohne Zeile in Issue, PR oder Memory, bis ein Nachtrag sie einsammelte.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location(
    "kuerzel_ohne_gegenzeile_scanner", _DIR / "kuerzel_ohne_gegenzeile_scanner.py"
)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

MODUL = _DIR / "kuerzel_ohne_gegenzeile_scanner.py"
MEMORY = "/home/x/.claude/projects/-home-x-github-platform/memory/feedback_x.md"


def _owner(text: str) -> dict:
    return {"type": "user", "origin": {"kind": "human"}, "message": {"content": text}}


def _werkzeug(name: str, eingabe: dict) -> dict:
    return {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": name, "input": eingabe}]},
    }


def _bash(befehl: str) -> dict:
    return _werkzeug("Bash", {"command": befehl})


# --- Positive Faelle --------------------------------------------------------


def test_should_flag_kuerzel_without_any_artifact_write() -> None:
    """Der Realfall: „MA go“, danach nur Arbeit, keine Gegenzeile."""
    eintraege = [_owner("MA go"), _bash("make test")]
    assert scanner.offene_kuerzel(eintraege) == ["MA"]


def test_should_flag_only_the_kuerzel_missing_from_the_artifact() -> None:
    eintraege = [
        _owner("Z6 go ; Z7 go ; Z10 go"),
        _werkzeug("Write", {"file_path": MEMORY, "content": "Owner-Wort „Z6 go“"}),
    ]
    assert scanner.offene_kuerzel(eintraege) == ["Z7", "Z10"]


def test_should_flag_kuerzel_named_only_in_a_scratch_file() -> None:
    """Eine Datei, die nie per gh hinausgeht, ist kein Artefakt."""
    eintraege = [
        _owner("FR go"),
        _werkzeug("Write", {"file_path": "/tmp/notiz.md", "content": "FR go erledigt"}),
    ]
    assert scanner.offene_kuerzel(eintraege) == ["FR"]


def test_should_not_count_z1_as_z10() -> None:
    """Wortgrenze: Z1 in der Zeile deckt Z10 nicht."""
    eintraege = [_owner("Z10 go"), _bash("gh issue comment 1 --body 'Z1 go umgesetzt'")]
    assert scanner.offene_kuerzel(eintraege) == ["Z10"]


# --- Negative Faelle --------------------------------------------------------


def test_should_not_flag_when_gh_comment_names_kuerzel() -> None:
    eintraege = [_owner("RT go"), _bash("gh issue comment 4 --body 'Owner „RT go“'")]
    assert scanner.offene_kuerzel(eintraege) == []


def test_should_not_flag_when_body_file_written_before_names_kuerzel() -> None:
    eintraege = [
        _owner("GZ go"),
        _werkzeug("Write", {"file_path": "/tmp/s/kommentar_gz.md", "content": "GZ go"}),
        _bash("gh pr comment 7 --body-file /tmp/s/kommentar_gz.md"),
    ]
    assert scanner.offene_kuerzel(eintraege) == []


def test_should_not_flag_when_memory_appended_via_shell() -> None:
    """Realfall 835f30 „VT go“: Memory per `printf … >>` ergaenzt."""
    eintraege = [_owner("VT go"), _bash(f"printf 'Owner „VT go“' >> {MEMORY}")]
    assert scanner.offene_kuerzel(eintraege) == []


def test_should_not_flag_when_mcp_tool_names_kuerzel() -> None:
    eintraege = [
        _owner("AL go"),
        _werkzeug("mcp__github__add_issue_comment", {"body": "AL go, 2026-10-17"}),
    ]
    assert scanner.offene_kuerzel(eintraege) == []


def test_should_only_judge_the_last_owner_message() -> None:
    """Aeltere Zuege sind vorbei und werden nicht jeden Turn neu gemeldet."""
    eintraege = [_owner("MA go"), _bash("make test"), _owner("danke")]
    assert scanner.offene_kuerzel(eintraege) == []


def test_should_ignore_injected_and_tool_result_messages() -> None:
    eintraege = [
        _owner("<system-reminder>XY go</system-reminder> weiter"),
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "AB go"}]}},
    ]
    assert scanner.offene_kuerzel(eintraege) == []


def test_should_ignore_lowercase_and_plain_go() -> None:
    assert scanner.offene_kuerzel([_owner("go, mach weiter"), _bash("ls")]) == []


# --- Hook-Vertrag -----------------------------------------------------------


def _lauf(tmp_path: Path, eintraege: list[dict], **env) -> subprocess.CompletedProcess:
    transkript = tmp_path / "t.jsonl"
    transkript.write_text("\n".join(json.dumps(e) for e in eintraege), encoding="utf-8")
    umgebung = {"GATE_HITS_DATEI": str(tmp_path / "hits.jsonl"), "PATH": "/usr/bin:/bin"}
    umgebung.update(env)
    return subprocess.run(
        [sys.executable, str(MODUL)],
        input=json.dumps({"transcript_path": str(transkript), "session_id": "t"}),
        capture_output=True,
        text=True,
        timeout=30,
        env=umgebung,
    )


def test_should_exit_zero_and_report_on_stderr(tmp_path: Path) -> None:
    res = _lauf(tmp_path, [_owner("MA go"), _bash("make test")])
    assert res.returncode == 0
    assert "kuerzel-ohne-artefakt-bezug" in res.stderr
    assert "MA go" in (tmp_path / "hits.jsonl").read_text(encoding="utf-8")


def test_should_stay_silent_with_switch_off(tmp_path: Path) -> None:
    res = _lauf(tmp_path, [_owner("MA go")], KUERZEL_GATE="aus")
    assert res.returncode == 0
    assert res.stderr == ""


def test_should_exit_zero_on_empty_stdin() -> None:
    res = subprocess.run(
        [sys.executable, str(MODUL)], input="{}", capture_output=True, text=True, timeout=30
    )
    assert res.returncode == 0
