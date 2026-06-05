#!/usr/bin/env bash
# main-tree-guard — schützt den "heiligen" Haupt-Tree vor HEAD-Flips (ADR-233 §2.1).
#
# git bietet keinen sauberen PRE-switch-Hook zum harten Blocken. Dieser Guard ist
# darum zweistufig und EHRLICH dokumentiert:
#   1) Enforcer (best effort): als post-checkout-Hook installiert, schnappt er den
#      Haupt-Tree nach einem versehentlichen Branch-Wechsel sofort auf main zurück
#      (symbolic-ref) UND protokolliert ein Guard-Event. Working-Tree-Dateien werden
#      NICHT angefasst (kein Datenverlust) — nur HEAD wird zurückgesetzt + Warnung.
#   2) Metrik: `report` zählt `unauthorized_head_flips` der letzten 30 Tage — die
#      messbare Kill-Gate-Größe aus ADR-233 §8.
#
# Die eigentliche Durchsetzung ist der `repo-session`-Wrapper (verbindlicher Entry
# Point). Dieser Guard ist das Sicherheitsnetz + die Messung dafür.
#
# Usage:
#   main-tree-guard.sh install <repo-path>   # Sentinel + post-checkout-Hook setzen
#   main-tree-guard.sh report  [repo-path]   # unauthorized_head_flips/30d
#   main-tree-guard.sh hook <prev> <new> <flag>   # (intern, von git aufgerufen)
set -euo pipefail

SENTINEL=".git/iil-main-tree-protected"
LOG=".git/iil-guard-events.log"

die() { echo "FEHLER: $*" >&2; exit 1; }

cmd_install() {
  local repo="${1:-}"; [ -n "$repo" ] || die "repo-path fehlt"
  local gitdir; gitdir="$(git -C "$repo" rev-parse --git-dir)" || die "kein git-Repo"
  ( cd "$repo" && touch "$SENTINEL" )
  local hookdir="$gitdir/hooks"; mkdir -p "$hookdir"
  local hook="$hookdir/post-checkout"
  local self; self="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  if [ -e "$hook" ] && ! grep -q 'main-tree-guard' "$hook" 2>/dev/null; then
    die "post-checkout-Hook existiert bereits und ist fremd: $hook — manuell prüfen."
  fi
  cat > "$hook" <<HOOK
#!/usr/bin/env bash
# installed by main-tree-guard (ADR-233)
exec "$self" hook "\$@"
HOOK
  chmod +x "$hook"
  # Nativer pre-commit-Hook (Retro 2026-06-05 #5): aktiviert den precommit-check OHNE das
  # Python-pre-commit-Framework (das oft nicht installiert ist → Guard war dormant, #5 rutschte durch).
  local pchook="$hookdir/pre-commit"
  if [ -e "$pchook" ] && ! grep -q 'main-tree-guard' "$pchook" 2>/dev/null; then
    echo "  ⚠️  pre-commit-Hook existiert bereits und ist fremd: $pchook — NICHT überschrieben." >&2
    echo "      (Nutzt du das pre-commit-Framework, ist der Check via .pre-commit-config.yaml aktiv.)" >&2
  else
    cat > "$pchook" <<HOOK
#!/usr/bin/env bash
# installed by main-tree-guard (ADR-233) — nativer Backstop, kein Framework nötig
exec "$self" precommit-check
HOOK
    chmod +x "$pchook"
    echo "✓ nativer pre-commit-Hook gesetzt."
  fi
  echo "✓ Guard installiert: Sentinel $repo/$SENTINEL + post-checkout- + pre-commit-Hook."
  echo "  Hinweis: harte Commit-Blockade jetzt auch ohne pre-commit-Framework (nativer Hook)."
}

# git post-checkout args: <prev-HEAD> <new-HEAD> <branch-checkout-flag(1=branch,0=file)>
cmd_hook() {
  local prev="${1:-}" new="${2:-}" flag="${3:-0}"
  # nur Branch-Checkouts interessieren (flag=1); File-Checkouts ignorieren
  [ "$flag" = "1" ] || exit 0
  # nur im geschützten Haupt-Tree aktiv
  [ -e "$SENTINEL" ] || exit 0
  local head; head="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || echo DETACHED)"
  if [ "$head" != "main" ]; then
    local ts; ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "$ts unauthorized_head_flip from=$prev to=$new head=$head" >> "$LOG"
    git symbolic-ref HEAD refs/heads/main 2>/dev/null || true
    echo "⚠️  main-tree-guard (ADR-233): Haupt-Tree ist heilig — HEAD auf 'main' zurückgesetzt." >&2
    echo "    Für editierende Arbeit: 'repo-session start <repo> --task <slug>' nutzen." >&2
    echo "    (Working-Tree-Dateien unverändert; Event protokolliert in $LOG)" >&2
  fi
  exit 0
}

cmd_report() {
  local repo="${1:-.}"
  local gitdir; gitdir="$(git -C "$repo" rev-parse --git-dir)" || die "kein git-Repo"
  local log="$gitdir/iil-guard-events.log"
  if [ ! -e "$log" ]; then echo "unauthorized_head_flips/30d: 0 (kein Log)"; return 0; fi
  local cutoff; cutoff="$(date -u -d '-30 days' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 0000)"
  local n; n="$(awk -v c="$cutoff" '$1 >= c' "$log" | grep -c unauthorized_head_flip || true)"
  echo "unauthorized_head_flips/30d: ${n:-0}"
  [ "${n:-0}" = "0" ] || { echo "  → Kill-Gate (ADR-233 §8): Konvention nicht erzwingbar (>0)."; tail -3 "$log"; }
}

# Backstop für pre-commit (ADR-233 §2.1): im sentinel-geschützten Haupt-Tree wird NICHT
# committet — editierende Arbeit gehört in einen per-session Worktree. In Worktrees ist
# ".git" eine Datei (kein Verzeichnis), der relative Sentinel-Pfad existiert dort nicht
# → der Hook greift NUR im Haupt-Tree. Fängt den HEAD-Flip-Commit-auf-main (Retro 2026-06-04 F2),
# der vom post-checkout-Snap-back allein nicht verhindert wird.
cmd_precommit_check() {
  local head; head="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || echo DETACHED)"
  # (1) Branch-Fallback (SENTINEL-UNABHÄNGIG): nie direkt auf main/master committen.
  #     Fängt den Commit-auf-main (Retro 2026-06-05 #5) AUCH in Klons, in denen
  #     'install' nie lief — der Hauptgrund des Rückfalls (Guard war dormant).
  case "$head" in
    main|master)
      echo "BLOCK: main-tree-guard (ADR-233): Commit direkt auf '$head' unterbunden." >&2
      echo "    Editierende Arbeit gehört in einen Feature-Branch / per-session Worktree:" >&2
      echo "    git switch -c <branch>   |   git worktree add /tmp/<slug> -b <branch> origin/main" >&2
      echo "    (Bewusster Override: git commit --no-verify)" >&2
      exit 1 ;;
  esac
  # (2) Tree-Schutz (Sentinel): im heiligen Haupt-Tree wird gar nicht committet (auch nicht
  #     auf einem Feature-Branch — editierende Arbeit gehört in einen per-session Worktree).
  [ -e "$SENTINEL" ] || exit 0   # Worktree/ungeschützt + nicht-main → erlauben
  echo "BLOCK: main-tree-guard (ADR-233): Commit im heiligen Haupt-Tree unterbunden." >&2
  echo "    Editierende Arbeit gehört in einen per-session Worktree:" >&2
  echo "    git worktree add /tmp/<slug> -b <branch> origin/main   (oder 'repo-session start')." >&2
  exit 1
}

case "${1:-}" in
  install)         shift; cmd_install "$@";;
  hook)            shift; cmd_hook "$@";;
  report)          shift; cmd_report "$@";;
  precommit-check) shift; cmd_precommit_check "$@";;
  *) echo "usage: main-tree-guard.sh {install <repo> | report [repo] | precommit-check | hook <prev> <new> <flag>}" >&2; exit 2;;
esac
