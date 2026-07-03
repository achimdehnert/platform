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

# PR-Kollisionscheck (ADR-233 R-6; Retro-Gate `parallel-session-pr-collision`, ≥2× → Gate-Pflicht).
# Billigster Check VOR dem Abzweigen: existiert für denselben Task-Slug schon ein offener PR
# (= zweite Session am selben Thema), harter Block. Sonst offene PRs zur Awareness listen.
# Fail-open NUR bei fehlendem Werkzeug/Auth (mit sichtbarem Hinweis) — nie stiller Durchlass.
# Override für bewusst parallele Arbeit: REPO_SESSION_SKIP_PR_CHECK=1.
check_pr_collision() {
  local repo="$1" task="$2"
  if [ "${REPO_SESSION_SKIP_PR_CHECK:-0}" = "1" ]; then
    echo "  ⚠ PR-Kollisionscheck übersprungen (REPO_SESSION_SKIP_PR_CHECK=1)." >&2; return 0
  fi
  command -v gh >/dev/null 2>&1 || { echo "  ⚠ gh nicht verfügbar — PR-Kollisionscheck übersprungen (ADR-233 R-6)." >&2; return 0; }
  local slug_repo; slug_repo="$(git -C "$repo" remote get-url origin 2>/dev/null | sed -E 's#\.git$##; s#.*[:/]([^/]+/[^/]+)$#\1#')"
  [ -n "$slug_repo" ] || { echo "  ⚠ Remote-Slug nicht bestimmbar — PR-Kollisionscheck übersprungen." >&2; return 0; }
  local open_prs; open_prs="$(gh pr list -R "$slug_repo" --state open --json number,headRefName,title 2>/dev/null)" \
    || { echo "  ⚠ 'gh pr list' fehlgeschlagen (Auth?) — PR-Kollisionscheck übersprungen." >&2; return 0; }
  if [ -z "$open_prs" ] || [ "$open_prs" = "[]" ]; then return 0; fi
  # Exakter Task-Slug im head-branch eines offenen PR = harter Block.
  local hit
  hit="$(printf '%s' "$open_prs" | python3 -c "import json,sys; t=sys.argv[1]; d=json.load(sys.stdin); print('\n'.join(f\"#{p['number']} {p['headRefName']} — {p['title']}\" for p in d if t and t in p['headRefName']))" "$task")"
  if [ -n "$hit" ]; then
    {
      echo "⛔ PR-Kollision (ADR-233 R-6, Retro-Gate parallel-session-pr-collision):"
      echo "   Offene PR(s) mit Task-Slug '$task':"
      printf '   %s\n' "$hit"
      echo "   → mergen/schließen ODER anderen --task-Slug wählen ODER REPO_SESSION_SKIP_PR_CHECK=1 (bewusst parallel)."
    } >&2
    die "Task '$task' hat bereits offene PR(s) — Kollisionsgefahr (siehe oben)."
  fi
  # Sonst: offene PRs zur Awareness (weich, kein Block).
  local n; n="$(printf '%s' "$open_prs" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))')"
  {
    echo "  ℹ $n offene PR(s) in $slug_repo — auf Scope-Überlappung achten:"
    printf '%s' "$open_prs" | python3 -c "import json,sys;[print(f\"     #{p['number']} {p['headRefName']}\") for p in json.load(sys.stdin)]"
  } >&2
}

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

  # ADR-233 R-6: vor dem Abzweigen auf offene PRs desselben Task-Slugs prüfen (Retro-Gate).
  check_pr_collision "$repo" "$task"

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
  -h|--help|help) echo "usage: repo-session.sh {start <repo> --task <slug> [--base <ref>] [--ephemeral] | list | end <wt>}"; exit 0;;
  *) echo "usage: repo-session.sh {start <repo> --task <slug> [--base <ref>] [--ephemeral] | list | end <wt>}" >&2; exit 2;;
esac
