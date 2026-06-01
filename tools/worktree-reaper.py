#!/usr/bin/env python3
"""worktree-reaper — deterministischer GC für git-Worktrees (ADR-233).

Entfernt Worktrees, deren Branch nachweislich **gemergt** ist (squash-aware via
`gh pr ... --state merged`) oder die **>N Tage unberührt** sind. Konservativ by
default:

- **dry-run** ist Standard; `--apply` führt Entfernungen erst aus.
- **Dirty-Guard:** ein Worktree mit uncommitted changes wird NIE angefasst.
- **Unsicherheit = KEEP:** wenn der Merge-Status nicht zweifelsfrei bestimmbar ist
  (kein `gh`, privater Fork, API-Fehler), wird der Worktree behalten, nie gereapt.
- **Stale-but-unmerged** wird nur mit `--include-stale` entfernt (sonst nur gemeldet).
  Stale-Entscheidung läuft primär über die **Lease** (repo-session.sh, `expires_at`,
  ADR-233 §2.4); nur ohne/unparsebare Lease fällt sie auf Commit-mtime zurück.
- Primärer Worktree und der aktuelle Worktree sind immer ausgenommen.
- Jede Entfernung wird in ein **Restore-Manifest** (JSONL) geschrieben:
  `git worktree add <path> <branch>` stellt sie wieder her.

Bezug: ADR-233, feedback_branch_cleanup_squash_worktree (squash-aware Wahrheit,
Worktree-Branches ausschließen, Restore-Manifest schreiben).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROTECTED_BRANCHES = {"main", "master"}
LEASE_DIR = Path(os.environ.get("REPO_SESSION_DIR", str(Path.home() / ".repo-session"))) / "leases"


def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip()


def list_worktrees() -> list[dict]:
    """Parse `git worktree list --porcelain` → [{path, head, branch, bare, detached}]."""
    rc, out = _run(["git", "worktree", "list", "--porcelain"])
    if rc != 0:
        sys.exit("FEHLER: kein git-Repo / `git worktree list` fehlgeschlagen.")
    trees, cur = [], {}
    for line in out.splitlines():
        if not line:
            if cur:
                trees.append(cur)
                cur = {}
            continue
        key, _, val = line.partition(" ")
        if key == "worktree":
            cur = {"path": val, "branch": None, "head": None, "detached": False, "bare": False}
        elif key == "HEAD":
            cur["head"] = val
        elif key == "branch":
            cur["branch"] = val.removeprefix("refs/heads/")
        elif key == "detached":
            cur["detached"] = True
        elif key == "bare":
            cur["bare"] = True
    if cur:
        trees.append(cur)
    return trees


def is_dirty(path: str) -> bool:
    rc, out = _run(["git", "status", "--porcelain"], cwd=path)
    return rc != 0 or bool(out)  # rc!=0 (z.B. Pfad weg) → konservativ als dirty werten


def commit_age_days(path: str) -> float | None:
    rc, out = _run(["git", "log", "-1", "--format=%ct"], cwd=path)
    if rc != 0 or not out.isdigit():
        return None
    age = datetime.now(timezone.utc).timestamp() - int(out)
    return age / 86400.0


def lease_for(path: str) -> dict | None:
    """Lease (repo-session.sh) für einen Worktree-Pfad finden, falls vorhanden."""
    if not LEASE_DIR.is_dir():
        return None
    for f in LEASE_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("worktree") == path:
            return d
    return None


def lease_expired(lease: dict) -> bool | None:
    """True/False ob expires_at überschritten; None wenn nicht parsebar."""
    exp = lease.get("expires_at")
    if not exp:
        return None
    try:
        ts = datetime.strptime(exp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    return datetime.now(timezone.utc) > ts


def pr_state(branch: str, repo: str | None) -> str:
    """'merged' | 'open' | 'none' | 'unknown' (gh fehlt/Fehler → unknown = KEEP)."""
    if not branch:
        return "unknown"
    # --state all: sonst defaultet gh auf 'open' und gemergte PRs bleiben unsichtbar.
    base = ["gh", "pr", "list", "--head", branch, "--state", "all",
            "--json", "number,state", "--limit", "10"]
    if repo:
        base += ["--repo", repo]
    rc, out = _run(base)
    if rc != 0:
        return "unknown"
    try:
        prs = json.loads(out or "[]")
    except json.JSONDecodeError:
        return "unknown"
    states = {p.get("state", "").upper() for p in prs}
    if "MERGED" in states:
        return "merged"
    if "OPEN" in states:
        return "open"
    return "none"


def classify(wt: dict, primary: str, current: str, repo: str | None, stale_days: int) -> tuple[str, str]:
    """→ (verdict, reason). verdict ∈ {KEEP, REAP_MERGED, REAP_STALE, SKIP}."""
    path, branch = wt["path"], wt["branch"]
    if wt.get("bare") or path == primary:
        return "SKIP", "primärer/barer Worktree"
    if Path(path) == Path(current):
        return "SKIP", "aktueller Worktree"
    if wt.get("detached") or not branch:
        return "SKIP", "detached HEAD — Branch unbestimmbar"
    if branch in PROTECTED_BRANCHES:
        return "SKIP", f"geschützter Branch ({branch})"
    if is_dirty(path):
        return "SKIP", "DIRTY — uncommitted changes (Guard)"
    state = pr_state(branch, repo)
    if state == "merged":
        return "REAP_MERGED", "PR gemergt (squash-aware)"
    if state == "unknown":
        return "KEEP", "Merge-Status unbestimmbar → konservativ behalten"
    if state == "open":
        return "KEEP", "offener PR"
    # Stale-Entscheidung: Lease primär (ADR-233 §2.4), mtime nur als Fallback.
    lease = lease_for(path)
    if lease is not None:
        exp = lease_expired(lease)
        if exp is True:
            return "REAP_STALE", f"Lease abgelaufen ({lease.get('expires_at')}), kein PR"
        if exp is False:
            return "KEEP", f"Lease aktiv bis {lease.get('expires_at')}"
        # exp is None → expires_at unparsebar, falle auf mtime zurück
    age = commit_age_days(path)
    if age is not None and age > stale_days:
        return "REAP_STALE", f"unberührt seit {age:.0f}d, kein PR (kein Lease)"
    return "KEEP", "aktiv / kein Reap-Kriterium"


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministischer git-Worktree-GC (ADR-233).")
    ap.add_argument("--apply", action="store_true", help="Entfernungen ausführen (Standard: dry-run).")
    ap.add_argument("--include-stale", action="store_true", help="Auch stale-but-unmerged entfernen.")
    ap.add_argument("--stale-days", type=int, default=14, help="Stale-Schwelle in Tagen (default 14).")
    ap.add_argument("--repo", default=None, help="OWNER/REPO für gh (default: aus Remote).")
    ap.add_argument("--manifest", default=None, help="Restore-Manifest-Pfad (JSONL).")
    args = ap.parse_args()

    trees = list_worktrees()
    primary = trees[0]["path"] if trees else ""
    current = _run(["git", "rev-parse", "--show-toplevel"])[1] or str(Path.cwd())

    plan, reap = [], []
    for wt in trees:
        verdict, reason = classify(wt, primary, current, args.repo, args.stale_days)
        plan.append((verdict, wt, reason))
        if verdict == "REAP_MERGED" or (verdict == "REAP_STALE" and args.include_stale):
            reap.append((wt, reason))

    print(f"{'VERDIKT':<13} {'BRANCH':<42} GRUND")
    print("-" * 90)
    for verdict, wt, reason in sorted(plan, key=lambda x: x[0]):
        print(f"{verdict:<13} {(wt['branch'] or '(detached)'):<42} {reason}")
    print(f"\n{len(reap)} Worktree(s) zum Entfernen, {len(plan) - len(reap)} behalten.")

    if not reap:
        return 0
    if not args.apply:
        print("\n[dry-run] Nichts entfernt. Mit --apply ausführen.")
        return 0

    mf = Path(args.manifest) if args.manifest else Path.cwd() / "worktree-reaper-manifest.jsonl"
    removed = 0
    with mf.open("a", encoding="utf-8") as f:
        for wt, reason in reap:
            rec = {
                "removed_at": datetime.now(timezone.utc).isoformat(),
                "path": wt["path"], "branch": wt["branch"], "head": wt["head"], "reason": reason,
            }
            rc, out = _run(["git", "worktree", "remove", wt["path"]])
            if rc == 0:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                removed += 1
                print(f"entfernt: {wt['branch']}  (restore: git worktree add {wt['path']} {wt['branch']})")
            else:
                print(f"FEHLER beim Entfernen {wt['path']}: {out}", file=sys.stderr)
    print(f"\n{removed} entfernt · Restore-Manifest: {mf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
