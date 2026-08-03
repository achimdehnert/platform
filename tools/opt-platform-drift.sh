#!/usr/bin/env bash
# tools/opt-platform-drift.sh — Drift des Prod-Klons /opt/platform gegen origin/main
#
# Warum es das gibt (platform#1585):
#   Der taegliche Mail-Ingest auf Prod liest seine Werkzeuge ueber einen
#   read-only-Mount aus einem git-Klon:
#     /opt/platform/tools/mail_agent -> /app/mail_tools (rw=false)
#   Diesen Klon zieht **nichts automatisch**. Geprueft am 2026-08-03: kein
#   `git pull` in /etc/cron.d/, keiner in /opt/scripts/, keine systemd-Unit;
#   der einzige Cron, der /opt/platform anfasst (`adr-outline-sync`), liest nur.
#   Das Reflog zeigt ausschliesslich Pulls zu unregelmaessigen Uhrzeiten
#   (05:01, 09:47, 06:01, 07:02, 15:12 UTC) — das sind Handgriffe aus Sessions,
#   kein Zeitplan. Zwischen 2026-07-02 und 2026-07-29 lag eine Luecke von 27
#   Tagen, in der niemand zog.
#
#   Ein Merge nach `main` wirkt hier also NICHT — er sieht nur so aus. Genau das
#   fiel an PR #1584 auf, dessen Text „wirksam ohne Deploy" behauptete, waehrend
#   der Prod-Klon die Aenderung gar nicht hatte.
#
#   Wie beim deploy.sh-Drift (Phase 0.7.1) kann sich der Klon nicht selbst
#   pruefen — der Check muss von aussen kommen. Deshalb haengt er in
#   tools/session_start_checks.sh und laeuft einmal pro Session.
#
# Usage:
#   tools/opt-platform-drift.sh            # nur pruefen, Exit 1 bei Drift
#   tools/opt-platform-drift.sh --quiet    # nur die Summary-Zeile (fuer Runner)
#   tools/opt-platform-drift.sh --sync     # Klon ziehen (BEWUSSTER Prod-Eingriff)
#
# --sync fuehrt `git pull --ff-only` auf einem Prod-Host aus und veraendert damit
# den Werkzeugstand, mit dem der naechtliche Mail-Ingest laeuft. Nie beilaeufig
# ausfuehren, nie aus dem Session-Runner heraus.
set -euo pipefail

PLATFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOSTS_YAML="$PLATFORM_DIR/infra/hosts.yaml"
REMOTE_CLONE="/opt/platform"

#: Verzeichnis, dessen Drift fachlich weh tut: es haengt read-only im
#: Mail-Container. Alles andere im Klon ist Beiwerk — die Unterscheidung steht
#: im Bericht, damit „28 Commits dahinter" nicht mit „Mail laeuft auf altem
#: Stand" verwechselt wird. Am 2026-08-03 war genau das der Fall: 28 Commits
#: Drift, aber tools/mail_agent/ identisch.
WATCH_PATH="tools/mail_agent"

DO_SYNC=0
QUIET=0
for a in "$@"; do
  case "$a" in
    --sync)  DO_SYNC=1 ;;
    --quiet) QUIET=1 ;;
    -h|--help) sed -n '1,32p' "$0"; exit 0 ;;
    *) echo "Unbekanntes Argument: $a" >&2; exit 64 ;;
  esac
done

mapfile -t TARGETS < <(python3 - "$HOSTS_YAML" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
h = (d.get("hosts") or {}).get("prod") or {}
if h.get("ssh"):
    print(f"prod\t{h['ssh']}")
PY
)

[[ ${#TARGETS[@]} -gt 0 ]] || { echo "FEHLER: kein prod-Host in $HOSTS_YAML" >&2; exit 2; }

DRIFTED=""
WATCH_DRIFTED=""
UNREACHABLE=""

[[ $QUIET -eq 1 ]] || {
  echo "Prod-Klon: $REMOTE_CLONE  (beobachtet: $WATCH_PATH)"
  printf '%-8s %-10s %-8s %s\n' "HOST" "HEAD" "DAHINTER" "STATUS"
}

for t in "${TARGETS[@]}"; do
  name="${t%%$'\t'*}"
  ssh_target="${t#*$'\t'}"

  # Ein einziger SSH-Aufruf: fetch + drei Messwerte. `git fetch` ist read-only
  # fuer den Arbeitsbaum — es bewegt nur Remote-Refs, kein Working-Tree-Schreiben.
  remote=$(ssh -o ConnectTimeout=10 -o BatchMode=yes "$ssh_target" \
    "cd $REMOTE_CLONE 2>/dev/null && git fetch -q origin 2>/dev/null; \
     git rev-parse --short HEAD 2>/dev/null; \
     git rev-list --count HEAD..origin/main 2>/dev/null; \
     git diff --quiet HEAD origin/main -- $WATCH_PATH 2>/dev/null && echo gleich || echo anders" \
    2>/dev/null || true)

  r_head=$(echo "$remote" | sed -n '1p')
  r_behind=$(echo "$remote" | sed -n '2p')
  r_watch=$(echo "$remote" | sed -n '3p')

  if [[ -z "$r_head" || -z "$r_behind" ]]; then
    UNREACHABLE="$UNREACHABLE $name"
    status="⚠️  nicht lesbar (Host down / kein SSH / kein git-Klon)"
    r_head="–"; r_behind="–"
  elif [[ "$r_behind" == "0" ]]; then
    status="✅ synchron mit origin/main"
  elif [[ "$r_watch" == "anders" ]]; then
    DRIFTED="$DRIFTED $name"
    WATCH_DRIFTED="$WATCH_DRIFTED $name"
    status="❌ DRIFT in $WATCH_PATH — Mail-Ingest laeuft auf altem Werkzeugstand"
  else
    DRIFTED="$DRIFTED $name"
    status="⚠️  dahinter, aber $WATCH_PATH identisch (kein Mail-Risiko)"
  fi

  [[ $QUIET -eq 1 ]] || printf '%-8s %-10s %-8s %s\n' "$name" "$r_head" "$r_behind" "$status"

  if [[ $DO_SYNC -eq 1 && "$r_head" != "–" && "$r_behind" != "0" ]]; then
    echo "→ $name: git pull --ff-only in $REMOTE_CLONE (bewusster Prod-Eingriff)"
    ssh -o ConnectTimeout=10 -o BatchMode=yes "$ssh_target" \
      "cd $REMOTE_CLONE && git pull --ff-only" || {
        echo "FEHLER: pull auf $name fehlgeschlagen" >&2; exit 1; }
  fi
done

# Ein nicht erreichbarer Host ist KEIN gruener Zustand — er ist ein eigener
# Ausgang (vgl. feedback_fetch_failure_is_not_a_green_state). Sonst liest sich
# „kein Drift gemeldet" als „geprueft und sauber", obwohl gar nichts gemessen
# wurde.
if [[ -n "$UNREACHABLE" ]]; then
  echo "RESULT: UNGEPRUEFT —${UNREACHABLE} nicht erreichbar; Drift unbekannt"
  exit 2
fi
if [[ -n "$WATCH_DRIFTED" ]]; then
  echo "RESULT: DRIFT —${WATCH_DRIFTED}: $WATCH_PATH weicht ab (Mail-Ingest auf altem Stand)"
  exit 1
fi
if [[ -n "$DRIFTED" ]]; then
  echo "RESULT: HINTERHER —${DRIFTED} dahinter, $WATCH_PATH aber identisch"
  exit 1
fi
echo "RESULT: OK — $REMOTE_CLONE synchron mit origin/main"
