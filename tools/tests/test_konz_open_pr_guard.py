"""Tests für scripts/konz_open_pr_guard.py (K1 aus platform#1944).

Spiegelt test_adr_open_pr_guard.py. `main()` ruft `gh` direkt auf; hier wird die
modul-lokale `gh()`-Funktion gemonkeypatcht, damit KEIN echter `gh`-/Netz-Call
stattfindet.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "konz_open_pr_guard.py"
_spec = importlib.util.spec_from_file_location("konz_open_pr_guard", _SCRIPT)
kpg = importlib.util.module_from_spec(_spec)
sys.modules["konz_open_pr_guard"] = kpg
_spec.loader.exec_module(kpg)


class _FakeCompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _make_fake_gh(open_prs: list[int], views: dict[int, list[dict]], list_rc: int = 0):
    def _fake_gh(*args: str) -> _FakeCompletedProcess:
        if args[0] == "pr" and args[1] == "list":
            if list_rc != 0:
                return _FakeCompletedProcess(
                    returncode=list_rc, stderr="gh: not authenticated"
                )
            payload = [{"number": n} for n in open_prs]
            return _FakeCompletedProcess(returncode=0, stdout=json.dumps(payload))
        if args[0] == "pr" and args[1] == "view":
            files = views.get(int(args[2]), [])
            return _FakeCompletedProcess(
                returncode=0, stdout=json.dumps({"files": files})
            )
        raise AssertionError(f"unerwarteter gh-Aufruf: {args}")

    return _fake_gh


def _p(path: str) -> dict:
    return {"path": path}


# --- claims_from_files ------------------------------------------------------


def test_should_extract_number_and_filename_from_konz_path():
    claims = kpg.claims_from_files(["docs/konzepte/KONZ-platform-043-formatsatz.md"])
    assert claims == {43: "KONZ-platform-043-formatsatz.md"}


def test_should_ignore_paths_that_are_not_konz_documents():
    assert kpg.claims_from_files(["docs/adr/ADR-300-x.md", "tools/y.py"]) == {}


# --- main -------------------------------------------------------------------


def test_should_skip_gracefully_without_pr_context(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("PR_NUMBER", raising=False)

    assert kpg.main() == 0
    assert "no PR context" in capsys.readouterr().out


def test_should_skip_gracefully_when_gh_unavailable(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "achimdehnert/platform")
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(kpg, "gh", _make_fake_gh(open_prs=[], views={}, list_rc=1))

    assert kpg.main() == 0
    assert "gh unavailable" in capsys.readouterr().out


def test_should_pass_when_open_prs_claim_distinct_numbers(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "achimdehnert/platform")
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(
        kpg,
        "gh",
        _make_fake_gh(
            open_prs=[42, 43],
            views={
                42: [_p("docs/konzepte/KONZ-platform-044-a.md")],
                43: [_p("docs/konzepte/KONZ-platform-045-b.md")],
            },
        ),
    )

    assert kpg.main() == 0
    assert "no in-flight KONZ-number collisions" in capsys.readouterr().out


def test_should_fail_on_the_real_konz043_collision(monkeypatch, capsys):
    """Regressionsfall 2026-08-12: PR #1942 (`konz-formatsatz`) und #1934
    (`konz043-activity-intelligence`) beanspruchten beide die 043 mit
    verschiedenem Slug. Ohne diesen Guard lief das durch.

    Die zweite Datei heisst hier bewusst NICHT wie im Original
    (`...-mail-activity-intelligence.md`): dieser Pfad existiert real auf `main`,
    und ein real existierender Pfad in einem Test zieht ihn in den
    CI-Trigger-Filter von `tools-tests.yml` (siehe
    test_ci_trigger_covers_test_inputs.py). Der Guard prueft die Nummer, nicht
    den Slug — die Aussagekraft des Falls bleibt damit unveraendert."""
    monkeypatch.setenv("GITHUB_REPOSITORY", "achimdehnert/platform")
    monkeypatch.setenv("PR_NUMBER", "1942")
    monkeypatch.setattr(
        kpg,
        "gh",
        _make_fake_gh(
            open_prs=[1942, 1934],
            views={
                1942: [_p("docs/konzepte/KONZ-platform-043-formatsatz-paket.md")],
                1934: [_p("docs/konzepte/KONZ-platform-043-activity-intelligence.md")],
            },
        ),
    )

    rc = kpg.main()
    out = capsys.readouterr().out

    assert rc == 1
    assert "::error::" in out
    assert "KONZ-platform-043" in out
    assert "formatsatz-paket" in out


def test_should_not_flag_two_prs_editing_the_same_konz_file(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "achimdehnert/platform")
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(
        kpg,
        "gh",
        _make_fake_gh(
            open_prs=[42, 43],
            views={
                42: [_p("docs/konzepte/KONZ-platform-041-shared.md")],
                43: [_p("docs/konzepte/KONZ-platform-041-shared.md")],
            },
        ),
    )

    assert kpg.main() == 0
    assert "no in-flight KONZ-number collisions" in capsys.readouterr().out


def test_should_stay_green_when_collision_does_not_involve_current_pr(
    monkeypatch, capsys
):
    monkeypatch.setenv("GITHUB_REPOSITORY", "achimdehnert/platform")
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(
        kpg,
        "gh",
        _make_fake_gh(
            open_prs=[42, 43, 44],
            views={
                42: [_p("docs/konzepte/KONZ-platform-050-unrelated.md")],
                43: [_p("docs/konzepte/KONZ-platform-043-a.md")],
                44: [_p("docs/konzepte/KONZ-platform-043-b.md")],
            },
        ),
    )

    assert kpg.main() == 0
