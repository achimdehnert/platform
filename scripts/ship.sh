#!/bin/bash
# =============================================================================
# platform/scripts/ship.sh — Zentrales Deploy-Script für alle Repos
# =============================================================================
# Wird von jedem Repo-Wrapper (scripts/ship.sh) aufgerufen, oder direkt:
#
#   Usage:
#     ./scripts/ship.sh "feat: commit msg"       # Build + Deploy Production
#     ./scripts/ship.sh staging                   # Build + Deploy Staging
#     ./scripts/ship.sh promote                   # Staging-Image → Production
#     ./scripts/ship.sh staging "feat: commit"    # Staging mit Commit-Msg
#
# Config: .ship.conf im Repo-Root (wird automatisch geladen)
#
# Pflichtfelder in .ship.conf:
#   APP_NAME    — Anzeigename
#   IMAGE       — ghcr.io/... Docker image (ohne :tag)
#   DOCKERFILE  — Pfad zum Dockerfile (relativ zum Repo-Root)
#   WEB_SERVICE — Docker Compose service name
#   COMPOSE_PATH — Absoluter Pfad auf dem Server
#   COMPOSE_FILE — z.B. docker-compose.prod.yml
#   HEALTH_URL  — https://...
#   MIGRATE_CMD — z.B. "python manage.py migrate --no-input"
#
# Optional:
#   SERVER       — Default: root@88.198.191.108
#   STAGING_PORT — Host-Port für Staging (Default: Prod-Port + 100)
# =============================================================================
set -euo pipefail

# -----------------------------------------------------------------------------
# Argumente parsen: [--repo DIR] [staging|promote] ["commit msg"]
# -----------------------------------------------------------------------------
REPO_DIR=""
COMMIT_MSG=""
MODE="production"   # production | staging | promote

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO_DIR="$2"; shift 2 ;;
    staging)
      MODE="staging"; shift ;;
    promote)
      MODE="promote"; shift ;;
    *)
      COMMIT_MSG="$1"; shift ;;
  esac
done

if [ -z "$REPO_DIR" ]; then
  # Wird aus scripts/ship.sh im Repo aufgerufen — zwei Ebenen hoch
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # Wenn wir in platform/scripts/ sind, können wir kein Repo inferieren
  if [ -f "$SCRIPT_DIR/../.ship.conf" ]; then
    REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
  else
    echo "ERROR: Kein Repo-Root gefunden. Bitte --repo /pfad/zum/repo angeben." >&2
    exit 1
  fi
fi

CONF="$REPO_DIR/.ship.conf"
if [ ! -f "$CONF" ]; then
  echo "ERROR: $CONF nicht gefunden. Bitte .ship.conf im Repo-Root anlegen." >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Config laden
# -----------------------------------------------------------------------------
# shellcheck source=/dev/null
source "$CONF"

SERVER="${SERVER:-root@88.198.191.108}"

# Pflichtfelder prüfen
for var in APP_NAME IMAGE DOCKERFILE WEB_SERVICE COMPOSE_PATH COMPOSE_FILE HEALTH_URL MIGRATE_CMD; do
  if [ -z "${!var:-}" ]; then
    echo "ERROR: $var ist nicht in $CONF gesetzt." >&2
    exit 1
  fi
done

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "   ${GREEN}✓${NC} $1"; }
warn() { echo -e "   ${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "   ${RED}✗${NC} $1"; exit 1; }

# -----------------------------------------------------------------------------
# Auto-commit message
# -----------------------------------------------------------------------------
if [ -z "${COMMIT_MSG:-}" ]; then
  CHANGED=$(git -C "$REPO_DIR" diff --cached --name-only 2>/dev/null; \
            git -C "$REPO_DIR" diff --name-only; \
            git -C "$REPO_DIR" ls-files --others --exclude-standard)
  PARTS=""
  for dir in templates apps static config scripts; do
    COUNT=$(echo "$CHANGED" | grep -c "^$dir/" || true)
    [ "$COUNT" -gt 0 ] && PARTS="$PARTS $dir($COUNT)"
  done
  [ -z "$PARTS" ] && PARTS=" update"
  COMMIT_MSG="chore:$PARTS"
fi

# Derive image base (strip :latest/:staging if present)
IMAGE_BASE="${IMAGE%%:*}"

echo ""
echo "🚀 $APP_NAME ship [$MODE] — $(date '+%H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# =============================================================================
# PROMOTE mode — retag staging → latest, push, deploy production
# =============================================================================
if [ "$MODE" = "promote" ]; then
  echo ""
  echo "🏷️  [1/3] Retag staging → latest..."
  docker pull "$IMAGE_BASE:staging" 2>/dev/null \
    || fail "Image $IMAGE_BASE:staging nicht gefunden. Erst 'ship staging' ausführen."
  docker tag "$IMAGE_BASE:staging" "$IMAGE_BASE:latest"
  ok "$IMAGE_BASE:staging → :latest"

  echo ""
  echo "📤 [2/3] Docker push :latest → GHCR..."
  docker push "$IMAGE_BASE:latest"
  ok "Image gepusht"

  echo ""
  echo "🖥️  [3/3] Production deploy..."
  ssh "$SERVER" "
    cd $COMPOSE_PATH &&
    IMAGE_TAG=latest docker compose -f $COMPOSE_FILE pull $WEB_SERVICE &&
    IMAGE_TAG=latest docker compose -f $COMPOSE_FILE up -d --force-recreate $WEB_SERVICE
  "
  ok "Production Container neugestartet"

  sleep 6
  ssh "$SERVER" "
    docker compose -f $COMPOSE_PATH/$COMPOSE_FILE exec -T $WEB_SERVICE $MIGRATE_CMD 2>&1 | tail -5
  " && ok "Migrationen ausgeführt" || warn "Migration check: bitte logs prüfen"

  echo ""
  echo "🏥 Health Check..."
  MAX_RETRIES=12; RETRY=0
  while [ $RETRY -lt $MAX_RETRIES ]; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "000")
    [ "$STATUS" = "200" ] && { ok "$HEALTH_URL → 200 OK"; break; }
    RETRY=$((RETRY + 1))
    [ $RETRY -eq $MAX_RETRIES ] && fail "Health check fehlgeschlagen ($STATUS)"
    sleep 5
  done

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo -e "✅ ${GREEN}Promote erfolgreich — $(date '+%H:%M:%S')${NC}"
  echo ""
  exit 0
fi

# =============================================================================
# STAGING + PRODUCTION: shared steps 1–3
# =============================================================================
if [ "$MODE" = "staging" ]; then
  TAG="staging"
else
  TAG="latest"
fi
FULL_IMAGE="$IMAGE_BASE:$TAG"

# =============================================================================
# 1. Git
# =============================================================================
echo ""
echo "📦 [1/4] Git commit + push..."
cd "$REPO_DIR"
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "$COMMIT_MSG"
  ok "Committed: $COMMIT_MSG"
else
  ok "Nichts zu committen — working tree clean"
fi
git push origin main
ok "GitHub: up to date"

# =============================================================================
# 2. Docker build
# =============================================================================
echo ""
echo "🔨 [2/4] Docker build → $FULL_IMAGE ..."
export GIT_TOKEN="${GIT_TOKEN:-${PROJECT_PAT:-${GITHUB_TOKEN:-}}}"
if [ -n "$GIT_TOKEN" ]; then
  DOCKER_BUILDKIT=1 docker build \
    --secret id=GIT_TOKEN,env=GIT_TOKEN \
    -f "$REPO_DIR/$DOCKERFILE" -t "$FULL_IMAGE" "$REPO_DIR"
else
  docker build -f "$REPO_DIR/$DOCKERFILE" -t "$FULL_IMAGE" "$REPO_DIR"
fi
ok "Image gebaut: $FULL_IMAGE"

# =============================================================================
# 3. Docker push
# =============================================================================
echo ""
echo "📤 [3/4] Docker push → GHCR..."
docker push "$FULL_IMAGE"
ok "Image gepusht: $FULL_IMAGE"

# =============================================================================
# 4. Server deploy
# =============================================================================
echo ""
if [ "$MODE" = "staging" ]; then
  echo "🖥️  [4/4] Staging deploy..."
  ssh "$SERVER" "
    cd $COMPOSE_PATH &&
    export IMAGE_TAG=staging &&
    docker compose -f $COMPOSE_FILE pull $WEB_SERVICE &&
    docker compose -f $COMPOSE_FILE up -d --force-recreate $WEB_SERVICE
  "
  ok "Container auf :staging Image aktualisiert"

  sleep 6
  ssh "$SERVER" "
    cd $COMPOSE_PATH && export IMAGE_TAG=staging &&
    docker compose -f $COMPOSE_FILE exec -T $WEB_SERVICE $MIGRATE_CMD 2>&1 | tail -5
  " && ok "Migrationen ausgeführt" || warn "Migration check: bitte logs prüfen"

  echo ""
  echo "🏥 Health Check..."
  MAX_RETRIES=12; RETRY=0
  while [ $RETRY -lt $MAX_RETRIES ]; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "000")
    [ "$STATUS" = "200" ] && { ok "$HEALTH_URL → 200 OK"; break; }
    RETRY=$((RETRY + 1))
    [ $RETRY -eq $MAX_RETRIES ] && fail "Health check fehlgeschlagen ($STATUS)"
    sleep 5
  done

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo -e "✅ ${GREEN}Staging Ship erfolgreich — $(date '+%H:%M:%S')${NC}"
  echo -e "   Promote mit: ${YELLOW}./scripts/ship.sh promote${NC}"
  echo ""
else
  echo "🖥️  [4/4] Production deploy..."
  ssh "$SERVER" "
    cd $COMPOSE_PATH &&
    docker compose -f $COMPOSE_FILE pull $WEB_SERVICE &&
    docker compose -f $COMPOSE_FILE up -d --force-recreate $WEB_SERVICE
  "
  ok "Container neugestartet"

  sleep 6
  ssh "$SERVER" "
    docker compose -f $COMPOSE_PATH/$COMPOSE_FILE exec -T $WEB_SERVICE $MIGRATE_CMD 2>&1 | tail -5
  " && ok "Migrationen ausgeführt" || warn "Migration check: bitte logs prüfen"

  echo ""
  echo "🏥 Health Check..."
  MAX_RETRIES=12; RETRY=0
  while [ $RETRY -lt $MAX_RETRIES ]; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "000")
    [ "$STATUS" = "200" ] && { ok "$HEALTH_URL → 200 OK"; break; }
    RETRY=$((RETRY + 1))
    [ $RETRY -eq $MAX_RETRIES ] && fail "Health check fehlgeschlagen ($STATUS)"
    sleep 5
  done

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo -e "✅ ${GREEN}Ship erfolgreich — $(date '+%H:%M:%S')${NC}"
  echo ""
fi
