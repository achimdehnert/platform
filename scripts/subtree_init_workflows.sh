#!/usr/bin/env bash
# subtree_init_workflows.sh — Workflows als Subtree in alle Repos einbinden.
#
# Voraussetzung: Branch `workflows-dist` existiert auf origin
# (= git subtree split --prefix=.windsurf/workflows -b workflows-dist + push).
#
# Pro Repo:
#   1. tracked Workflow-Files entfernen (git rm)
#   2. Filesystem-Symlinks weg
#   3. git subtree add --prefix=.windsurf/workflows --squash
#
# Usage:
#   ./subtree_init_workflows.sh --dry-run                          # zeigen was getan würde
#   ./subtree_init_workflows.sh --apply                            # ausführen ohne push
#   ./subtree_init_workflows.sh --apply --push                     # incl. push
#   ./subtree_init_workflows.sh --apply --repos bfagent,risk-hub   # nur ausgewählte Repos

set -euo pipefail
GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
REMOTE_URL="${SUBTREE_REMOTE:-git@github.com:achimdehnert/platform.git}"
BRANCH="${SUBTREE_BRANCH:-workflows-dist}"
PREFIX=".windsurf/workflows"
SSH_CMD="${GIT_SSH_COMMAND:-ssh -i $HOME/.ssh/id_ed25519 -o BatchMode=yes}"

MODE=""
DO_PUSH=0
REPOS_FILTER=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) MODE=dry-run; shift;;
    --apply)   MODE=apply; shift;;
    --push)    DO_PUSH=1; shift;;
    --repos)   REPOS_FILTER="$2"; shift 2;;
    *) echo "Unknown: $1"; exit 1;;
  esac
done

[[ -z "$MODE" ]] && { echo "Usage: $0 --dry-run | --apply [--push] [--repos a,b,c]"; exit 1; }

# Liste aller Repos
candidate_repos=()
if [[ -n "$REPOS_FILTER" ]]; then
  IFS=',' read -ra candidate_repos <<< "$REPOS_FILTER"
else
  for d in "$GITHUB_DIR"/*/; do
    name=$(basename "$d")
    [[ "$name" == *.* ]] && continue
    [[ "$name" == "platform" ]] && continue
    [[ -d "$d/.windsurf/workflows" ]] || continue
    candidate_repos+=("$name")
  done
fi

echo "Target: ${#candidate_repos[@]} Repos · Modus: $MODE · Push: $DO_PUSH"
echo

ok=0; skip=0; fail=0
for name in "${candidate_repos[@]}"; do
  repo="$GITHUB_DIR/$name"
  [[ -d "$repo/.git" ]] || { echo "✗ $name: kein git-Repo"; skip=$((skip+1)); continue; }

  # Schon Subtree?
  if git -C "$repo" log --grep="Squashed '$PREFIX/'" --oneline | head -1 | grep -q .; then
    echo "⊙ $name: schon als Subtree" ; skip=$((skip+1)); continue
  fi

  # Hat es überhaupt einen Workflow-Pfad mit Symlinks zu platform?
  has_symlinks=$(find "$repo/$PREFIX" -maxdepth 1 -type l 2>/dev/null | head -1)
  has_tracked=$(git -C "$repo" ls-files "$PREFIX/" 2>/dev/null | head -1)
  if [[ -z "$has_symlinks" && -z "$has_tracked" ]]; then
    echo "⊙ $name: keine Workflow-Files" ; skip=$((skip+1)); continue
  fi

  echo "▶ $name"

  if [[ "$MODE" == "dry-run" ]]; then
    echo "    würde: git rm + rm -rf $PREFIX + subtree add"
    continue
  fi

  cd "$repo"
  branch=$(git branch --show-current)
  has_upstream=0
  git rev-parse --abbrev-ref "$branch@{u}" >/dev/null 2>&1 && has_upstream=1

  # 0. Stash uncommitted + FF zu remote (nur wenn upstream existiert)
  if [[ $has_upstream -eq 1 ]]; then
    GIT_SSH_COMMAND="$SSH_CMD" git fetch origin >/dev/null 2>&1 || true
    if [[ -n "$(git status --porcelain)" ]]; then
      git stash push --include-untracked -m "subtree-init-stash" >/dev/null 2>&1 || true
    fi
    if ! git merge --ff-only "origin/$branch" >/dev/null 2>&1; then
      git stash pop >/dev/null 2>&1 || true
      echo "    ⚠ remote ahead/diverged (echt) — skip (manuell rebase nötig)"
      fail=$((fail+1)); continue
    fi
    git stash drop >/dev/null 2>&1 || true
  else
    # Feature-Branch ohne upstream — stash uncommitted, proceed lokal
    if [[ -n "$(git status --porcelain)" ]]; then
      git stash push --include-untracked -m "subtree-init-stash" >/dev/null 2>&1 || true
      git stash drop >/dev/null 2>&1 || true
    fi
  fi
  # 1. tracked Files raus (wenn überhaupt tracked)
  if [[ -n "$has_tracked" ]]; then
    git rm -rf "$PREFIX/" >/dev/null 2>&1 || true
    git commit -m "chore: remove tracked workflow files (replace with subtree)" >/dev/null 2>&1 || true
  fi
  # 2. Filesystem leeren (Symlinks + Reste)
  rm -rf "$PREFIX"

  # 3. subtree add
  if ! GIT_SSH_COMMAND="$SSH_CMD" git subtree add --prefix="$PREFIX" "$REMOTE_URL" "$BRANCH" --squash >/dev/null 2>&1; then
    echo "    ✗ subtree add failed" ; fail=$((fail+1)); continue
  fi

  # 4. Push (nur wenn upstream existiert + DO_PUSH gesetzt)
  pushed=0
  if [[ $DO_PUSH -eq 1 && $has_upstream -eq 1 ]]; then
    if GIT_SSH_COMMAND="$SSH_CMD" git push origin "$branch" >/dev/null 2>&1; then
      pushed=1
    else
      echo "    ⚠ subtree OK, push failed" ; fail=$((fail+1)); continue
    fi
  fi

  ok=$((ok+1))
  if [[ $pushed -eq 1 ]]; then
    echo "    ✅ subtree eingebunden + pushed"
  elif [[ $has_upstream -eq 0 ]]; then
    echo "    ✅ subtree eingebunden (lokal — kein upstream auf $branch)"
  else
    echo "    ✅ subtree eingebunden"
  fi
done

echo
echo "── Zusammenfassung ── ✅ $ok · ⊙ $skip · ✗ $fail"
