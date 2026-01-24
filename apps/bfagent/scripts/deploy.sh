#!/bin/bash
#
# BF Agent Deployment Script
# ===========================
# Zero-downtime deployment to production
#
# Usage:
#   ./scripts/deploy.sh [branch]
#
# Default branch: main

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# =============================================================================
# Configuration
# =============================================================================

PROJECT_DIR="/opt/bfagent"
BRANCH="${1:-main}"
BACKUP_DIR="/var/backups/bfagent"

# =============================================================================
# Pre-Deployment Checks
# =============================================================================

log "🚀 Starting deployment of BF Agent..."
info "Branch: $BRANCH"
info "Directory: $PROJECT_DIR"

# Check if we're in the right directory
cd "$PROJECT_DIR" || exit 1

# Check if git is clean
if [ -n "$(git status --porcelain)" ]; then
    warn "Working directory has uncommitted changes!"
    read -p "Continue anyway? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Deployment cancelled"
        exit 0
    fi
fi

# Check if Docker is running
if ! docker ps &> /dev/null; then
    error "Docker is not running!"
    exit 1
fi

# =============================================================================
# Create Pre-Deployment Backup
# =============================================================================

log "📦 Creating pre-deployment backup..."

DEPLOY_BACKUP="$BACKUP_DIR/before_deploy_$(date +%Y%m%d_%H%M%S).sql.gz"
mkdir -p "$BACKUP_DIR"

docker exec bfagent_db pg_dump -U bfagent bfagent_prod | gzip > "$DEPLOY_BACKUP"
log "✅ Backup created: $DEPLOY_BACKUP"

# Save current commit for rollback
PREVIOUS_COMMIT=$(git rev-parse HEAD)
info "Current commit: ${PREVIOUS_COMMIT:0:8}"

# =============================================================================
# Pull Latest Code
# =============================================================================

log "📥 Pulling latest code..."

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull origin "$BRANCH"

NEW_COMMIT=$(git rev-parse HEAD)
info "New commit: ${NEW_COMMIT:0:8}"

if [ "$PREVIOUS_COMMIT" == "$NEW_COMMIT" ]; then
    warn "No new changes to deploy"
    read -p "Continue anyway? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Deployment cancelled"
        exit 0
    fi
fi

# Show changes
log "Changes being deployed:"
git log --oneline "$PREVIOUS_COMMIT".."$NEW_COMMIT" | head -10

# =============================================================================
# Install Dependencies
# =============================================================================

log "📚 Installing dependencies..."

source .venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install -r requirements-postgres.txt -q

log "✅ Dependencies installed"

# =============================================================================
# Run Migrations
# =============================================================================

log "🗄️  Running database migrations..."

# Check for pending migrations
PENDING=$(python manage.py showmigrations --plan | grep '\[ \]' | wc -l)

if [ "$PENDING" -gt 0 ]; then
    info "Found $PENDING pending migrations"
    python manage.py migrate --noinput
    log "✅ Migrations applied"
else
    info "No pending migrations"
fi

# =============================================================================
# Collect Static Files
# =============================================================================

log "📦 Collecting static files..."

python manage.py collectstatic --noinput --clear

log "✅ Static files collected"

# =============================================================================
# Run Tests (Optional)
# =============================================================================

# Uncomment if you want to run tests before deployment
# log "🧪 Running tests..."
# python manage.py test --parallel --keepdb
# log "✅ Tests passed"

# =============================================================================
# Deploy Application
# =============================================================================

log "🔄 Restarting application..."

# Graceful restart
sudo systemctl reload bfagent 2>/dev/null || sudo systemctl restart bfagent

# Wait for service to start
sleep 3

# =============================================================================
# Health Check
# =============================================================================

log "🏥 Running health checks..."

MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost:8000/health/ > /dev/null; then
        log "✅ Health check passed"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            error "Health check failed after $MAX_RETRIES attempts!"

            warn "Rolling back deployment..."
            git checkout "$PREVIOUS_COMMIT"
            sudo systemctl restart bfagent

            error "Deployment failed - rolled back to previous version"
            exit 1
        fi
        warn "Health check failed (attempt $RETRY_COUNT/$MAX_RETRIES), retrying..."
        sleep 2
    fi
done

# =============================================================================
# Verify Deployment
# =============================================================================

log "🔍 Verifying deployment..."

# Check service status
if ! sudo systemctl is-active --quiet bfagent; then
    error "Service is not running!"
    exit 1
fi

# Check response time
RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health/)
info "Response time: ${RESPONSE_TIME}s"

if (( $(echo "$RESPONSE_TIME > 5" | bc -l) )); then
    warn "Response time is high (> 5s)"
fi

# Check for errors in logs
RECENT_ERRORS=$(sudo journalctl -u bfagent --since "1 minute ago" | grep -i error | wc -l)
if [ "$RECENT_ERRORS" -gt 0 ]; then
    warn "Found $RECENT_ERRORS errors in recent logs"
    sudo journalctl -u bfagent --since "1 minute ago" | grep -i error | tail -5
fi

log "✅ Verification complete"

# =============================================================================
# Post-Deployment Tasks
# =============================================================================

log "🧹 Running post-deployment tasks..."

# Clear cache (optional)
python manage.py shell -c "from django.core.cache import cache; cache.clear()" 2>/dev/null || true

# Update search indexes (if applicable)
# python manage.py update_index 2>/dev/null || true

log "✅ Post-deployment tasks complete"

# =============================================================================
# Deployment Summary
# =============================================================================

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                   🎉 DEPLOYMENT SUCCESSFUL                    ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║ Branch:          $BRANCH"
echo "║ Previous commit: ${PREVIOUS_COMMIT:0:8}"
echo "║ New commit:      ${NEW_COMMIT:0:8}"
echo "║ Backup:          $DEPLOY_BACKUP"
echo "║ Time:            $(date +'%Y-%m-%d %H:%M:%S')"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

log "Next steps:"
echo "  1. Monitor logs: sudo journalctl -u bfagent -f"
echo "  2. Check metrics: https://yourdomain.com/admin/"
echo "  3. Test functionality"
echo ""
echo "To rollback if needed:"
echo "  git checkout $PREVIOUS_COMMIT"
echo "  sudo systemctl restart bfagent"
echo "  Or use: ./scripts/restore.sh $DEPLOY_BACKUP"
echo ""

exit 0
