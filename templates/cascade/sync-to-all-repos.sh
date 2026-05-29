#!/usr/bin/env bash
# Cascade Config Sync — Single Source of Truth → alle Repos
#
# Syncs ~/github/platform/templates/cascade/.windsurfignore (Master)
# in jeden Git-Repo unter ~/github und ~/shared.
#
# Idempotent: schreibt nur wenn Diff. Behält Backup wenn Override.
#
# Usage:
#   sync-to-all-repos.sh              # echter Run
#   sync-to-all-repos.sh --dry-run    # zeigt was passieren würde
#   sync-to-all-repos.sh --verbose    # zeigt auch unveränderte

set -euo pipefail

MASTER_DIR="${HOME}/github/platform/templates/cascade"
MASTER_IGNORE="${MASTER_DIR}/.windsurfignore"
SEARCH_ROOTS=("${HOME}/github" "${HOME}/shared")

DRY_RUN=0
VERBOSE=0
for arg in "$@"; do
  case "$arg" in
    --dry-run|-n) DRY_RUN=1 ;;
    --verbose|-v) VERBOSE=1 ;;
    -h|--help)
      sed -n '2,15p' "$0" | sed 's/^# //;s/^#//'
      exit 0 ;;
  esac
done

if [ ! -f "$MASTER_IGNORE" ]; then
  echo "FEHLER: Master nicht gefunden: $MASTER_IGNORE" >&2
  exit 1
fi

created=0
updated=0
unchanged=0
skipped=0

while IFS= read -r gitdir; do
  d=$(dirname "$gitdir")
  name=$(basename "$d")
  target="$d/.windsurfignore"

  # Skip wenn Repo selbst der Master ist
  if [ "$d" = "${HOME}/github/platform" ]; then
    if [ "$VERBOSE" = "1" ]; then echo "SKIP    $name (Master-Repo)"; fi
    skipped=$((skipped + 1))
    continue
  fi

  if [ ! -f "$target" ]; then
    if [ "$DRY_RUN" = "1" ]; then
      echo "WOULD-CREATE  $name"
    else
      cp "$MASTER_IGNORE" "$target"
      echo "CREATE        $name"
    fi
    created=$((created + 1))
  elif ! cmp -s "$target" "$MASTER_IGNORE"; then
    if [ "$DRY_RUN" = "1" ]; then
      echo "WOULD-UPDATE  $name"
    else
      cp "$target" "${target}.bak.$(date +%Y%m%d-%H%M%S)"
      cp "$MASTER_IGNORE" "$target"
      echo "UPDATE        $name (backup → .bak)"
    fi
    updated=$((updated + 1))
  else
    if [ "$VERBOSE" = "1" ]; then echo "OK            $name"; fi
    unchanged=$((unchanged + 1))
  fi
done < <(find "${SEARCH_ROOTS[@]}" -mindepth 2 -maxdepth 4 -name ".git" -type d 2>/dev/null)

echo "==="
echo "$(date -Iseconds)  master=$MASTER_IGNORE"
if [ "$DRY_RUN" = "1" ]; then
  echo "DRY-RUN: would create=$created  would update=$updated  unchanged=$unchanged  skipped=$skipped"
else
  echo "Result:  created=$created  updated=$updated  unchanged=$unchanged  skipped=$skipped"
fi
