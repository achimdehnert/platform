#!/usr/bin/env bash
# /opt/scripts/deploy.sh — iil-Platform Unified Deploy Script (ADR-120, ADR-166)
# Auf PROD (88.198.191.108) und DEV/Staging (88.99.38.75) installieren
#
# Usage: deploy.sh <APP_NAME> <APP_PATH> <IMAGE_TAG> <ENVIRONMENT> [HEALTH_CHECK_URL] [--break-glass "REASON"]
# Example: deploy.sh risk-hub /opt/risk-hub v1.4.2 production https://schutztat.de/livez/
# Manual:  deploy.sh risk-hub /opt/risk-hub latest production "" --break-glass "hotfix: rollback nginx config"
set -euo pipefail

# Version-Stempel der Git-Quelle. Wird im Deploy-Banner ausgegeben und von
# tools/deploy-script-drift.sh gegen die Host-Kopien geprüft — die Host-Kopie
# wird von Hand verteilt und lief messbar auseinander (Prod hing am 2026-07-25
# eine Revision hinter Git+Staging, u.a. ohne den override-Fix aus platform#1075).
DEPLOY_SH_VERSION="2026-08-20.1"

APP_NAME="${1:?'APP_NAME fehlt'}"
APP_PATH="${2:?'APP_PATH fehlt'}"
IMAGE_TAG="${3:?'IMAGE_TAG fehlt'}"
ENVIRONMENT="${4:?'ENVIRONMENT fehlt (staging|production)'}"
HEALTH_CHECK_URL="${5:-}"

# ADR-021 §2.20 — Intent-Token / break-glass flag
BREAK_GLASS_REASON=""
for _i in "${@:6}"; do
  if [[ "$_i" == "--break-glass" ]]; then
    _next=false
    for _j in "${@:6}"; do
      [[ "$_next" == "true" ]] && { BREAK_GLASS_REASON="$_j"; break; }
      [[ "$_j" == "--break-glass" ]] && _next=true
    done
    break
  fi
done

# ADR-160: log to file only if writable — never break deploy for logging
LOG_DIR="/var/log/iil-deploys"
mkdir -p "$LOG_DIR" 2>/dev/null || true
LOG_FILE="$LOG_DIR/${APP_NAME}_$(date +%Y%m%d_%H%M%S)_$$.log"
if touch "$LOG_FILE" 2>/dev/null; then
  exec > >(tee -a "$LOG_FILE" 2>/dev/null || cat) 2>&1
fi

# Validierung
[[ "$ENVIRONMENT" =~ ^(staging|production)$ ]] || { echo "FEHLER: ENVIRONMENT ungültig: $ENVIRONMENT" >&2; exit 1; }
[[ -d "$APP_PATH" ]] || { echo "FEHLER: $APP_PATH existiert nicht" >&2; exit 2; }
[[ -f "$APP_PATH/docker-compose.yml" || -f "$APP_PATH/docker-compose.prod.yml" ]] || {
  echo "FEHLER: Kein Compose-File in $APP_PATH" >&2; exit 3;
}

# Vorherigen Tag für Rollback speichern
PREVIOUS_TAG=""
if [[ -f "$APP_PATH/.env" ]]; then
  PREVIOUS_TAG=$(grep "^IMAGE_TAG=" "$APP_PATH/.env" | cut -d= -f2 || true)
fi

# Compose-File nach Umgebung wählen (ADR-022)
# Production: docker-compose.prod.yml
# Staging:    docker-compose.staging.yml
# Fallback:   docker-compose.yml
COMPOSE_FILE="docker-compose.yml"
if [[ "$ENVIRONMENT" == "production" && -f "$APP_PATH/docker-compose.prod.yml" ]]; then
  COMPOSE_FILE="docker-compose.prod.yml"
elif [[ "$ENVIRONMENT" == "staging" && -f "$APP_PATH/docker-compose.staging.yml" ]]; then
  COMPOSE_FILE="docker-compose.staging.yml"
fi

# platform#1063 — override-Dateien sind Teil des deklarierten Stacks. Ohne sie
# in der -f-Kette behandelt `up --remove-orphans` deren Container als Waisen
# und LÖSCHT sie (Realfall 2026-07-10: weltenhub_db + weltenhub_redis entfernt
# → Login-Ausfall ~15 min). Alle compose-Aufrufe nutzen ab hier
# "${COMPOSE_ARGS[@]}" statt -f "$COMPOSE_FILE".
# --- KETTE-ANFANG (tools/tests/test_deploy_compose_kette.py fuehrt genau
#     diesen Block aus — eine Kopie im Test wuerde davon wegdriften.)
COMPOSE_ARGS=(-f "$APP_PATH/$COMPOSE_FILE")

# platform#2586 K2 — die -f-Kette kommt aus dem MANIFEST, nicht aus einem hart
# benannten Dateinamen und auch nicht aus einem Glob am Host.
#
# Warum nicht ein Glob: dann faehrt jede Datei mit, die irgendwann einmal auf
# dem Host landete. Am 2026-09-01 lagen in /opt/mcp-hub eine
# docker-compose.rag.yml, die das Repo nicht mehr kennt, und eine
# .llm-mcp.yml.bak — beide waeren mitgefahren (KONZ-015-Fehlerklasse).
#
# Warum ueberhaupt: bis hierher stand genau EIN zusaetzlicher Name in der Kette
# (docker-compose.override.yml, platform#1063). Jede andere Overlay-Datei blieb
# draussen, und `up --remove-orphans` LOESCHT deren Container. Realfall
# 2026-09-01: mcp_hub_rag wurde 34 Minuten nach seiner Erzeugung entfernt;
# llm_gateway und mcp_hub_grafana waren aus demselben Grund schon vorher weg.
#
# Reihenfolge: Basis-Datei zuerst, Overlays danach — spaetere -f gewinnen. Die
# Manifest-Reihenfolge ist alphabetisch und taugt dafuer NICHT
# (docker-compose.llm-mcp.yml sortiert vor docker-compose.prod.yml).
_MANIFEST_PFAD="$APP_PATH/.deploy-manifest.json"
_DEKLARIERT=()
if [[ -f "$_MANIFEST_PFAD" ]]; then
  mapfile -t _DEKLARIERT < <(python3 -c "
import json, sys
try:
    d = json.load(open('$_MANIFEST_PFAD'))
except Exception:
    sys.exit(0)
for name in sorted(d.get('compose_files') or {}):
    print(name)
" 2>/dev/null || true)
fi

if [[ ${#_DEKLARIERT[@]} -gt 0 ]]; then
  for _f in "${_DEKLARIERT[@]}"; do
    [[ "$_f" == "$COMPOSE_FILE" ]] && continue          # Basis steht schon drin
    if [[ ! -f "$APP_PATH/$_f" ]]; then
      echo "::error::ADR-021 §2.20: '$_f' steht im CI-Manifest, fehlt aber am Host. Der Sync ist unvollstaendig — Abbruch statt Deploy mit halbem Stack."
      exit 8
    fi
    COMPOSE_ARGS+=(-f "$APP_PATH/$_f")
  done
  echo "✅ -f-Kette aus dem Manifest: ${#_DEKLARIERT[@]} deklarierte Datei(en)"

  # Undeklarierte compose-Dateien am Host: melden, aber NICHT mitfahren lassen.
  # Sie sind der Grund, warum die Kette aus dem Manifest kommt.
  for _h in "$APP_PATH"/docker-compose*.yml "$APP_PATH"/docker-compose*.yaml; do
    [[ -f "$_h" ]] || continue
    _n=$(basename "$_h")
    [[ "$_n" == "$COMPOSE_FILE" ]] && continue
    if ! printf '%s\n' "${_DEKLARIERT[@]}" | grep -qxF "$_n"; then
      echo "::warning::$_n liegt am Host, steht aber in keinem CI-Manifest — faehrt NICHT mit (undeklarierte Host-Datei, KONZ-015)."
    fi
  done
else
  # Rueckfall fuer Hubs, deren Manifest noch von einer aelteren shared-ci-Version
  # stammt: das Verhalten von platform#1063, unveraendert.
  if [[ -f "$APP_PATH/docker-compose.override.yml" ]]; then
    COMPOSE_ARGS+=(-f "$APP_PATH/docker-compose.override.yml")
    # Herkunfts-Warnung: Host-Override ohne CI-Manifest-Eintrag = aeltere
    # shared-ci-Version (synct override noch nicht) ODER undeklarierte
    # Host-Datei (KONZ-015-Fehlerklasse). Heute: laut warnen + mitfahren
    # (sonst Rezidiv der Container-Loeschung).
    if [[ "$ENVIRONMENT" == "production" ]] && ! python3 -c "import json,sys; d=json.load(open('$APP_PATH/.deploy-manifest.json')); sys.exit(0 if d.get('override_sha') else 1)" 2>/dev/null; then
      echo "::warning::docker-compose.override.yml am Host ohne override_sha im CI-Manifest — Herkunft ungesichert (platform#1063). Wird mitdeployt; Enforcement folgt."
    fi
  fi
  echo "::warning::Kein compose_files im Manifest — aeltere shared-ci-Version. -f-Kette faellt auf platform#1063 zurueck (nur docker-compose.override.yml)."
fi
# --- KETTE-ENDE

# ADR-021 §2.19 — pin COMPOSE_PROJECT_NAME explicitly for both environments.
# Previously only staging was pinned; prod relied on Docker Compose's implicit
# directory-derived name. Ground-truth audit (2026-06-01): all prod projects
# already use NAME == APP_NAME (verified via `docker compose ls` on prod —
# mcp-hub→mcp-hub, dev-hub→dev-hub, risk-hub→risk-hub etc). Pinning to the
# same value makes the contract explicit and causes deploy.sh to hard-fail if
# the running project name ever diverges (instead of silently managing the
# wrong project, stranding old containers that --remove-orphans can't find).
if [[ "$ENVIRONMENT" == "staging" ]]; then
  export COMPOSE_PROJECT_NAME="staging-${APP_NAME}"
else
  export COMPOSE_PROJECT_NAME="${APP_NAME}"
fi

# Safety check: if a running project with a DIFFERENT name owns containers in
# APP_PATH, warn loudly — this indicates a project-name migration is needed
# before this deploy can safely use --remove-orphans.
_running_proj=$(docker compose "${COMPOSE_ARGS[@]}" ls --format json 2>/dev/null \
  | python3 -c "import sys,json; rows=json.load(sys.stdin); print(rows[0]['Name'] if rows else '')" 2>/dev/null || true)
if [[ -n "$_running_proj" && "$_running_proj" != "$COMPOSE_PROJECT_NAME" ]]; then
  echo "::warning::COMPOSE_PROJECT_NAME mismatch — running='$_running_proj' expected='$COMPOSE_PROJECT_NAME'. --remove-orphans will not see the old containers. Continuing, but inspect manually."
fi

# ADR-021 §2.18 — Container Ownership Labels. Generate an override that stamps
# every service with iil.* provenance labels so audits/health key on labels,
# not container-name guessing (the name-only heuristic hid the orphaned
# Discord-Bot). Best-effort: on any failure we deploy without labels rather
# than break the deploy.
LABEL_ARGS=()
cd "$APP_PATH"
if _svcs=$(docker compose "${COMPOSE_ARGS[@]}" config --services 2>/dev/null); then
  _lf="$APP_PATH/.deploy-labels.override.yml"
  {
    echo "services:"
    for _s in $_svcs; do
      printf '  %s:\n    labels:\n' "$_s"
      printf '      iil.repo: "%s"\n      iil.service: "%s"\n      iil.environment: "%s"\n      iil.image_tag: "%s"\n      iil.deployed_at: "%s"\n' \
        "$APP_NAME" "$_s" "$ENVIRONMENT" "$IMAGE_TAG" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    done
  } > "$_lf" && LABEL_ARGS=(-f "$_lf")
fi

# Setzt IMAGE_TAG in der .env auf den tatsächlich laufenden Stand zurück.
# Nötig, wenn wir VOR `up -d` abbrechen (Migrations-Gate): die .env trägt dann
# schon den neuen Tag, deployt ist aber weiterhin der alte — ein späteres
# manuelles `docker compose up` würde sonst ungewollt den neuen Code starten.
_restore_image_tag() {
  [[ -n "$PREVIOUS_TAG" && -f "$APP_PATH/.env" ]] || return 0
  sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=${PREVIOUS_TAG}|" "$APP_PATH/.env" 2>/dev/null || true
  echo "↩️  .env IMAGE_TAG auf laufenden Stand zurückgesetzt: $PREVIOUS_TAG"
}

# Rollback-Funktion
rollback() {
  local ec=$?
  if [[ -n "$PREVIOUS_TAG" && "$PREVIOUS_TAG" != "$IMAGE_TAG" ]]; then
    echo "❌ Deploy fehlgeschlagen (exit $ec) — Rollback auf $PREVIOUS_TAG"
    cd "$APP_PATH"
    export IMAGE_TAG="$PREVIOUS_TAG"
    export _ROLLBACK_MODE=1  # bypass manifest/sha check during rollback
    docker compose "${COMPOSE_ARGS[@]}" "${LABEL_ARGS[@]}" up -d --force-recreate 2>&1 || {
      echo "KRITISCH: Rollback fehlgeschlagen! Manuell: IMAGE_TAG=$PREVIOUS_TAG docker compose ${COMPOSE_ARGS[*]} up -d" >&2
      exit 10
    }
    echo "⚠️  Rollback auf $PREVIOUS_TAG erfolgreich"
  fi
  exit "$ec"
}
trap rollback ERR

echo "═══════════════════════════════════════════════════"
echo "iil-Platform Deploy — ADR-120 (deploy.sh $DEPLOY_SH_VERSION)"
echo "App:  $APP_NAME"
echo "Env:  $ENVIRONMENT"
echo "Tag:  $IMAGE_TAG"
[[ -n "$PREVIOUS_TAG" ]] && echo "Prev: $PREVIOUS_TAG"
echo "═══════════════════════════════════════════════════"

# IMAGE_TAG in .env schreiben
if [[ -f "$APP_PATH/.env" ]] && grep -q "^IMAGE_TAG=" "$APP_PATH/.env"; then
  sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=${IMAGE_TAG}|" "$APP_PATH/.env"
else
  echo "IMAGE_TAG=${IMAGE_TAG}" >> "$APP_PATH/.env"
fi

# GHCR Login — bevorzugt kurzlebigen Workflow-Token (GHCR_TOKEN env), sonst Host-Datei.
# shared-ci _deploy-unified.yml reicht GHCR_TOKEN=${{ secrets.GITHUB_TOKEN }} + GHCR_USER durch
# (shared-ci#10 Facette A): so loggt JEDER Deploy mit eigenem ephemeren Token ein und hängt
# nicht mehr an der manuell gepflegten /opt/scripts/.ghcr_token, die unbemerkt ablaufen kann.
# Fallback auf die Host-Datei bleibt → rückwärtskompatibel für Konsumenten auf altem shared-ci-Ref.
#
# CREDENTIAL-ISOLATION (platform#1078 Befund 4): bis hierher schrieb `docker login`
# in die GETEILTE ~/.docker/config.json des Deploy-Users — und es gab kein `logout`.
# Die Credential blieb also nach jedem Deploy auf dem Host liegen. Ist sie abgelaufen,
# faellt Docker beim naechsten Pull NICHT auf einen anonymen Zugriff zurueck, sondern
# schickt die tote Credential mit und bekommt "denied". Genau daran starb der
# ausschreibungs-hub-Deploy am 2026-08-10 (platform#1845) — dort im Job-Setup einer
# Docker-Action, also an einer Stelle, die mit diesem Skript gar nichts zu tun hat.
# Das ist der Kern des Befunds: die vergiftete Datei trifft FREMDE Pulls auf demselben Host.
#
# Bewusst NICHT `docker logout` am Ende: auf diesen Hosts laufen mehrere Hubs, ein
# logout des einen Deploys wuerde einem zeitgleich laufenden anderen die Credential
# unter den Fuessen wegziehen. Stattdessen bekommt der Login eine eigene, kurzlebige
# DOCKER_CONFIG — die geteilte Datei wird nie angefasst, es gibt nichts aufzuraeumen
# und nichts, was liegenbleiben koennte. Nebeneffekt: der Token landet in einem
# mktemp-Verzeichnis (0700) statt in einer dauerhaften Datei.
_GHCR_CONFIG_DIR=""
_ghcr_config_cleanup() {
  [[ -n "$_GHCR_CONFIG_DIR" && -d "$_GHCR_CONFIG_DIR" ]] && rm -rf "$_GHCR_CONFIG_DIR"
  return 0
}
trap _ghcr_config_cleanup EXIT

if [[ -n "${GHCR_TOKEN:-}" ]]; then
  _GHCR_CONFIG_DIR="$(mktemp -d)"
  export DOCKER_CONFIG="$_GHCR_CONFIG_DIR"
  echo "$GHCR_TOKEN" | docker login ghcr.io -u "${GHCR_USER:-achimdehnert}" --password-stdin
elif [[ -f "/opt/scripts/.ghcr_token" ]]; then
  _GHCR_CONFIG_DIR="$(mktemp -d)"
  export DOCKER_CONFIG="$_GHCR_CONFIG_DIR"
  docker login ghcr.io -u achimdehnert --password-stdin < /opt/scripts/.ghcr_token
fi

# Deploy
cd "$APP_PATH"

# ADR-021 §2.17 + §2.20 — manifest verify + intent-token check (prod only).
# Rollbacks bypass the check so a failing deploy can always be rolled back.
_ROLLBACK_MODE="${_ROLLBACK_MODE:-0}"
if [[ "$ENVIRONMENT" == "production" && "$_ROLLBACK_MODE" != "1" ]]; then
  _MANIFEST="$APP_PATH/.deploy-manifest.json"

  # §2.20 Intent-Token: CI must have written a manifest; manual deploys require --break-glass.
  if [[ ! -f "$_MANIFEST" ]]; then
    if [[ -n "$BREAK_GLASS_REASON" ]]; then
      _BG_LOG="/var/log/iil-deploys/break-glass.log"
      mkdir -p "$(dirname "$_BG_LOG")" 2>/dev/null || true
      printf '%s [break-glass] app=%s image=%s reason="%s"\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$APP_NAME" "$IMAGE_TAG" "$BREAK_GLASS_REASON" \
        >> "$_BG_LOG" 2>/dev/null || true
      echo "⚠️  break-glass: proceeding without manifest. Reason: $BREAK_GLASS_REASON"
    else
      echo "::error::ADR-021 §2.20: No .deploy-manifest.json found. Production deploys require a CI-issued intent manifest. For manual deploys use: --break-glass \"REASON\""
      exit 6
    fi
  else
    # §2.17 compose_sha verify — fail-closed if on-host compose was tampered with.
    _EXPECTED_SHA=$(python3 -c "import json; d=json.load(open('$_MANIFEST')); print(d.get('compose_sha',''))" 2>/dev/null || true)
    if [[ -n "$_EXPECTED_SHA" && -f "$APP_PATH/$COMPOSE_FILE" ]]; then
      _ACTUAL_SHA=$(sha256sum "$APP_PATH/$COMPOSE_FILE" | awk '{print $1}')
      if [[ "$_ACTUAL_SHA" != "$_EXPECTED_SHA" ]]; then
        echo "::error::ADR-021 §2.17: compose sha256 mismatch. expected=$_EXPECTED_SHA actual=$_ACTUAL_SHA. Host compose may have been modified after CI sync. Aborting (fail-closed)."
        exit 7
      fi
      echo "✅ compose sha256 verified: $_ACTUAL_SHA"
    fi
    # platform#1063 — override-Integrität: sobald das CI-Manifest eine
    # override_sha trägt (neuere shared-ci-Version), gilt für die Override
    # dieselbe fail-closed-Prüfung wie für die Haupt-Datei.
    # platform#2586 K3 — jede deklarierte Datei wird geprueft, nicht nur die
    # Basis. Ohne das traegt der Deploy eine Overlay-Datei mit, deren Inhalt
    # nach dem CI-Sync veraendert wurde.
    python3 - "$_MANIFEST" "$APP_PATH" <<'PYSHA' || exit 7
import hashlib, json, pathlib, sys

manifest, app = sys.argv[1], pathlib.Path(sys.argv[2])
dateien = json.load(open(manifest)).get("compose_files") or {}
for name, erwartet in sorted(dateien.items()):
    pfad = app / name
    if not pfad.exists():
        print(f"::error::ADR-021 2.17: {name} steht im Manifest, fehlt am Host.")
        raise SystemExit(1)
    ist = hashlib.sha256(pfad.read_bytes()).hexdigest()
    if ist != erwartet:
        print(f"::error::ADR-021 2.17: sha256 mismatch fuer {name}. "
              f"expected={erwartet} actual={ist}. Abbruch (fail-closed).")
        raise SystemExit(1)
    print(f"OK compose sha256 verified: {name}")
PYSHA

    _EXPECTED_OSHA=$(python3 -c "import json; d=json.load(open('$_MANIFEST')); print(d.get('override_sha',''))" 2>/dev/null || true)
    if [[ -n "$_EXPECTED_OSHA" && -f "$APP_PATH/docker-compose.override.yml" ]]; then
      _ACTUAL_OSHA=$(sha256sum "$APP_PATH/docker-compose.override.yml" | awk '{print $1}')
      if [[ "$_ACTUAL_OSHA" != "$_EXPECTED_OSHA" ]]; then
        echo "::error::ADR-021 §2.17 (platform#1063): override sha256 mismatch. expected=$_EXPECTED_OSHA actual=$_ACTUAL_OSHA. Aborting (fail-closed)."
        exit 7
      fi
      echo "✅ override sha256 verified: $_ACTUAL_OSHA"
    fi
  fi
fi

# Staging: vor dem Hochfahren den Altstack sauber abräumen.
# `up -d --remove-orphans` entfernt nur Orphans DESSELBEN Compose-Projekts;
# ein Altcontainer aus einem früheren Run (anderes Projekt/Netz) bleibt
# bestehen und blockiert dauerhaft Host-Ports (real passiert:
# risk_hub_staging_minio hielt 127.0.0.1:9002 → Deploy + Rollback failten).
# Nur staging, damit Prod (self-hosted, kein Stale-Stack-Problem) keinen
# zusätzlichen Downtime durch ein down→up bekommt.
if [[ "$ENVIRONMENT" == "staging" ]]; then
  echo "Staging: räume Altstack ab (down --remove-orphans)"
  docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans 2>&1 || true
fi

docker compose "${COMPOSE_ARGS[@]}" pull

# ── Schema-Migrationen — VOR dem Traffic-Switch, fail-closed ──────────────────
# Root-Cause illustration-hub#66: dieses Skript lief ohne migrate-Schritt →
# gemergte Migrationen erreichten die Prod-DB nie ("Deploy grün ≠ Schema aktuell").
# Gemessen 2026-07-24: assets.0004 (is_active) fehlte auf Prod; der erste echte
# Render starb an `column "is_active" does not exist` — bei durchweg grünen Deploys.
#
# Reihenfolge mit Absicht VOR `up -d`: die Migration läuft in einem Wegwerf-
# Container des BEREITS GEPULLTEN neuen Images, während der alte Stack noch
# Traffic bedient.
#   migrate scheitert → alter Code + altes Schema laufen unberührt weiter; es
#                       entsteht kein Fenster "neuer Code auf altem Schema"
#   migrate ok        → `up -d` schaltet auf den neuen Code um
# `exec` in den laufenden Container (Vorgänger-Ansatz) kann das nicht leisten:
# vor `up` läuft dort das ALTE Image (Migration fehlt), nach `up` bedient der
# neue Code bereits Traffic gegen das alte Schema.
#
# Voraussetzung ist die übliche expand/contract-Disziplin: eine Migration muss
# zum ALTEN Code rückwärtskompatibel sein (additive Spalten; Löschen/Umbenennen
# erst im Folge-Release). Siehe docs/conventions/deploy-migrations.md.
#
# Opt-out für Stacks, die bewusst anders migrieren:  DEPLOY_MIGRATE=0
# Override, falls die Service-Heuristik danebengreift: DEPLOY_MIGRATE_SERVICE=<name>
if [[ "${DEPLOY_MIGRATE:-1}" == "1" ]]; then
  _MIG_SVC="${DEPLOY_MIGRATE_SERVICE:-}"
  if [[ -z "$_MIG_SVC" ]]; then
    _MIG_SVC=$(docker compose "${COMPOSE_ARGS[@]}" config --services 2>/dev/null \
      | grep -E '(^|[-_])web$' | head -1 || true)
  fi

  if [[ -z "$_MIG_SVC" ]]; then
    echo "ℹ️  Migrate: kein '*web'-Service deklariert — übersprungen (Nicht-Django-Stack)."
  elif ! docker compose "${COMPOSE_ARGS[@]}" run --rm --no-deps --entrypoint sh \
         "$_MIG_SVC" -c 'test -f manage.py' >/dev/null 2>&1; then
    # Laut, nicht still: ein falsch-negatives Skippen ist genau die Fehlerklasse
    # aus #66 (Migration bleibt unbemerkt aus). Override via DEPLOY_MIGRATE_SERVICE.
    echo "::warning::Migrate: '$_MIG_SVC' hat kein manage.py im WORKDIR — übersprungen. Falls doch Django: DEPLOY_MIGRATE_SERVICE setzen."
  else
    echo "--- Migrationen ($_MIG_SVC, Image $IMAGE_TAG) ---"

    # Deklarierte Abhängigkeiten (db/redis) hochziehen, ohne laufende Container
    # anzufassen. Nötig, weil die Migration gleich mit --no-deps läuft:
    # `run` OHNE --no-deps startet die Deps nicht nur, es RECREATED sie
    # (gemessen 2026-07-25 auf risk-hub-staging: db + redis wurden neu erstellt) —
    # das wäre ein DB-Neustart bei JEDEM Prod-Deploy. `up -d --no-recreate` ist
    # idempotent und lässt bereits laufende Container in Ruhe; auf Staging, wo
    # dieses Skript vorher `down` fährt, zieht es db/redis überhaupt erst hoch.
    _MIG_DEPS=$(docker compose "${COMPOSE_ARGS[@]}" config --format json 2>/dev/null \
      | python3 -c "import json,sys; d=json.load(sys.stdin); print(' '.join((d.get('services',{}).get('$_MIG_SVC') or {}).get('depends_on') or {}))" 2>/dev/null || true)
    if [[ -n "$_MIG_DEPS" ]]; then
      echo "    Abhängigkeiten bereitstellen: $_MIG_DEPS"
      # Wortsplitting ist hier gewollt: $_MIG_DEPS ist eine Service-Liste.
      # shellcheck disable=SC2086
      docker compose "${COMPOSE_ARGS[@]}" up -d --no-recreate $_MIG_DEPS
    fi

    # --entrypoint sh ist Pflicht, kein Stilmittel: die App-Images haben einen
    # eigenen ENTRYPOINT (z.B. `/entrypoint.sh [web|worker|celery]`). Ohne
    # Override kommt "python manage.py migrate" nur als dessen ARGUMENT an, der
    # Container antwortet mit Usage-Text und Exit 1 — die Migration liefe nie,
    # der Deploy bräche mit irreführender Meldung ab (gemessen 2026-07-25).
    #
    # Der Override hat aber einen Preis, der 2026-08-20 in travel-beat sichtbar
    # wurde: er umgeht damit AUCH die Logik IM Entrypoint. travel-beat hatte nach
    # einem Crash-Loop (2026-06-17) genau richtig `DATABASE_URL_MIGRATE` eingebaut
    # — privilegierte DDL als Migrations-Rolle, Laufzeit weiter als restricted
    # User — und dieser Mechanismus war auf dem Deploy-Pfad **wirkungslos**, weil
    # der Entrypoint hier nie läuft. Ergebnis: `migrate_schemas` lief als
    # restricted Rolle, die auf den Tenant-Schemata kein USAGE hat, und starb mit
    # "no schema has been selected to create in" — exakt der Fehler, den der
    # Entrypoint-Kommentar vorhersagt. Der Prod-Stand hing dadurch seit dem
    # 2026-08-11 zurück (travel-beat#79).
    #
    # Deshalb wird die Ableitung hier nachgezogen, mit derselben Semantik wie im
    # Entrypoint: `DATABASE_URL_MIGRATE` gewinnt, sonst bleibt `DATABASE_URL`.
    # Repos ohne die Variable verhalten sich damit unverändert — die Zuweisung
    # wirkt nur für diesen einen Prozess, nicht für den laufenden Stack.
    if ! docker compose "${COMPOSE_ARGS[@]}" run --rm --no-deps --entrypoint sh \
           "$_MIG_SVC" -c 'DATABASE_URL="${DATABASE_URL_MIGRATE:-$DATABASE_URL}" python manage.py migrate --noinput'; then
      _restore_image_tag
      echo "::error::Migration fehlgeschlagen — Deploy abgebrochen. Der ALTE Stack läuft unverändert weiter." >&2
      echo "         DB kann teilmigriert sein: 'manage.py showmigrations' prüfen." >&2
      echo "         KEIN blindes '--fake' — genau das erzeugte den half-applied-Zustand aus #66." >&2
      exit 2
    fi
    # Verifikation: nach 'migrate' darf nichts mehr pending sein. Fängt
    # Teil-Applies und --fake-Artefakte (assets.0002 aus #66), die 'migrate'
    # selbst mit Exit 0 hinterlassen kann.
    if ! docker compose "${COMPOSE_ARGS[@]}" run --rm --no-deps --entrypoint sh \
           "$_MIG_SVC" -c 'DATABASE_URL="${DATABASE_URL_MIGRATE:-$DATABASE_URL}" python manage.py migrate --check --noinput' >/dev/null 2>&1; then
      _restore_image_tag
      echo "::error::Nach 'migrate' sind weiter Migrationen pending — Schema-Drift, Deploy abgebrochen." >&2
      echo "         Kein Auto-Rollback: Teil-Migrationen lassen sich nicht sicher zurückrollen." >&2
      exit 2
    fi
    echo "✅ Schema aktuell ('migrate --check' sauber)"
  fi
else
  echo "ℹ️  Migrate: per DEPLOY_MIGRATE=0 deaktiviert."
fi

docker compose "${COMPOSE_ARGS[@]}" "${LABEL_ARGS[@]}" up -d --force-recreate --remove-orphans

# Health-Check
# Staging: derive local URL from the WEB service's host-port mapping.
# We must NOT just take the first 127.0.0.1:PORT line in the compose
# file — that frequently belongs to MinIO/Redis/etc. Try (in order):
#   1. docker compose port lookup on every service whose name ends in -web
#   2. awk-parse the compose block under a `*-web:` service key
#   3. legacy fallback: first 127.0.0.1 host port (preserves old behaviour)
if [[ "$ENVIRONMENT" == "staging" ]]; then
  LOCAL_PORT=""

  for svc in $(docker compose "${COMPOSE_ARGS[@]}" config --services 2>/dev/null | grep -E '(^|-)web$' || true); do
    LOCAL_PORT=$(docker compose "${COMPOSE_ARGS[@]}" port "$svc" 8000 2>/dev/null | awk -F: '{print $NF}' | head -1 || true)
    [[ -n "$LOCAL_PORT" ]] && break
  done

  if [[ -z "$LOCAL_PORT" ]]; then
    LOCAL_PORT=$(awk '
      /^  [a-zA-Z0-9_-]+-web:[[:space:]]*$/ { in_web=1; next }
      /^  [a-zA-Z0-9_-]+:[[:space:]]*$/     { in_web=0 }
      in_web && match($0, /127\.0\.0\.1:[0-9]+/) {
        s = substr($0, RSTART, RLENGTH)
        sub(/.*:/, "", s)
        print s; exit
      }
    ' "$APP_PATH/$COMPOSE_FILE" || true)
  fi

  if [[ -z "$LOCAL_PORT" ]]; then
    LOCAL_PORT=$(grep -oP '127\.0\.0\.1:\K\d+' "$APP_PATH/$COMPOSE_FILE" | head -1 || true)
  fi

  if [[ -n "$LOCAL_PORT" ]]; then
    HEALTH_CHECK_URL="http://127.0.0.1:${LOCAL_PORT}/livez/"
    echo "Staging: using local health check $HEALTH_CHECK_URL"
  fi
fi

# Retry-Budget konfigurierbar (Default 30 × 5s ≈ 150s Sleep + curl). Vorher fix 12 (60s) —
# zu kurz für langsame Cold-Starts (z.B. dev-hub: 16 Django-Apps gunicorn-Boot >60s) →
# falsch-roter Deploy trotz gesundem Prod (ADR-231 Welle 0). Loop bricht beim ersten 200 →
# schnelle Apps verlieren nichts; nur echt-langsame/kaputte Deploys nutzen das Budget aus.
# Per-Deploy übersteuerbar via env HEALTH_CHECK_RETRIES.
HEALTH_CHECK_RETRIES="${HEALTH_CHECK_RETRIES:-30}"
if [[ -n "$HEALTH_CHECK_URL" ]]; then
  echo "Health-Check: $HEALTH_CHECK_URL (max $HEALTH_CHECK_RETRIES Versuche)"
  for i in $(seq 1 "$HEALTH_CHECK_RETRIES"); do
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "$HEALTH_CHECK_URL" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
      echo "✅ Health-Check OK (Versuch $i/$HEALTH_CHECK_RETRIES)"
      break
    fi
    echo "⏳ Versuch $i/$HEALTH_CHECK_RETRIES — HTTP $HTTP_CODE"
    sleep 5
    [[ $i -eq "$HEALTH_CHECK_RETRIES" ]] && { echo "❌ Health-Check fehlgeschlagen nach $((HEALTH_CHECK_RETRIES * 5))s"; exit 4; }
  done
else
  sleep 5
  docker compose "${COMPOSE_ARGS[@]}" ps | grep -qi "unhealthy\|exit\|error" && {
    echo "❌ Container in Fehlerzustand"
    exit 5
  }
  echo "✅ Container läuft"
fi

# ── Crashloop-Gate (platform#1124): ein Web-livez-200 beweist NICHT, dass
# Sidecar-Container (beat, worker) gesund sind. Ein Crashloop zyklt durch
# "Up (healthy)" und entgeht jeder Momentaufnahme (`ps | grep` oben) — daher
# RestartCount über ein Grace-Fenster VERGLEICHEN statt einmal messen. Ein
# langsamer Cold-Start (der bis hierher schon durch den Health-Check-Retry
# stabilisiert ist) hat Δ=0; nur ein echter Loop wächst weiter.
# Realfall trading-hub 2026-07-12: beat crashloopte 5h18min hinter grünen
# Deploys, weil nur livez geprüft wurde (Retro platform#1123 C3/C4).
if [[ "${SKIP_CRASHLOOP_GATE:-0}" != "1" ]]; then
  CRASHLOOP_GRACE="${CRASHLOOP_GRACE:-45}"
  _cids=$(docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null || true)
  if [[ -n "$_cids" ]]; then
    echo "Crashloop-Gate: RestartCount-Delta über ${CRASHLOOP_GRACE}s …"
    declare -A _rc0
    for _c in $_cids; do
      _rc0["$_c"]=$(docker inspect -f '{{.RestartCount}}' "$_c" 2>/dev/null || echo 0)
    done
    sleep "$CRASHLOOP_GRACE"
    _bad=""
    for _c in $_cids; do
      _name=$(docker inspect -f '{{.Name}}' "$_c" 2>/dev/null | sed 's#^/##')
      _rc1=$(docker inspect -f '{{.RestartCount}}' "$_c" 2>/dev/null || echo 0)
      _state=$(docker inspect -f '{{.State.Status}}' "$_c" 2>/dev/null || echo unknown)
      if (( _rc1 > ${_rc0["$_c"]:-0} )); then
        echo "❌ $_name crashloopt: RestartCount ${_rc0["$_c"]} → $_rc1 im Grace-Fenster"
        _bad="$_bad $_name"
      elif [[ "$_state" == "exited" ]]; then
        # platform#1849: "exited" ist NICHT per se ungesund. Ein One-Shot
        # (migrate, seed, collectstatic) beendet sich planmäßig — das ist sein
        # Erfolgsfall. Bis hierher galt jedes "exited" als Defekt; dadurch war
        # z.B. jeder tax-hub-Deploy rot, obwohl Web lief, die Migrationen
        # angewandt waren und /livez/ 200 lieferte (5 Läufe in Folge).
        #
        # Unterschieden wird über die Restart-Policy, nicht über den Namen:
        # Dienste laufen mit "unless-stopped"/"always" und haben in "exited"
        # nichts verloren — ein One-Shot läuft ohne Policy ("no"). Der
        # ExitCode muss zusätzlich 0 sein; ein One-Shot, der mit Fehler
        # abbricht (fehlgeschlagene Migration!), bleibt ein Befund.
        _ec=$(docker inspect -f '{{.State.ExitCode}}' "$_c" 2>/dev/null || echo 1)
        _pol=$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$_c" 2>/dev/null || echo "")
        if (( _ec == 0 )) && [[ "$_pol" == "no" || -z "$_pol" ]]; then
          echo "ℹ️  $_name beendet (ExitCode 0, restart=${_pol:-no}) — One-Shot, kein Befund"
        else
          echo "❌ $_name im Zustand 'exited' (ExitCode $_ec, restart=${_pol:-no})"
          _bad="$_bad $_name"
        fi
      elif [[ "$_state" == "restarting" || "$_state" == "dead" ]]; then
        echo "❌ $_name im Zustand '$_state'"
        _bad="$_bad $_name"
      fi
    done
    if [[ -n "$_bad" ]]; then
      echo "❌ Crashloop-Gate fehlgeschlagen:$_bad — Deploy gilt als NICHT gesund."
      exit 6
    fi
    echo "✅ Crashloop-Gate OK — kein Container crashloopt (Δ RestartCount = 0)"
  fi
fi

# Cleanup: nur dangling (ungetaggte) Images — nicht zu aggressiv
docker image prune -f 2>/dev/null || true

trap - ERR
echo "═══════════════════════════════════════════════════"
echo "✅ Deploy erfolgreich: $APP_NAME:$IMAGE_TAG ($ENVIRONMENT)"
echo "═══════════════════════════════════════════════════"
