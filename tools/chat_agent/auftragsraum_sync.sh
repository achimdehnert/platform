#!/usr/bin/env bash
# auftragsraum_sync.sh — Auffangnetz-Lauf fuer den Raum "Achim / Lotse"
# (KONZ-platform-059, platform#3079, chat-hub#90).
#
# WOZU
#   Sortierer und Raum-Wache teilen sich seit der Raum-Zusammenlegung
#   2026-09-14 DASSELBE State-Dir (`CHAT_LOTSE_STATE_DIR`) und damit
#   dasselbe Sync-Token (`state["since"]`, chat_lotse.py). Laeuft die Wache,
#   haelt sie `sync.lock` und `sync` verweigert den Dienst mit Exit 1 —
#   das ist der richtige Zustand (die Wache bearbeitet die Zurufe live,
#   nichts nachzuholen). Laeuft keine Wache, holt `sync` alles seit dem
#   letzten Stand, und dieses Skript reicht es an den Sortierer weiter.
#   Kein doppeltes Bearbeiten, weil beide Seiten dasselbe Token bewegen.
#
# BENUTZUNG
#   bash tools/chat_agent/auftragsraum_sync.sh
#
# OVERRIDES (fuer Tests, sonst unveraendert lassen)
#   AUFTRAGSRAUM_ENV      Owner-Env-Datei (Default: ~/.claude/auftragsraum.env)
#   CHAT_LOTSE_PY         Python-Interpreter fuer chat_lotse.py
#                         (Default: ~/.venvs/chat-lotse/bin/python)
#   CHAT_LOTSE_SCRIPT     Pfad zu chat_lotse.py
#                         (Default: ~/github/chat-hub/deploy/chat_lotse.py)
#   AUFTRAGSRAUM_JOURNAL  Journal-Pfad, an `sortieren`/`offen` als --journal
#                         durchgereicht (sonst deren eigener Default)
#
# EXIT-CODES
#   0  sortiert (oder: Wache haelt den Lock — nichts nachzuholen)
#   >0 `sync` scheiterte aus einem anderen Grund als dem Wache-Lock
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

AUFTRAGSRAUM_ENV_DATEI="${AUFTRAGSRAUM_ENV:-$HOME/.claude/auftragsraum.env}"
if [ -f "$AUFTRAGSRAUM_ENV_DATEI" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$AUFTRAGSRAUM_ENV_DATEI"
  set +a
fi

CHAT_LOTSE_PY="${CHAT_LOTSE_PY:-$HOME/.venvs/chat-lotse/bin/python}"
CHAT_LOTSE_SCRIPT="${CHAT_LOTSE_SCRIPT:-$HOME/github/chat-hub/deploy/chat_lotse.py}"

TMP_SYNC="$(mktemp)"
TMP_ERR="$(mktemp)"
trap 'rm -f "$TMP_SYNC" "$TMP_ERR"' EXIT

SYNC_RC=0
"$CHAT_LOTSE_PY" "$CHAT_LOTSE_SCRIPT" sync >"$TMP_SYNC" 2>"$TMP_ERR" || SYNC_RC=$?

if [ "$SYNC_RC" -ne 0 ]; then
  # Wache haelt sync.lock — chat_lotse.py meldet das ueber LotseError
  # ("FEHLER: Ein anderer Lotse-Lauf (watch oder sync) haelt die Sperre …",
  # acquire_sync_lock in chat-hub/deploy/chat_lotse.py) und beendet sich mit
  # Exit 1. Das ist kein Fehler dieses Auffangnetzes, sondern der Beweis,
  # dass eine Wache die Zurufe schon live bearbeitet.
  if grep -q "haelt die Sperre" "$TMP_ERR"; then
    echo "Wache laeuft — Zurufe werden live bearbeitet, nichts nachzuholen"
    exit 0
  fi
  cat "$TMP_ERR" >&2
  exit "$SYNC_RC"
fi

SORTIEREN_ARGS=(sortieren --eingabe "$TMP_SYNC")
OFFEN_ARGS=(offen)
if [ -n "${AUFTRAGSRAUM_JOURNAL:-}" ]; then
  SORTIEREN_ARGS+=(--journal "$AUFTRAGSRAUM_JOURNAL")
  OFFEN_ARGS+=(--journal "$AUFTRAGSRAUM_JOURNAL")
fi

python3 "$REPO_ROOT/tools/chat_agent/auftragsraum.py" "${SORTIEREN_ARGS[@]}"
python3 "$REPO_ROOT/tools/chat_agent/auftragsraum.py" "${OFFEN_ARGS[@]}"
