"""Drill fuer den Hinweis-Hook `pr_anlegen_kollision_hinweis.py` (Gate parallel-session-pr-collision).

Anlass: platform#3722, Vorschlag G5. Beide Kollisionen seit dem Umbau (gleiche Datei,
gleiches Issue ohne Querverweis) entstanden NACH dem Sitzungsstart — dort zeigte
`repo-session.sh` die Liste offener PRs, aber nicht mehr beim Anlegen.

`gh` wird durch ein Fake-Skript im PATH ersetzt, das eine JSON-Fixture ausgibt; das
Git-Repo ist ein Wegwerf-Repo mit `origin/main`-Ref. Kein Netz, kein echtes GitHub.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "pr_anlegen_kollision_hinweis.py"
ANLEGEN = (
    "gh pr create -R example-org/example-repo --title 'feat(x): y' --body 'Refs #{nr}'"
)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def _repo(tmp_path: Path, dateien: list[str]) -> Path:
    """Repo mit origin/main und einem Branch, der `dateien` neu anlegt."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "basis.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "basis.txt")
    _git(repo, "commit", "-q", "-m", "basis")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "switch", "-q", "-c", "feature/eigener-branch")
    for d in dateien:
        pfad = repo / d
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text("neu", encoding="utf-8")
        _git(repo, "add", d)
    _git(repo, "commit", "-q", "-m", "arbeit")
    return repo


def _fake_gh(tmp_path: Path, prs: list[dict] | None, exit_code: int = 0) -> Path:
    """PATH-Verzeichnis mit einem `gh`, das die Fixture druckt (oder scheitert)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fixture = tmp_path / "prs.json"
    fixture.write_text(json.dumps(prs or []), encoding="utf-8")
    skript = bin_dir / "gh"
    skript.write_text(
        f'#!/bin/sh\nif [ {exit_code} -ne 0 ]; then echo "API rate limit exceeded" >&2; exit {exit_code}; fi\n'
        f'cat "{fixture}"\n',
        encoding="utf-8",
    )
    skript.chmod(skript.stat().st_mode | stat.S_IXUSR)
    return bin_dir


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


def _pr(
    nummer: int,
    titel: str,
    body: str,
    dateien: list[str],
    branch: str = "andere/sitzung",
) -> dict:
    return {
        "number": nummer,
        "title": titel,
        "body": body,
        "headRefName": branch,
        "files": [{"path": d} for d in dateien],
    }


# --- Positivkontrollen ------------------------------------------------------


def test_should_hinweis_zeigen_wenn_anderer_pr_dasselbe_issue_nennt(tmp_path):
    repo = _repo(tmp_path, ["tools/a.py"])
    gh = _fake_gh(tmp_path, [_pr(901, "fix: anderes", "Loest #4711", ["docs/z.md"])])
    res = _lauf(repo, gh, ANLEGEN.format(nr=4711))
    assert res.returncode == 0, res.stderr
    text = _kontext(res)
    assert "#901" in text and "#4711" in text
    assert "keine Sperre" in text


def test_should_hinweis_zeigen_wenn_anderer_pr_dieselbe_datei_beruehrt(tmp_path):
    repo = _repo(tmp_path, ["tools/gemeinsam.py", "tools/nur_ich.py"])
    gh = _fake_gh(
        tmp_path, [_pr(902, "refactor: z", "ohne Nummer", ["tools/gemeinsam.py"])]
    )
    res = _lauf(repo, gh, ANLEGEN.format(nr=1))
    assert res.returncode == 0, res.stderr
    text = _kontext(res)
    assert "#902" in text and "tools/gemeinsam.py" in text


# --- Gegenproben ------------------------------------------------------------


def test_should_keinen_hinweis_zeigen_bei_disjunkten_dateien_und_issues(tmp_path):
    repo = _repo(tmp_path, ["tools/a.py"])
    gh = _fake_gh(tmp_path, [_pr(903, "docs: b", "Refs #9999", ["docs/b.md"])])
    res = _lauf(repo, gh, ANLEGEN.format(nr=4711))
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == ""


def test_should_ausgenommene_sammeldatei_nicht_als_kollision_werten(tmp_path):
    repo = _repo(tmp_path, ["CHANGELOG.md"])
    gh = _fake_gh(tmp_path, [_pr(904, "docs: c", "kein Bezug", ["CHANGELOG.md"])])
    res = _lauf(repo, gh, ANLEGEN.format(nr=4711))
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == ""


def test_should_eigenen_branch_nicht_gegen_sich_selbst_melden(tmp_path):
    repo = _repo(tmp_path, ["tools/a.py"])
    gh = _fake_gh(
        tmp_path,
        [
            _pr(
                905,
                "eigener",
                "Refs #4711",
                ["tools/a.py"],
                branch="feature/eigener-branch",
            )
        ],
    )
    res = _lauf(repo, gh, ANLEGEN.format(nr=4711))
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == ""


def test_should_bei_gh_fehler_nicht_blockieren(tmp_path):
    repo = _repo(tmp_path, ["tools/a.py"])
    gh = _fake_gh(tmp_path, None, exit_code=1)
    res = _lauf(repo, gh, ANLEGEN.format(nr=4711))
    assert res.returncode == 0, res.stderr
    if res.stdout.strip():
        ausgabe = json.loads(res.stdout)["hookSpecificOutput"]
        assert "permissionDecision" not in ausgabe
        assert "nicht pruefbar" in ausgabe["additionalContext"]


def test_should_anderes_kommando_nicht_pruefen(tmp_path):
    repo = _repo(tmp_path, ["tools/a.py"])
    # gh ist hier so praepariert, dass es einen Treffer lieferte — der Hook darf es nie fragen.
    gh = _fake_gh(tmp_path, [_pr(906, "x", "Refs #4711", ["tools/a.py"])])
    for kommando in (
        "gh pr list -R example-org/example-repo",
        "gh pr view 4711",
        "echo gh pr create",
        "git status",
    ):
        res = _lauf(repo, gh, kommando)
        assert res.returncode == 0, res.stderr
        assert res.stdout.strip() == "", kommando


def test_should_bei_kaputtem_json_exit_null_liefern(tmp_path):
    res = subprocess.run(
        [sys.executable, str(HOOK)],
        input="kein json",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0
    assert res.stdout.strip() == ""
