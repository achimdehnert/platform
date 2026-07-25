#!/usr/bin/env bash
# tools/deploy-script-drift.sh — Drift zwischen Git-Quelle und Host-Kopien von deploy.sh
#
# Warum es das gibt (Messung 2026-07-25):
#   scripts/deploy.sh ist die Quelle, /opt/scripts/deploy.sh auf prod+staging die
#   ausgeführte Kopie — verteilt wird sie VON HAND. Genau das lief auseinander:
#     staging  5948722f…  == Git    ✅
#     prod     0c6a076e…  != Git    ❌ (Stand 13.07. statt 21.07.)
#   Prod fehlte damit u.a. der override-Chain-Fix aus platform#1075 (der ohne ihn
#   Container fremder Projekte als Waisen löschen konnte, Realfall weltenhub).
#   Nichts hat das gemeldet: der Deploy war jedes Mal grün.
#
#   Diese Drift ist strukturell unsichtbar, weil das Skript sich nicht selbst
#   prüfen kann — der Check muss von außen kommen. Er hängt in
#   tools/session_start_checks.sh (Phase 0.7.1) und läuft damit in jeder Session.
#
# Usage:
#   tools/deploy-script-drift.sh            # nur prüfen, Exit 1 bei Drift
#   tools/deploy-script-drift.sh --sync     # Host-Kopien aktualisieren (bewusste Aktion!)
#   tools/deploy-script-drift.sh --quiet    # nur die Summary-Zeile (für Runner)
#
# --sync schreibt den Deploy-Entrypoint auf Prod. Das ist ein Prod-Eingriff mit
# Fleet-Blast-Radius (alle ~10 Hubs deployen darüber) — nie beiläufig ausführen.
set -euo pipefail

PLATFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$PLATFORM_DIR/scripts/deploy.sh"
HOSTS_YAML="$PLATFORM_DIR/infra/hosts.yaml"
REMOTE_PATH="/opt/scripts/deploy.sh"

DO_SYNC=0
QUIET=0
for a in "$@"; do
  case "$a" in
    --sync)  DO_SYNC=1 ;;
    --quiet) QUIET=1 ;;
    -h|--help) sed -n '1,25p' "$0"; exit 0 ;;
    *) echo "Unbekanntes Argument: $a" >&2; exit 64 ;;
  esac
done

[[ -f "$SRC" ]] || { echo "FEHLER: $SRC nicht gefunden" >&2; exit 2; }

SRC_MD5=$(md5sum "$SRC" | awk '{print $1}')
SRC_VER=$(grep -m1 '^DEPLOY_SH_VERSION=' "$SRC" | cut -d'"' -f2 || echo "unversioniert")

# Ziel-Hosts aus der Infra-SoT lesen — nicht hier hartkodieren (hosts.yaml ist
# die einzige Quelle für Server-Adressen, CLAUDE.md "Infra-SoT").
mapfile -t TARGETS < <(python3 - "$HOSTS_YAML" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
for name in ("prod", "staging"):
    h = (d.get("hosts") or {}).get(name) or {}
    if h.get("ssh"):
        print(f"{name}\t{h['ssh']}")
PY
)

[[ ${#TARGETS[@]} -gt 0 ]] || { echo "FEHLER: keine prod/staging-Hosts in $HOSTS_YAML" >&2; exit 2; }

DRIFTED=""
UNREACHABLE=""

[[ $QUIET -eq 1 ]] || {
  echo "Quelle: scripts/deploy.sh  version=$SRC_VER  md5=$SRC_MD5"
  printf '%-10s %-34s %-14s %s\n' "HOST" "MD5" "VERSION" "STATUS"
}

for t in "${TARGETS[@]}"; do
  name="${t%%$'\t'*}"
  ssh_target="${t#*$'\t'}"

  remote=$(ssh -o ConnectTimeout=10 -o BatchMode=yes "$ssh_target" \
    "md5sum $REMOTE_PATH 2>/dev/null | awk '{print \$1}'; grep -m1 '^DEPLOY_SH_VERSION=' $REMOTE_PATH 2>/dev/null | cut -d'\"' -f2" 2>/dev/null || true)

  r_md5=$(echo "$remote" | sed -n '1p')
  r_ver=$(echo "$remote" | sed -n '2p')
  [[ -n "$r_ver" ]] || r_ver="unversioniert"

  if [[ -z "$r_md5" ]]; then
    UNREACHABLE="$UNREACHABLE $name"
    status="⚠️  nicht lesbar (Host down / kein SSH / Datei fehlt)"
  elif [[ "$r_md5" == "$SRC_MD5" ]]; then
    status="✅ synchron"
  else
    DRIFTED="$DRIFTED $name"
    status="❌ DRIFT — Host führt eine andere Version aus als Git"
  fi

  [[ $QUIET -eq 1 ]] || printf '%-10s %-34s %-14s %s\n' "$name" "${r_md5:-–}" "$r_ver" "$status"

  if [[ $DO_SYNC -eq 1 && -n "$r_md5" && "$r_md5" != "$SRC_MD5" ]]; then
    echo "→ sync nach $ssh_target:$REMOTE_PATH …"
    # Backup der Host-Kopie behalten: sie ist der einzige Zeuge dessen, was
    # zuletzt real deployt hat, falls die neue Version Probleme macht.
    ssh -o BatchMode=yes "$ssh_target" "cp -a $REMOTE_PATH ${REMOTE_PATH}.bak-\$(date +%Y%m%d%H%M%S)"
    scp -q -o BatchMode=yes "$SRC" "$ssh_target:$REMOTE_PATH"
    ssh -o BatchMode=yes "$ssh_target" "chmod 755 $REMOTE_PATH"
    new_md5=$(ssh -o BatchMode=yes "$ssh_target" "md5sum $REMOTE_PATH | awk '{print \$1}'")
    if [[ "$new_md5" == "$SRC_MD5" ]]; then
      echo "   ✅ $name jetzt synchron ($new_md5)"
      DRIFTED="${DRIFTED/ $name/}"
    else
      echo "   ❌ $name: md5 nach sync immer noch abweichend ($new_md5)" >&2
    fi
  fi
done

DRIFTED="${DRIFTED# }"; UNREACHABLE="${UNREACHABLE# }"

if [[ -n "$DRIFTED" ]]; then
  echo "RESULT: DRIFT — Host-Kopie(n) weichen von Git ab: $DRIFTED (beheben: tools/deploy-script-drift.sh --sync)"
  exit 1
elif [[ -n "$UNREACHABLE" ]]; then
  echo "RESULT: UNGEPRUEFT — nicht erreichbar: $UNREACHABLE (die uebrigen sind synchron)"
  exit 0
else
  echo "RESULT: OK — alle Host-Kopien synchron mit scripts/deploy.sh ($SRC_VER)"
fi
