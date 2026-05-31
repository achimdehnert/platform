#!/usr/bin/env bash
# F1 .windsurf-Sweep — untrackt synced .windsurf-Workflows, die auf origin/main als
# Regular File (mode 100644) getrackt sind und ein platform-Pendant haben.
#
#   DRY-RUN (Default): zeigt nur den Plan, ändert nichts.
#   F1_APPLY=1 : git rm --cached + (Klasse C) präzise .gitignore-Zeilen, lokaler Commit.
#   F1_PUSH=1  : zusätzlich Branch pushen + PR öffnen (gh).
#
# Misst IMMER gegen origin/main (frisch gefetcht) — nie gegen stale lokale Trees.
# Fasst platform selbst NIE an. Behält repo-eigene Pfade ohne platform-Pendant (z.B. project-facts.md).
set -uo pipefail
GH="${GITHUB_DIR:-$HOME/github}"
PWF="$GH/platform/.windsurf"
APPLY="${F1_APPLY:-0}"; PUSH="${F1_PUSH:-0}"
BR="chore/untrack-synced-windsurf"

for d in "$GH"/*/; do
  r=$(basename "$d"); [ -d "$d/.git" ] || continue; [ "$r" = platform ] && continue
  git -C "$d" fetch origin main --quiet 2>/dev/null || { echo "$r: fetch FAIL — skip"; continue; }

  # synced 100644-Pfade auf origin/main mit platform-Pendant
  synced=()
  while read -r mode _ _ path; do
    [ "$mode" = 100644 ] || continue
    [ -e "$PWF/${path#.windsurf/}" ] && synced+=("$path")
  done < <(git -C "$d" ls-tree -r origin/main .windsurf 2>/dev/null)
  [ "${#synced[@]}" -eq 0 ] && continue

  blanket=no; grep -qE '^[[:space:]]*\.windsurf/?[[:space:]]*$' "$d/.gitignore" 2>/dev/null && blanket=yes
  echo "== $r : ${#synced[@]} synced (blanket-gitignore=$blanket)"
  [ "$APPLY" = 1 ] || { printf '   would untrack: %s\n' "${synced[@]}"; continue; }

  git -C "$d" switch -C "$BR" origin/main --quiet
  printf '%s\n' "${synced[@]}" | git -C "$d" rm --quiet --cached --pathspec-from-file=-
  if [ "$blanket" = no ]; then
    # präzise je-Pfad-Zeilen, nur fehlende anhängen
    for p in "${synced[@]}"; do grep -qxF "$p" "$d/.gitignore" 2>/dev/null || echo "$p" >> "$d/.gitignore"; done
    git -C "$d" add .gitignore
  fi
  git -C "$d" commit --quiet -m "chore: stop tracking synced .windsurf (platform audit F1)

Untrackt ${#synced[@]} synced .windsurf-Workflows (mode 100644 auf origin, on-disk Symlinks
-> typechange-dirty). Inhalt lebt in platform-SSoT. Setzt voraus: sync-workflows-to-repos.yml
retired (ADR-230-Rollout), sonst re-committet die CI sie wieder.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  # Gate
  dirty=$(git -C "$d" status --porcelain .windsurf | wc -l)
  echo "   committed; .windsurf dirty nachher=$dirty (muss 0)"
  if [ "$PUSH" = 1 ] && [ "$dirty" -eq 0 ]; then
    git -C "$d" push -u origin "$BR" --quiet && \
    gh -R "achimdehnert/$r" pr create --base main --head "$BR" \
      --title "chore: stop tracking synced .windsurf (platform audit F1)" \
      --body "Platform-Audit F1 (platform#359). Untrackt ${#synced[@]} synced .windsurf-Workflows. Voraussetzung: sync-workflows-to-repos.yml retired (ADR-230). Review via Windsurf." 2>&1 | tail -1
  fi
done
