#!/usr/bin/env bash
# subtree_update_workflows.sh — Workflows-Subtree-Branch refreshen + Repos pullen.
#
# Workflow:
#   1. In platform: workflows-Änderungen committen + push (normal)
#   2. Dieses Script: split + push workflows-dist Branch
#   3. Dieses Script: in jedem Target-Repo `git subtree pull` (squashed)
#
# Usage:
#   ./subtree_update_workflows.sh                         # alle Repos pullen
#   ./subtree_update_workflows.sh --push                  # incl. push pro Repo
#   ./subtree_update_workflows.sh --repos a,b,c           # nur diese
#   ./subtree_update_workflows.sh --skip-split            # split überspringen

set -euo pipefail
GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
PLATFORM="$GITHUB_DIR/platform"
REMOTE_URL="${SUBTREE_REMOTE:-git@github.com:achimdehnert/platform.git}"
BRANCH="${SUBTREE_BRANCH:-workflows-dist}"
PREFIX=".windsurf/workflows"
SSH_CMD="${GIT_SSH_COMMAND:-ssh -i $HOME/.ssh/id_ed25519 -o BatchMode=yes}"

DO_PUSH=0
SKIP_SPLIT=0
REPOS_FILTER=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --push)        DO_PUSH=1; shift;;
    --skip-split)  SKIP_SPLIT=1; shift;;
    --repos)       REPOS_FILTER="$2"; shift 2;;
    *) echo "Unknown: $1"; exit 1;;
  esac
done

# Step 1: subtree split refreshen
if [[ $SKIP_SPLIT -eq 0 ]]; then
  echo "▶ platform: subtree split → $BRANCH"
  cd "$PLATFORM"
  git subtree split --prefix="$PREFIX" -b "$BRANCH" >/dev/null
  GIT_SSH_COMMAND="$SSH_CMD" git push origin "$BRANCH" --force-with-lease 2>&1 | tail -2
fi

# Step 2: per Repo pull
candidate_repos=()
if [[ -n "$REPOS_FILTER" ]]; then
  IFS=',' read -ra candidate_repos <<< "$REPOS_FILTER"
else
  for d in "$GITHUB_DIR"/*/; do
    name=$(basename "$d")
    [[ "$name" == *.* || "$name" == "platform" ]] && continue
    git -C "$d" log --grep="Squashed '$PREFIX/'" --oneline 2>/dev/null | head -1 | grep -q . && \
      candidate_repos+=("$name")
  done
fi

echo "Target: ${#candidate_repos[@]} Subtree-Repos · Push: $DO_PUSH"
echo

ok=0; nop=0; fail=0
for name in "${candidate_repos[@]}"; do
  repo="$GITHUB_DIR/$name"
  cd "$repo"
  before=$(git rev-parse HEAD)
  if ! GIT_SSH_COMMAND="$SSH_CMD" git subtree pull --prefix="$PREFIX" "$REMOTE_URL" "$BRANCH" --squash -m "chore: sync $PREFIX from platform" >/dev/null 2>&1; then
    echo "✗ $name: pull failed" ; ((fail++)); continue
  fi
  after=$(git rev-parse HEAD)
  if [[ "$before" == "$after" ]]; then
    echo "⊙ $name: up-to-date" ; ((nop++)); continue
  fi
  if [[ $DO_PUSH -eq 1 ]]; then
    branch=$(git branch --show-current)
    GIT_SSH_COMMAND="$SSH_CMD" git push origin "$branch" >/dev/null 2>&1 && \
      echo "✅ $name: pulled + pushed" || echo "⚠ $name: pulled, push failed"
  else
    echo "✅ $name: pulled (lokal)"
  fi
  ((ok++))
done

echo
echo "── ✅ $ok aktualisiert · ⊙ $nop up-to-date · ✗ $fail Fehler"
