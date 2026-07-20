"""Tests für scripts/adr_open_pr_guard.py (Issue #997, T-13).

In-flight ADR-Nummern-Kollisionsguard (adr-guard.yml) — bisher 0 Tests trotz
realer Wirkung (fängt genau die ADR-221..227-Renumber-Kollision von 2026-05).
`main()` ruft `gh` direkt auf; hier wird die modul-lokale `gh()`-Funktion
gemonkeypatcht, damit KEIN echter `gh`-/Netz-Call stattfindet.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "adr_open_pr_guard.py"
_spec = importlib.util.spec_from_file_location("adr_open_pr_guard", _SCRIPT)
apg = importlib.util.module_from_spec(_spec)
sys.modules["adr_open_pr_guard"] = apg
_spec.loader.exec_module(apg)


class _FakeCompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _make_fake_gh(open_prs: list[int], views: dict[int, list[dict]], list_rc: int = 0):
    """Baut ein Fake für `gh(*args)`.

    ``views``: PR-Nummer -> Liste von {"path": "docs/adr/ADR-NNN-slug.md"}-Dicts
    (wie `gh pr view --json files` sie liefert).
    """

    def _fake_gh(*args: str) -> _FakeCompletedProcess:
        if args[0] == "pr" and args[1] == "list":
            if list_rc != 0:
                return _FakeCompletedProcess(returncode=list_rc, stderr="gh: not authenticated")
            payload = [{"number": n} for n in open_prs]
            return _FakeCompletedProcess(returncode=0, stdout=json.dumps(payload))
        if args[0] == "pr" and args[1] == "view":
            n = int(args[2])
            files = views.get(n, [])
            return _FakeCompletedProcess(returncode=0, stdout=json.dumps({"files": files}))
        raise AssertionError(f"unerwarteter gh-Aufruf: {args}")

    return _fake_gh


def test_should_skip_gracefully_without_pr_context(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("PR_NUMBER", raising=False)

    rc = apg.main()

    assert rc == 0
    assert "no PR context" in capsys.readouterr().out


def test_should_skip_gracefully_when_gh_unavailable(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "achimdehnert/platform")
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(apg, "gh", _make_fake_gh(open_prs=[], views={}, list_rc=1))

    rc = apg.main()

    assert rc == 0
    assert "gh unavailable" in capsys.readouterr().out


def test_should_pass_on_happy_path_no_collision(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "achimdehnert/platform")
    monkeypatch.setenv("PR_NUMBER", "42")
    fake_gh = _make_fake_gh(
        open_prs=[42, 43],
        views={
            42: [{"path": "docs/adr/ADR-300-first.md"}],
            43: [{"path": "docs/adr/ADR-301-second.md"}],
        },
    )
    monkeypatch.setattr(apg, "gh", fake_gh)

    rc = apg.main()

    assert rc == 0
    assert "no in-flight ADR-number collisions" in capsys.readouterr().out


def test_should_fail_on_in_flight_collision_analogous_to_adr265(monkeypatch, capsys):
    """Repro-analog zum ADR-265-Vorfall (2026-07-05): zwei offene PRs beanspruchen
    dieselbe Nummer mit UNTERSCHIEDLICHEN Slugs — echte Kollision, muss failen."""
    monkeypatch.setenv("GITHUB_REPOSITORY", "achimdehnert/platform")
    monkeypatch.setenv("PR_NUMBER", "42")
    fake_gh = _make_fake_gh(
        open_prs=[42, 43],
        views={
            42: [{"path": "docs/adr/ADR-300-first-slug.md"}],
            43: [{"path": "docs/adr/ADR-300-second-slug.md"}],
        },
    )
    monkeypatch.setattr(apg, "gh", fake_gh)

    rc = apg.main()

    out = capsys.readouterr().out
    assert rc == 1
    assert "::error::" in out
    assert "ADR-300" in out


def test_should_not_flag_same_file_edited_by_two_prs_as_collision(monkeypatch, capsys):
    """Zwei PRs editieren dieselbe existierende ADR-Datei (gleicher Dateiname) —
    das ist keine Kollision, nur paralleles Editieren."""
    monkeypatch.setenv("GITHUB_REPOSITORY", "achimdehnert/platform")
    monkeypatch.setenv("PR_NUMBER", "42")
    fake_gh = _make_fake_gh(
        open_prs=[42, 43],
        views={
            42: [{"path": "docs/adr/ADR-300-shared.md"}],
            43: [{"path": "docs/adr/ADR-300-shared.md"}],
        },
    )
    monkeypatch.setattr(apg, "gh", fake_gh)

    rc = apg.main()

    assert rc == 0
    assert "no in-flight ADR-number collisions" in capsys.readouterr().out


def test_should_not_fail_current_pr_when_collision_excludes_it(monkeypatch, capsys):
    """Kollision existiert zwischen PR 43/44, aber die aktuell laufende PR (42) ist
    nicht beteiligt — `main()` muss für PR 42 trotzdem grün (0) zurückgeben."""
    monkeypatch.setenv("GITHUB_REPOSITORY", "achimdehnert/platform")
    monkeypatch.setenv("PR_NUMBER", "42")
    fake_gh = _make_fake_gh(
        open_prs=[42, 43, 44],
        views={
            42: [{"path": "docs/adr/ADR-500-unrelated.md"}],
            43: [{"path": "docs/adr/ADR-300-first-slug.md"}],
            44: [{"path": "docs/adr/ADR-300-second-slug.md"}],
        },
    )
    monkeypatch.setattr(apg, "gh", fake_gh)

    rc = apg.main()

    assert rc == 0
