"""Drill für scope_checkpoint_scanner.py (KONZ-038 K4, Slug scope-checkpoint-not-durably-recorded)."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location(
    "scope_checkpoint_scanner", _DIR / "scope_checkpoint_scanner.py"
)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)


def _transcript(tmp_path, assistant_text: str, extra_records=()):
    p = tmp_path / "t.jsonl"
    zeilen = [
        {"type": "user", "message": {"content": "mach mal"}},
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": assistant_text}]},
        },
        *extra_records,
    ]
    p.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


def _run(monkeypatch, capsys, path, **event_extra):
    ev = {"transcript_path": str(path), **event_extra}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(ev)))
    rc = scanner.main()
    out = capsys.readouterr().out.strip()
    return rc, (json.loads(out) if out else {})


@pytest.mark.parametrize(
    "satz",
    [
        "Scope-Checkpoint: Wir sind jetzt 3 Repos von deiner ursprünglichen Frage entfernt — ist das noch gewollt?",
        "Damit berühren wir ein drittes Repo.",
        "Wir erreichen jetzt einen Prod-Schritt, ich halte inne.",
        "Der Scope ist gewachsen: aus einem Fix wurden vier Baustellen.",
    ],
)
def test_should_checkpoint_ohne_artefakt_melden(monkeypatch, capsys, tmp_path, satz):
    rc, out = _run(monkeypatch, capsys, _transcript(tmp_path, satz))
    assert rc == 0
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "scope-checkpoint" in ctx, f"Drill fehlgeschlagen für: {satz!r}"


@pytest.mark.parametrize(
    "satz",
    [
        "Ich habe das Repo geklont und die Tests laufen.",
        "Das dritte Kapitel der Doku ist fertig.",
        "Prod läuft stabil, keine Auffälligkeiten.",
        "Die ursprüngliche Frage war nach dem Format.",
    ],
)
def test_should_normale_prosa_in_ruhe_lassen(monkeypatch, capsys, tmp_path, satz):
    rc, out = _run(monkeypatch, capsys, _transcript(tmp_path, satz))
    assert rc == 0
    assert out == {}, f"False Positive auf: {satz!r} → {out}"


def test_should_bei_pr_kommentar_im_turn_still_sein(monkeypatch, capsys, tmp_path):
    bash_rec = {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Bash",
                    "input": {
                        "command": "gh pr comment 42 --body 'Scope-Checkpoint: ...'"
                    },
                }
            ]
        },
    }
    p = _transcript(
        tmp_path,
        "Scope-Checkpoint: drittes Repo berührt — ist das noch gewollt?",
        extra_records=[bash_rec],
    )
    rc, out = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert out == {}, f"Durables Artefakt nicht erkannt: {out}"


def test_should_bei_doku_write_im_turn_still_sein(monkeypatch, capsys, tmp_path):
    write_rec = {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Write",
                    "input": {
                        "file_path": "docs/konzepte/KONZ-platform-038.md",
                        "content": "Checkpoint-Ergebnis",
                    },
                }
            ]
        },
    }
    p = _transcript(
        tmp_path, "Scope-Checkpoint: Prod-Schritt erreicht.", extra_records=[write_rec]
    )
    rc, out = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert out == {}


def test_should_im_continuation_turn_schweigen(monkeypatch, capsys, tmp_path):
    p = _transcript(tmp_path, "Scope-Checkpoint: drittes Repo.")
    rc, out = _run(monkeypatch, capsys, p, stop_hook_active=True)
    assert rc == 0
    assert out == {}
