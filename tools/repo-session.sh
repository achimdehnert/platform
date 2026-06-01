#!/usr/bin/env bash
# repo-session — verbindlicher Entry Point fuer editierende Coding-Sessions (ADR-233).
#
# Statt im geteilten Haupt-Tree den Branch zu wechseln (HEAD-Flip-Kollision), legt
# jede editierende Session hier einen isolierten git-Worktree VON origin/main an,
# mit deterministischem Branch-Schema und einer maschinenlesbaren Lease, die der
# worktree-reaper konsumiert. Der Haupt-Tree bleibt "heilig" auf main.
#
# Usage:
#   repo-session.sh start <repo-path> --task <slug> [--base <ref>] [--ephemeral]
#   repo-session.sh list
#   repo-session.sh end <worktree-path>        # Worktree entfernen (nur wenn clean), Lease schliessen
#
# Lease-Felder (ADR-233 §2.4): session_id, owner, created_at, last_touch, branch,
#   base_sha, repo, worktree, intended_pr, expires_at, ephemeral.
#
# Env:
#   REPO_SESSION_DIR   (default ~/.repo-session)  — Leases + Worktree-Wurzel
#   REPO_SESSION_TTL_DAYS (default 7)             — expires_at = created_at + TTL
set -euo pipefail

ROOT="${REPO_SESSION_DIR:-$HOME/.repo-session}"
LEASE_DIR="$ROOT/leases"
WT_ROOT="$ROOT/worktrees"
EPHEMERAL_ROOT="/tmp/repo-session"   # ADR-233 R-5: /tmp nur fuer ephemere
TTL_DAYS="${REPO_SESSION_TTL_DAYS:-7}"

die() { echo "FEHLER: $*" >&2; exit 1; }

slug() { printf '%s' "$1" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9._-'; }

cmd_start() {
  local repo="" task="" base="origin/main" ephemeral="false"
  repo="${1:-}"; shift || true
  while [ $# -gt 0 ]; do
    case "$1" in
      --task) task="$2"; shift 2;;
      --base) base="$2"; shift 2;;
      --ephemeral) ephemeral="true"; shift;;
      *) die "unbekannte Option: $1";;
    esac
  done
  [ -n "$repo" ] || die "repo-path fehlt"
  [ -n "$task" ] || die "--task <slug> fehlt"
  [ -d "$repo/.git" ] || repo="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || die "kein git-Repo: $repo"

  # Haupt-Tree heilig: muss auf main stehen, bevor wir abzweigen.
  local cur; cur="$(git -C "$repo" rev-parse --abbrev-ref HEAD)"
  [ "$cur" = "main" ] || die "Haupt-Tree ($repo) ist auf '$cur', nicht 'main' — heiliger Tree verletzt (ADR-233)."

  git -C "$repo" fetch --prune origin main -q
  local base_sha; base_sha="$(git -C "$repo" rev-parse "$base")" || die "base_ref '$base' nicht auflösbar"

  local owner date_s rname branch wt sid
  owner="$(slug "$(git -C "$repo" config user.name 2>/dev/null || echo agent)")"; owner="${owner:-agent}"
  date_s="$(date -u +%Y-%m-%d)"
  rname="$(basename "$repo")"
  task="$(slug "$task")"
  branch="session/$date_s/$owner/$task"
  sid="${date_s}-${owner}-${task}-$(date -u +%H%M%S)"
  if [ "$ephemeral" = "true" ]; then
    wt="$EPHEMERAL_ROOT/$rname/$sid"
  else
    wt="$WT_ROOT/$rname/$sid"
  fi
  mkdir -p "$(dirname "$wt")" "$LEASE_DIR"

  git -C "$repo" worktree add -b "$branch" "$wt" "$base" >&2 \
    || die "worktree add fehlgeschlagen (Branch '$branch' evtl. vergeben?)"

  local now exp lease
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  exp="$(date -u -d "+${TTL_DAYS} days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
  lease="$LEASE_DIR/$sid.json"
  cat > "$lease" <<JSON
{
  "session_id": "$sid",
  "owner": "$owner",
  "repo": "$rname",
  "branch": "$branch",
  "base_sha": "$base_sha",
  "worktree": "$wt",
  "created_at": "$now",
  "last_touch": "$now",
  "expires_at": "$exp",
  "intended_pr": null,
  "ephemeral": $ephemeral
}
JSON
  echo "$wt"                 # stdout = Worktree-Pfad (zum cd)
  {
    echo "✓ Session-Worktree angelegt (ADR-233):"
    echo "  Branch : $branch  (von $base @ ${base_sha:0:12})"
    echo "  Pfad   : $wt"
    echo "  Lease  : $lease  (expires $exp, ephemeral=$ephemeral)"
    echo "  cd \"$wt\""
  } >&2
}

cmd_list() {
  [ -d "$LEASE_DIR" ] || { echo "keine Leases."; return 0; }
  local n=0
  for l in "$LEASE_DIR"/*.json; do
    [ -e "$l" ] || continue
    n=$((n+1))
    python3 - "$l" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print(f"- {d['branch']:48} {d['worktree']}  (exp {d['expires_at']}, eph={d['ephemeral']})")
PY
  done
  echo "$n Lease(s)."
}

cmd_end() {
  local wt="${1:-}"; [ -n "$wt" ] || die "worktree-path fehlt"
  local repo; repo="$(git -C "$wt" rev-parse --path-format=absolute --git-common-dir 2>/dev/null | sed 's#/\.git$##')" || true
  # Dirty-Guard: nie einen Tree mit uncommitted changes entfernen
  if [ -n "$(git -C "$wt" status --porcelain 2>/dev/null)" ]; then
    die "Worktree $wt ist DIRTY — erst committen/pushen (Guard)."
  fi
  git -C "$wt" worktree remove "$wt" 2>/dev/null || git worktree remove "$wt"
  # Lease schliessen
  for l in "$LEASE_DIR"/*.json; do
    [ -e "$l" ] || continue
    grep -q "\"worktree\": \"$wt\"" "$l" && mv "$l" "$l.closed" && echo "Lease geschlossen: $l.closed"
  done
  echo "Worktree entfernt: $wt (Branch bleibt erhalten)"
}

case "${1:-}" in
  start) shift; cmd_start "$@";;
  list)  cmd_list;;
  end)   shift; cmd_end "$@";;
  *) echo "usage: repo-session.sh {start <repo> --task <slug> [--base <ref>] [--ephemeral] | list | end <wt>}" >&2; exit 2;;
esac
