#!/bin/bash
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  UNIVERSAL DEPLOYMENT SCRIPT                                               ║
# ║  Platform: BF Agent Platform                                               ║
# ║  Version: 1.0.0                                                            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
#
# Usage:
#   ./deploy.sh [OPTIONS]
#
# Required Environment Variables:
#   IMAGE_TAG         - Docker image tag to deploy
#   APP_NAME          - Application name (e.g., travel-beat)
#   COMPOSE_FILE      - Docker Compose file (default: docker-compose.prod.yml)
#   ENV_FILE          - Environment file (default: .env.prod)
#
# Optional Environment Variables:
#   REGISTRY          - Container registry (default: ghcr.io)
#   ROLLING_UPDATE    - Enable rolling update (default: true)
#   HEALTH_RETRIES    - Health check retries (default: 10)
#   HEALTH_INTERVAL   - Seconds between checks (default: 10)
#   ROLLBACK_ON_FAIL  - Auto-rollback on failure (default: true)

set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Required
IMAGE_TAG="${IMAGE_TAG:?ERROR: IMAGE_TAG is required}"
APP_NAME="${APP_NAME:?ERROR: APP_NAME is required}"

# Optional with defaults
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"
REGISTRY="${REGISTRY:-ghcr.io}"
ROLLING_UPDATE="${ROLLING_UPDATE:-true}"
HEALTH_RETRIES="${HEALTH_RETRIES:-10}"
HEALTH_INTERVAL="${HEALTH_INTERVAL:-10}"
ROLLBACK_ON_FAIL="${ROLLBACK_ON_FAIL:-true}"

# Derived
DEPLOY_DIR="$(pwd)"
DEPLOYMENTS_DIR="${DEPLOY_DIR}/deployments"
IMAGE_TAG_VAR="${APP_NAME^^}_IMAGE_TAG"
IMAGE_TAG_VAR="${IMAGE_TAG_VAR//-/_}"
WEB_SERVICE="${APP_NAME}-web"
WORKER_SERVICE="${APP_NAME}-celery"
BEAT_SERVICE="${APP_NAME}-celery-beat"

# State
DEPLOYMENT_ID=""
PREVIOUS_TAG=""
DEPLOY_SUCCESS=false

# ═══════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════

log() {
    echo "[$(date -Iseconds)] $*"
}

log_header() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  $*"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
}

log_success() {
    echo "[$(date -Iseconds)] ✅ $*"
}

log_error() {
    echo "[$(date -Iseconds)] ❌ $*" >&2
}

log_warning() {
    echo "[$(date -Iseconds)] ⚠️  $*"
}

# ═══════════════════════════════════════════════════════════════════════════
# DEPLOYMENT TRACKING
# ═══════════════════════════════════════════════════════════════════════════

init_deployment() {
    log_header "DEPLOYMENT - ${APP_NAME}"
    
    # Create deployments directory
    mkdir -p "${DEPLOYMENTS_DIR}"
    
    # Generate deployment ID
    DEPLOYMENT_ID=$(date +%Y%m%d%H%M%S)
    
    # Get previous tag
    if [[ -f "${ENV_FILE}" ]]; then
        PREVIOUS_TAG=$(grep "^${IMAGE_TAG_VAR}=" "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "")
    fi
    
    log "Deployment ID: ${DEPLOYMENT_ID}"
    log "Previous tag:  ${PREVIOUS_TAG:-none}"
    log "New tag:       ${IMAGE_TAG}"
    
    # Create deployment record
    cat > "${DEPLOYMENTS_DIR}/${DEPLOYMENT_ID}.json" << EOF
{
    "id": "${DEPLOYMENT_ID}",
    "app": "${APP_NAME}",
    "image_tag": "${IMAGE_TAG}",
    "previous_tag": "${PREVIOUS_TAG}",
    "started_at": "$(date -Iseconds)",
    "status": "in_progress",
    "compose_file": "${COMPOSE_FILE}",
    "env_file": "${ENV_FILE}"
}
EOF
}

update_deployment_status() {
    local status="$1"
    local deployment_file="${DEPLOYMENTS_DIR}/${DEPLOYMENT_ID}.json"
    
    if [[ -f "${deployment_file}" ]]; then
        # Update status using jq if available, otherwise sed
        if command -v jq &> /dev/null; then
            local temp_file=$(mktemp)
            jq ".status = \"${status}\" | .completed_at = \"$(date -Iseconds)\"" \
                "${deployment_file}" > "${temp_file}"
            mv "${temp_file}" "${deployment_file}"
        else
            sed -i "s/\"status\": \"in_progress\"/\"status\": \"${status}\"/" "${deployment_file}"
        fi
    fi
}

cleanup_old_deployments() {
    # Keep only last 100 deployment records
    local count=$(ls -1 "${DEPLOYMENTS_DIR}"/*.json 2>/dev/null | wc -l)
    if [[ $count -gt 100 ]]; then
        ls -1t "${DEPLOYMENTS_DIR}"/*.json | tail -n +101 | xargs rm -f
        log "Cleaned up old deployment records"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# DOCKER OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

update_env_file() {
    log "Updating ${ENV_FILE} with new image tag..."
    
    if [[ -f "${ENV_FILE}" ]]; then
        if grep -q "^${IMAGE_TAG_VAR}=" "${ENV_FILE}"; then
            sed -i "s|^${IMAGE_TAG_VAR}=.*|${IMAGE_TAG_VAR}=${IMAGE_TAG}|" "${ENV_FILE}"
        else
            echo "${IMAGE_TAG_VAR}=${IMAGE_TAG}" >> "${ENV_FILE}"
        fi
    else
        echo "${IMAGE_TAG_VAR}=${IMAGE_TAG}" > "${ENV_FILE}"
    fi
    
    log_success "Environment file updated"
}

pull_images() {
    log "Pulling Docker images..."
    
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" pull
    
    log_success "Images pulled"
}

rolling_update() {
    log_header "ROLLING UPDATE"
    
    # Check if web service exists
    if ! docker compose -f "${COMPOSE_FILE}" config --services | grep -q "^${WEB_SERVICE}$"; then
        log_warning "Web service ${WEB_SERVICE} not found, using standard update"
        standard_update
        return
    fi
    
    log "Scaling up new container..."
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d --no-deps --scale "${WEB_SERVICE}=2" "${WEB_SERVICE}" || true
    
    log "Waiting for new container to be healthy..."
    sleep 15
    
    log "Scaling down old container..."
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d --no-deps --scale "${WEB_SERVICE}=1" "${WEB_SERVICE}"
    
    # Update workers if they exist
    if docker compose -f "${COMPOSE_FILE}" config --services | grep -q "^${WORKER_SERVICE}$"; then
        log "Updating worker containers..."
        docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
            up -d --no-deps "${WORKER_SERVICE}" "${BEAT_SERVICE}" 2>/dev/null || true
    fi
    
    log_success "Rolling update completed"
}

standard_update() {
    log "Running standard update (no rolling)..."
    
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d
    
    log_success "Standard update completed"
}

collect_static() {
    log "Collecting static files..."
    
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        exec -T "${WEB_SERVICE}" python manage.py collectstatic --noinput 2>/dev/null || true
    
    log_success "Static files collected"
}

cleanup_docker() {
    log "Cleaning up old Docker resources..."
    
    docker system prune -f --filter "until=24h" 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# ═══════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════

health_check() {
    local health_url="${1:-}"
    
    if [[ -z "${health_url}" ]]; then
        log_warning "No health URL provided, skipping health check"
        return 0
    fi
    
    log_header "HEALTH CHECK"
    log "URL: ${health_url}"
    log "Retries: ${HEALTH_RETRIES}, Interval: ${HEALTH_INTERVAL}s"
    
    for i in $(seq 1 "${HEALTH_RETRIES}"); do
        log "Attempt ${i}/${HEALTH_RETRIES}..."
        
        local response
        local status
        
        response=$(curl -sf -w "\n%{http_code}" "${health_url}" 2>&1 || echo -e "\n000")
        status=$(echo "${response}" | tail -n 1)
        
        if [[ "${status}" == "200" ]]; then
            log_success "Health check passed!"
            return 0
        fi
        
        log_warning "Status: ${status}, waiting ${HEALTH_INTERVAL}s..."
        sleep "${HEALTH_INTERVAL}"
    done
    
    log_error "Health check failed after ${HEALTH_RETRIES} attempts"
    return 1
}

# ═══════════════════════════════════════════════════════════════════════════
# ROLLBACK
# ═══════════════════════════════════════════════════════════════════════════

rollback() {
    log_header "🚨 ROLLBACK"
    
    if [[ -z "${PREVIOUS_TAG}" ]]; then
        log_error "No previous tag available for rollback"
        return 1
    fi
    
    log "Rolling back to: ${PREVIOUS_TAG}"
    
    # Update env file with previous tag
    sed -i "s|^${IMAGE_TAG_VAR}=.*|${IMAGE_TAG_VAR}=${PREVIOUS_TAG}|" "${ENV_FILE}"
    
    # Rollback
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --force-recreate
    
    # Record rollback
    cat > "${DEPLOYMENTS_DIR}/rollback_$(date +%Y%m%d%H%M%S).json" << EOF
{
    "id": "rollback_$(date +%Y%m%d%H%M%S)",
    "app": "${APP_NAME}",
    "rolled_back_to": "${PREVIOUS_TAG}",
    "rolled_back_from": "${IMAGE_TAG}",
    "rolled_back_at": "$(date -Iseconds)",
    "status": "rolled_back"
}
EOF
    
    log_success "Rollback completed"
}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

main() {
    local health_url="${HEALTH_URL:-}"
    
    # Trap errors for rollback
    trap 'on_error' ERR
    
    init_deployment
    
    update_env_file
    pull_images
    
    if [[ "${ROLLING_UPDATE}" == "true" ]]; then
        rolling_update
    else
        standard_update
    fi
    
    collect_static
    
    # Health check
    if [[ -n "${health_url}" ]]; then
        if ! health_check "${health_url}"; then
            log_error "Deployment failed health check"
            
            if [[ "${ROLLBACK_ON_FAIL}" == "true" ]]; then
                rollback
                update_deployment_status "rolled_back"
                exit 1
            fi
            
            update_deployment_status "failed"
            exit 1
        fi
    fi
    
    cleanup_docker
    cleanup_old_deployments
    
    DEPLOY_SUCCESS=true
    update_deployment_status "success"
    
    log_header "DEPLOYMENT SUCCESSFUL"
    log "App:     ${APP_NAME}"
    log "Tag:     ${IMAGE_TAG}"
    log "ID:      ${DEPLOYMENT_ID}"
}

on_error() {
    local exit_code=$?
    log_error "Deployment failed with exit code: ${exit_code}"
    
    if [[ "${DEPLOY_SUCCESS}" != "true" && "${ROLLBACK_ON_FAIL}" == "true" && -n "${PREVIOUS_TAG}" ]]; then
        rollback
        update_deployment_status "rolled_back"
    else
        update_deployment_status "failed"
    fi
    
    exit "${exit_code}"
}

# Run main
main "$@"
