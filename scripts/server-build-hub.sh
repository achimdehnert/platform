#!/usr/bin/env bash
# =============================================================================
# server-build-hub.sh — Build + Deploy a single hub on the server (ADR-142)
#
# Usage:
#   ./server-build-hub.sh <hub-name>         # Build + deploy one hub
#   ./server-build-hub.sh --all              # Build + deploy all hubs
#   ./server-build-hub.sh --list             # Show all known hubs
#
# This script:
#   1. Clones or pulls the repo from GitHub
#   2. Builds the Docker image locally on the server
#   3. Tags it as the expected GHCR image name
#   4. Restarts the compose service
#
# Requirements: git, docker, docker compose, GITHUB_TOKEN env var
# =============================================================================
set -euo pipefail

GITHUB_ORG="achimdehnert"
BUILD_DIR="/opt/hub-builds"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Hub registry: hub-name|server-dir|image-name|dockerfile-path|compose-web-service
declare -A HUBS
HUBS[travel-beat]="/opt/travel-beat|ghcr.io/achimdehnert/travel-beat:latest|docker/Dockerfile|travel-beat-web"
HUBS[cad-hub]="/opt/cad-hub|ghcr.io/achimdehnert/cad-hub:latest|docker/app/Dockerfile|cad-hub-web"
HUBS[coach-hub]="/opt/coach-hub|ghcr.io/achimdehnert/coach-hub:latest|docker/app/Dockerfile|coach-hub-web"
HUBS[bfagent]="/opt/bfagent-app|ghcr.io/achimdehnert/bfagent-web:latest|Dockerfile|bfagent-web"
HUBS[wedding-hub]="/opt/wedding-hub|ghcr.io/achimdehnert/wedding-hub:latest|docker/app/Dockerfile|wedding-hub-web"
HUBS[weltenhub]="/opt/weltenhub|ghcr.io/achimdehnert/weltenhub:latest|Dockerfile|weltenhub-web"
HUBS[writing-hub]="/opt/writing-hub|ghcr.io/achimdehnert/writing-hub:latest|Dockerfile|writing-hub-web"
HUBS[illustration-hub]="/opt/illustration-hub|ghcr.io/achimdehnert/illustration-hub:latest|Dockerfile|illustration-hub-web"
HUBS[137-hub]="/opt/137-hub|ghcr.io/achimdehnert/137-hub:latest|docker/app/Dockerfile|137-hub-web"
HUBS[ausschreibungs-hub]="/opt/ausschreibungs-hub|ghcr.io/achimdehnert/ausschreibungs-hub:latest|docker/app/Dockerfile|ausschreibungs-hub-web"
HUBS[billing-hub]="/opt/billing-hub|ghcr.io/achimdehnert/billing-hub:latest|docker/app/Dockerfile|billing-hub-web"
HUBS[risk-hub]="/opt/risk-hub|ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest|docker/app/Dockerfile|risk-hub-web"
HUBS[trading-hub]="/opt/trading-hub|ghcr.io/achimdehnert/trading-hub/trading-hub-web:latest|docker/app/Dockerfile|trading-hub-web"
HUBS[pptx-hub]="/opt/pptx-hub|ghcr.io/achimdehnert/pptx-hub/pptx-hub-web:latest|docker/app/Dockerfile|pptx-hub-web"

log() { echo "[$(date +%H:%M:%S)] $*"; }
err() { echo "[$(date +%H:%M:%S)] ERROR: $*" >&2; }

list_hubs() {
    echo "Known hubs:"
    for hub in $(echo "${!HUBS[@]}" | tr ' ' '\n' | sort); do
        IFS='|' read -r server_dir image dockerfile svc <<< "${HUBS[$hub]}"
        echo "  $hub → $server_dir ($image)"
    done
}

build_hub() {
    local hub="$1"
    if [[ -z "${HUBS[$hub]+x}" ]]; then
        err "Unknown hub: $hub"
        list_hubs
        return 1
    fi

    IFS='|' read -r server_dir image dockerfile svc <<< "${HUBS[$hub]}"

    log "========== Building $hub =========="

    # Step 1: Clone or pull
    local src_dir="$BUILD_DIR/$hub"
    mkdir -p "$BUILD_DIR"

    if [[ -d "$src_dir/.git" ]]; then
        log "Pulling latest from GitHub..."
        cd "$src_dir"
        git fetch origin main --depth=1 2>/dev/null || git fetch origin main
        git reset --hard origin/main
    else
        log "Cloning $hub from GitHub..."
        local clone_url="https://${GITHUB_TOKEN:+${GITHUB_TOKEN}@}github.com/$GITHUB_ORG/$hub.git"
        git clone --depth=1 --branch main "$clone_url" "$src_dir"
        cd "$src_dir"
    fi

    # Step 2: Build Docker image
    log "Building Docker image: $image"
    local build_args=""
    # Add GIT_TOKEN if Dockerfile needs it for private deps
    if grep -q "GIT_TOKEN\|GITHUB_TOKEN" "$dockerfile" 2>/dev/null; then
        build_args="--build-arg GIT_TOKEN=$GITHUB_TOKEN"
    fi

    docker build \
        $build_args \
        -f "$dockerfile" \
        -t "$image" \
        . 2>&1 | tail -5

    if [[ $? -ne 0 ]]; then
        err "Docker build FAILED for $hub"
        return 1
    fi
    log "Image built: $image"

    # Step 3: Restart compose service
    local compose_file="$server_dir/docker-compose.prod.yml"
    if [[ ! -f "$compose_file" ]]; then
        compose_file="$server_dir/docker-compose.yml"
    fi

    if [[ -f "$compose_file" ]]; then
        log "Restarting compose service in $server_dir..."
        cd "$server_dir"
        # Find the actual web service name from compose
        local actual_svc
        actual_svc=$(docker compose -f "$compose_file" ps --format '{{.Service}}' 2>/dev/null | grep -E "web|app|$hub" | head -1)
        if [[ -n "$actual_svc" ]]; then
            docker compose -f "$compose_file" up -d --no-deps --force-recreate "$actual_svc"
        else
            docker compose -f "$compose_file" up -d
        fi
        log "Service restarted"

        # Step 4: Health check (wait up to 30s)
        log "Waiting for health check..."
        sleep 5
        local container
        container=$(docker compose -f "$compose_file" ps --format '{{.Names}}' 2>/dev/null | grep -E "web|app" | head -1)
        if [[ -n "$container" ]]; then
            local status
            status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-healthcheck")
            log "Container $container: $status"
        fi
    else
        err "No compose file found in $server_dir"
        return 1
    fi

    log "========== $hub: DONE =========="
}

# --- Main ---
case "${1:-}" in
    --list)
        list_hubs
        ;;
    --all)
        failures=0
        for hub in $(echo "${!HUBS[@]}" | tr ' ' '\n' | sort); do
            build_hub "$hub" || ((failures++))
        done
        log "Completed. Failures: $failures / ${#HUBS[@]}"
        ;;
    "")
        echo "Usage: $0 <hub-name> | --all | --list"
        list_hubs
        ;;
    *)
        build_hub "$1"
        ;;
esac
