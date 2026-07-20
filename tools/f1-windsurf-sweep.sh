#!/usr/bin/env bash
# F1 .windsurf-Sweep — API-BASIERT, ORG-AGNOSTISCH. Untrackt synced .windsurf-Workflows OHNE
# jeden lokalen Checkout zu berühren: alles via GitHub-API gegen origin/main (Branch + Tree-Delete
# (+ .gitignore-Blanket für Klasse C) + Commit + PR). Immun gegen dirty/konfliktbehaftete/parallel
# bearbeitete lokale Trees (Audit-F3). Owner wird PRO REPO aus dem Remote aufgelöst (achimdehnert,
# ttz-lif, meiki-lra, iilgmbh, …) — keine hardcodierte Org.
#
#   DRY-RUN (Default):  nur API-Reads, zeigt Plan (löschen + ggf. .gitignore-Ergänzung). Keine Writes.
#   F1_APPLY=1 :        Branch + Tree-Delete(+gitignore)-Commit + PR via API.
#   F1_MERGE=1 :        zusätzlich `pr merge --squash --admin` (bewusster Bypass der orthogonalen,
#                       separat behandelten roten Consumer-CI — nur für den verifiziert-orthogonalen Untrack).
#   F1_ONLY=<repo> :    nur dieses eine Repo.
#
# Gelöscht werden nur mode-100644-.windsurf-Blobs mit platform-Pendant (synced). Symlink-getrackte
# (120000) + repo-eigene (z.B. project-facts.md, kein platform-Pendant) bleiben. Klasse C (kein
# blanket-.windsurf/ in .gitignore) bekommt im selben Commit `.windsurf/` ergänzt (beeinflusst
# getrackte Dateien NICHT → project-facts.md bleibt). platform + EXCLUDE_TEMP + archivierte werden nie angefasst.
set -uo pipefail
GH="${GITHUB_DIR:-$HOME/github}"
PWF="$GH/platform/.windsurf"
APPLY="${F1_APPLY:-0}"; MERGE="${F1_MERGE:-0}"; ONLY="${F1_ONLY:-}"
BR="chore/untrack-synced-windsurf"

# --- TEMPORÄRE Exclude-Liste — Repos mit AKTIVER Arbeit (nach Abschluss ENTFERNEN!) ---
#   (leer 2026-06-06: dev-hub-Sweep abgeschlossen — die aktive Session von 2026-06-01 ist
#    aufgelöst, PR #56/Traefik berührt kein .windsurf; F1-Flotte damit vollständig.)
EXCLUDE_TEMP=""

for d in "$GH"/*/; do
  rn=$(basename "$d"); [ -d "$d/.git" ] || continue; [ "$rn" = platform ] && continue
  [ -n "$ONLY" ] && [ "$rn" != "$ONLY" ] && continue
  for x in $EXCLUDE_TEMP; do [ "$rn" = "$x" ] && { echo "== $rn : SKIP (temp-exclude — aktiv bearbeitet)"; continue 2; }; done

  # Owner/Repo aus Remote (lokal, read-only) — org-agnostisch
  slug=$(git -C "$d" remote get-url origin 2>/dev/null | sed -E 's#\.git$##' | grep -oE '[^/:]+/[^/:]+$')
  [ -z "$slug" ] && { echo "== $rn : SKIP (kein origin-Remote)"; continue; }
  OR="$slug"   # owner/repo

  # existiert + nicht archiviert?
  arch=$(gh api "repos/$OR" -q '.archived' 2>/dev/null) || { echo "== $rn : SKIP (Repo nicht via API erreichbar: $OR)"; continue; }
  [ "$arch" = true ] && { echo "== $rn : SKIP (archiviert, read-only)"; continue; }

  main_sha=$(gh api "repos/$OR/commits/main" -q .sha 2>/dev/null) || { echo "== $rn : SKIP (kein main)"; continue; }
  base_tree=$(gh api "repos/$OR/commits/$main_sha" -q .commit.tree.sha 2>/dev/null) || { echo "== $rn : SKIP (tree-Fehler)"; continue; }

  mapfile -t synced < <(
    gh api "repos/$OR/git/trees/$main_sha?recursive=1" \
      -q '.tree[] | select(.type=="blob" and .mode=="100644" and (.path|startswith(".windsurf/"))) | .path' 2>/dev/null \
    | while read -r p; do
        # project-facts.md ist per-Repo AUTHORED (eigener Inhalt: Repo-Name/Typ/PyPI),
        # nicht aus platform synced — platform hat zwar ein gleichnamiges Pendant, aber
        # der Pfad-Match ist ein FALSE POSITIVE. NIE löschen (sonst geht repo-spezifischer
        # Inhalt verloren — Realfall iil-voice-agent 2026-06-24). Memory: F1-Tool-Bug.
        case "$p" in */project-facts.md) continue;; esac
        [ -e "$PWF/${p#.windsurf/}" ] && printf '%s\n' "$p"
      done )
  [ "${#synced[@]}" -eq 0 ] && { echo "== $rn : 0 synced — skip"; continue; }

  # blanket-.windsurf/ in origin-.gitignore?  (API, nicht lokal)
  gi=$(gh api "repos/$OR/contents/.gitignore?ref=main" -q .content 2>/dev/null | base64 -d 2>/dev/null || true)
  blanket=no; printf '%s\n' "$gi" | grep -qE '^[[:space:]]*\.windsurf/?[[:space:]]*$' && blanket=yes
  klasse=A; [ "$blanket" = no ] && klasse=C
  echo "== $rn ($OR) : ${#synced[@]} synced · blanket=$blanket · Klasse $klasse"

  if [ "$APPLY" != 1 ]; then
    printf '   would delete: %s\n' "${synced[@]}"
    [ "$klasse" = C ] && echo "   would add to .gitignore: .windsurf/"
    continue
  fi

  # Klasse C: neuen .gitignore-Blob (blanket .windsurf/ ergänzen) erzeugen
  gi_sha=""
  if [ "$klasse" = C ]; then
    newgi=$(printf '%s\n%s\n' "${gi%$'\n'}" ".windsurf/" | sed '/^$/N;/^\n$/D')
    gi_sha=$(gh api -X POST "repos/$OR/git/blobs" -f content="$newgi" -f encoding=utf-8 -q .sha 2>/dev/null) \
      || { echo "   FEHLER: .gitignore-Blob"; continue; }
  fi

  payload=$(python3 -c '
import json,sys
base=sys.argv[1]; gi=sys.argv[2]; paths=sys.argv[3:]
tree=[{"path":p,"mode":"100644","type":"blob","sha":None} for p in paths]
if gi: tree.append({"path":".gitignore","mode":"100644","type":"blob","sha":gi})
print(json.dumps({"base_tree":base,"tree":tree}))' "$base_tree" "$gi_sha" "${synced[@]}")
  new_tree=$(printf '%s' "$payload" | gh api -X POST "repos/$OR/git/trees" --input - -q .sha 2>/dev/null) \
    || { echo "   FEHLER: tree create"; continue; }

  gi_note=""; [ "$klasse" = C ] && gi_note=" + .gitignore: .windsurf/"
  msg="chore: stop tracking synced .windsurf (platform audit F1)

Untrackt ${#synced[@]} synced .windsurf-Workflows$gi_note (origin/main, API-basiert — kein
lokaler Checkout berührt). Inhalt lebt in platform-SSoT. Voraussetzung: sync-workflows-to-repos.yml
retired (ADR-230, platform#364). Reiner Tooling-Cleanup, keine Anwendungs-/Mandantendaten.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  new_commit=$(gh api -X POST "repos/$OR/git/commits" \
      -f message="$msg" -f tree="$new_tree" -f "parents[]=$main_sha" -q .sha 2>/dev/null) \
    || { echo "   FEHLER: commit create"; continue; }
  gh api -X POST "repos/$OR/git/refs" -f ref="refs/heads/$BR" -f sha="$new_commit" >/dev/null 2>&1 \
    || gh api -X PATCH "repos/$OR/git/refs/heads/$BR" -f sha="$new_commit" -F force=true >/dev/null 2>&1
  pr=$(gh -R "$OR" pr create --base main --head "$BR" \
        --title "chore: stop tracking synced .windsurf (platform audit F1)" \
        --body "Platform-Audit F1 (platform#359). Untrackt ${#synced[@]} synced .windsurf-Workflows$gi_note (API-basiert, kein lokaler Checkout). Voraussetzung: sync-workflows-to-repos.yml retired (ADR-230, #364). Reiner Tooling-Cleanup, keine Mandantendaten. Orthogonal zur Consumer-CI. Review via Windsurf." 2>&1 | tail -1)
  echo "   PR: $pr"
  [ "$MERGE" = 1 ] && gh -R "$OR" pr merge "$BR" --squash --admin --delete-branch 2>&1 | sed 's/^/   merge: /' | tail -1
done
