"""Drill fuer den Hinweis-Hook `tag_ohne_nicht_pr_lauf_hinweis.py` (Gate tag-ohne-nicht-pr-lauf).

Anlass: Retro ec3416 Befunde 1 und 24 — iilgmbh/shared-ci v1.1.27 wurde nach gruenen
PR-Laeufen getaggt; jeder push/dispatch-Lauf der Aufrufer scheiterte danach mit 0 Jobs.

`gh` wird durch ein Fake-Skript im PATH ersetzt, das eine Laufliste ausgibt; das Git-Repo
ist ein Wegwerf-Repo mit einem `workflow_call`-Workflow. Kein Netz, kein echtes GitHub.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "tag_ohne_nicht_pr_lauf_hinweis.py"
REUSABLE = "name: ci-python\non:\n  workflow_call:\n    inputs: {}\njobs: {}\n"
EIGEN = "name: ci\non:\n  pull_request:\njobs: {}\n"


def _git(cwd: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return res.stdout.strip()


def _repo(tmp_path: Path, workflow: str = REUSABLE) -> Path:
    repo = tmp_path / "repo"
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "_ci-python.yml").write_text(
        workflow, encoding="utf-8"
    )
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "basis")
    return repo


def _fake_gh(tmp_path: Path, runs: list[dict] | None, exit_code: int = 0) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fixture = tmp_path / "runs.json"
    fixture.write_text(json.dumps(runs or []), encoding="utf-8")
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


def _run(event: str, conclusion: str = "success") -> dict:
    return {
        "event": event,
        "conclusion": conclusion,
        "status": "completed",
        "workflowName": "ci",
    }


NUR_PR_GRUEN = [_run("pull_request"), _run("pull_request"), _run("push", "failure")]


# --- Positivkontrollen ------------------------------------------------------


def test_should_hinweis_zeigen_beim_realfall_tag_nach_pr_laeufen(tmp_path):
    """Form von shared-ci v1.1.27: nur pull_request gruen, push rot — Tag wird angelegt."""
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, NUR_PR_GRUEN)
    res = _lauf(repo, bin_dir, "git tag v1.1.27 && git push origin v1.1.27")
    assert res.returncode == 0
    text = _kontext(res)
    assert "v1.1.27" in text
    assert "pull_request/success ×2" in text and "push/failure ×1" in text
    assert "workflow_dispatch" in text
    sha = _git(repo, "rev-parse", "HEAD")
    assert f"--commit {sha}" in (tmp_path / "gh-aufrufe.log").read_text(
        encoding="utf-8"
    )


def test_should_hinweis_zeigen_bei_gh_release_create(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, [_run("pull_request")])
    res = _lauf(repo, bin_dir, "gh release create v2.0.0 --notes 'x'")
    assert "v2.0.0" in _kontext(res)


def test_should_hinweis_zeigen_bei_push_tags_ohne_laeufe(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, [])
    res = _lauf(repo, bin_dir, "git push --tags")
    text = _kontext(res)
    assert "keine Laeufe" in text


def test_should_commit_des_bestehenden_tags_pruefen(tmp_path):
    """Tag existiert schon (git tag frueher, jetzt gh release): sein Commit zaehlt, nicht HEAD."""
    repo = _repo(tmp_path)
    _git(repo, "tag", "v1.0.0")
    alt = _git(repo, "rev-parse", "HEAD")
    (repo / "neu.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "neu.txt")
    _git(repo, "commit", "-q", "-m", "danach")
    bin_dir = _fake_gh(tmp_path, [_run("pull_request")])
    _lauf(repo, bin_dir, "gh release create v1.0.0")
    assert f"--commit {alt}" in (tmp_path / "gh-aufrufe.log").read_text(
        encoding="utf-8"
    )


# --- Gegenproben ------------------------------------------------------------


def test_should_schweigen_bei_gruenem_push_lauf(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, [_run("pull_request"), _run("push")])
    res = _lauf(repo, bin_dir, "git tag v1.1.28")
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_should_schweigen_bei_gruenem_dispatch_lauf(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, [_run("workflow_dispatch")])
    res = _lauf(repo, bin_dir, "gh release create v1.1.28")
    assert res.stdout.strip() == ""


def test_should_schweigen_ohne_workflow_call_im_repo(tmp_path):
    repo = _repo(tmp_path, workflow=EIGEN)
    bin_dir = _fake_gh(tmp_path, NUR_PR_GRUEN)
    res = _lauf(repo, bin_dir, "git tag v1.0.0")
    assert res.stdout.strip() == ""
    assert not (tmp_path / "gh-aufrufe.log").exists()


def test_should_tag_listen_und_loeschen_ignorieren(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, NUR_PR_GRUEN)
    for kommando in (
        "git tag -l 'v1.*'",
        "git tag --list",
        "git tag -d v1.0.0",
        "git push origin main",
    ):
        res = _lauf(repo, bin_dir, kommando)
        assert res.stdout.strip() == "", kommando


def test_should_fail_open_bei_gh_fehler(tmp_path):
    repo = _repo(tmp_path)
    bin_dir = _fake_gh(tmp_path, None, exit_code=1)
    res = _lauf(repo, bin_dir, "git tag v1.1.27")
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


def test_should_tag_name_aus_kommandoformen_lesen():
    sys.path.insert(0, str(HOOK.parent))
    import tag_ohne_nicht_pr_lauf_hinweis as modul

    assert modul.tag_name("git tag -a v1.2.3 -m 'rel'") == "v1.2.3"
    assert modul.tag_name("git tag -s v1.2.3") == "v1.2.3"
    assert modul.tag_name("cd x && git push origin refs/tags/v9") == "v9"
    assert modul.tag_name("git push origin v1.1.27") == "v1.1.27"
    assert modul.tag_name("gh release create v3 --generate-notes") == "v3"
    assert modul.tag_name("git tag") is None
    assert modul.tag_name("git tag -l") is None
    assert modul.tag_name("git push origin main") is None
