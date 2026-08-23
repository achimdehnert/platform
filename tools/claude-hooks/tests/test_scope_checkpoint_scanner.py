"""Drill fuer scope_checkpoint_scanner.py Rev 2 (Slug scope-checkpoint-not-durably-recorded).

Rev 2 hat die Richtung des Gates umgedreht: die Bedingung kommt aus
Tool-Evidenz, der Wortlaut ist nur noch die Erfuellung. Die Drills spiegeln
das — der wichtigste ist ``test_should_fire_when_third_repo_written_and_no
_checkpoint_spoken``: genau diese Fehlerform (x10 im Retro) war fuer Rev 1
strukturell unsichtbar.
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
    "scope_checkpoint_scanner", _DIR / "scope_checkpoint_scanner.py"
)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

import gate_hits  # noqa: E402  (haengt am sys.path oben)


@pytest.fixture(autouse=True)
def _isolieren(tmp_path, monkeypatch):
    """Protokoll UND Entprellungs-Merker isolieren.

    Ohne den zweiten Teil traegt der erste Drill den Merker in das echte
    /tmp und alle folgenden Drills derselben Session-ID sind still — der
    Drill wuerde sich selbst entwerten (dieselbe Klasse wie der
    Fixture-Leak, den Rev 1 am 2026-08-15 hatte).
    """
    monkeypatch.setattr(gate_hits, "HITS", tmp_path / "gate-hits.jsonl")
    monkeypatch.setattr(
        scanner, "_merker", lambda sid: tmp_path / f"merker_{sid or 'na'}.txt"
    )


def _zeile_text(text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _zeile_bash(cmd: str, cwd: str = "") -> dict:
    return {
        "type": "assistant",
        "cwd": cwd,
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Bash",
                    "id": "t1",
                    "input": {"command": cmd},
                }
            ]
        },
    }


def _zeile_edit(pfad: str) -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Edit",
                    "id": "t2",
                    "input": {"file_path": pfad},
                }
            ]
        },
    }


def _transcript(tmp_path, zeilen):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


def _run(monkeypatch, capsys, path, **event_extra):
    ev = {"transcript_path": str(path), "session_id": "drill", **event_extra}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(ev)))
    rc = scanner.main()
    out = capsys.readouterr().out.strip()
    return rc, (json.loads(out) if out else {})


def _kontext(antwort: dict) -> str:
    return antwort.get("hookSpecificOutput", {}).get("additionalContext", "")


DREI_REPOS = [
    _zeile_edit("/home/devuser/github/platform/docs/x.md"),
    _zeile_edit("/home/devuser/github/risk-hub/app/y.py"),
    _zeile_edit("/home/devuser/github/dev-hub/app/z.py"),
]


# --- Fehlerform A: die Luecke, fuer die Rev 1 blind war --------------------


def test_should_fire_when_third_repo_written_and_no_checkpoint_spoken(
    tmp_path, monkeypatch, capsys
):
    p = _transcript(tmp_path, [*DREI_REPOS, _zeile_text("So, fertig.")])
    rc, antwort = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert "Fehlerform A" in _kontext(antwort)
    assert "3 beschriebene Repos" in _kontext(antwort)


def test_should_fire_when_prod_step_ran_and_no_checkpoint_spoken(
    tmp_path, monkeypatch, capsys
):
    p = _transcript(
        tmp_path,
        [_zeile_bash("bash deploy.sh risk-hub"), _zeile_text("Deploy laeuft.")],
    )
    _, antwort = _run(monkeypatch, capsys, p)
    assert "Fehlerform A" in _kontext(antwort)
    assert "Prod-/Publish-Schritt" in _kontext(antwort)


def test_should_count_worktree_paths_as_repos(tmp_path, monkeypatch, capsys):
    """ADR-233-Worktrees sind der Normalfall — ohne sie waere das Gate blind."""
    zeilen = [
        _zeile_edit("/home/devuser/.repo-session/worktrees/platform/abc/docs/a.md"),
        _zeile_edit("/home/devuser/.repo-session/worktrees/mcp-hub/def/b.py"),
        _zeile_edit("/home/devuser/.repo-session/worktrees/risk-hub/ghi/c.py"),
        _zeile_text("fertig"),
    ]
    _, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert "mcp-hub" in _kontext(antwort)


# --- Fehlerform B: Rev-1-Verhalten, sitzungsweit ---------------------------


def test_should_fire_form_b_when_checkpoint_spoken_but_nothing_durable(
    tmp_path, monkeypatch, capsys
):
    zeilen = [*DREI_REPOS, _zeile_text("Scope-Checkpoint: ist das noch gewollt?")]
    _, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert "Fehlerform B" in _kontext(antwort)


def test_should_stay_silent_when_checkpoint_spoken_and_durably_recorded(
    tmp_path, monkeypatch, capsys
):
    zeilen = [
        *DREI_REPOS,
        _zeile_text("Scope-Checkpoint: ist das noch gewollt?"),
        _zeile_bash("gh issue comment 42 -b 'Checkpoint: Owner hat zugestimmt'"),
    ]
    rc, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert rc == 0
    assert antwort == {}


# --- Nicht-Ausloesen: die Fehlalarm-Seite ---------------------------------


def test_should_stay_silent_below_repo_threshold(tmp_path, monkeypatch, capsys):
    zeilen = [
        _zeile_edit("/home/devuser/github/platform/a.md"),
        _zeile_edit("/home/devuser/github/risk-hub/b.py"),
        _zeile_text("nur zwei Repos, kein Prod"),
    ]
    _, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert antwort == {}


def test_should_not_count_read_only_git_commands_as_write(
    tmp_path, monkeypatch, capsys
):
    """`git status` in drei Repos ist keine Scope-Eskalation."""
    zeilen = [
        _zeile_bash("git status", cwd="/home/devuser/github/platform"),
        _zeile_bash("git log --oneline -5", cwd="/home/devuser/github/risk-hub"),
        _zeile_bash("git diff", cwd="/home/devuser/github/dev-hub"),
        _zeile_text("nur gelesen"),
    ]
    _, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert antwort == {}


def test_should_stay_silent_when_stop_hook_active(tmp_path, monkeypatch, capsys):
    p = _transcript(tmp_path, [*DREI_REPOS, _zeile_text("fertig")])
    _, antwort = _run(monkeypatch, capsys, p, stop_hook_active=True)
    assert antwort == {}


# --- Entprellung -----------------------------------------------------------


def test_should_report_each_failure_form_only_once_per_session(
    tmp_path, monkeypatch, capsys
):
    p = _transcript(tmp_path, [*DREI_REPOS, _zeile_text("fertig")])
    _, erste = _run(monkeypatch, capsys, p)
    _, zweite = _run(monkeypatch, capsys, p)
    assert "Fehlerform A" in _kontext(erste)
    assert zweite == {}


def test_should_not_accept_durable_artifact_written_before_the_checkpoint(
    tmp_path, monkeypatch, capsys
):
    """Ein frueherer docs/-Edit belegt den spaeteren Checkpoint nicht.

    Ohne die Reihenfolge-Kopplung war Fehlerform B praktisch tot: fast jede
    Sitzung fasst irgendwann eine Datei unter `docs/` an. Gefunden vom
    eigenen Drill am 2026-08-19, nicht im Review.
    """
    zeilen = [
        _zeile_edit("/home/devuser/github/platform/docs/frueher.md"),
        _zeile_edit("/home/devuser/github/risk-hub/app/y.py"),
        _zeile_edit("/home/devuser/github/dev-hub/app/z.py"),
        _zeile_text("Scope-Checkpoint: ist das noch gewollt?"),
    ]
    _, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert "Fehlerform B" in _kontext(antwort)


# ── Rev 3: Reichweite steht in der Wirkung, nicht in den Argumenten ──────────


def _zeile_bash_id(cmd: str, tid: str, cwd: str = "") -> dict:
    return {
        "type": "assistant",
        "cwd": cwd,
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Bash",
                    "id": tid,
                    "input": {"command": cmd},
                }
            ]
        },
    }


def _zeile_ergebnis(tid: str, text: str) -> dict:
    return {
        "type": "user",
        "message": {
            "content": [{"type": "tool_result", "tool_use_id": tid, "content": text}]
        },
    }


#: So sieht die Ausgabe des Arbeitsbaum-Reapers aus — ein Aufruf, viele Repos.
REAPER_AUSGABE = (
    "entfernt: /home/devuser/.repo-session/worktrees/platform/2026-08-20-a-b + Lease geschlossen\n"
    "entfernt: /home/devuser/.repo-session/worktrees/risk-hub/2026-08-19-c-d + Lease geschlossen\n"
    "entfernt: /home/devuser/.repo-session/worktrees/dev-hub/2026-08-18-e-f + Lease geschlossen\n"
)


def test_should_flottenlauf_ueber_die_ausgabe_zaehlen(tmp_path, monkeypatch, capsys):
    """Der Rueckfall aus Retro 8d6869-incr #8, nachgestellt.

    Ein Kommando, ein Pfad im Aufruf — und 69 entfernte Arbeitskopien ueber die
    ganze Flotte. Rev 2 sah ein Repo und schwieg.
    """
    zeilen = [
        _zeile_bash_id(
            "python3 ~/github/platform/tools/worktree-reaper.py --apply --karenz-stunden 0",
            "reap1",
        ),
        _zeile_ergebnis("reap1", REAPER_AUSGABE),
    ]
    rc, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert rc == 0
    assert _kontext(antwort), "Flottenlauf blieb unter der Schwelle"


def test_should_lesendes_kommando_nicht_zaehlen(tmp_path, monkeypatch, capsys):
    """Gegenprobe: dieselbe Ausgabe, nur gelesen.

    Ein `grep -rn ~/github/` nennt dieselben Pfade und fasst nichts an. Ohne
    diese Trennung wuerde jede Suche ueber die Flotte einen Checkpoint fordern —
    und das Gate waere binnen einer Sitzung Rauschen.
    """
    zeilen = [
        _zeile_bash_id("grep -rn 'worktrees' /home/devuser/.repo-session/", "les1"),
        _zeile_ergebnis("les1", REAPER_AUSGABE),
    ]
    rc, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert rc == 0
    assert not _kontext(antwort)


def test_should_fremdes_ergebnis_nicht_zuordnen(tmp_path, monkeypatch, capsys):
    """Ein Ergebnis ohne passendes schreibendes Kommando zaehlt nicht.

    Die Zuordnung laeuft ueber `tool_use_id`. Faellt sie weg, zaehlt jede
    Ausgabe irgendeines Tools — dann misst das Gate wieder Erwaehnungen.
    """
    zeilen = [_zeile_ergebnis("gibt-es-nicht", REAPER_AUSGABE)]
    rc, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert rc == 0
    assert not _kontext(antwort)


def test_should_ergebnis_als_bloecke_lesen(tmp_path, monkeypatch, capsys):
    """`content` kommt je nach Client als String ODER als Block-Liste."""
    zeilen = [
        _zeile_bash_id(
            "bash ~/github/platform/tools/repo-session.sh reap --alle", "r2"
        ),
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "r2",
                        "content": [{"type": "text", "text": REAPER_AUSGABE}],
                    }
                ]
            },
        },
    ]
    rc, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert rc == 0
    assert _kontext(antwort)


def test_should_lange_ausgabe_beschneiden():
    """Kostenbremse: nur der Anfang der Ausgabe wird abgesucht."""
    text = "x" * (scanner._AUSGABE_MAX + 500) + "/home/devuser/github/spaet-hub/x"
    assert "spaet-hub" not in scanner._repos_aus_ausgabe(text)
