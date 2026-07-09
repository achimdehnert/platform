"""Tests für tools/repo-session.sh check_pr_collision() (T-10, ADR-233 R-6).

check_pr_collision() ist ein hartes Gate (PR #889) mit mehreren Fail-open-
Pfaden (kein `gh`, `gh`-Auth fehlgeschlagen) — bis zu diesem Test 0 automatisierte
Tests. Ruft `repo-session.sh start` end-to-end über subprocess gegen ein lokales
Fixture-Repo auf (bare "origin" + Arbeitsbaum), mit einem `gh`-PATH-Shim-Skript,
das kanonisches `gh pr list --json ...`-JSON zurückgibt. Deckt die drei Pfade ab:

  1. Block-Pfad      — offener PR mit demselben Task-Slug im headRefName → exit 1
  2. Awareness-Pfad   — offene PRs vorhanden, aber kein Slug-Treffer → Erfolg + Hinweis
  3. Fail-open-Pfad   — `gh` nicht auf PATH → Erfolg + sichtbare Warnung, kein Crash

Läuft in einer isolierten Sandbox: PATH ist auf einen kuratierten Shim-Ordner
reduziert (nur die vom Skript tatsächlich benötigten Binaries verlinkt), damit
"gh fehlt" real simulierbar ist, ohne das echte System-`gh` zu verstecken/löschen.
REPO_SESSION_DIR zeigt auf tmp_path — rührt NICHT an ~/.repo-session.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO_SESSION_SH = Path(__file__).resolve().parents[2] / "tools" / "repo-session.sh"

# Binaries, die repo-session.sh + check_pr_collision beim Namen aufrufen (kein
# Bash-Builtin). `bash` selbst wird per absolutem Pfad aufgerufen (s.u.), muss
# hier trotzdem verlinkt sein, weil subprocess(env=...) das PATH aus `env` für
# die Auflösung von argv[0] benutzt.
_REQUIRED_BINARIES = [
    "git", "python3", "sed", "tr", "date", "mkdir", "cat",
    "basename", "dirname", "bash", "rm", "printf", "grep",
]


def _make_shim_path(tmp_path: Path, with_gh: str | None) -> str:
    """Baut einen PATH-Ordner mit genau den benötigten Binaries (+ optional `gh`).

    ``with_gh``: Inhalt eines ausführbaren `gh`-Shim-Skripts, oder None für
    "gh fehlt komplett" (Fail-open-Pfad-Repro).
    """
    shim_dir = tmp_path / "shimbin"
    shim_dir.mkdir()
    for name in _REQUIRED_BINARIES:
        real = shutil.which(name)
        assert real, f"Testumgebung: benötigtes Tool '{name}' nicht auffindbar"
        os.symlink(real, shim_dir / name)
    if with_gh is not None:
        gh_path = shim_dir / "gh"
        gh_path.write_text(with_gh)
        gh_path.chmod(0o755)
    return str(shim_dir)


def _make_fixture_repo(tmp_path: Path) -> Path:
    """Lokales bare-'origin' + Arbeitsbaum auf main, damit fetch/rev-parse
    offline funktionieren (kein echtes GitHub nötig)."""
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    git = shutil.which("git")
    subprocess.run([git, "init", "--bare", "-q", str(origin)], check=True)
    subprocess.run([git, "init", "-q", "-b", "main", str(work)], check=True)
    subprocess.run([git, "-C", str(work), "config", "user.email", "t@example.com"], check=True)
    subprocess.run([git, "-C", str(work), "config", "user.name", "Test User"], check=True)
    (work / "README.md").write_text("fixture\n")
    subprocess.run([git, "-C", str(work), "add", "."], check=True)
    subprocess.run([git, "-C", str(work), "commit", "-q", "-m", "init"], check=True)
    subprocess.run([git, "-C", str(work), "remote", "add", "origin", str(origin)], check=True)
    subprocess.run([git, "-C", str(work), "push", "-q", "origin", "main"], check=True)
    return work


def _run_start(tmp_path: Path, repo: Path, task: str, path: str) -> subprocess.CompletedProcess:
    env = {
        "PATH": path,
        "HOME": str(tmp_path),  # git config fallback / ssh-Suche darf nicht ins echte HOME
        "REPO_SESSION_DIR": str(tmp_path / ".repo-session"),
    }
    bash_bin = shutil.which("bash")
    return subprocess.run(
        [bash_bin, str(REPO_SESSION_SH), "start", str(repo), "--task", task],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_should_block_on_open_pr_with_matching_task_slug(tmp_path):
    repo = _make_fixture_repo(tmp_path)
    gh_shim = (
        "#!/usr/bin/env bash\n"
        'echo \'[{"number": 42, "headRefName": "session/2026-01-01/someone/mytask", '
        '"title": "colliding work"}]\'\n'
    )
    path = _make_shim_path(tmp_path, with_gh=gh_shim)

    res = _run_start(tmp_path, repo, "mytask", path)

    assert res.returncode != 0
    assert "PR-Kollision" in res.stderr
    assert "#42" in res.stderr


def test_should_allow_start_and_list_prs_for_awareness_when_no_slug_match(tmp_path):
    repo = _make_fixture_repo(tmp_path)
    gh_shim = (
        "#!/usr/bin/env bash\n"
        'echo \'[{"number": 7, "headRefName": "session/2026-01-01/someone/unrelated-task", '
        '"title": "other work"}]\'\n'
    )
    path = _make_shim_path(tmp_path, with_gh=gh_shim)

    res = _run_start(tmp_path, repo, "mytask", path)

    assert res.returncode == 0, res.stderr
    assert "offene PR(s)" in res.stderr
    assert "#7" in res.stderr
    # Worktree tatsächlich angelegt (Pfad auf stdout)
    assert res.stdout.strip() != ""
    assert Path(res.stdout.strip()).is_dir()


def test_should_fail_open_with_warning_when_gh_missing(tmp_path):
    repo = _make_fixture_repo(tmp_path)
    path = _make_shim_path(tmp_path, with_gh=None)  # kein gh im PATH

    res = _run_start(tmp_path, repo, "mytask", path)

    assert res.returncode == 0, res.stderr
    assert "gh nicht verfügbar" in res.stderr
    assert "übersprungen" in res.stderr
    assert Path(res.stdout.strip()).is_dir()


def test_should_skip_check_when_env_override_set(tmp_path):
    repo = _make_fixture_repo(tmp_path)
    gh_shim = (
        "#!/usr/bin/env bash\n"
        'echo \'[{"number": 42, "headRefName": "session/2026-01-01/someone/mytask", '
        '"title": "colliding work"}]\'\n'
    )
    path = _make_shim_path(tmp_path, with_gh=gh_shim)
    env = {
        "PATH": path,
        "HOME": str(tmp_path),
        "REPO_SESSION_DIR": str(tmp_path / ".repo-session"),
        "REPO_SESSION_SKIP_PR_CHECK": "1",
    }
    bash_bin = shutil.which("bash")
    res = subprocess.run(
        [bash_bin, str(REPO_SESSION_SH), "start", str(repo), "--task", "mytask"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0, res.stderr
    assert "übersprungen" in res.stderr
    assert "REPO_SESSION_SKIP_PR_CHECK" in res.stderr
