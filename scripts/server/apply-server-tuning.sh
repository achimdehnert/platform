#!/usr/bin/env bash
# ==============================================================================
# BF Agent Platform — Apply Server Tuning (ADR-098)
# ==============================================================================
# Applies Docker daemon config + Linux sysctl parameters to PROD or DEV server.
# Safe to re-run (idempotent). Does NOT modify any docker-compose files.
#
# Usage:
#   ./apply-server-tuning.sh              # Apply all (requires root)
#   ./apply-server-tuning.sh --dry-run    # Show what would change, no writes
#   ./apply-server-tuning.sh --sysctl-only
#   ./apply-server-tuning.sh --daemon-only
#
# Requires: root, docker
# After running: systemctl restart docker  (for daemon.json changes to take effect)
# ==============================================================================
set -euo pipefail

readonly SCRIPT_VERSION="1.0.0"
readonly ADR="ADR-098"

# ── CLI Args ──────────────────────────────────────────────────────────────────
DRY_RUN=false
SYSCTL_ONLY=false
DAEMON_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)     DRY_RUN=true ;;
        --sysctl-only) SYSCTL_ONLY=true ;;
        --daemon-only) DAEMON_ONLY=true ;;
        --help)
            grep '^#' "$0" | head -18 | sed 's/^# \?//'
            exit 0
            ;;
    esac
done

# ── Colors ────────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'
else
    RED=''; YELLOW=''; GREEN=''; CYAN=''; BOLD=''; DIM=''; RESET=''
fi

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "  ${CYAN}→${RESET}  $*"; }
ok()      { echo -e "  ${GREEN}✔${RESET}  $*"; }
changed() { echo -e "  ${YELLOW}⚡${RESET}  $*"; }
dry()     { echo -e "  ${DIM}[dry-run]${RESET}  $*"; }
err()     { echo -e "  ${RED}✘${RESET}  $*" >&2; }

write_file() {
    local path="$1" content="$2"
    if $DRY_RUN; then
        dry "Would write: $path"
    else
        echo "$content" > "$path"
        changed "Written: $path"
    fi
}

# ── Root check ────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]] && ! $DRY_RUN; then
    err "This script must be run as root (or with --dry-run for preview)"
    exit 1
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "  BF Agent Platform — Server Tuning v${SCRIPT_VERSION}"
echo "  ${ADR}: Production Infrastructure Standard"
echo "  Host: $(hostname) | Date: $(date '+%Y-%m-%d %H:%M')"
echo ""

# ── §1 Docker Daemon ──────────────────────────────────────────────────────────
apply_docker_daemon() {
    echo "§1 Docker Daemon (daemon.json)"
    echo ""

    local daemon_json='{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5",
    "compress": "true"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": { "Name": "nofile", "Hard": 65536, "Soft": 65536 }
  },
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true,
  "max-concurrent-downloads": 6,
  "max-concurrent-uploads": 3,
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "5GB",
      "policy": [
        { "keepStorage": "2GB", "filter": ["unused-for=168h"] },
        { "keepStorage": "5GB", "all": true }
      ]
    }
  }
}'

    if [[ -f /etc/docker/daemon.json ]] && ! $DRY_RUN; then
        cp /etc/docker/daemon.json "/etc/docker/daemon.json.bak.$(date +%Y%m%d-%H%M%S)"
        info "Backed up existing daemon.json"
    fi

    write_file "/etc/docker/daemon.json" "$daemon_json"

    if $DRY_RUN; then
        dry "Would reload/restart docker daemon"
    else
        if systemctl reload docker 2>/dev/null; then
            ok "Docker daemon reloaded"
        else
            changed "Run manually: systemctl restart docker"
        fi
    fi
    echo ""
}

# ── §2 Linux Kernel / sysctl ──────────────────────────────────────────────────
apply_sysctl() {
    echo "§2 Linux Kernel / sysctl Parameters"
    echo ""

    local sysctl_conf="# BF Agent Platform — ADR-098 Production Tuning
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
vm.swappiness = 10
vm.overcommit_memory = 1
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512"

    local sysctl_file="/etc/sysctl.d/99-docker-perf.conf"

    if [[ -f "$sysctl_file" ]] && ! $DRY_RUN; then
        cp "$sysctl_file" "${sysctl_file}.bak.$(date +%Y%m%d-%H%M%S)"
        info "Backed up existing sysctl config"
    fi

    write_file "$sysctl_file" "$sysctl_conf"

    if $DRY_RUN; then
        dry "Would run: sysctl -p $sysctl_file"
    else
        sysctl -p "$sysctl_file" > /dev/null 2>&1
        ok "sysctl parameters applied (persistent across reboots)"
        for key in vm.swappiness net.core.somaxconn fs.inotify.max_user_watches; do
            printf "     %-40s = %s\n" "$key" "$(sysctl -n $key)"
        done
    fi
    echo ""
}

# ── §3 Swap Safety Net ────────────────────────────────────────────────────────
configure_swap() {
    echo "§3 Swap Safety Net (2 GB)"
    echo ""

    local swap_total
    swap_total=$(free -m | awk '/Swap/{print $2}')

    if (( swap_total >= 1024 )); then
        ok "Swap already configured (${swap_total}MB) — skipping"
        echo ""
        return
    fi

    info "No swap detected — creating 2 GB swapfile"

    if $DRY_RUN; then
        dry "Would create /swapfile (2 GB) + add to /etc/fstab"
    else
        if [[ ! -f /swapfile ]]; then
            fallocate -l 2G /swapfile
            chmod 600 /swapfile
            mkswap /swapfile > /dev/null
            ok "Created /swapfile (2 GB)"
        fi
        if ! swapon --show | grep -q /swapfile; then
            swapon /swapfile
            ok "Swap activated"
        fi
        if ! grep -q '/swapfile' /etc/fstab; then
            echo '/swapfile none swap sw 0 0' >> /etc/fstab
            ok "Added /swapfile to /etc/fstab"
        fi
    fi
    echo ""
}

# ── §4 Docker Cleanup Cron ────────────────────────────────────────────────────
configure_cleanup_cron() {
    echo "§4 Docker Cleanup Cron (daily 03:00)"
    echo ""

    local cron_file="/etc/cron.d/docker-cleanup"

    if [[ -f "$cron_file" ]]; then
        ok "Docker cleanup cron already exists — skipping"
    else
        local cron_content="SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 3 * * * root docker image prune -f --filter 'until=24h' >> /var/log/docker-cleanup.log 2>&1
0 3 * * 0 root docker system prune -f --filter 'until=168h' >> /var/log/docker-cleanup.log 2>&1"
        write_file "$cron_file" "$cron_content"
    fi
    echo ""
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_next_steps() {
    echo "Next Steps"
    echo "─────────────────────────────────────────────────"
    if $DRY_RUN; then
        echo "  DRY RUN complete — run without --dry-run to apply."
    else
        echo "  Server-level tuning applied. Remaining per-app steps:"
        echo "  1. Merge scripts/server/compose-hardening/template.yml into each docker-compose.prod.yml"
        echo "  2. Add Gunicorn env vars to .env.prod (WORKERS=2 THREADS=2 WORKER_CLASS=gthread MAX_REQUESTS=1000)"
        echo "  3. Verify: bash scripts/server/bf-tuning-audit.sh"
    fi
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    if ! $SYSCTL_ONLY; then
        apply_docker_daemon
    fi
    if ! $DAEMON_ONLY; then
        apply_sysctl
        configure_swap
        configure_cleanup_cron
    fi
    print_next_steps
}

main
