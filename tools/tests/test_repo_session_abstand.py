"""Tests fuer tools/repo-session.sh `abstand` (Session-Start-Phase 0.4.4).

Befund 2026-09-24 (platform#3471, #2562): 0.4.4 meldete 129 Laeufe lang
"18 Lease(s) ueber der Schwelle — vor weiterer Arbeit im Worktree: git merge
origin/main", obwohl alle 18 Leases seit Wochen ABGELAUFEN waren (aelteste
2026-08-07). In einem Worktree ohne gueltige Lease arbeitet niemand, also steht
auch kein Merge bevor — der Rat hatte keinen Adressaten. `abstand` zaehlt
abgelaufene Leases seither nicht mehr und nennt ihre Zahl als Zusatz.

End-to-end ueber subprocess gegen ein lokales Fixture-Repo (bare "origin" +
Arbeitsbaum), analog test_repo_session_lease_match.py. REPO_SESSION_DIR und
GITHUB_DIR zeigen auf tmp_path — ruehrt NICHT an ~/.repo-session oder ~/github.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_SESSION_SH = Path(__file__).resolve().parents[2] / "tools" / "repo-session.sh"
SCHWELLE = 25


def _git(*args: str) -> None:
    subprocess.run([shutil.which("git"), *args], check=True, capture_output=True)


def _fixture_repo(tmp_path: Path) -> tuple[Path, str]:
    """Repo `work` mit origin/main, das SCHWELLE+1 Commits vor `base_sha` liegt."""
    origin = tmp_path / "origin.git"
    work = tmp_path / "github" / "work"
    work.parent.mkdir(parents=True)
    _git("init", "--bare", "-q", str(origin))
    _git("init", "-q", "-b", "main", str(work))
    _git("-C", str(work), "config", "user.email", "t@example.com")
    _git("-C", str(work), "config", "user.name", "Test User")
    (work / "README.md").write_text("fixture\n")
    _git("-C", str(work), "add", ".")
    _git("-C", str(work), "commit", "-q", "-m", "init")
    base_sha = subprocess.run(
        [shutil.which("git"), "-C", str(work), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    for i in range(SCHWELLE + 1):
        (work / "README.md").write_text(f"fixture {i}\n")
        _git("-C", str(work), "commit", "-q", "-am", f"c{i}")
    _git("-C", str(work), "remote", "add", "origin", str(origin))
    _git("-C", str(work), "push", "-q", "origin", "main")
    return work, base_sha


def _lease(tmp_path: Path, base_sha: str, expires_at: datetime) -> None:
    leases = tmp_path / ".repo-session" / "leases"
    leases.mkdir(parents=True, exist_ok=True)
    (leases / "2026-09-24-test-abstand-000000.json").write_text(
        json.dumps(
            {
                "session_id": "2026-09-24-test-abstand-000000",
                "owner": "test",
                "repo": "work",
                "branch": "session/2026-09-24/test/abstand",
                "base_sha": base_sha,
                "worktree": str(tmp_path / "wt"),
                "created_at": "2026-09-24T00:00:00Z",
                "last_touch": "2026-09-24T00:00:00Z",
                "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "intended_pr": None,
                "ephemeral": False,
            }
        )
    )


def _abstand(tmp_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [shutil.which("bash"), str(REPO_SESSION_SH), "abstand"],
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path),
            "GITHUB_DIR": str(tmp_path / "github"),
            "REPO_SESSION_DIR": str(tmp_path / ".repo-session"),
            "REPO_SESSION_SKIP_PR_CHECK": "1",
        },
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_should_warn_for_active_lease_over_threshold(tmp_path: Path) -> None:
    _, base_sha = _fixture_repo(tmp_path)
    _lease(tmp_path, base_sha, datetime.now(UTC) + timedelta(days=7))

    r = _abstand(tmp_path)

    assert r.returncode == 1, r.stdout + r.stderr
    assert "1 von 1 Lease(s) ueber der Schwelle" in r.stdout
    assert "abgelaufene" not in r.stdout


def test_should_not_count_expired_lease_but_name_it(tmp_path: Path) -> None:
    _, base_sha = _fixture_repo(tmp_path)
    _lease(tmp_path, base_sha, datetime.now(UTC) - timedelta(days=1))

    r = _abstand(tmp_path)

    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 Lease(s), keine ueber der Schwelle" in r.stdout
    assert "1 abgelaufene Lease(s) nicht gezaehlt" in r.stdout
    assert "⚠" not in r.stdout
