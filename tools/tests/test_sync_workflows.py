"""Tests für scripts/sync-workflows.sh (ADR-265 REC-5b/REC-1, closes #946).

Drei Sync-Guards laufen fleet-weit über 64 Repos in 3 Orgs, hatten aber bis zu
diesem Test keine automatisierten Tests (`ls tools/tests/*sync*` → leer):

  1. SSoT-Skip     — Repo mit origin=platform-Repo wird VOR jeder Ausgabe
                      übersprungen (sync_repo(), früher Return ohne Marker).
  2. Tracked-Guard  — ein im Ziel-Index getrackter Workflow-Pfad wird NIE
                      durch einen Symlink ersetzt → "SKIP-TRACKED".
  3. Ignore-Guard   — ohne wirksame '.windsurf/'-.gitignore-Zeile wird das
                      ganze Repo übersprungen → "SKIP-REPO".

Zusätzlich deckt dieses Modul die additive SKIP-Längsaggregation ab (Schluss-
Summary-Zeile "SKIP-SUMMARY: ..." + --strict → Exit != 0 bei Skips).

Läuft end-to-end über subprocess gegen ein synthetisches Fixture-"GITHUB_DIR"
(tmp_path): ein Minimal-"platform"-Verzeichnis (nur die eine benötigte
Workflow-Datei + eine leere Registry) + ein einzelnes Ziel-Repo, das je nach
Testfall SSoT-Origin / getrackten Workflow / fehlende .gitignore-Zeile
simuliert. `--dry-run` ist in JEDEM Aufruf gesetzt, damit nichts geschrieben
wird (Symlinks/mkdir).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

SYNC_SH = Path(__file__).resolve().parents[2] / "scripts" / "sync-workflows.sh"

# Der einzige Workflow-Name, den die Fixtures brauchen — er ist Teil von
# UNIVERSAL (jedes Repo bekommt ihn), reicht also für alle drei Guard-Fälle.
WF_NAME = "knowledge-capture"


def _make_platform_root(tmp_path: Path) -> None:
    """Minimaler 'platform'-Ordner unter tmp_path: eine Workflow-Quelldatei
    + eine leere, aber valide Registry (django_apps/org_django_apps/frameworks
    müssen als Keys existieren, s. sync-workflows.sh Z.104-118)."""
    wf_dir = tmp_path / "platform" / ".windsurf" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / f"{WF_NAME}.md").write_text("# fixture workflow\n")

    registry_dir = tmp_path / "platform" / "registry"
    registry_dir.mkdir(parents=True)
    (registry_dir / "github_repos.yaml").write_text(
        "django_apps: {}\norg_django_apps: {}\nframeworks: {}\n"
    )


def _git(repo_dir: Path, *args: str) -> None:
    git = shutil.which("git")
    subprocess.run([git, "-C", str(repo_dir), *args], check=True, capture_output=True)


def _make_target_repo(tmp_path: Path, name: str, origin_url: str) -> Path:
    """Legt tmp_path/<name> als frisches Git-Repo mit `origin`-Remote an
    (keine Erreichbarkeit nötig — nur `git remote get-url` wird genutzt)."""
    repo_dir = tmp_path / name
    repo_dir.mkdir(parents=True)
    _git(repo_dir, "init", "-q")
    _git(repo_dir, "config", "user.email", "t@example.com")
    _git(repo_dir, "config", "user.name", "Test User")
    _git(repo_dir, "remote", "add", "origin", origin_url)
    return repo_dir


def _run_sync(tmp_path: Path, *extra_args: str) -> subprocess.CompletedProcess:
    bash_bin = shutil.which("bash")
    env = {"GITHUB_DIR": str(tmp_path), "PATH": os.environ.get("PATH", "")}
    return subprocess.run(
        [bash_bin, str(SYNC_SH), "--dry-run", *extra_args],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


# --- Guard 1: SSoT-Skip (sync-workflows.sh, sync_repo(), origin=platform) ---


def test_should_skip_repo_silently_when_origin_is_platform_ssot(tmp_path):
    _make_platform_root(tmp_path)
    _make_target_repo(
        tmp_path, "fixture-ssot-pin", "https://github.com/achimdehnert/platform.git"
    )

    res = _run_sync(tmp_path, "fixture-ssot-pin")

    assert res.returncode == 0, res.stderr
    # SSoT-Skip returned VOR jeder Ausgabe (kein "📦"-Header, keine LINK/WARN-
    # Zeile für dieses Repo) — die Abwesenheit jeglicher Repo-Erwähnung IST
    # der Beweis für den frühen Return.
    assert "fixture-ssot-pin" not in res.stdout
    assert "📦" not in res.stdout


# --- Guard 2: Tracked-Guard (sync_workflow(), getrackter Ziel-Pfad) ---


def test_should_skip_tracked_workflow_with_skip_tracked_marker(tmp_path):
    _make_platform_root(tmp_path)
    repo_dir = _make_target_repo(
        tmp_path, "fixture-tracked", "https://github.com/achimdehnert/fixture-tracked.git"
    )
    # Ignore-Guard muss zuerst passieren, damit sync_repo() überhaupt bis zum
    # Tracked-Guard in sync_workflow() vordringt.
    (repo_dir / ".gitignore").write_text(".windsurf/\n")
    wf_dir = repo_dir / ".windsurf" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / f"{WF_NAME}.md").write_text("# eigene, getrackte Kopie\n")
    _git(repo_dir, "add", ".gitignore")
    # -f: der Pfad ist durch die eigene .gitignore-Zeile "verdeckt" — das
    # Fixture bildet genau den ADR-265-Realfall nach (Datei wurde getrackt,
    # BEVOR die .gitignore-Zeile committet wurde), daher bewusst force-add.
    _git(repo_dir, "add", "-f", f".windsurf/workflows/{WF_NAME}.md")
    _git(repo_dir, "commit", "-q", "-m", "fixture: tracked workflow copy")

    res = _run_sync(tmp_path, "fixture-tracked")

    assert res.returncode == 0, res.stderr
    assert "SKIP-TRACKED" in res.stdout
    assert f"{WF_NAME}.md ist im Index getrackt" in res.stdout


# --- Guard 3: Ignore-Guard (sync_repo(), '.windsurf/' nicht in .gitignore) ---


def test_should_skip_repo_when_windsurf_not_gitignored(tmp_path):
    _make_platform_root(tmp_path)
    _make_target_repo(
        tmp_path, "fixture-no-ignore", "https://github.com/achimdehnert/fixture-no-ignore.git"
    )
    # bewusst KEIN .gitignore mit '.windsurf/'-Zeile

    res = _run_sync(tmp_path, "fixture-no-ignore")

    assert res.returncode == 0, res.stderr
    assert "📦 fixture-no-ignore" in res.stdout
    assert "SKIP-REPO" in res.stdout
    assert "'.windsurf/' nicht in .gitignore" in res.stdout


# --- Maßnahme 2: SKIP-Längsaggregation (Summary-Zeile + --strict) ---


def test_should_print_skip_summary_and_exit_nonzero_in_strict_mode(tmp_path):
    _make_platform_root(tmp_path)
    _make_target_repo(
        tmp_path, "fixture-strict-skip", "https://github.com/achimdehnert/fixture-strict-skip.git"
    )
    # kein .gitignore → Ignore-Guard greift → 1 Skip

    res = _run_sync(tmp_path, "--strict", "fixture-strict-skip")

    assert "SKIP-SUMMARY" in res.stdout
    assert "1 Repo(s) übersprungen" in res.stdout
    assert "fixture-strict-skip" in res.stdout  # taucht im SKIP-REPO-Teil der Summary auf
    assert res.returncode != 0, "strict + Skips>0 muss Exit != 0 liefern"


def test_should_exit_zero_without_strict_despite_skip(tmp_path):
    _make_platform_root(tmp_path)
    _make_target_repo(
        tmp_path, "fixture-nonstrict-skip", "https://github.com/achimdehnert/fixture-nonstrict-skip.git"
    )

    res = _run_sync(tmp_path, "fixture-nonstrict-skip")  # kein --strict

    assert "SKIP-SUMMARY" in res.stdout
    assert "1 Repo(s) übersprungen" in res.stdout
    assert res.returncode == 0, "ohne --strict bleibt der Exit-Code trotz Skip 0"


def test_should_report_zero_skips_and_exit_zero_in_strict_mode_when_clean(tmp_path):
    _make_platform_root(tmp_path)
    repo_dir = _make_target_repo(
        tmp_path, "fixture-clean", "https://github.com/achimdehnert/fixture-clean.git"
    )
    (repo_dir / ".gitignore").write_text(".windsurf/\n")
    _git(repo_dir, "add", ".gitignore")
    _git(repo_dir, "commit", "-q", "-m", "fixture: gitignore only")

    res = _run_sync(tmp_path, "--strict", "fixture-clean")

    assert res.returncode == 0, res.stderr
    assert "SKIP-SUMMARY: 0 Repos übersprungen" in res.stdout
