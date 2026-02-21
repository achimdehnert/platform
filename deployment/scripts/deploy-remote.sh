#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# deploy-remote.sh — Production deploy script for Hetzner VMs
# ═══════════════════════════════════════════════════════════════════════════════
#
# Called via SSH from GitHub Actions or manually on the VM.
# Handles: image pull, DB migrations (expand-only gate), rolling restart,
#          healthcheck loop, automatic rollback, audit logging.
#
# Usage:
#   deploy-remote.sh --tag <IMAGE_TAG> --app <APP_NAME> [OPTIONS]
#
# Options:
#   --tag              Docker image tag to deploy (required)
#   --app              Application name, e.g. bfagent (required)
#   --compose-file     Compose file (default: docker-compose.prod.yml)
#   --env-file         Env file (default: .env.prod)
#   --deploy-dir       Deploy directory (default: /opt/<app>)
#   --web-service      Web service name in compose (default: <app>-web)
#   --health-endpoint  Health check path (default: /healthz/)
#   --health-retries   Number of health check retries (default: 12)
#   --health-interval  Seconds between retries (default: 5)
#   --skip-migrate     Skip database migrations
#   --skip-backup      Skip pre-deploy DB backup
#   --dry-run          Print actions without executing
#   --rollback-to      Rollback to a specific tag (skips pull/migrate)
#   --django-tenants   Use migrate_schemas instead of migrate (ADR-056)
#
# Exit codes:
#   0 = success
#   1 = general error
#   2 = healthcheck failed (rollback attempted)
#   3 = rollback failed (manual intervention required)
#   4 = migration failed (containers NOT restarted)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ─── Defaults ────────────────────────────────────────────────────────────────
IMAGE_TAG=""
APP_NAME=""
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
DEPLOY_DIR=""
WEB_SERVICE=""
SKIP_MIGRATE=false
SKIP_BACKUP=false
DRY_RUN=false
ROLLBACK_TO=""
HEALTH_RETRIES=12
HEALTH_INTERVAL=5
HEALTH_ENDPOINT="/healthz/"
DJANGO_TENANTS=false

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

ts()    { date '+%Y-%m-%dT%H:%M:%S%z'; }
log()   { echo -e "${GREEN}[$(ts)]${NC} $*"; }
warn()  { echo -e "${YELLOW}[$(ts)] WARN:${NC} $*" >&2; }
err()   { echo -e "${RED}[$(ts)] ERROR:${NC} $*" >&2; }
info()  { echo -e "${BLUE}[$(ts)]${NC} $*"; }

audit() {
    local action="$1" status="$2" detail="${3:-}"
    local entry
    entry=$(printf '{"ts":"%s","app":"%s","tag":"%s","action":"%s","status":"%s","detail":"%s"}' \
        "$(ts)" "$APP_NAME" "$IMAGE_TAG" "$action" "$status" "$detail")
    echo "$entry" >> "${DEPLOY_DIR}/deployments.jsonl"
}

die() { err "$1"; audit "deploy" "failed" "$1"; exit "${2:-1}"; }

# ─── Parse arguments ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tag)               IMAGE_TAG="$2";         shift 2 ;;
        --app)               APP_NAME="$2";          shift 2 ;;
        --compose-file)      COMPOSE_FILE="$2";      shift 2 ;;
        --env-file)          ENV_FILE="$2";          shift 2 ;;
        --deploy-dir)        DEPLOY_DIR="$2";        shift 2 ;;
        --web-service)       WEB_SERVICE="$2";       shift 2 ;;
        --skip-migrate)      SKIP_MIGRATE=true;      shift   ;;
        --skip-backup)       SKIP_BACKUP=true;       shift   ;;
        --dry-run)           DRY_RUN=true;           shift   ;;
        --rollback-to)       ROLLBACK_TO="$2";       shift 2 ;;
        --health-retries)    HEALTH_RETRIES="$2";    shift 2 ;;
        --health-interval)   HEALTH_INTERVAL="$2";   shift 2 ;;
        --health-endpoint)   HEALTH_ENDPOINT="$2";   shift 2 ;;
        --django-tenants)    DJANGO_TENANTS=true;    shift   ;;
        *) die "Unknown option: $1" 1 ;;
    esac
done

[[ -z "$IMAGE_TAG" ]] && die "--tag is required" 1
[[ -z "$APP_NAME" ]]  && die "--app is required" 1

DEPLOY_DIR="${DEPLOY_DIR:-/opt/${APP_NAME}}"
WEB_SERVICE="${WEB_SERVICE:-${APP_NAME}-web}"
TAG_VAR="IMAGE_TAG"

# ─── Validate environment ────────────────────────────────────────────────────
[[ -d "$DEPLOY_DIR" ]]                   || die "Deploy dir not found: $DEPLOY_DIR" 1
[[ -f "${DEPLOY_DIR}/${COMPOSE_FILE}" ]] || die "Compose file not found: ${DEPLOY_DIR}/${COMPOSE_FILE}" 1
[[ -f "${DEPLOY_DIR}/${ENV_FILE}" ]]     || die "Env file not found: ${DEPLOY_DIR}/${ENV_FILE}" 1
command -v docker >/dev/null             || die "docker not found" 1
docker info >/dev/null 2>&1              || die "docker daemon not running" 1

cd "$DEPLOY_DIR"
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

log "═══════════════════════════════════════════════════════════"
log "  Deploy: ${APP_NAME}  Tag: ${IMAGE_TAG}"
log "  Dir: ${DEPLOY_DIR}  Compose: ${COMPOSE_FILE}"
$DJANGO_TENANTS && log "  Mode: django-tenants (migrate_schemas)"
log "═══════════════════════════════════════════════════════════"

# ─── 1. Save current state ───────────────────────────────────────────────────
PREV_TAG=$(grep -oP "${TAG_VAR}=\K.*" "$ENV_FILE" 2>/dev/null | head -1 | tr -d '\n\r' || echo "unknown")
echo "${TAG_VAR}=${PREV_TAG}" > "${DEPLOY_DIR}/.rollback_state"
info "Previous tag: ${PREV_TAG}"

[[ -n "$ROLLBACK_TO" ]] && { log "Rolling back to ${ROLLBACK_TO}..."; IMAGE_TAG="$ROLLBACK_TO"; }

if $DRY_RUN; then
    info "[DRY-RUN] Would set ${TAG_VAR}=${IMAGE_TAG} and restart ${WEB_SERVICE}"
    exit 0
fi

# ─── 2. Pre-deploy DB backup ─────────────────────────────────────────────────
if ! $SKIP_BACKUP; then
    DB_CONTAINER=$(compose ps --format '{{.Names}}' 2>/dev/null | grep -E '(postgres|_db)' | head -1 || true)
    if [[ -n "$DB_CONTAINER" ]]; then
        BACKUP_DIR="${DEPLOY_DIR}/backups"
        mkdir -p "$BACKUP_DIR"
        BACKUP_FILE="${BACKUP_DIR}/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz"
        log "Creating DB backup..."
        if docker exec "$DB_CONTAINER" pg_dumpall -U "${POSTGRES_USER:-postgres}" 2>/dev/null | gzip > "$BACKUP_FILE"; then
            info "Backup: ${BACKUP_FILE} ($(du -h "$BACKUP_FILE" | cut -f1))"
            audit "backup" "ok" "$BACKUP_FILE"
        else
            warn "DB backup failed — continuing (non-blocking)"
        fi
        ls -1t "${BACKUP_DIR}"/pre_deploy_*.sql.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
    else
        info "No postgres container found — skipping backup"
    fi
fi

# ─── 3. Update image tag ──────────────────────────────────────────────────────
log "Setting ${TAG_VAR}=${IMAGE_TAG}"
if grep -q "^${TAG_VAR}=" "$ENV_FILE"; then
    sed -i "s|^${TAG_VAR}=.*|${TAG_VAR}=${IMAGE_TAG}|" "$ENV_FILE"
else
    echo "${TAG_VAR}=${IMAGE_TAG}" >> "$ENV_FILE"
fi

# ─── 4. Pull new image ────────────────────────────────────────────────────────
log "Pulling images..."
compose pull "$WEB_SERVICE" || die "Image pull failed for tag ${IMAGE_TAG}" 1

# ─── 5. Migrations ───────────────────────────────────────────────────────────
if ! $SKIP_MIGRATE && [[ -z "$ROLLBACK_TO" ]]; then
    log "Running migrations (expand phase)..."
    MIGRATE_EXIT=0

    if $DJANGO_TENANTS; then
        # Step 5a: shared schema
        log "Running migrate_schemas --shared (django-tenants)..."
        compose run --rm --no-deps "$WEB_SERVICE" \
            python manage.py migrate_schemas --shared --noinput 2>&1 | tee /tmp/migrate.log || MIGRATE_EXIT=$?

        if [[ $MIGRATE_EXIT -ne 0 ]]; then
            err "migrate_schemas --shared FAILED (exit code: ${MIGRATE_EXIT})"
            sed -i "s|^${TAG_VAR}=.*|${TAG_VAR}=${PREV_TAG}|" "$ENV_FILE"
            audit "migrate" "failed" "step=shared,exit=${MIGRATE_EXIT}"
            exit 4
        fi

        # Step 5b: provision default tenant (idempotent)
        # TenantMixin has no 'name' field — only schema_name is required
        log "Provisioning default tenant (idempotent)..."
        compose run --rm --no-deps "$WEB_SERVICE" python manage.py shell -c "
from apps.tenants.models import Client, Domain
schema = '${APP_NAME}'.replace('-', '_')
if not Client.objects.filter(schema_name=schema).exists():
    t = Client(schema_name=schema)
    t.save(verbosity=0)
    Domain.objects.get_or_create(domain='${APP_NAME}.app', defaults={'tenant': t, 'is_primary': True})
    print('Tenant created: ' + schema)
else:
    print('Tenant already exists: ' + schema)
" 2>&1 || warn "Tenant provisioning warning — check logs"

        # Step 5c: all tenant schemas
        log "Running migrate_schemas (all tenants)..."
        compose run --rm --no-deps "$WEB_SERVICE" \
            python manage.py migrate_schemas --noinput 2>&1 | tee -a /tmp/migrate.log || MIGRATE_EXIT=$?
    else
        compose run --rm --no-deps "$WEB_SERVICE" \
            python manage.py migrate --noinput 2>&1 | tee /tmp/migrate.log || MIGRATE_EXIT=$?
    fi

    if [[ $MIGRATE_EXIT -ne 0 ]]; then
        err "Migration FAILED (exit code: ${MIGRATE_EXIT})"
        sed -i "s|^${TAG_VAR}=.*|${TAG_VAR}=${PREV_TAG}|" "$ENV_FILE"
        audit "migrate" "failed" "exit=${MIGRATE_EXIT}"
        exit 4
    fi
    log "Migrations applied successfully"
    audit "migrate" "ok" ""
fi

# ─── 6. Rolling restart ───────────────────────────────────────────────────────
log "Restarting ${WEB_SERVICE}..."
compose up -d --no-deps --force-recreate "$WEB_SERVICE"

WORKER_SERVICE="${APP_NAME}-worker"
if compose ps --services 2>/dev/null | grep -q "^${WORKER_SERVICE}$"; then
    log "Restarting ${WORKER_SERVICE}..."
    compose up -d --no-deps --force-recreate "$WORKER_SERVICE"
fi

WEB_CONTAINER=$(compose ps --format '{{.Names}}' "$WEB_SERVICE" 2>/dev/null | head -1)

# ─── 7. Healthcheck ───────────────────────────────────────────────────────────
log "Waiting for healthcheck (${HEALTH_RETRIES}x${HEALTH_INTERVAL}s)..."

# Prefer host port binding; fall back to container IP.
# Use python3 to extract the first IP cleanly — avoids bash regex issues
# with multi-network containers that concatenate IPs without separator.
HEALTH_PORT=$(docker port "$WEB_CONTAINER" 8000 2>/dev/null | head -1 | cut -d: -f2 || echo "")
if [[ -n "$HEALTH_PORT" ]]; then
    HEALTH_URL="http://127.0.0.1:${HEALTH_PORT}${HEALTH_ENDPOINT}"
else
    CONTAINER_IP=$(docker inspect "$WEB_CONTAINER" \
        --format '{{json .NetworkSettings.Networks}}' 2>/dev/null \
        | python3 -c "import sys,json; nets=json.load(sys.stdin); print(list(nets.values())[0]['IPAddress'])" \
        2>/dev/null || echo "")
    HEALTH_URL="http://${CONTAINER_IP:-127.0.0.1}:8000${HEALTH_ENDPOINT}"
fi
info "Health URL: ${HEALTH_URL}"

HEALTHY=false
for i in $(seq 1 "$HEALTH_RETRIES"); do
    sleep "$HEALTH_INTERVAL"
    HTTP_CODE=$(curl -sf -o /dev/null -w '%{http_code}' "$HEALTH_URL" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
        log "Healthcheck PASSED (attempt ${i}/${HEALTH_RETRIES})"
        HEALTHY=true
        break
    fi
    warn "Healthcheck: HTTP ${HTTP_CODE} (attempt ${i}/${HEALTH_RETRIES})"
done

# ─── 8. Rollback on failure ───────────────────────────────────────────────────
if ! $HEALTHY; then
    err "Healthcheck FAILED after ${HEALTH_RETRIES} attempts"
    audit "healthcheck" "failed" "url=${HEALTH_URL},last_http=${HTTP_CODE}"

    if [[ "$PREV_TAG" != "unknown" && "$PREV_TAG" != "$IMAGE_TAG" ]]; then
        warn "Rolling back to ${PREV_TAG}..."
        sed -i "s|^${TAG_VAR}=.*|${TAG_VAR}=${PREV_TAG}|" "$ENV_FILE"
        compose pull "$WEB_SERVICE" || true
        compose up -d --no-deps --force-recreate "$WEB_SERVICE"
        sleep 10
        RB_CODE=$(curl -sf -o /dev/null -w '%{http_code}' "$HEALTH_URL" 2>/dev/null || echo "000")
        if [[ "$RB_CODE" == "200" ]]; then
            warn "Rollback SUCCEEDED (HTTP ${RB_CODE})"
            audit "rollback" "ok" "to=${PREV_TAG}"
            exit 2
        else
            err "Rollback FAILED (HTTP ${RB_CODE}) — MANUAL INTERVENTION REQUIRED"
            audit "rollback" "failed" "to=${PREV_TAG},http=${RB_CODE}"
            exit 3
        fi
    else
        err "No previous tag to rollback to — MANUAL INTERVENTION REQUIRED"
        exit 3
    fi
fi

# ─── 9. Cleanup + Success ─────────────────────────────────────────────────────
docker image prune -f >/dev/null 2>&1 || true
rm -f "${DEPLOY_DIR}/.rollback_state"
audit "deploy" "ok" "from=${PREV_TAG}"
log "═══════════════════════════════════════════════════════════"
log "  DEPLOY OK: ${APP_NAME} → ${IMAGE_TAG}"
log "  Previous:  ${PREV_TAG}"
log "═══════════════════════════════════════════════════════════"
exit 0
