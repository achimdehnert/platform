"""Tests für scripts/checks/handover_append_only.py (KONZ-027 Arm A, platform#1319)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "checks" / "handover_append_only.py"


def _repo(tmp_path: Path, base_content: str) -> tuple[Path, str]:
    """Wegwerf-Repo mit AGENT_HANDOVER_LOG.md; gibt (Pfad, base-SHA) zurück."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@example.invalid"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    (tmp_path / "AGENT_HANDOVER_LOG.md").write_text(base_content, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "base"], check=True)
    sha = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return tmp_path, sha


def _commit(repo: Path, content: str) -> None:
    (repo / "AGENT_HANDOVER_LOG.md").write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "change"], check=True)


def _run(repo: Path, base: str, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--base", base, "--head", "HEAD", *extra],
        cwd=repo, capture_output=True, text=True, timeout=30,
    )


BASE = "## Stand 2026-07-20\n- Punkt A\n- Punkt B\n"


def test_should_pass_when_only_appended(tmp_path):
    repo, sha = _repo(tmp_path, BASE)
    _commit(repo, BASE + "\n## Stand 2026-07-21\n- Punkt C\n")
    res = _run(repo, sha)
    assert res.returncode == 0, res.stdout + res.stderr


def test_should_fail_when_existing_line_edited(tmp_path):
    repo, sha = _repo(tmp_path, BASE)
    _commit(repo, "## Stand 2026-07-20\n- Punkt A GEÄNDERT\n- Punkt B\n")
    res = _run(repo, sha)
    assert res.returncode == 1
    assert "Punkt A" in res.stdout


def test_should_fail_when_existing_line_deleted(tmp_path):
    repo, sha = _repo(tmp_path, BASE)
    _commit(repo, "## Stand 2026-07-20\n- Punkt B\n")
    res = _run(repo, sha)
    assert res.returncode == 1


def test_should_reproduce_pr_1317_pattern(tmp_path):
    # Realer Anlassfall: #1317 entfernte eine bestehende "Erledigt"-Zeile und fügte
    # sie verändert weiter unten wieder ein. Genau das muss das Gate fangen —
    # sonst misst der A/B-Vergleich in #1302 den Bruch statt den Arm.
    repo, sha = _repo(tmp_path, "> Erledigt 07-20: alt\n> Erledigt 07-19: aelter\n")
    _commit(repo, "> Erledigt 07-21: neu\n> Erledigt 07-20: alt, ergaenzt\n> Erledigt 07-19: aelter\n")
    res = _run(repo, sha)
    assert res.returncode == 1


def test_should_allow_removals_with_optout(tmp_path):
    repo, sha = _repo(tmp_path, BASE)
    _commit(repo, "## Stand 2026-07-20\n- Punkt B\n")
    res = _run(repo, sha, "--allow-removals")
    assert res.returncode == 0
    assert "Opt-out" in res.stdout


def test_should_pass_when_file_untouched(tmp_path):
    repo, sha = _repo(tmp_path, BASE)
    (repo / "andere.md").write_text("egal\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "other"], check=True)
    res = _run(repo, sha)
    assert res.returncode == 0
    assert "unverändert" in res.stdout


def test_should_exit_two_when_base_ref_missing(tmp_path):
    repo, _ = _repo(tmp_path, BASE)
    res = _run(repo, "refs/heads/gibt-es-nicht")
    assert res.returncode == 2


def test_should_report_line_numbers(tmp_path):
    repo, sha = _repo(tmp_path, "Z1\nZ2\nZ3\nZ4\n")
    _commit(repo, "Z1\nZ2\nZ3 GEÄNDERT\nZ4\n")
    res = _run(repo, sha)
    assert res.returncode == 1
    assert "Zeile 3" in res.stdout


@pytest.mark.parametrize("n", [1, 12])
def test_should_cap_listing_at_ten_entries(tmp_path, n):
    base = "".join(f"Z{i}\n" for i in range(1, 21))
    repo, sha = _repo(tmp_path, base)
    _commit(repo, "".join(f"Z{i}\n" for i in range(1, 21) if i > n))
    res = _run(repo, sha)
    assert res.returncode == 1
    if n > 10:
        assert "weitere" in res.stdout
