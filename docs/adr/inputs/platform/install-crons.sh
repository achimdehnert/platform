#!/usr/bin/env bash
# ============================================================================
# install-crons.sh — Install all monitoring cron jobs on the server
# ============================================================================
#
# Run this ONCE on the server to set up automated monitoring.
# Idempotent — safe to re-run.
#
# Usage:
#   ./install-crons.sh                 # Install all crons
#   ./install-crons.sh --dry-run       # Show what would be installed
#   ./install-crons.sh --remove        # Remove all platform crons
#
# Installs:
#   Every 5 min  — health-monitor.sh (service health)
#   Daily 02:00  — db-backup.sh --all (database backups)
#   Daily 06:00  — ssl-check.sh (certificate expiry)
#   Daily 08:00  — drift-check.sh (config drift)
#   Weekly Sun   — docker-cleanup.sh (disk cleanup)
#
# ============================================================================
set -euo pipefail

SCRIPTS_DIR="/opt/deploy/scripts"
CRON_MARKER="# platform-managed-cron"

DRY_RUN=false
REMOVE=false

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --remove)  REMOVE=true ;;
    esac
done

info()   { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()     { echo -e "\033[1;32m[OK]\033[0m    $*"; }
change() { echo -e "\033[1;36m[SET]\033[0m   $*"; }

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         Install Platform Cron Jobs                   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Verify scripts exist ─────────────────────────────────────────────────

REQUIRED_SCRIPTS=(
    health-monitor.sh
    db-backup.sh
    ssl-check.sh
    drift-check.sh
    docker-cleanup.sh
)

if ! $REMOVE; then
    for script in "${REQUIRED_SCRIPTS[@]}"; do
        if [[ ! -f "${SCRIPTS_DIR}/${script}" ]]; then
            echo "ERROR: ${SCRIPTS_DIR}/${script} not found." >&2
            echo "Copy scripts to ${SCRIPTS_DIR}/ first." >&2
            exit 1
        fi
    done
    ok "All scripts found in ${SCRIPTS_DIR}/"
fi

# ── Build crontab entries ────────────────────────────────────────────────

CRON_ENTRIES=$(cat <<CRON
${CRON_MARKER}
# Health monitoring — every 5 minutes
*/5 * * * * ${SCRIPTS_DIR}/health-monitor.sh --quiet 2>&1 | logger -t health-monitor
# Database backups — daily at 02:00 UTC
0 2 * * * ${SCRIPTS_DIR}/db-backup.sh --all 2>&1 | logger -t db-backup
# SSL certificate check — daily at 06:00 UTC
0 6 * * * ${SCRIPTS_DIR}/ssl-check.sh --quiet 2>&1 | logger -t ssl-check
# Configuration drift check — daily at 08:00 UTC
0 8 * * * ${SCRIPTS_DIR}/drift-check.sh --quiet 2>&1 | logger -t drift-check
# Docker cleanup — weekly Sunday at 03:00 UTC
0 3 * * 0 ${SCRIPTS_DIR}/docker-cleanup.sh 2>&1 | logger -t docker-cleanup
${CRON_MARKER}
CRON
)

# ── Remove existing platform crons ───────────────────────────────────────

remove_platform_crons() {
    local current
    current=$(crontab -l 2>/dev/null || echo "")

    if ! echo "$current" | grep -q "$CRON_MARKER"; then
        info "No platform crons found in crontab"
        return
    fi

    local cleaned
    cleaned=$(echo "$current" | awk -v marker="$CRON_MARKER" '
        $0 == marker { skip = !skip; next }
        !skip { print }
    ')

    if $DRY_RUN; then
        info "[dry-run] Would remove platform cron entries"
    else
        echo "$cleaned" | crontab -
        change "Removed platform cron entries"
    fi
}

# ── Install ──────────────────────────────────────────────────────────────

install_crons() {
    # First remove old entries (idempotent)
    remove_platform_crons

    local current
    current=$(crontab -l 2>/dev/null || echo "")

    local new_crontab="${current}
${CRON_ENTRIES}"

    if $DRY_RUN; then
        info "[dry-run] Would install these cron entries:"
        echo ""
        echo "$CRON_ENTRIES"
        echo ""
    else
        echo "$new_crontab" | crontab -
        change "Installed platform cron entries"
        echo ""
        echo "  Installed cron jobs:"
        echo "    */5 * * * *  health-monitor.sh"
        echo "    0 2 * * *    db-backup.sh --all"
        echo "    0 6 * * *    ssl-check.sh"
        echo "    0 8 * * *    drift-check.sh"
        echo "    0 3 * * 0    docker-cleanup.sh (weekly)"
    fi
}

# ── Make scripts executable ──────────────────────────────────────────────

ensure_executable() {
    for script in "${REQUIRED_SCRIPTS[@]}"; do
        local path="${SCRIPTS_DIR}/${script}"
        if [[ -f "$path" ]] && [[ ! -x "$path" ]]; then
            chmod +x "$path"
            change "chmod +x ${script}"
        fi
    done

    # Also make services.conf readable
    for conf_path in "${SCRIPTS_DIR}/services.conf" "${SCRIPTS_DIR}/setup/services.conf"; do
        if [[ -f "$conf_path" ]] && [[ ! -r "$conf_path" ]]; then
            chmod 644 "$conf_path"
        fi
    done
}

# ── Main ─────────────────────────────────────────────────────────────────

if $REMOVE; then
    remove_platform_crons
else
    ensure_executable
    install_crons
fi

echo ""
ok "Done. Verify with: crontab -l | grep platform"
echo ""
