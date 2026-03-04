#!/usr/bin/env bash
# ==============================================================================
# BF Agent Platform — Docker/Hetzner Tuning Audit
# ==============================================================================
# Checks current server parameters against ADR-022 recommendations.
# Safe to run on PROD — read-only, no changes made.
#
# Usage:
#   chmod +x bf-tuning-audit.sh
#   ./bf-tuning-audit.sh              # Full audit
#   ./bf-tuning-audit.sh --fix        # Audit + apply safe auto-fixes
#   ./bf-tuning-audit.sh --json       # Machine-readable JSON output
#   ./bf-tuning-audit.sh --app bfagent  # Single app check only
#
# Requires: docker, docker compose v2, jq
# ==============================================================================
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
readonly SCRIPT_VERSION="1.0.0"
readonly SCRIPT_DATE="2026-03-03"

# All known platform apps (ADR-063 port mapping)
declare -A APPS=(
    ["bfagent"]="8080:/opt/bfagent-app"
    ["travel-beat"]="8082:/opt/travel-beat"
    ["risk-hub"]="8090:/opt/risk-hub"
    ["cad-hub"]="8094:/opt/cad-hub"
    ["trading-hub"]="8088:/opt/trading-hub"
    ["weltenhub"]="8085:/opt/weltenhub"
    ["mcp-hub"]="8081:/opt/mcp-hub"
)

# Target thresholds (from recommendations)
readonly TARGET_WEB_MEM_MB=384
readonly TARGET_DB_MEM_MB=512
readonly TARGET_REDIS_MEM_MB=128
readonly TARGET_WORKER_MEM_MB=512
readonly TARGET_REDIS_MAXMEM_MB=96
readonly TARGET_SWAPPINESS=10
readonly TARGET_SOMAXCONN=65535
readonly TARGET_INOTIFY_WATCHES=524288
readonly TARGET_FILE_MAX=2097152
readonly TARGET_PG_RANDOM_PAGE_COST="1.1"
readonly TARGET_PG_MAX_CONN=50

# ── CLI Args ──────────────────────────────────────────────────────────────────
FIX_MODE=false
JSON_MODE=false
SINGLE_APP=""

for arg in "$@"; do
    case "$arg" in
        --fix)   FIX_MODE=true ;;
        --json)  JSON_MODE=true ;;
        --app)   shift; SINGLE_APP="${1:-}" ;;
        --help)
            grep '^#' "$0" | head -20 | sed 's/^# \?//'
            exit 0
            ;;
    esac
done

# ── Colors ────────────────────────────────────────────────────────────────────
if [[ -t 1 ]] && ! $JSON_MODE; then
    RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'
else
    RED=''; YELLOW=''; GREEN=''; CYAN=''; BOLD=''; DIM=''; RESET=''
fi

# ── Counters ───────────────────────────────────────────────────────────────────
PASS=0; WARN=0; FAIL=0
declare -a FINDINGS=()

# ── Helpers ───────────────────────────────────────────────────────────────────
log_section() {
    $JSON_MODE && return
    echo ""
    echo -e "${CYAN}${BOLD}\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550${RESET}"
    echo -e "${CYAN}${BOLD}  $1${RESET}"
    echo -e "${CYAN}${BOLD}\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550${RESET}"
}

pass() {
    local msg="$1"
    ((PASS++)) || true
    $JSON_MODE || printf "  ${GREEN}\u2714${RESET}  %s\n" "$msg"
    FINDINGS+=("{\"status\":\"PASS\",\"msg\":$(echo \"$msg\" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))')}")
}

warn() {
    local msg="$1" detail="${2:-}"
    ((WARN++)) || true
    $JSON_MODE || printf "  ${YELLOW}\u26a0${RESET}  %s${DIM}%s${RESET}\n" "$msg" "${detail:+  \u2192 $detail}"
    FINDINGS+=("{\"status\":\"WARN\",\"msg\":$(echo \"$msg\" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))'),\"detail\":$(echo \"$detail\" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))')}")
}

fail() {
    local msg="$1" detail="${2:-}" fix="${3:-}"
    ((FAIL++)) || true
    $JSON_MODE || printf "  ${RED}\u2718${RESET}  %s${DIM}%s${RESET}\n" "$msg" "${detail:+  \u2192 $detail}"
    [[ -n "$fix" ]] && ! $JSON_MODE && printf "     ${DIM}Fix: %s${RESET}\n" "$fix"
    FINDINGS+=("{\"status\":\"FAIL\",\"msg\":$(echo \"$msg\" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))'),\"detail\":$(echo \"$detail\" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))'),\"fix\":$(echo \"$fix\" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))')}")
}

bytes_to_mb() { echo $(( $1 / 1024 / 1024 )); }

apply_sysctl_fix() {
    local key="$1" value="$2"
    if $FIX_MODE; then
        sysctl -w "${key}=${value}" > /dev/null 2>&1 && \
            echo -e "     ${GREEN}\u21b3 Applied: ${key}=${value}${RESET}"
    fi
}

# ── Prerequisites ───────────────────────────────────────────────────────────────
check_prerequisites() {
    log_section "Prerequisites"
    command -v docker  &>/dev/null && pass "docker available" \
                                   || { fail "docker not found"; exit 1; }
    docker compose version &>/dev/null && pass "docker compose v2 available" \
                                        || fail "docker compose v2 not found" \
                                               "Install: apt-get install docker-compose-plugin"
    command -v jq      &>/dev/null && pass "jq available" \
                                   || warn "jq not found" "Some checks will be skipped"
    command -v python3 &>/dev/null && pass "python3 available" \
                                   || { fail "python3 not found"; exit 1; }
}

# ── 1. Docker Daemon ───────────────────────────────────────────────────────────────
check_docker_daemon() {
    log_section "1. Docker Daemon Configuration"
    local daemon_cfg
    daemon_cfg=$(docker info --format '{{json .}}' 2>/dev/null || echo "{}")

    local log_driver
    log_driver=$(echo "$daemon_cfg" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('LoggingDriver','unknown'))
" 2>/dev/null || echo "unknown")
    [[ "$log_driver" == "json-file" ]] \
        && pass "Logging driver: json-file" \
        || fail "Logging driver is '$log_driver' (expected: json-file)" \
                "" "Set in /etc/docker/daemon.json: {\"log-driver\":\"json-file\"}"

    local live_restore
    live_restore=$(cat /etc/docker/daemon.json 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('live-restore',False))" \
        2>/dev/null || echo "false")
    [[ "$live_restore" == "True" || "$live_restore" == "true" ]] \
        && pass "live-restore: enabled" \
        || fail "live-restore: disabled" \
                "Containers stop on daemon restart" \
                'Add to /etc/docker/daemon.json: "live-restore": true'

    local uproxy
    uproxy=$(cat /etc/docker/daemon.json 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('userland-proxy',True))" \
        2>/dev/null || echo "true")
    [[ "$uproxy" == "False" || "$uproxy" == "false" ]] \
        && pass "userland-proxy: disabled (kernel NAT)" \
        || warn "userland-proxy: enabled" 'Set "userland-proxy": false'

    local storage_driver
    storage_driver=$(echo "$daemon_cfg" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('Driver','unknown'))
" 2>/dev/null || echo "unknown")
    [[ "$storage_driver" == "overlay2" ]] \
        && pass "Storage driver: overlay2" \
        || fail "Storage driver: '$storage_driver' (expected: overlay2)"

    local bk_gc
    bk_gc=$(cat /etc/docker/daemon.json 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print('enabled' if d.get('builder',{}).get('gc',{}).get('enabled',False) else 'disabled')" \
        2>/dev/null || echo "disabled")
    [[ "$bk_gc" == "enabled" ]] \
        && pass "BuildKit GC: enabled" \
        || warn "BuildKit GC: disabled" "Docker build cache grows unbounded"

    local dangling
    dangling=$(docker images -f dangling=true -q 2>/dev/null | wc -l)
    (( dangling == 0 )) \
        && pass "No dangling images" \
        || warn "${dangling} dangling image(s) found" "Run: docker image prune -f"
}

# ── 2. sysctl ───────────────────────────────────────────────────────────────────────
check_sysctl_val() {
    local key="$1" target="$2" op="$3" detail="$4" fix_val="${5:-$target}"
    local current
    current=$(sysctl -n "$key" 2>/dev/null || echo "0")
    local ok=false
    case "$op" in
        eq) [[ "$current" == "$target" ]] && ok=true ;;
        le) (( $(echo "$current <= $target" | bc -l 2>/dev/null || echo 0) )) && ok=true ;;
        ge) (( $(echo "$current >= $target" | bc -l 2>/dev/null || echo 0) )) && ok=true ;;
    esac
    if $ok; then
        pass "${key} = ${current} (target: ${op} ${target})"
    else
        fail "${key} = ${current} (target: ${op} ${target})" "$detail" "sysctl -w ${key}=${fix_val}"
        apply_sysctl_fix "$key" "$fix_val"
    fi
}

check_sysctl() {
    log_section "2. Linux Kernel / sysctl Parameters"
    check_sysctl_val "vm.swappiness"               "$TARGET_SWAPPINESS"  "le" "High swappiness degrades NVMe performance" "10"
    check_sysctl_val "vm.overcommit_memory"        "1"                   "eq" "Required for Docker fork() safety" "1"
    check_sysctl_val "net.core.somaxconn"          "$TARGET_SOMAXCONN"   "ge" "Low backlog limits concurrent connections" "65535"
    check_sysctl_val "net.ipv4.tcp_max_syn_backlog" "$TARGET_SOMAXCONN"  "ge" "Low SYN backlog drops connections under load" "65535"
    check_sysctl_val "net.ipv4.tcp_tw_reuse"       "1"                   "eq" "TIME_WAIT accumulation wastes ports" "1"
    check_sysctl_val "fs.file-max"                 "$TARGET_FILE_MAX"    "ge" "Low file-max causes EMFILE errors" "2097152"
    check_sysctl_val "fs.inotify.max_user_watches" "$TARGET_INOTIFY_WATCHES" "ge" "Low inotify limit breaks Django file watching" "524288"
    check_sysctl_val "fs.inotify.max_user_instances" "512"              "ge" "Low inotify instances limit" "512"
}

# ── 3+4+5. Container Resources ──────────────────────────────────────────────────────
check_container_resources() {
    local app="$1" app_path="$2"
    local compose_file="${app_path}/docker-compose.prod.yml"
    [[ ! -f "$compose_file" ]] && warn "$app: compose file not found at $compose_file" && return

    # Check each service type for memory limits
    for svc_pattern in "web" "worker" "db" "redis"; do
        local has_limit
        has_limit=$(python3 -c "
import sys, re
try:
    with open('${compose_file}') as f:
        content = f.read()
    # Simple check: look for memory limit near service name
    pattern = r'${svc_pattern}.*?memory:\s*(\d+[MG])'
    m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    print(m.group(1) if m else '')
except Exception:
    print('')
" 2>/dev/null || echo "")

        local target_mb
        case "$svc_pattern" in
            web)    target_mb=$TARGET_WEB_MEM_MB ;;
            worker) target_mb=$TARGET_WORKER_MEM_MB ;;
            db)     target_mb=$TARGET_DB_MEM_MB ;;
            redis)  target_mb=$TARGET_REDIS_MEM_MB ;;
        esac

        if [[ -n "$has_limit" ]]; then
            pass "$app/${svc_pattern}: memory limit ${has_limit} configured"
        else
            fail "$app/${svc_pattern}: no memory limit" \
                 "Container can consume all ${target_mb}MB+ without constraint" \
                 "Add deploy.resources.limits.memory: ${target_mb}M to ${svc_pattern} service"
        fi
    done

    # Check restart policy
    if grep -q 'restart:' "$compose_file"; then
        pass "$app: restart policy configured"
    else
        warn "$app: no restart policy" "Add restart: unless-stopped to all services"
    fi

    # Check logging limits
    if grep -q 'max-size' "$compose_file"; then
        pass "$app: log rotation configured"
    else
        warn "$app: no log rotation" "Add logging.options.max-size: 10m to prevent disk fill"
    fi

    # Check shm_size for db
    if grep -q 'shm_size' "$compose_file"; then
        pass "$app/db: shm_size configured"
    else
        warn "$app/db: no shm_size" "Add shm_size: 128m to db service for PostgreSQL sort performance"
    fi
}

check_all_apps() {
    local apps_to_check
    if [[ -n "$SINGLE_APP" ]]; then
        apps_to_check=("$SINGLE_APP")
    else
        apps_to_check=("${!APPS[@]}")
    fi

    log_section "3. Container Resource Limits"
    for app in "${apps_to_check[@]}"; do
        local info="${APPS[$app]:-}"
        [[ -z "$info" ]] && warn "$app: not in APPS registry" && continue
        local app_path="${info#*:}"
        check_container_resources "$app" "$app_path"
    done
}

# ── 4. PostgreSQL ────────────────────────────────────────────────────────────────
check_postgresql() {
    log_section "4. PostgreSQL Configuration"

    local apps_to_check
    if [[ -n "$SINGLE_APP" ]]; then
        apps_to_check=("$SINGLE_APP")
    else
        apps_to_check=("${!APPS[@]}")
    fi

    for app in "${apps_to_check[@]}"; do
        local info="${APPS[$app]:-}"
        [[ -z "$info" ]] && continue
        local app_path="${info#*:}"

        # Find the db container for this app
        local db_container
        db_container=$(docker ps --format '{{.Names}}' 2>/dev/null \
            | grep -E "^${app//-/_}_db|^${app}-db" | head -1 || true)
        [[ -z "$db_container" ]] && continue

        # random_page_cost (critical for NVMe)
        local rpc
        rpc=$(docker exec "$db_container" \
            psql -U postgres -tAc "SHOW random_page_cost" 2>/dev/null | tr -d ' ' || echo "")
        if [[ -n "$rpc" ]]; then
            if python3 -c "import sys; sys.exit(0 if float('${rpc}') <= 1.2 else 1)" 2>/dev/null; then
                pass "$app/db: random_page_cost=${rpc} (NVMe-optimized)"
            else
                fail "$app/db: random_page_cost=${rpc} (target: <= 1.2)" \
                     "PostgreSQL prefers seq scans over index scans on NVMe — wrong plan choice" \
                     "Add -c random_page_cost=1.1 to postgres command in compose"
            fi
        fi

        # max_connections
        local max_conn
        max_conn=$(docker exec "$db_container" \
            psql -U postgres -tAc "SHOW max_connections" 2>/dev/null | tr -d ' ' || echo "")
        if [[ -n "$max_conn" ]]; then
            if (( max_conn <= TARGET_PG_MAX_CONN )); then
                pass "$app/db: max_connections=${max_conn} (efficient)"
            else
                warn "$app/db: max_connections=${max_conn} (target: <= ${TARGET_PG_MAX_CONN})" \
                     "7 x ${max_conn} = $((7 * max_conn)) theoretical connections on 8GB RAM"
            fi
        fi

        # shared_buffers
        local sb
        sb=$(docker exec "$db_container" \
            psql -U postgres -tAc "SHOW shared_buffers" 2>/dev/null | tr -d ' ' || echo "")
        [[ -n "$sb" ]] && pass "$app/db: shared_buffers=${sb}"
    done
}

# ── 5. Redis ───────────────────────────────────────────────────────────────────────
check_redis() {
    log_section "5. Redis Configuration"

    local apps_to_check
    if [[ -n "$SINGLE_APP" ]]; then
        apps_to_check=("$SINGLE_APP")
    else
        apps_to_check=("${!APPS[@]}")
    fi

    for app in "${apps_to_check[@]}"; do
        local info="${APPS[$app]:-}"
        [[ -z "$info" ]] && continue

        local redis_container
        redis_container=$(docker ps --format '{{.Names}}' 2>/dev/null \
            | grep -E "^${app//-/_}_redis|^${app}-redis" | head -1 || true)
        [[ -z "$redis_container" ]] && continue

        # maxmemory
        local maxmem
        maxmem=$(docker exec "$redis_container" redis-cli CONFIG GET maxmemory 2>/dev/null \
            | tail -1 | tr -d ' ' || echo "0")
        local maxmem_mb=$(( ${maxmem:-0} / 1024 / 1024 ))

        if (( maxmem_mb >= TARGET_REDIS_MAXMEM_MB )); then
            pass "$app/redis: maxmemory=${maxmem_mb}MB (target: >= ${TARGET_REDIS_MAXMEM_MB}MB)"
        else
            fail "$app/redis: maxmemory not set (${maxmem_mb}MB)" \
                 "Redis can grow unbounded and OOM the server" \
                 "Add --maxmemory ${TARGET_REDIS_MAXMEM_MB}mb --maxmemory-policy allkeys-lru to redis command"
        fi

        # eviction policy
        local eviction
        eviction=$(docker exec "$redis_container" redis-cli CONFIG GET maxmemory-policy 2>/dev/null \
            | tail -1 | tr -d ' ' || echo "noeviction")
        if [[ "$eviction" == "allkeys-lru" || "$eviction" == "volatile-lru" ]]; then
            pass "$app/redis: eviction policy=${eviction} (safe)"
        else
            fail "$app/redis: eviction policy=${eviction} (target: allkeys-lru)" \
                 "noeviction causes Redis errors when full instead of graceful eviction" \
                 "Add --maxmemory-policy allkeys-lru to redis command"
        fi
    done
}

# ── 6. Gunicorn ─────────────────────────────────────────────────────────────────────
check_gunicorn() {
    log_section "6. Gunicorn Configuration"

    local apps_to_check
    if [[ -n "$SINGLE_APP" ]]; then
        apps_to_check=("$SINGLE_APP")
    else
        apps_to_check=("${!APPS[@]}")
    fi

    for app in "${apps_to_check[@]}"; do
        local web_container
        web_container=$(docker ps --format '{{.Names}}' 2>/dev/null \
            | grep -E "^${app//-/_}_web|^${app}-web" | head -1 || true)
        [[ -z "$web_container" ]] && continue

        local cmd
        cmd=$(docker inspect "$web_container" 2>/dev/null \
            | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list): data = data[0]
cmd = data.get('Config', {}).get('Cmd', [])
print(' '.join(str(c) for c in cmd))
" 2>/dev/null || echo "")

        local env_vars
        env_vars=$(docker inspect "$web_container" 2>/dev/null \
            | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list): data = data[0]
envs = data.get('Config', {}).get('Env', [])
for e in envs:
    if any(k in e for k in ['GUNICORN', 'WORKERS', 'THREADS', 'TIMEOUT']):
        print(e)
" 2>/dev/null || echo "")

        if echo "$cmd $env_vars" | grep -q "max.requests"; then
            pass "$app/web: --max-requests configured (memory leak protection)"
        else
            fail "$app/web: --max-requests NOT configured" \
                 "Workers never recycle - gradual memory leak over days" \
                 "Add GUNICORN_MAX_REQUESTS=1000 to .env.prod"
        fi

        if echo "$cmd $env_vars" | grep -qE "gthread|gevent|uvicorn"; then
            pass "$app/web: async/threaded worker class configured"
        else
            warn "$app/web: worker-class not gthread" \
                 "Default sync workers less efficient for HTMX I/O - consider gthread"
        fi
    done
}

# ── 7. System Health ────────────────────────────────────────────────────────────────
check_system_health() {
    log_section "7. Disk & System Health"

    local disk_usage
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    if (( disk_usage < 70 )); then
        pass "Root disk: ${disk_usage}%"
    elif (( disk_usage < 85 )); then
        warn "Root disk: ${disk_usage}% (>70% warning)" "docker system prune -af --filter 'until=24h'"
    else
        fail "Root disk: ${disk_usage}% (CRITICAL)" "Server may fill up" "docker system prune -af"
    fi

    local swap_total swap_used
    swap_total=$(free -m | awk '/Swap/{print $2}')
    swap_used=$(free -m  | awk '/Swap/{print $3}')
    if (( swap_total == 0 )); then
        warn "No swap" "Add 2GB swapfile: fallocate -l 2G /swapfile"
    elif (( swap_used > 0 )); then
        fail "Swap in use: ${swap_used}MB/${swap_total}MB" "Active swapping = degraded performance" "docker stats --no-stream"
    else
        pass "Swap ${swap_total}MB configured, idle"
    fi

    local mem_avail
    mem_avail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
    if (( mem_avail > 512 )); then
        pass "Available RAM: ${mem_avail}MB"
    elif (( mem_avail > 256 )); then
        warn "Available RAM low: ${mem_avail}MB"
    else
        fail "Available RAM critically low: ${mem_avail}MB" "OOM kills imminent"
    fi

    local load1 ncpu load_pct
    load1=$(awk '{print $1}' /proc/loadavg)
    ncpu=$(nproc)
    load_pct=$(python3 -c "print(int(float('${load1}') / ${ncpu} * 100))")
    if (( load_pct < 70 )); then
        pass "Load: ${load1} / ${ncpu} CPUs (${load_pct}%)"
    elif (( load_pct < 90 )); then
        warn "Load: ${load1} / ${ncpu} CPUs (${load_pct}%) - under pressure"
    else
        fail "Load: ${load1} / ${ncpu} CPUs (${load_pct}%) - CPU saturated" "" "docker stats --no-stream"
    fi

    local oom_count
    oom_count=$(dmesg 2>/dev/null | grep -c 'Out of memory' || echo '0')
    (( oom_count == 0 )) \
        && pass "No OOM events in dmesg" \
        || fail "OOM killer: ${oom_count} event(s)" "Containers were killed" "journalctl -k | grep -i 'killed process'"
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
    local total=$(( PASS + WARN + FAIL ))

    if $JSON_MODE; then
        python3 << PYEOF
import json
findings_raw = [${FINDINGS[*]:-}]
summary = {
    'version': '${SCRIPT_VERSION}',
    'date': '$(date -Iseconds)',
    'hostname': '$(hostname)',
    'totals': {'pass': ${PASS}, 'warn': ${WARN}, 'fail': ${FAIL}, 'total': ${total}},
    'findings': findings_raw
}
print(json.dumps(summary, indent=2))
PYEOF
        return
    fi

    echo ""
    echo -e "${BOLD}AUDIT SUMMARY -- $(hostname) -- $(date '+%Y-%m-%d %H:%M')${RESET}"
    printf "  ${GREEN}PASS${RESET}  %3d\n" "$PASS"
    printf "  ${YELLOW}WARN${RESET}  %3d\n" "$WARN"
    printf "  ${RED}FAIL${RESET}  %3d\n" "$FAIL"
    printf "  Total %3d checks\n" "$total"
    echo ""
    if (( FAIL == 0 && WARN == 0 )); then
        echo -e "  ${GREEN}All checks passed!${RESET}"
    elif (( FAIL == 0 )); then
        echo -e "  ${YELLOW}Good -- address warnings when possible.${RESET}"
    else
        echo -e "  ${RED}${FAIL} critical issue(s) to fix.${RESET}"
    fi
    $FIX_MODE && echo -e "  --fix mode was active: safe sysctl fixes applied."
    echo ""
    (( FAIL > 0 )) && exit 2; (( WARN > 0 )) && exit 1; exit 0
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    $JSON_MODE || echo ""
    $JSON_MODE || echo "  BF Agent Platform -- Tuning Audit v${SCRIPT_VERSION}"
    $JSON_MODE || echo "  Hetzner / Docker Performance & Reliability"
    $JSON_MODE || echo ""
    check_prerequisites
    check_docker_daemon
    check_sysctl
    check_all_apps
    check_postgresql
    check_redis
    check_gunicorn
    check_system_health
    print_summary
}

main
