"""Drill fuer den Hinweis-Hook `issue_anlegen_dubletten_hinweis.py` (Gate issue-ohne-dublettensuche).

Anlass: Retro ec3416 Befund 11 — iilgmbh/shared-ci#113 wurde zum selben 0-Jobs-Lauf
angelegt wie #112 (andere Sitzung, 34 min frueher), ohne Suche im Zielrepo.

`gh` wird durch ein Fake-Skript im PATH ersetzt, das die Suchanfrage protokolliert und
eine JSON-Fixture ausgibt; das Git-Repo ist ein Wegwerf-Repo mit origin-URL. Kein Netz.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "issue_anlegen_dubletten_hinweis.py"
RUN_ID = "38532968320"
REALFALL = (
    "gh issue create -R example-org/shared-ci "
    f"--title 'v1.1.27: _ci-python.yml scheitert ohne Jobs (Lauf {RUN_ID})' "
    "--body 'Lauf ohne Jobs nach dem Tag-Bump.'"
)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def _repo(
    tmp_path: Path, remote: str = "git@github.com:example-org/example-repo.git"
) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "remote", "add", "origin", remote)
    return repo


def _fake_gh(tmp_path: Path, issues: list[dict] | None, exit_code: int = 0) -> Path:
    """PATH-Verzeichnis mit einem `gh`, das die Fixture druckt und seine Argumente mitschreibt."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fixture = tmp_path / "issues.json"
    fixture.write_text(json.dumps(issues or []), encoding="utf-8")
    protokoll = tmp_path / "gh-aufrufe.log"
    skript = bin_dir / "gh"
    skript.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{protokoll}"\n'
        f'if [ {exit_code} -ne 0 ]; then echo "API rate limit exceeded" >&2; exit {exit_code}; fi\n'
        f'cat "{fixture}"\n',
        encoding="utf-8",
    )
    skript.chmod(skript.stat().st_mode | stat.S_IXUSR)
    return bin_dir


def _aufrufe(tmp_path: Path) -> str:
    pfad = tmp_path / "gh-aufrufe.log"
    return pfad.read_text(encoding="utf-8") if pfad.exists() else ""


def _lauf(repo: Path, bin_dir: Path, kommando: str):
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_input": {"command": kommando}, "cwd": str(repo)}),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def _kontext(res) -> str:
    if not res.stdout.strip():
        return ""
    return json.loads(res.stdout)["hookSpecificOutput"]["additionalContext"]


def _issue(nummer: int, titel: str, state: str = "OPEN") -> dict:
    return {
        "number": nummer,
        "title": titel,
        "state": state,
        "updatedAt": "2026-10-14T14:43:00Z",
    }


# --- Positivkontrollen ------------------------------------------------------


def test_should_hinweis_zeigen_beim_realfall_shared_ci_112(tmp_path):
    """Form von shared-ci#113: dasselbe Symptom liegt als #112 schon vor — Treffer per Run-ID."""
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(
        tmp_path,
        [_issue(112, f"v1.1.27 bricht Nicht-PR-Laeufe mit 0 Jobs (Lauf {RUN_ID})")],
    )
    res = _lauf(repo, bin_dir, REALFALL)
    assert res.returncode == 0
    text = _kontext(res)
    assert "#112" in text
    assert RUN_ID in text
    assert "Konsumenten-Repos" in text  # Zielrepo heisst shared-ci
    assert f'"{RUN_ID}"' in _aufrufe(tmp_path)  # exakter Marker, nicht Titelwoerter


def test_should_mit_titelwoertern_suchen_wenn_kein_marker(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(
        tmp_path, [_issue(7, "Deploy-Melder liest Jobstatus falsch", "CLOSED")]
    )
    res = _lauf(
        repo,
        bin_dir,
        "gh issue create --title 'Deploy-Melder meldet gruen bei leerem Jobstatus' --body 'x'",
    )
    text = _kontext(res)
    assert "#7 [closed]" in text
    aufrufe = _aufrufe(tmp_path)
    assert "-R example-org/example-repo" in aufrufe  # Repo aus origin
    assert "Deploy-Melder" in aufrufe and "Jobstatus" in aufrufe
    assert "--state all" in aufrufe


def test_should_body_datei_mit_lesen(tmp_path):
    repo = _repo(tmp_path)
    body = tmp_path / "body.md"
    body.write_text(f"Siehe Lauf {RUN_ID}.", encoding="utf-8")
    bin_dir = _fake_gh(tmp_path, [_issue(3, "Lauf ohne Jobs")])
    res = _lauf(
        repo, bin_dir, f"gh issue create --title 'Neuer Befund' --body-file {body}"
    )
    assert "#3" in _kontext(res)
    assert RUN_ID in _aufrufe(tmp_path)


# --- Gegenproben ------------------------------------------------------------


def test_should_schweigen_ohne_treffer(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, [])
    res = _lauf(repo, bin_dir, REALFALL)
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_should_schweigen_wenn_suche_schon_im_kommando_steht(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, [_issue(112, "Dublette")])
    res = _lauf(
        repo,
        bin_dir,
        f"gh issue list -R example-org/shared-ci --search '{RUN_ID}' --state all; {REALFALL}",
    )
    assert res.stdout.strip() == ""
    assert _aufrufe(tmp_path) == ""


def test_should_andere_kommandos_ignorieren(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, [_issue(1, "x")])
    res = _lauf(
        repo, bin_dir, "gh issue comment 5 --body 'ok' && gh pr create --title t"
    )
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_should_fail_open_bei_gh_fehler(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, None, exit_code=1)
    res = _lauf(repo, bin_dir, REALFALL)
    assert res.returncode == 0
    assert "nicht pruefbar" in _kontext(res)


def test_should_fail_open_ohne_json(tmp_path):
    bin_dir = _fake_gh(tmp_path, [])
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    res = subprocess.run(
        [sys.executable, str(HOOK)],
        input="kein json",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_should_suchbegriffe_marker_vor_woertern_waehlen():
    sys.path.insert(0, str(HOOK.parent))
    import issue_anlegen_dubletten_hinweis as modul

    assert modul.suchbegriffe(f"Lauf {RUN_ID} rot", "siehe owner/repo#630") == [
        RUN_ID,
        "#630",
    ]
    woerter = modul.suchbegriffe(
        "Dependabot-PRs sind rot, weil ihnen Secrets fehlen", ""
    )
    assert woerter[0] == "Dependabot-PRs"
    assert "weil" not in woerter and len(woerter) <= modul.MAX_SUCHWOERTER
    assert modul.suchbegriffe("kurz", "") == []
