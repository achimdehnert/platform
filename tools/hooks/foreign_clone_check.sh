#!/usr/bin/env bash
# GATE_HEADER (KONZ-038 D8) — maschinenlesbar fuer tools/gate_drill_check.py:
#   "slug": "stale-local-clone-as-ground-truth"
#   "mode": "advisory"
#   "owner": "achim"
#   "last_drill_pass": "2026-10-05"
#   "evidence": "tools/tests/test_foreign_clone_check.py"
#
# Claude Code PreToolUse(Bash) hook — Rueckstand eines FREMDEN Klons melden.
#
# Warum es das zusaetzlich gibt (Sitzung 2026-09-03, meiki-hub): der
# Schwester-Hook `stale_clone_check.sh` laeuft beim Sitzungsstart auf
# CLAUDE_PROJECT_DIR, also auf dem Repo, in dem gearbeitet wird. Ein FREMDES
# Repo, das mitten in der Sitzung als INHALTSQUELLE gelesen wird, ist fuer ihn
# unsichtbar. Realfall: Sitzungs-Repo meiki-hub, gelesen wurde frist-hub —
# dessen Klon lag drei Commits hinter origin. Portiert wurde aus dem alten
# Stand; Spec, Bildschirme, zwoelf Bilder und ein Handbuch fehlten. Gefunden
# nur, weil ein Doku-Verweis auf einen Ordner zeigte, den es lokal nicht gab.
# Der Slug stand da bereits neunmal in den Retros und HATTE ein Gate — das war
# also kein neues Muster, sondern ein Gate, das seinen Fall nicht sah
# (platform#2732, Retro platform#2730).
#
# Vertrag: IMMER Exit 0 — ein Hinweis darf keine Session blockieren. Kein
# `git pull`, kein Schreibzugriff: nur `fetch` und zaehlen. Je Repo einmal pro
# Sitzung, damit wiederholte Lesezugriffe nicht wiederholt fetchen.
set -uo pipefail

GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"

# Die Eingabe kommt als JSON auf stdin; ohne jq reicht ein grober Auszug —
# wir brauchen nur die Pfade und die Sitzungskennung, nicht die Struktur.
eingabe="$(timeout 2 cat 2>/dev/null || true)"
[ -n "$eingabe" ] || exit 0

# Der Merker haengt an der SITZUNG, nicht am Prozess: jeder Hook-Aufruf ist ein
# eigener Prozess, mit $$ im Namen waere "einmal pro Sitzung" wirkungslos.
# Die Kennung steht im Ereignis-JSON (`session_id`). Bis 2026-10-05 las der Hook
# nur CLAUDE_SESSION_ID — die setzt Claude Code im Hook-Prozess NICHT. Der
# Merker hiess deshalb fuer jede Sitzung "-ohne", und "einmal pro Sitzung" wurde
# "einmal ueberhaupt": frist-hub stand seit 2026-09-03 darin, schreib-hub seit
# 2026-09-12, und am 2026-09-24 schwieg der Hook zu beiden, obwohl beide hinter
# origin lagen (Retro 2026-09-24 meiki-hub 2a5c44, platform#3722 G7).
# Ohne Kennung kein Merker: lieber bei jedem Zugriff pruefen als fuer immer
# schweigen.
sitzung="$(printf '%s' "$eingabe" \
  | grep -oE '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 \
  | sed -E 's/.*:[[:space:]]*"([^"]*)"$/\1/' | tr -cd 'A-Za-z0-9._-')"
[ -n "$sitzung" ] || sitzung="$(printf '%s' "${CLAUDE_SESSION_ID:-}" | tr -cd 'A-Za-z0-9._-')"
MERKER=""
[ -n "$sitzung" ] && MERKER="${TMPDIR:-/tmp}/claude-fremdklon-geprueft-${sitzung}"

# Repo der laufenden Sitzung — es hat schon seinen eigenen Melder.
eigenes=""
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  eigenes="$(basename "$CLAUDE_PROJECT_DIR")"
fi

# Alle Vorkommen von <github-dir>/<repo> einsammeln, auch als ~/github/<repo>.
kandidaten="$(printf '%s' "$eingabe" \
  | grep -oE "(${GITHUB_DIR}|~/github|\\\$HOME/github|\\\$\{GITHUB_DIR[^}]*\})/[A-Za-z0-9._-]+" \
  | sed -E "s#.*/##" | sort -u)"
[ -n "$kandidaten" ] || exit 0

for repo in $kandidaten; do
  [ "$repo" = "$eigenes" ] && continue
  pfad="$GITHUB_DIR/$repo"
  [ -d "$pfad/.git" ] || continue
  # Je Repo nur einmal pro Sitzung
  if [ -n "$MERKER" ]; then
    grep -qx "$repo" "$MERKER" 2>/dev/null && continue
    echo "$repo" >> "$MERKER" 2>/dev/null || true
  fi

  # Abruf gescheitert (kein Netz, kein Zugang): kein Urteil, aber auch keine
  # Stille — ein Klon, dessen Stand niemand kennt, ist keine Quelle ohne Vorbehalt.
  if ! timeout 15 git -C "$pfad" fetch --quiet origin 2>/dev/null; then
    echo "ℹ FREMDER KLON UNGEPRUEFT: $repo — Abruf von origin fehlgeschlagen,"
    echo "   Stand gegenueber origin unbekannt. Als QUELLE nur mit Vorbehalt lesen."
    continue
  fi
  ziel="origin/$(git -C "$pfad" branch --show-current 2>/dev/null)"
  git -C "$pfad" rev-parse --verify --quiet "$ziel" >/dev/null 2>&1 || ziel="origin/main"
  git -C "$pfad" rev-parse --verify --quiet "$ziel" >/dev/null 2>&1 || continue

  hinter="$(git -C "$pfad" rev-list --count "HEAD..$ziel" 2>/dev/null || echo 0)"
  [ "$hinter" -gt 0 ] 2>/dev/null || continue

  neuestes="$(git -C "$pfad" log -1 --format='%h %s' "$ziel" 2>/dev/null | cut -c1-70)"
  echo "⚠ FREMDER KLON VERALTET: $repo liegt $hinter Commit(s) hinter $ziel."
  echo "   Neuestes dort: $neuestes"
  echo "   Wird dieses Repo als QUELLE gelesen (Inhalte uebernehmen, Vergleich,"
  echo "   Zitat), gilt der Arbeitsbaum nicht: aus dem Ref lesen"
  echo "   (git -C $pfad show $ziel:<pfad>) oder vorher nachziehen."
done
exit 0
