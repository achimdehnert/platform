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
#
# JEDER Host mit ssh-Eintrag, nicht zwei feste Namen (platform#2711, gemessen
# 2026-09-02). Bis hierher fragte diese Liste genau `prod` und `staging` ab. Einen
# Host namens `staging` gibt es seit dem 2026-08-30 nicht mehr — der Eintrag heißt
# `dev-desktop` —, und `prod-b` kam mit ADR-292 dazu. Der Melder prüfte damit **einen**
# von drei Hosts, die den Entrypoint wirklich ausführen, und meldete dabei ungerührt
# „alle Host-Kopien synchron". Gemessen an diesem Tag: prod 2026-09-01.1,
# **prod-b 2026-08-10.1** (drei Wochen und mehrere Korrekturen zurück),
# dev-desktop 2026-08-20.1. Sichtbar war nur prod.
#
# Das ist dieselbe Fehlerklasse, gegen die dieses Werkzeug gebaut wurde — eine
# unsichtbare Drift —, nur eine Ebene höher: nicht die Kopie lief weg, sondern die
# Liste dessen, was überhaupt angesehen wird. Eine Namensliste veraltet still; eine
# abgeleitete Liste kann das nicht.
#
# Hosts ohne Kopie (Backup-Ziel, Inferenzknoten) sind KEIN Befund — sie führen keinen
# Deploy aus. Das unterscheidet der Lauf unten an der fehlenden Datei, nicht an einer
# zweiten Namensliste, die genauso veralten würde.
mapfile -t TARGETS < <(python3 - "$HOSTS_YAML" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
for name, h in sorted((d.get("hosts") or {}).items()):
    if isinstance(h, dict) and h.get("ssh"):
        print(f"{name}\t{h['ssh']}")
PY
)

[[ ${#TARGETS[@]} -gt 0 ]] || { echo "FEHLER: keine Hosts mit ssh-Eintrag in $HOSTS_YAML" >&2; exit 2; }

DRIFTED=""
UNREACHABLE=""
OHNE_KOPIE=""

[[ $QUIET -eq 1 ]] || {
  echo "Quelle: scripts/deploy.sh  version=$SRC_VER  md5=$SRC_MD5"
  printf '%-10s %-34s %-14s %s\n' "HOST" "MD5" "VERSION" "STATUS"
}

for t in "${TARGETS[@]}"; do
  name="${t%%$'\t'*}"
  ssh_target="${t#*$'\t'}"

  # `DA=` trennt „Host antwortet nicht" von „Host hat keine Kopie". Vorher fielen
  # beide in denselben Topf, und ein Backup-Ziel ohne Deploy-Rolle sah aus wie ein
  # stummer Prod-Host. Kommt gar nichts zurück, ist der Host stumm.
  #
  # Das Prüfskript geht über stdin, nicht als ssh-Argument: durch die
  # Anführungszeichen von zwei Shells hindurch überlebten weder `awk '{print $1}'`
  # noch `cut -d'"'`, und der Melder meldete daraufhin für JEDEN Host Drift, weil
  # die md5 leer zurückkam. Beschriftete Zeilen statt Positionen aus demselben
  # Grund — fehlt der Versionsstempel, verschiebt sich sonst alles um eine Zeile.
  remote=$(ssh -o ConnectTimeout=10 -o BatchMode=yes "$ssh_target" bash -s -- "$REMOTE_PATH" 2>/dev/null <<'EOS' || true
p="$1"
if [ -f "$p" ]; then
  echo "DA=ja"
  echo "MD5=$(md5sum "$p" | cut -d' ' -f1)"
  echo "VER=$(grep -m1 '^DEPLOY_SH_VERSION=' "$p" | cut -d'"' -f2)"
else
  echo "DA=nein"; echo "MD5="; echo "VER="
fi
EOS
)

  r_da=$(sed -n 's/^DA=//p' <<< "$remote")
  r_md5=$(sed -n 's/^MD5=//p' <<< "$remote")
  r_ver=$(sed -n 's/^VER=//p' <<< "$remote")
  [[ -n "$r_ver" ]] || r_ver="unversioniert"

  if [[ -z "$r_da" ]]; then
    UNREACHABLE="$UNREACHABLE $name"
    status="⚠️  nicht erreichbar (Host down / kein SSH) — ungeprüft"
  elif [[ "$r_da" == "nein" ]]; then
    OHNE_KOPIE="$OHNE_KOPIE $name"
    status="–  keine Kopie (führt keinen Deploy aus) — kein Befund"
    r_ver="–"
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

DRIFTED="${DRIFTED# }"; UNREACHABLE="${UNREACHABLE# }"; OHNE_KOPIE="${OHNE_KOPIE# }"

# Wie viele Hosts tragen den Entrypoint überhaupt? Diese Zahl gehört in jede
# Summary — sonst liest sich „alle synchron" bei einem geprüften Host genauso
# beruhigend wie bei dreien. Genau daran lag platform#2711.
GEPRUEFT=$(( ${#TARGETS[@]} - $(wc -w <<< "$UNREACHABLE") - $(wc -w <<< "$OHNE_KOPIE") ))
MIT_KOPIE="$GEPRUEFT Host(s) mit Kopie von ${#TARGETS[@]} befragten"
[[ -n "$OHNE_KOPIE" ]] && MIT_KOPIE="$MIT_KOPIE, ohne Kopie: $OHNE_KOPIE"

if [[ -n "$DRIFTED" ]]; then
  echo "RESULT: DRIFT — Host-Kopie(n) weichen von Git ab: $DRIFTED ($MIT_KOPIE) (beheben: tools/deploy-script-drift.sh --sync)"
  exit 1
elif [[ -n "$UNREACHABLE" ]]; then
  echo "RESULT: UNGEPRUEFT — nicht erreichbar: $UNREACHABLE (die uebrigen synchron; $MIT_KOPIE)"
  exit 0
else
  echo "RESULT: OK — alle Host-Kopien synchron mit scripts/deploy.sh ($SRC_VER) — $MIT_KOPIE"
fi
