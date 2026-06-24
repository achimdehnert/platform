#!/usr/bin/env bash
# worktree-reaper-all — geplanter GC über ALLE Repos mit Session-Worktrees (ADR-233).
#
# Schließt die Akkumulations-Wurzel des Längsschnitt-Slugs `worktree-orphan-accumulation`
# (≥2× über session-retros, retro_kpis.py → gate-pflichtig): `tools/worktree-reaper.py`
# räumt gemergte Worktrees korrekt, lief aber NIRGENDS automatisch mit `--apply` — nur
# als Dry-Run am `repo-session end`/session-ende, der nur den EINEN übergebenen Tree
# behandelt. Orphans aus `gh pr merge` ohne `end` blieben für immer liegen (Realfall
# 2026-06-24: 3 gemergte Worktrees + offene Leases zurück bis 2026-06-10).
#
# Dieser Wrapper iteriert die Repos, die tatsächlich Session-Worktrees haben, und ruft
# den Reaper je Repo konservativ mit `--apply`.
#
# Konservativ by design (worktree-reaper.py):
#   - nur REAP_MERGED (KEIN --include-stale) → entfernt ausschließlich Worktrees mit
#     squash-aware gemergtem PR; stale-but-unmerged wird nur gemeldet.
#   - Dirty-Guard: uncommitted changes → nie angefasst.
#   - unknown (gh fehlt/Fehler) → KEEP.
#   - Branches/Remote werden NIE verändert; jede Entfernung in ein Restore-Manifest.
#
# Aufruf: per systemd --user Timer (worktree-reaper.timer) oder manuell.
# Env-Overrides: GITHUB_DIR, WORKTREE_REAPER, WORKTREE_REAPER_LOG, REPO_SESSION_DIR.
set -euo pipefail

GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
REAPER="${WORKTREE_REAPER:-$GITHUB_DIR/platform/tools/worktree-reaper.py}"
REPO_SESSION_DIR="${REPO_SESSION_DIR:-$HOME/.repo-session}"
LOG="${WORKTREE_REAPER_LOG:-$REPO_SESSION_DIR/reaper.log}"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

mkdir -p "$(dirname "$LOG")"

[ -f "$REAPER" ] || { echo "$(ts) FEHLER: Reaper nicht gefunden: $REAPER" | tee -a "$LOG" >&2; exit 1; }

# Repos mit registrierten Session-Worktrees ableiten (Unterordner unter worktrees/).
wt_root="$REPO_SESSION_DIR/worktrees"
[ -d "$wt_root" ] || { echo "$(ts) keine Worktree-Wurzel ($wt_root) — nichts zu tun" >>"$LOG"; exit 0; }

repos="$(find "$wt_root" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null || true)"
[ -n "$repos" ] || { echo "$(ts) keine Session-Worktrees — nichts zu tun" >>"$LOG"; exit 0; }

echo "=== $(ts) worktree-reaper-all start ===" >>"$LOG"
rc_total=0
for rname in $repos; do
  repo_path="$GITHUB_DIR/$rname"
  if [ ! -d "$repo_path/.git" ]; then
    echo "$(ts) SKIP $rname — kein git-Repo unter $repo_path" >>"$LOG"
    continue
  fi
  echo "--- $(ts) reaping $rname ---" >>"$LOG"
  # Reaper liest worktrees + gh-Repo aus cwd → im Repo-Verzeichnis ausführen.
  if ! ( cd "$repo_path" && python3 "$REAPER" --apply ) >>"$LOG" 2>&1; then
    rc_total=1
    echo "$(ts) FEHLER reaper in $rname" >>"$LOG"
  fi
done
echo "=== $(ts) worktree-reaper-all done (rc=$rc_total) ===" >>"$LOG"
exit "$rc_total"
