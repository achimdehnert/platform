"""Drill für session_modellmix.py (#2750 K1, Slug fable-session-delegation-unmeasured).

Fixture: Haupt-Transkript mit drei claude-fable-5-1-Nachrichten (eine davon
delegiert per `Agent`-Tool, eine ohne `usage`, dazwischen eine kaputte JSON-
Zeile) plus ein Subagenten-Transkript mit zwei claude-sonnet-5-Nachrichten
(`Edit` + `Bash`, beide schreibend). Vorgerechnet:
  fable:  output=100  gesamt=250  schreibend=0
  sonnet: output=150  gesamt=300  schreibend=2
  total:  output=250  gesamt=550  schreibend=2
  anteil_tokens_nicht_hauptmodell        = 300/550*100 = 54.5
  anteil_schreibaufrufe_nicht_hauptmodell = 2/2*100     = 100.0
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "session_modellmix.py"


def _fable_records():
    return [
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "model": "claude-fable-5-1",
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                    "content": [
                        {"type": "text", "text": "delegiere"},
                        {"type": "tool_use", "name": "Agent", "input": {}},
                    ],
                },
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "model": "claude-fable-5-1",
                    "usage": {"input_tokens": 50, "output_tokens": 50},
                    "content": [{"type": "tool_use", "name": "Read", "input": {}}],
                },
            }
        ),
        "{kaputt json ohne schluss",
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "model": "claude-fable-5-1",
                    "content": [],
                },
            }
        ),
    ]


def _sonnet_records():
    return [
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 100, "output_tokens": 100},
                    "content": [{"type": "tool_use", "name": "Edit", "input": {}}],
                },
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 50, "output_tokens": 50},
                    "content": [{"type": "tool_use", "name": "Bash", "input": {}}],
                },
            }
        ),
    ]


def _write_session(tmp_path: Path, session_id: str, with_subagent: bool = True) -> Path:
    main_path = tmp_path / f"{session_id}.jsonl"
    main_path.write_text("\n".join(_fable_records()) + "\n", encoding="utf-8")
    if with_subagent:
        sub_dir = tmp_path / session_id / "subagents"
        sub_dir.mkdir(parents=True)
        (sub_dir / "agent-1.jsonl").write_text(
            "\n".join(_sonnet_records()) + "\n", encoding="utf-8"
        )
    return main_path


def _run(args, input_text: str | None = None, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        check=False,
    )


def test_should_anteile_laut_fixture_stimmen(tmp_path):
    main_path = _write_session(tmp_path, "sess-abc123")
    r = _run([str(main_path), "--json"])
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["hauptmodell"] == "claude-fable-5-1"
    assert data["anteil_tokens_nicht_hauptmodell"] == 54.5
    assert data["anteil_schreibaufrufe_nicht_hauptmodell"] == 100.0
    assert data["n_subagenten"] == 1


def test_should_positivkontrolle_submodell_100_prozent_schreibend(tmp_path):
    """Belegt: die 100.0 kommt vom echten Sub-Modell-Anteil, nicht vom Filter."""
    main_path = _write_session(tmp_path, "sess-posctrl")
    r = _run([str(main_path), "--json"])
    data = json.loads(r.stdout)
    assert data["modelle"]["claude-sonnet-5"]["schreibend"] == 2
    assert data["modelle"]["claude-fable-5-1"]["schreibend"] == 0
    assert data["anteil_schreibaufrufe_nicht_hauptmodell"] == 100.0
    assert data["gesamt_tokens"] == 550


def test_should_zweimal_ausfuehren_byte_identisch_sein(tmp_path):
    main_path = _write_session(tmp_path, "sess-repeat")
    r1 = _run([str(main_path), "--json"])
    r2 = _run([str(main_path), "--json"])
    assert r1.returncode == 0 and r2.returncode == 0
    assert r1.stdout == r2.stdout


def test_should_ohne_subagents_verzeichnis_null_anteile_liefern(tmp_path):
    main_path = _write_session(tmp_path, "sess-nosub", with_subagent=False)
    r = _run([str(main_path), "--json"])
    data = json.loads(r.stdout)
    assert r.returncode == 0
    assert data["n_subagenten"] == 0
    assert data["anteil_tokens_nicht_hauptmodell"] == 0.0
    assert data["anteil_schreibaufrufe_nicht_hauptmodell"] == 0.0


def test_should_hook_modus_genau_eine_zeile_anhaengen_dann_zwei(tmp_path):
    main_path = _write_session(tmp_path, "sess-ledger12345")
    ledger = tmp_path / "ledger.tsv"
    event = json.dumps(
        {"transcript_path": str(main_path), "session_id": "sess-ledger12345"}
    )
    env = {"MODELLMIX_LEDGER": str(ledger), "PATH": "/usr/bin:/bin"}
    r1 = _run(["--hook"], input_text=event, env=env)
    r2 = _run(["--hook"], input_text=event, env=env)
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert r1.returncode == 0 and r2.returncode == 0
    assert lines[0].startswith("datum_iso\t")
    assert len(lines) == 3
    assert lines.count(lines[0]) == 1


def test_should_hook_modus_kaputtes_stdin_exit_0_liefern(tmp_path):
    r = _run(["--hook"], input_text="das ist kein json")
    assert r.returncode == 0


def test_should_hook_modus_fehlendes_transkript_exit_0_liefern(tmp_path):
    event = json.dumps(
        {"transcript_path": str(tmp_path / "nicht-da.jsonl"), "session_id": "x"}
    )
    r = _run(["--hook"], input_text=event)
    assert r.returncode == 0


def test_should_cli_modus_unbekannte_session_exit_2_liefern(tmp_path):
    r = _run(["unbekannte-session-id", "--projects-dir", str(tmp_path)])
    assert r.returncode == 2
