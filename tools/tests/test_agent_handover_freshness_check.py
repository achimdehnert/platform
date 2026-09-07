"""Tests für scripts/checks/agent_handover_freshness_check.py (Gate `handover-stale-vor-merge`,
AGENT_HANDOVER.md-Zweig).

Rezenz-Check statt Live-Status-Banner (Begründung im Skript-Docstring: 19 Repos mit
AGENT_HANDOVER.md, zwei inkompatible Dialekte, keines trägt ein "Live-Status:"-Banner) — eine
datierte Überschrift in den ersten HEAD_LINES Zeilen darf gegenüber dem letzten Commit, der die
Datei berührt hat, höchstens STALE_DAYS alt sein.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "checks" / "agent_handover_freshness_check.py"


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(cwd) if cwd else None,
    )


def _git_repo_with_commit(
    tmp_path: Path, filename: str, content: str, commit_date: str
) -> Path:
    """Frisches Git-Repo mit EINEM Commit, der `filename` an einem festen Datum anlegt —
    deterministisch statt von der Systemuhr abhängig (Date.now()-Fallen vermeiden)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / filename).write_text(content, encoding="utf-8")
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": f"{commit_date}T12:00:00",
        "GIT_COMMITTER_DATE": f"{commit_date}T12:00:00",
    }
    subprocess.run(["git", "add", filename], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add"], cwd=repo, check=True, env=env)
    return repo


def test_should_pass_when_heading_date_matches_last_commit_date(tmp_path):
    # Dialekt 1 (iil-voice-agent-Stil): "## ⚡ Aktueller Stand (<datum>)".
    repo = _git_repo_with_commit(
        tmp_path,
        "AGENT_HANDOVER.md",
        "# Titel\n\n## ⚡ Aktueller Stand (2026-07-07)\n\nInhalt.\n",
        "2026-07-07",
    )
    res = _run("AGENT_HANDOVER.md", cwd=repo)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "PASS" in res.stdout


def test_should_pass_for_library_dialect_heading(tmp_path):
    # Dialekt 2 (Package-Repo-Stil): "## Current state (observed <datum>)".
    repo = _git_repo_with_commit(
        tmp_path,
        "AGENT_HANDOVER.md",
        "# Titel\n\n## Current state (observed 2026-07-07)\n\nContent.\n",
        "2026-07-07",
    )
    res = _run("AGENT_HANDOVER.md", cwd=repo)
    assert res.returncode == 0, res.stdout + res.stderr


def test_should_fail_when_no_dated_heading_in_head_lines(tmp_path):
    f = tmp_path / "AGENT_HANDOVER.md"
    f.write_text("# Titel\n\nKein Datum irgendwo hier.\n")
    res = _run(str(f))
    assert res.returncode == 1
    assert "FAIL" in res.stdout
    assert "keine datierte Überschrift" in res.stdout


def test_should_fail_when_heading_date_is_stale_vs_last_commit(tmp_path):
    # Datei wurde am 2026-07-07 committet, die Überschrift behauptet aber weiterhin einen
    # >30 Tage alten Stand — genau die Drift, die das Gate fangen soll.
    repo = _git_repo_with_commit(
        tmp_path,
        "AGENT_HANDOVER.md",
        "# Titel\n\n## Aktueller Stand (2026-05-01)\n\nAlter Inhalt, PR aber gerade gemergt.\n",
        "2026-07-07",
    )
    res = _run("AGENT_HANDOVER.md", cwd=repo)
    assert res.returncode == 1
    assert "FAIL" in res.stdout
    assert "älter als" in res.stdout


def test_should_pass_when_no_git_history_is_determinable(tmp_path):
    # Kein Git-Repo (z.B. flaches Checkout/Sonderfall) -> degradiert zu PASS statt False-Positive.
    f = tmp_path / "AGENT_HANDOVER.md"
    f.write_text(
        "# Titel\n\n## Aktueller Stand (2020-01-01)\n\nSehr alt, aber kein Git-Kontext.\n"
    )
    res = _run(str(f))
    assert res.returncode == 0, res.stdout + res.stderr


def test_should_skip_missing_files_instead_of_crashing(tmp_path):
    res = _run(str(tmp_path / "AGENT_HANDOVER-geloescht.md"))
    assert res.returncode == 0
    assert "SKIP" in res.stdout


def test_should_exit_usage_error_without_args():
    res = _run()
    assert res.returncode == 2


def test_should_report_one_exit_code_for_mixed_batch(tmp_path):
    repo = _git_repo_with_commit(
        tmp_path,
        "AGENT_HANDOVER.md",
        "# T\n\n## Aktueller Stand (2026-07-07)\n\nfrisch.\n",
        "2026-07-07",
    )
    stale = repo / "AGENT_HANDOVER_BAD.md"
    stale.write_text("# T\n\nkein Datum.\n")
    res = _run("AGENT_HANDOVER.md", "AGENT_HANDOVER_BAD.md", cwd=repo)
    assert res.returncode == 1
    assert "PASS" in res.stdout and "FAIL" in res.stdout


def test_should_pass_on_platform_own_agent_handover_dogfood():
    # Dogfood: platform trägt selbst ein AGENT_HANDOVER.md mit datierter Überschrift — muss das
    # Gate real bestehen, nicht nur an synthetischen Fixtures.
    handover = REPO_ROOT / "AGENT_HANDOVER.md"
    assert handover.is_file(), (
        "Bestands-AGENT_HANDOVER.md fehlt — Test-Fixture-Annahme kaputt"
    )
    res = _run(str(handover), cwd=REPO_ROOT)
    assert res.returncode == 0, res.stdout + res.stderr


# --- Rev 2 (2026-09-07, platform#2374): zweite Pruefbedingung ---------------
#
# Die erste Bedingung vergleicht die Ueberschrift mit dem letzten Commit, der die
# DATEI beruehrt hat, und ist damit blind fuer die Fehlform, die den Slug ×19 hat
# wiederkehren lassen: die Datei wird gar nicht angefasst (Retro 0f59ce, 13 Merges
# in 7 Repos, Rezenz-Abstand 0 Tage → gruen). Die Tests hier drillen genau das.


def _commit(repo: Path, name: str, betreff: str, datum: str) -> None:
    (repo / name).write_text(f"# {name}\n", encoding="utf-8")
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": f"{datum}T12:00:00",
        "GIT_COMMITTER_DATE": f"{datum}T12:00:00",
    }
    subprocess.run(["git", "add", name], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", betreff], cwd=repo, check=True, env=env
    )


def _repo_mit_handover_und_n_commits(tmp_path: Path, n: int, betreff: str) -> Path:
    """Handover am Tag 1, danach `n` weitere Commits, die es NICHT beruehren."""
    repo = _git_repo_with_commit(
        tmp_path,
        "AGENT_HANDOVER.md",
        "# T\n\n## Aktueller Stand (2026-09-02)\n\nStand.\n",
        "2026-09-02",
    )
    for i in range(n):
        _commit(repo, f"datei_{i}.txt", f"{betreff} {i}", "2026-09-03")
    return repo


def test_should_pass_without_flag_even_when_many_commits_landed(tmp_path):
    # Das ist der Realfall 0f59ce: 13 Merges, Handover unberuehrt — der Rezenz-Check
    # allein sieht ihn nicht. Der Test haelt diese Blindstelle als BEWUSSTE Grenze
    # der ersten Bedingung fest, damit ihr Verschwinden auffaellt.
    repo = _repo_mit_handover_und_n_commits(tmp_path, 13, "feat: irgendwas")
    res = _run("AGENT_HANDOVER.md", cwd=repo)
    assert res.returncode == 0, res.stdout + res.stderr


def test_should_fail_when_commits_since_touch_exceed_threshold(tmp_path):
    # POSITIVKONTROLLE: derselbe Fall MIT eingeschalteter zweiter Bedingung.
    repo = _repo_mit_handover_und_n_commits(tmp_path, 13, "feat: irgendwas")
    res = _run("--commits-schwelle", "12", "AGENT_HANDOVER.md", cwd=repo)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "13 Commits" in res.stdout


def test_should_pass_when_commits_stay_below_threshold(tmp_path):
    repo = _repo_mit_handover_und_n_commits(tmp_path, 5, "feat: irgendwas")
    res = _run("--commits-schwelle", "12", "AGENT_HANDOVER.md", cwd=repo)
    assert res.returncode == 0, res.stdout + res.stderr


def test_should_not_count_dependabot_bumps(tmp_path):
    # 20 reine Bumps duerfen die Zahl nicht treiben — sonst misst die Bedingung
    # die Betriebsamkeit des Bots statt die fehlende Handover-Pflege.
    repo = _repo_mit_handover_und_n_commits(tmp_path, 20, "deps: Bump ruff from 1 to 2")
    res = _run("--commits-schwelle", "12", "AGENT_HANDOVER.md", cwd=repo)
    assert res.returncode == 0, res.stdout + res.stderr


def test_should_count_only_non_deps_subjects():
    sys.path.insert(0, str(SCRIPT.parent))
    import agent_handover_freshness_check as m

    assert (
        m.zaehle_sitzungs_commits(
            [
                "feat(x): echt",
                "deps: Bump ruff from 1 to 2",
                "Bump actions/checkout from 4 to 5",
                "chore(deps): Bump x",
                "fix(y): auch echt",
                "",
            ]
        )
        == 2
    )


def test_should_pass_when_base_ref_is_unknown(tmp_path):
    # Nicht aufloesbare Basis = keine Historie = PASS, nicht Fehlalarm. Ein Melder,
    # der bei fehlendem Kontext rot wird, wird abgeschaltet und meldet danach nichts.
    repo = _repo_mit_handover_und_n_commits(tmp_path, 13, "feat: irgendwas")
    res = _run(
        "--commits-schwelle",
        "12",
        "--basis",
        "origin/gibtsnicht",
        "AGENT_HANDOVER.md",
        cwd=repo,
    )
    assert res.returncode == 0, res.stdout + res.stderr


def test_should_exit_usage_error_for_non_numeric_threshold(tmp_path):
    repo = _repo_mit_handover_und_n_commits(tmp_path, 1, "feat: x")
    res = _run("--commits-schwelle", "viel", "AGENT_HANDOVER.md", cwd=repo)
    assert res.returncode == 2
