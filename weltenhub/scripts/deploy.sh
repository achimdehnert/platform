#!/usr/bin/env bash
# =============================================================================
# Weltenhub Deployment Script
# =============================================================================
# Deploys Weltenhub to Hetzner VM via Docker Compose
#
# Usage:
#   ./scripts/deploy.sh [IMAGE_TAG]
#
# Prerequisites:
#   - SSH access to Hetzner VM (88.198.191.108)
#   - Docker and Docker Compose installed on target
#   - .env.prod file configured
#
# Exit Codes:
#   0 - Success
#   1 - General error
#   2 - SSH connection failed
#   3 - Docker operation failed
#   4 - Health check failed
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
readonly PROJECT_NAME="weltenhub"

# Target server configuration
readonly SSH_HOST="${DEPLOY_HOST:-88.198.191.108}"
readonly SSH_USER="${DEPLOY_USER:-root}"
readonly REMOTE_PATH="${DEPLOY_PATH:-/opt/weltenhub}"

# Image configuration
readonly IMAGE_REPO="${IMAGE_REPO:-ghcr.io/achimdehnert/weltenhub}"
readonly IMAGE_TAG="${1:-latest}"

# Compose files
readonly COMPOSE_FILE="docker-compose.prod.yml"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

log_success() {
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# Execute command on remote server
remote_exec() {
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
        "${SSH_USER}@${SSH_HOST}" "$@"
}

# Check if remote server is reachable
check_ssh_connection() {
    log_info "Checking SSH connection to ${SSH_HOST}..."
    if ! remote_exec "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_error "Cannot connect to ${SSH_HOST}"
        exit 2
    fi
    log_success "SSH connection established"
}

# Ensure remote directory exists
ensure_remote_directory() {
    log_info "Ensuring remote directory ${REMOTE_PATH} exists..."
    remote_exec "mkdir -p ${REMOTE_PATH}"
}

# Copy deployment files to remote
copy_deployment_files() {
    log_info "Copying deployment files to remote..."
    
    # Copy docker-compose and env files
    scp -o StrictHostKeyChecking=accept-new \
        "${PROJECT_DIR}/${COMPOSE_FILE}" \
        "${SSH_USER}@${SSH_HOST}:${REMOTE_PATH}/"
    
    # Copy .env.prod if it exists locally
    if [[ -f "${PROJECT_DIR}/.env.prod" ]]; then
        scp -o StrictHostKeyChecking=accept-new \
            "${PROJECT_DIR}/.env.prod" \
            "${SSH_USER}@${SSH_HOST}:${REMOTE_PATH}/"
    fi
    
    log_success "Deployment files copied"
}

# Update IMAGE_TAG in remote .env.prod
update_image_tag() {
    log_info "Setting IMAGE_TAG=${IMAGE_TAG} in remote .env.prod..."
    
    remote_exec "cd ${REMOTE_PATH} && \
        if grep -q '^IMAGE_TAG=' .env.prod 2>/dev/null; then \
            sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=${IMAGE_TAG}/' .env.prod; \
        else \
            echo 'IMAGE_TAG=${IMAGE_TAG}' >> .env.prod; \
        fi"
    
    log_success "IMAGE_TAG updated"
}

# Pull new Docker images
docker_pull() {
    log_info "Pulling Docker images..."
    
    if ! remote_exec "cd ${REMOTE_PATH} && \
        docker compose -f ${COMPOSE_FILE} pull"; then
        log_error "Failed to pull Docker images"
        exit 3
    fi
    
    log_success "Docker images pulled"
}

# Start/restart services
docker_up() {
    log_info "Starting services..."
    
    if ! remote_exec "cd ${REMOTE_PATH} && \
        docker compose -f ${COMPOSE_FILE} up -d --remove-orphans"; then
        log_error "Failed to start services"
        exit 3
    fi
    
    log_success "Services started"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    if ! remote_exec "cd ${REMOTE_PATH} && \
        docker compose -f ${COMPOSE_FILE} exec -T weltenhub \
        python manage.py migrate --noinput"; then
        log_error "Migration failed"
        exit 3
    fi
    
    log_success "Migrations completed"
}

# Collect static files
collect_static() {
    log_info "Collecting static files..."
    
    remote_exec "cd ${REMOTE_PATH} && \
        docker compose -f ${COMPOSE_FILE} exec -T weltenhub \
        python manage.py collectstatic --noinput" || true
    
    log_success "Static files collected"
}

# Health check
health_check() {
    log_info "Running health check..."
    
    local max_attempts=30
    local attempt=1
    local health_url="http://localhost:8000/health/"
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Health check attempt ${attempt}/${max_attempts}..."
        
        if remote_exec "curl -sf ${health_url}" >/dev/null 2>&1; then
            log_success "Health check passed"
            return 0
        fi
        
        sleep 2
        ((attempt++))
    done
    
    log_error "Health check failed after ${max_attempts} attempts"
    exit 4
}

# Show service status
show_status() {
    log_info "Service status:"
    remote_exec "cd ${REMOTE_PATH} && \
        docker compose -f ${COMPOSE_FILE} ps"
}

# Cleanup old images
cleanup_old_images() {
    log_info "Cleaning up old Docker images..."
    remote_exec "docker image prune -f" || true
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    log_info "=========================================="
    log_info "Deploying ${PROJECT_NAME}"
    log_info "Image: ${IMAGE_REPO}:${IMAGE_TAG}"
    log_info "Target: ${SSH_USER}@${SSH_HOST}:${REMOTE_PATH}"
    log_info "=========================================="
    
    check_ssh_connection
    ensure_remote_directory
    copy_deployment_files
    update_image_tag
    docker_pull
    docker_up
    run_migrations
    collect_static
    health_check
    show_status
    cleanup_old_images
    
    log_info "=========================================="
    log_success "Deployment completed successfully!"
    log_info "URL: https://weltenhub.iil.pet/"
    log_info "=========================================="
}

main "$@"
