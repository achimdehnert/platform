#!/bin/bash
# =============================================================================
# Universal Background Build & Deploy Script
# Löst MCP ssh_manage Timeout-Problem bei langen Docker Builds
#
# Usage:  nohup bash /opt/build-deploy.sh <app-name> > /dev/null 2>&1 &
# Status: cat /opt/<app>/build-deploy.status
# Log:    tail -f /opt/<app>/build-deploy.log
#
# Requires: GHCR auth in /root/.docker/config.json
# Location on server: /opt/build-deploy.sh (shared by all apps)
# =============================================================================
set -euo pipefail

APP="${1:-trading-hub}"
# bfagent uses /opt/bfagent-app but GitHub repo is 'bfagent'
REPO_NAME="${APP}"
[ "$APP" = "bfagent-app" ] && REPO_NAME="bfagent"

DEPLOY_DIR="/opt/${APP}"
LOG="${DEPLOY_DIR}/build-deploy.log"
STATUS="${DEPLOY_DIR}/build-deploy.status"
CLONE_DIR="/tmp/${REPO_NAME}-build"

# Find compose file (apps use different paths)
COMPOSE=""
for f in "${DEPLOY_DIR}/docker-compose.prod.yml" \
         "${DEPLOY_DIR}/deploy/docker-compose.prod.yml"; do
    [ -f "$f" ] && COMPOSE="$f" && break
done
[ -z "$COMPOSE" ] && { echo "ERROR: No compose file found in ${DEPLOY_DIR}"; exit 1; }

# Detect GHCR image name (3 strategies)
# NOTE: All commands must tolerate failure due to set -eo pipefail
# 1. From compose file literal (e.g. risk-hub)
IMAGE=$(grep -oP 'ghcr\.io/achimdehnert/[^:"]+:latest' "$COMPOSE" 2>/dev/null | head -1 || true)
# 2. From running container (handles ${VAR} interpolation in compose, e.g. trading-hub)
if [ -z "$IMAGE" ]; then
    CONTAINER="${APP//-/_}_web"
    IMAGE=$(docker inspect --format='{{.Config.Image}}' "$CONTAINER" 2>/dev/null || true)
fi
# 3. Fallback: simple naming convention
[ -z "$IMAGE" ] && IMAGE="ghcr.io/achimdehnert/${REPO_NAME}:latest"

update_status() {
    echo "$1" > "$STATUS"
    echo "[$(date '+%H:%M:%S')] $1" >> "$LOG"
}

cleanup() {
    [ $? -ne 0 ] && update_status "FAILED"
    rm -rf "$CLONE_DIR" /tmp/platform-tmp 2>/dev/null || true
}
trap cleanup EXIT

echo "" > "$LOG"
update_status "STARTED"

# Kill stuck builds
pkill -f "docker build.*${APP}" 2>/dev/null || true
sleep 2

# Extract GitHub token
update_status "TOKEN"
TOKEN=$(python3 -c "
import json, base64
d = json.load(open('/root/.docker/config.json'))
auth = d['auths']['ghcr.io']['auth']
print(base64.b64decode(auth).decode().split(':')[1])
")
[ -z "$TOKEN" ] && { update_status "FAILED:NO_TOKEN"; exit 1; }

# Clone repo
update_status "CLONE"
rm -rf "$CLONE_DIR" /tmp/platform-tmp
git clone --depth 1 "https://achimdehnert:${TOKEN}@github.com/achimdehnert/${REPO_NAME}.git" "$CLONE_DIR" 2>>"$LOG"

# Clone bfagent-core if needed by any Dockerfile
update_status "DEPS"
if grep -rq "bfagent-core" "$CLONE_DIR/docker/" 2>/dev/null || \
   grep -q "bfagent-core" "$CLONE_DIR/Dockerfile" 2>/dev/null; then
    mkdir -p "$CLONE_DIR/packages"
    git clone --depth 1 "https://achimdehnert:${TOKEN}@github.com/achimdehnert/platform.git" /tmp/platform-tmp 2>>"$LOG"
    cp -r /tmp/platform-tmp/packages/bfagent-core "$CLONE_DIR/packages/bfagent-core"
    rm -rf /tmp/platform-tmp
fi

# Docker Build — detect Dockerfile (repos use different locations)
update_status "BUILD"
cd "$CLONE_DIR"
DOCKERFILE=""
for df in docker/app/Dockerfile docker/Dockerfile Dockerfile; do
    [ -f "$df" ] && DOCKERFILE="$df" && break
done
[ -z "$DOCKERFILE" ] && { update_status "FAILED:NO_DOCKERFILE"; exit 1; }
update_status "BUILD ($DOCKERFILE -> $IMAGE)"
docker build -f "$DOCKERFILE" -t "$IMAGE" . >> "$LOG" 2>&1
update_status "BUILD_OK"

# Push to GHCR
update_status "PUSH"
docker push "$IMAGE" >> "$LOG" 2>&1
update_status "PUSH_OK"

# Deploy
update_status "DEPLOY"
cd "$DEPLOY_DIR"
docker compose -f "$COMPOSE" pull >> "$LOG" 2>&1
docker compose -f "$COMPOSE" up -d --force-recreate >> "$LOG" 2>&1
update_status "DEPLOY_OK"

# Health check — detect host port from compose ports mapping
sleep 10
update_status "HEALTH"

# Extract host port from ports: section (formats: "8088:8000", "127.0.0.1:8088:8000")
# Specifically look for web service ports, skip db/redis/rabbitmq
HEALTH_PORT=$(grep -A2 'ports:' "$COMPOSE" 2>/dev/null | grep -oP '\b(8[0-9]{3}):\d+' | head -1 | cut -d: -f1 || true)
# Fallback: try to get from running web container
if [ -z "$HEALTH_PORT" ]; then
    CONTAINER="${APP//-/_}_web"
    HEALTH_PORT=$(docker port "$CONTAINER" 2>/dev/null | grep -oP '\d+$' | head -1 || true)
fi
[ -z "$HEALTH_PORT" ] && HEALTH_PORT="8088"

# Try common health endpoints
for i in $(seq 1 6); do
    for path in /livez/ /health/ /healthz/; do
        HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://localhost:${HEALTH_PORT}${path}" 2>/dev/null || echo "000")
        if [ "$HTTP" = "200" ]; then
            update_status "DONE:OK (port=${HEALTH_PORT} path=${path})"
            exit 0
        fi
    done
    update_status "HEALTH: attempt $i/6 (port=${HEALTH_PORT}, last_http=${HTTP})"
    sleep 10
done

update_status "DONE:HEALTH_FAIL (port=${HEALTH_PORT})"
exit 1
