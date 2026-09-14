#!/usr/bin/env bash
# Orchestrator-Schlüssel-Abgleich (Prävention zu mcp-hub#179):
# Prüft, ob der Client-Schlüssel (Schlüsselkasten ~/.secrets) und das
# Server-Schloss (hetzner-prod, /opt/mcp-hub/.env.prod) zusammenpassen.
# Vergleicht NUR Prüfsummen — Schlüsselwerte erscheinen nirgends.
#
# Nutzung:  tools/orchestrator_key_sync_check.sh            # Live-Abgleich
#           tools/orchestrator_key_sync_check.sh --selftest # Negativtest (Regel 10 / Charta-Muster)
# Exit 0 = synchron · Exit 1 = DRIFT (Alarm) · Exit 2 = nicht prüfbar
set -euo pipefail

vergleiche() {  # $1=lokal $2=server -> 0 ok, 1 drift
  if [ "$1" = "$2" ]; then
    echo "OK: Orchestrator-Schlüssel synchron (…${1})"
    return 0
  else
    echo "ALARM: Schlüssel-Drift! Schlüsselkasten …${1} ≠ Server-Schloss …${2}" >&2
    echo "       Vermutlich Rotation ohne Heimat-Nachzug — Vorgehen: mcp-hub#179 / policies/orchestrator.md §Rotation" >&2
    return 1
  fi
}

if [ "${1:-}" = "--selftest" ]; then
  vergleiche "gleich0000" "gleich0000" >/dev/null || { echo "SELFTEST: Grün-Fall fehlgeschlagen" >&2; exit 2; }
  if vergleiche "aaaa00000000" "bbbb00000000" >/dev/null 2>&1; then
    echo "SELFTEST: Rot-Fixture feuerte NICHT — Wächter ist Deko" >&2; exit 2
  fi
  echo "SELFTEST: Rot-Fixture gefeuert ✓, Grün-Fall bestanden ✓"
  exit 0
fi

# Toleranter Leser (bare UND NAME=WERT, platform#3129) — nie selbst lesen.
LESER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/secret_lesen.sh"
WERT=$("$LESER" orchestrator_mcp_api_key) \
  || { echo "nicht prüfbar: Schlüsselkasten nicht lesbar" >&2; exit 2; }
LOKAL=$(printf '%s' "$WERT" | sha256sum | cut -c1-12)
unset WERT

SERVER=$(ssh -o ConnectTimeout=10 hetzner-prod \
  "grep -m1 '^ORCHESTRATOR_MCP_API_KEY=' /opt/mcp-hub/.env.prod | cut -d= -f2- | tr -d '[:space:]' | sha256sum | cut -c1-12" \
) || { echo "nicht prüfbar: Server nicht erreichbar" >&2; exit 2; }

vergleiche "$LOKAL" "$SERVER"
