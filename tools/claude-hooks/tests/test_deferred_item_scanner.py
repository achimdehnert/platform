"""Drill für deferred_item_scanner.py (KONZ-038 K4, Slug deferred-item-no-tracking-issue).

Treffer und Nicht-Treffer gleichberechtigt: ein Scanner, der bei „das können wir
später diskutieren" feuert, wird abgeschaltet und schützt dann gar nichts.
"""

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
    "deferred_item_scanner", _DIR / "deferred_item_scanner.py"
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


def _bash_record(cmd: str):
    return {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]
        },
    }


@pytest.mark.parametrize(
    "satz",
    [
        "Den Backfill habe ich bewusst ausgelassen.",
        "Das Migration-Cleanup ist nicht Teil dieses PRs.",
        "Den Refactor ziehe ich später nach.",
        "Die Härtung kommt in einem separaten PR.",
        "The cache fix is out of scope for this change.",
    ],
)
def test_should_vertagung_ohne_tracking_melden(monkeypatch, capsys, tmp_path, satz):
    rc, out = _run(monkeypatch, capsys, _transcript(tmp_path, satz))
    assert rc == 0
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "deferred-item" in ctx, f"Drill fehlgeschlagen für: {satz!r}"


@pytest.mark.parametrize(
    "satz",
    [
        "Das können wir später diskutieren.",
        "Der Punkt bleibt offen und steht im Board.",  # Status-Prosa, bewusst kein Treffer
        "Vielleicht später.",
        "Follow-up-Fragen beantworte ich gern.",
        "Die Tests laufen jetzt durch.",
    ],
)
def test_should_alltagsprosa_in_ruhe_lassen(monkeypatch, capsys, tmp_path, satz):
    rc, out = _run(monkeypatch, capsys, _transcript(tmp_path, satz))
    assert rc == 0
    assert out == {}, f"False Positive auf: {satz!r} → {out}"


def test_should_bei_issue_create_im_turn_still_sein(monkeypatch, capsys, tmp_path):
    p = _transcript(
        tmp_path,
        "Den Backfill habe ich bewusst ausgelassen und getrackt.",
        extra_records=[_bash_record("gh issue create --title 'Backfill nachziehen'")],
    )
    rc, out = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert out == {}, f"Tracking-Artefakt nicht erkannt: {out}"


def test_should_bei_konz_write_im_turn_still_sein(monkeypatch, capsys, tmp_path):
    write_rec = {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Write",
                    "input": {
                        "file_path": "docs/konzepte/KONZ-platform-038-x.md",
                        "content": "Ledger-Zeile",
                    },
                }
            ]
        },
    }
    p = _transcript(
        tmp_path, "Der Fleet-Rollout ist vertagt.", extra_records=[write_rec]
    )
    rc, out = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert out == {}


def test_should_im_continuation_turn_schweigen(monkeypatch, capsys, tmp_path):
    p = _transcript(tmp_path, "Der Backfill ist bewusst ausgelassen.")
    rc, out = _run(monkeypatch, capsys, p, stop_hook_active=True)
    assert rc == 0
    assert out == {}


# --- Retro 287b23 #6: verschieben-FN + MCP-Tracking-Kanal ------------------------


def test_should_verschieben_in_ich_form_melden(monkeypatch, capsys, tmp_path):
    rc, out = _run(
        monkeypatch,
        capsys,
        _transcript(tmp_path, "Das Cleanup verschiebe ich auf morgen."),
    )
    assert rc == 0
    assert "deferred-item" in out.get("hookSpecificOutput", {}).get(
        "additionalContext", ""
    )


def test_should_termin_verschiebung_in_ruhe_lassen(monkeypatch, capsys, tmp_path):
    rc, out = _run(
        monkeypatch,
        capsys,
        _transcript(tmp_path, "Der Termin wurde auf Dienstag verschoben."),
    )
    assert rc == 0
    assert out == {}, f"False Positive auf Termin-Prosa: {out}"


def test_should_mcp_issue_tool_als_tracking_erkennen(monkeypatch, capsys, tmp_path):
    mcp_rec = {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "mcp__github__create_issue",
                    "input": {"title": "Backfill nachziehen"},
                }
            ]
        },
    }
    p = _transcript(
        tmp_path, "Den Backfill habe ich bewusst ausgelassen.", extra_records=[mcp_rec]
    )
    rc, out = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert out == {}, f"MCP-Tracking-Kanal nicht erkannt: {out}"
