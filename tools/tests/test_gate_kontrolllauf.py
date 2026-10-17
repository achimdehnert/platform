"""Tests fuer tools/gate_kontrolllauf.py (platform#4061, Retro 835f30 Befund 1).

Der Probe-Hook schreibt wie ein echter Hook ueber `GATE_HITS_DATEI`. Geprueft
wird, dass ein Kontrolllauf nie ins Protokoll des Aufrufers schreibt — auch
wenn dessen Umgebung schon auf das echte Log zeigt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gate_kontrolllauf as gk  # noqa: E402

PROBE_HOOK = """
import json, os, sys
json.load(sys.stdin)
with open(os.environ["GATE_HITS_DATEI"], "a") as f:
    f.write(json.dumps({"slug": "probe-gate", "marker": "treffer", "modus": "blocking"}) + "\\n")
print(json.dumps({"hookSpecificOutput": {"permissionDecision": "deny"}}))
sys.exit(2)
"""


def _hook(tmp_path: Path) -> Path:
    pfad = tmp_path / "probe_hook.py"
    pfad.write_text(PROBE_HOOK, encoding="utf-8")
    return pfad


def test_should_not_write_to_callers_gate_log(tmp_path, monkeypatch, capsys):
    echtes_log = tmp_path / "echt" / "gate-hits.jsonl"
    echtes_log.parent.mkdir()
    echtes_log.write_text("", encoding="utf-8")
    monkeypatch.setenv(gk.ENV_PROTOKOLL, str(echtes_log))
    eingabe = tmp_path / "eingabe.json"
    eingabe.write_text(json.dumps({"tool_name": "Bash"}), encoding="utf-8")

    assert gk.main([str(_hook(tmp_path)), "--eingabe", str(eingabe)]) == 2
    assert echtes_log.read_text(encoding="utf-8") == ""


def test_should_report_hook_output_and_log_lines(tmp_path, capsys):
    lauf, zeilen = gk.kontrolllauf(_hook(tmp_path), json.dumps({"tool_name": "Bash"}))
    assert '"deny"' in lauf.stdout
    assert [(z["slug"], z["marker"], z["modus"]) for z in zeilen] == [
        ("probe-gate", "treffer", "blocking")
    ]
