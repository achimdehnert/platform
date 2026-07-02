"""Tests fuer tools/worktree-reaper.py (ADR-233 Worktree-GC).

Fokus (Issue #819 Haeppchen 2): Dirty-Guard (nie anfassen), dry-run-Default
(nichts geloescht ohne --apply), Stale-Logik (Lease vs. mtime-Fallback).

Baut ECHTE git-Repos + echte `git worktree add`-Worktrees per subprocess in
tmp_path auf (keine Mocks fuer git selbst) -- nur `gh`-Aufrufe (pr_state) werden
gemonkeypatcht, da die weder Netzzugriff noch echte PRs brauchen/haben sollen.
LEASE_DIR wird pro Test auf ein tmp_path-Unterverzeichnis gemonkeypatcht, damit
kein Test die echten ~/.repo-session-Leases dieser Session beruehrt.

Datei heisst worktree-reaper.py (Bindestrich) -> Laden via
importlib.util.spec_from_file_location (Muster: tests/test_render_staging.py).
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
from datetime import datetime, timedelta, timezone

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "worktree-reaper.py"
_SPEC = importlib.util.spec_from_file_location("worktree_reaper", _SCRIPT)
rw = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rw)


# ─────────────────────────────────────────────────────────────────────────────
# git-Repo-Fixture-Helfer
# ─────────────────────────────────────────────────────────────────────────────


def _git(cwd: pathlib.Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = os.environ.copy()
    full_env.setdefault("GIT_AUTHOR_NAME", "test")
    full_env.setdefault("GIT_AUTHOR_EMAIL", "test@example.invalid")
    full_env.setdefault("GIT_COMMITTER_NAME", "test")
    full_env.setdefault("GIT_COMMITTER_EMAIL", "test@example.invalid")
    if env:
        full_env.update(env)
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, env=full_env, check=True,
    )


def _make_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """Legt ein frisches git-Repo mit einem Initial-Commit auf 'main' an."""
    repo = tmp_path / "primary"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


def _add_worktree(
    repo: pathlib.Path, tmp_path: pathlib.Path, name: str, branch: str,
    days_old: int | None = None,
) -> pathlib.Path:
    """Fuegt einen echten `git worktree add`-Worktree hinzu, optional mit
    zurueckdatiertem Commit (fuer Stale-mtime-Fallback-Tests, ohne interne
    Funktionen zu mocken)."""
    wt_path = tmp_path / name
    _git(repo, "worktree", "add", "-q", "-b", branch, str(wt_path))
    if days_old is not None:
        when = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
        (wt_path / "marker.txt").write_text("old\n", encoding="utf-8")
        _git(wt_path, "add", "marker.txt")
        _git(
            wt_path, "commit", "-q", "-m", "backdated",
            env={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when},
        )
    return wt_path


def _wt_dict(path: pathlib.Path, branch: str, **overrides) -> dict:
    base = {"path": str(path), "branch": branch, "head": "deadbeef", "detached": False, "bare": False}
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# list_worktrees
# ─────────────────────────────────────────────────────────────────────────────


def test_should_list_primary_and_added_worktrees(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _add_worktree(repo, tmp_path, "wt1", "feature-a")
    monkeypatch.chdir(repo)
    trees = rw.list_worktrees()
    branches = {t["branch"] for t in trees}
    assert "main" in branches
    assert "feature-a" in branches
    assert len(trees) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Dirty-Guard
# ─────────────────────────────────────────────────────────────────────────────


def test_should_detect_clean_worktree_as_not_dirty(tmp_path):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-clean", "feature-clean")
    assert rw.is_dirty(str(wt)) is False


def test_should_detect_uncommitted_change_as_dirty(tmp_path):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-dirty", "feature-dirty")
    (wt / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")
    assert rw.is_dirty(str(wt)) is True


def test_should_classify_dirty_worktree_as_skip_even_when_mergeable(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-dirty2", "feature-dirty2")
    (wt / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")
    # Selbst wenn der PR laengst gemergt waere, darf der Dirty-Guard das NIE
    # uebersteuern -- pr_state wird absichtlich so gemonkeypatcht, dass ein
    # falscher Guard sofort auffiele (Aufruf wuerde REAP_MERGED liefern).
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "merged")
    verdict, reason = rw.classify(
        _wt_dict(wt, "feature-dirty2"), primary=str(repo), current=str(repo),
        repo=None, stale_days=14,
    )
    assert verdict == "SKIP"
    assert "DIRTY" in reason


# ─────────────────────────────────────────────────────────────────────────────
# classify — Grundfaelle ohne Netzzugriff (pr_state gemonkeypatcht)
# ─────────────────────────────────────────────────────────────────────────────


def test_should_skip_primary_worktree(tmp_path):
    repo = _make_repo(tmp_path)
    verdict, reason = rw.classify(
        _wt_dict(repo, "main"), primary=str(repo), current=str(repo),
        repo=None, stale_days=14,
    )
    assert verdict == "SKIP"
    assert "primär" in reason or "primaer" in reason.lower() or "bar" in reason


def test_should_skip_protected_branch(tmp_path):
    repo = _make_repo(tmp_path)
    other = tmp_path / "not-a-real-path"
    verdict, reason = rw.classify(
        _wt_dict(other, "main"), primary=str(repo), current=str(tmp_path / "current"),
        repo=None, stale_days=14,
    )
    assert verdict == "SKIP"
    assert "geschützt" in reason or "main" in reason


def test_should_skip_detached_head(tmp_path):
    repo = _make_repo(tmp_path)
    other = tmp_path / "detached-wt"
    verdict, reason = rw.classify(
        _wt_dict(other, None, detached=True), primary=str(repo), current=str(tmp_path / "current"),
        repo=None, stale_days=14,
    )
    assert verdict == "SKIP"
    assert "detached" in reason.lower()


def test_should_reap_merged_branch(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-merged", "feature-merged")
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "merged")
    verdict, reason = rw.classify(
        _wt_dict(wt, "feature-merged"), primary=str(repo), current=str(tmp_path / "current"),
        repo=None, stale_days=14,
    )
    assert verdict == "REAP_MERGED"


def test_should_keep_when_merge_status_unknown(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-unknown", "feature-unknown")
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "unknown")
    verdict, reason = rw.classify(
        _wt_dict(wt, "feature-unknown"), primary=str(repo), current=str(tmp_path / "current"),
        repo=None, stale_days=14,
    )
    assert verdict == "KEEP"
    assert "unbestimmbar" in reason


def test_should_keep_open_pr(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-open", "feature-open")
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "open")
    verdict, reason = rw.classify(
        _wt_dict(wt, "feature-open"), primary=str(repo), current=str(tmp_path / "current"),
        repo=None, stale_days=14,
    )
    assert verdict == "KEEP"


# ─────────────────────────────────────────────────────────────────────────────
# Stale-Logik: Lease hat Vorrang vor mtime-Fallback
# ─────────────────────────────────────────────────────────────────────────────


def test_should_reap_stale_when_lease_expired(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-lease-expired", "feature-lease-exp")
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "none")
    monkeypatch.setattr(rw, "LEASE_DIR", tmp_path / "leases")
    (tmp_path / "leases").mkdir()
    (tmp_path / "leases" / "l1.json").write_text(
        json.dumps({"worktree": str(wt), "expires_at": "2020-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    verdict, reason = rw.classify(
        _wt_dict(wt, "feature-lease-exp"), primary=str(repo), current=str(tmp_path / "current"),
        repo=None, stale_days=14,
    )
    assert verdict == "REAP_STALE"
    assert "Lease" in reason


def test_should_keep_when_lease_active_even_if_commit_old(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-lease-active", "feature-lease-act", days_old=30)
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "none")
    monkeypatch.setattr(rw, "LEASE_DIR", tmp_path / "leases")
    (tmp_path / "leases").mkdir()
    future = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    (tmp_path / "leases" / "l1.json").write_text(
        json.dumps({"worktree": str(wt), "expires_at": future}),
        encoding="utf-8",
    )
    verdict, reason = rw.classify(
        _wt_dict(wt, "feature-lease-act"), primary=str(repo), current=str(tmp_path / "current"),
        repo=None, stale_days=14,
    )
    # Lease aktiv gewinnt gegen den 30 Tage alten Commit (mtime-Fallback greift NICHT).
    assert verdict == "KEEP"
    assert "Lease" in reason


def test_should_fallback_to_mtime_when_no_lease_present(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-no-lease-old", "feature-no-lease-old", days_old=30)
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "none")
    monkeypatch.setattr(rw, "LEASE_DIR", tmp_path / "leases-empty")  # existiert nicht -> kein Lease
    verdict, reason = rw.classify(
        _wt_dict(wt, "feature-no-lease-old"), primary=str(repo), current=str(tmp_path / "current"),
        repo=None, stale_days=14,
    )
    assert verdict == "REAP_STALE"
    assert "kein Lease" in reason


def test_should_keep_fresh_worktree_without_lease(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-no-lease-fresh", "feature-no-lease-fresh")
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "none")
    monkeypatch.setattr(rw, "LEASE_DIR", tmp_path / "leases-empty")
    verdict, reason = rw.classify(
        _wt_dict(wt, "feature-no-lease-fresh"), primary=str(repo), current=str(tmp_path / "current"),
        repo=None, stale_days=14,
    )
    assert verdict == "KEEP"


# ─────────────────────────────────────────────────────────────────────────────
# main() — dry-run-Default loescht NICHTS, --apply entfernt tatsaechlich
# ─────────────────────────────────────────────────────────────────────────────


def test_should_default_to_dry_run_and_remove_nothing(tmp_path, monkeypatch, capsys):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-dryrun", "feature-dryrun")
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "merged")
    monkeypatch.setattr(rw, "LEASE_DIR", tmp_path / "leases-empty")
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.argv", ["worktree-reaper.py"])

    rc = rw.main()

    assert rc == 0
    out = capsys.readouterr().out
    assert "[dry-run] Nichts entfernt" in out
    # Worktree muss danach immer noch existieren.
    trees = rw.list_worktrees()
    assert any(t["branch"] == "feature-dryrun" for t in trees)
    assert wt.is_dir()


def test_should_remove_merged_worktree_with_apply(tmp_path, monkeypatch, capsys):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-apply", "feature-apply")
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "merged")
    monkeypatch.setattr(rw, "LEASE_DIR", tmp_path / "leases-empty")
    monkeypatch.chdir(repo)
    manifest = tmp_path / "manifest.jsonl"
    monkeypatch.setattr(
        "sys.argv", ["worktree-reaper.py", "--apply", "--manifest", str(manifest)]
    )

    rc = rw.main()

    assert rc == 0
    trees = rw.list_worktrees()
    assert not any(t["branch"] == "feature-apply" for t in trees)
    assert not wt.is_dir()
    # Restore-Manifest wurde geschrieben (JSONL mit Pfad/Branch/Grund).
    lines = manifest.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["branch"] == "feature-apply"
    assert rec["path"] == str(wt)


def test_should_never_remove_dirty_worktree_even_with_apply(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path, "wt-dirty-apply", "feature-dirty-apply")
    (wt / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")
    # pr_state wuerde "merged" liefern, WENN classify() so weit kaeme -- der
    # Dirty-Guard muss das aber vorher abfangen (siehe classify()-Reihenfolge).
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "merged")
    monkeypatch.setattr(rw, "LEASE_DIR", tmp_path / "leases-empty")
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.argv", ["worktree-reaper.py", "--apply"])

    rc = rw.main()

    assert rc == 0
    trees = rw.list_worktrees()
    assert any(t["branch"] == "feature-dirty-apply" for t in trees)
    assert wt.is_dir()


def test_should_keep_stale_worktree_without_include_stale_flag(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(
        repo, tmp_path, "wt-stale-noflag", "feature-stale-noflag", days_old=30,
    )
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "none")
    monkeypatch.setattr(rw, "LEASE_DIR", tmp_path / "leases-empty")
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.argv", ["worktree-reaper.py", "--apply"])  # ohne --include-stale

    rc = rw.main()

    assert rc == 0
    trees = rw.list_worktrees()
    assert any(t["branch"] == "feature-stale-noflag" for t in trees)
    assert wt.is_dir()


def test_should_remove_stale_worktree_with_include_stale_flag(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    wt = _add_worktree(
        repo, tmp_path, "wt-stale-flag", "feature-stale-flag", days_old=30,
    )
    monkeypatch.setattr(rw, "pr_state", lambda branch, repo: "none")
    monkeypatch.setattr(rw, "LEASE_DIR", tmp_path / "leases-empty")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "sys.argv", ["worktree-reaper.py", "--apply", "--include-stale", "--stale-days", "14"]
    )

    rc = rw.main()

    assert rc == 0
    trees = rw.list_worktrees()
    assert not any(t["branch"] == "feature-stale-flag" for t in trees)
    assert not wt.is_dir()
