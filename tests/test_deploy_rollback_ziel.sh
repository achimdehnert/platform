#!/usr/bin/env bash
# tests/test_deploy_rollback_ziel.sh — Vertragstest für das Rollback-Ziel und die
# Registry-Wiederholung in scripts/deploy.sh (writing-hub#982, platform#2685).
#
# Warum als Test und nicht "einmal von Hand geprüft": beide Blöcke laufen bei
# JEDEM Deploy JEDES Hubs, und ihr Versagen ist am grünen Deploy nicht zu sehen.
# Genau das war der Realfall am 2026-09-02: `.env` trug einen Tag, der nie lief,
# das Skript meldete ihn als `Prev:` und das Rollback zog daraufhin ein Abbild,
# das der Host nicht hatte. Ein Test, der nur "Deploy grün" prüft, hätte das
# nie gefunden — der Deploy war ja rot, und der FEHLER lag im Notausgang.
#
# Geprüfte Zusagen:
#   1. Läuft ein App-Container, ist ER die Quelle des Rollback-Ziels — auch wenn
#      `.env` etwas anderes behauptet.
#   2. Läuft keiner, ist `.env` die Rückfallebene (Erstinstallation).
#   3. Fremde Container (Postgres, Redis, anderer Hub) verfälschen das Ziel nicht.
#   4. Die Registry-Wiederholung gibt nach DEPLOY_REGISTRY_RETRIES Versuchen auf
#      und meldet Fehlschlag — sie läuft nicht endlos.
#   5. Ein Aufruf, der beim zweiten Versuch klappt, gilt als Erfolg.
#
# Beide Blöcke werden 1:1 aus scripts/deploy.sh extrahiert (keine Nachbildung,
# die auseinanderlaufen könnte) und gegen einen `docker`-Stub gefahren — der
# Test braucht daher weder Docker noch Netz.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/scripts/deploy.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FAILED=0
pruefe() { # pruefe <name> <erwartet> <tatsaechlich>
  if [[ "$2" == "$3" ]]; then
    echo "  ok    $1"
  else
    echo "  FAIL  $1 — erwartet '$2', bekam '$3'" >&2
    FAILED=1
  fi
}

# ── Block 1: Rollback-Ziel ────────────────────────────────────────────────────
ZIEL="$TMP/ziel.sh"
sed -n '/^# Vorherigen Tag für Rollback speichern\./,/^# Compose-File nach Umgebung/p' \
  "$SRC" | head -n -1 > "$ZIEL"
if ! grep -q "_running_image_tag" "$ZIEL"; then
  echo "FAIL: Rollback-Ziel-Block nicht aus $SRC extrahierbar — Marker geändert?" >&2
  exit 1
fi

ziel_ermitteln() { # ziel_ermitteln <docker-ps-ausgabe> <env-inhalt>
  local ps_out="$1" env_inhalt="$2"
  local app_dir="$TMP/app"; rm -rf "$app_dir"; mkdir -p "$app_dir"
  [[ -n "$env_inhalt" ]] && printf '%s\n' "$env_inhalt" > "$app_dir/.env"
  (
    set -euo pipefail
    APP_NAME="writing-hub"; APP_PATH="$app_dir"
    docker() { [[ "$*" == *"ps --format"* ]] && printf '%s\n' "$ps_out"; return 0; }
    # shellcheck disable=SC1090
    source "$ZIEL" >/dev/null 2>&1
    printf '%s' "$PREVIOUS_TAG"
  )
}

echo "Block 1 — Rollback-Ziel:"

# 1. Laufender Container schlägt .env
ist=$(ziel_ermitteln \
  "ghcr.io/achimdehnert/writing-hub:main-0ef9843
postgres:15-alpine" \
  "IMAGE_TAG=main-3abbb31")
pruefe "laufender Container schlaegt .env" "main-0ef9843" "$ist"

# 2. Kein App-Container → .env als Rückfallebene
ist=$(ziel_ermitteln "postgres:15-alpine" "IMAGE_TAG=main-3abbb31")
pruefe "ohne App-Container faellt auf .env zurueck" "main-3abbb31" "$ist"

# 3. Fremde Hubs auf demselben Host verfälschen nichts
ist=$(ziel_ermitteln \
  "ghcr.io/achimdehnert/illustration-hub:v1.7.0
ghcr.io/achimdehnert/writing-hub:main-0ef9843
redis:7-alpine" \
  "IMAGE_TAG=main-3abbb31")
pruefe "fremder Hub verfaelscht das Ziel nicht" "main-0ef9843" "$ist"

# 4. Weder Container noch .env → leer, kein Rollback
ist=$(ziel_ermitteln "postgres:15-alpine" "")
pruefe "ohne beides bleibt das Ziel leer" "" "$ist"

# ── Block 2: Registry-Wiederholung ───────────────────────────────────────────
WDH="$TMP/wdh.sh"
sed -n '/^: "\${DEPLOY_REGISTRY_RETRIES/,/^}$/p' "$SRC" > "$WDH"
if ! grep -q "_mit_wiederholung" "$WDH"; then
  echo "FAIL: Wiederholungs-Block nicht aus $SRC extrahierbar — Marker geändert?" >&2
  exit 1
fi

echo "Block 2 — Registry-Wiederholung:"

# 5. Gibt nach der konfigurierten Zahl auf (und laeuft nicht endlos)
ist=$(
  set +e
  DEPLOY_REGISTRY_RETRIES=3 DEPLOY_REGISTRY_BACKOFF=0
  export DEPLOY_REGISTRY_RETRIES DEPLOY_REGISTRY_BACKOFF
  # shellcheck disable=SC1090
  source "$WDH"
  n=0; immer_rot() { n=$((n+1)); return 1; }
  _mit_wiederholung "Testschritt" immer_rot >/dev/null 2>&1
  echo "rc=$? versuche=$n"
)
pruefe "gibt nach 3 Versuchen auf" "rc=1 versuche=3" "$ist"

# 6. Erfolg im zweiten Versuch zaehlt als Erfolg
ist=$(
  set +e
  DEPLOY_REGISTRY_RETRIES=4 DEPLOY_REGISTRY_BACKOFF=0
  export DEPLOY_REGISTRY_RETRIES DEPLOY_REGISTRY_BACKOFF
  # shellcheck disable=SC1090
  source "$WDH"
  n=0; erst_rot_dann_gruen() { n=$((n+1)); [[ $n -ge 2 ]]; }
  _mit_wiederholung "Testschritt" erst_rot_dann_gruen >/dev/null 2>&1
  echo "rc=$? versuche=$n"
)
pruefe "Erfolg im zweiten Versuch zaehlt" "rc=0 versuche=2" "$ist"

# ── Block 3: .env-Wiederherstellung im Rollback ──────────────────────────────
echo "Block 3 — .env-Wiederherstellung:"

# 7. rollback() setzt .env zurueck, BEVOR es hochfaehrt — sonst bliebe nach einem
#    gescheiterten `up -d` der nie gelaufene Tag stehen (die Kette aus dem Realfall).
rb_zeilen=$(sed -n '/^rollback() {/,/^}$/p' "$SRC")
restore_pos=$(printf '%s\n' "$rb_zeilen" | grep -n "_restore_image_tag" | head -1 | cut -d: -f1)
up_pos=$(printf '%s\n' "$rb_zeilen" | grep -n "up -d --force-recreate" | head -1 | cut -d: -f1)
if [[ -n "$restore_pos" && -n "$up_pos" && "$restore_pos" -lt "$up_pos" ]]; then
  echo "  ok    rollback() setzt .env vor dem Hochfahren zurueck"
else
  echo "  FAIL  rollback() ruft _restore_image_tag nicht vor 'up -d' (restore=$restore_pos up=$up_pos)" >&2
  FAILED=1
fi

echo
if [[ $FAILED -eq 0 ]]; then echo "ALLE ZUSAGEN GEHALTEN"; else echo "TESTS FEHLGESCHLAGEN" >&2; fi
exit $FAILED
