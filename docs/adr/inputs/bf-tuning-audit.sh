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

# ── Counters ──────────────────────────────────────────────────────────────────
PASS=0; WARN=0; FAIL=0
declare -a FINDINGS=()

# ── Helpers ───────────────────────────────────────────────────────────────────
log_section() {
    $JSON_MODE && return
    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════${RESET}"
    echo -e "${CYAN}${BOLD}  $1${RESET}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════${RESET}"
}

pass() {
    local msg="$1"
    ((PASS++)) || true
    $JSON_MODE || printf "  ${GREEN}✔${RESET}  %s\n" "$msg"
    FINDINGS+=("{\"status\":\"PASS\",\"msg\":$(echo "$msg" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))')}")
}

warn() {
    local msg="$1" detail="${2:-}"
    ((WARN++)) || true
    $JSON_MODE || printf "  ${YELLOW}⚠${RESET}  %s${DIM}%s${RESET}\n" "$msg" "${detail:+  → $detail}"
    FINDINGS+=("{\"status\":\"WARN\",\"msg\":$(echo "$msg" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))'),\"detail\":$(echo "$detail" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))')}")
}

fail() {
    local msg="$1" detail="${2:-}" fix="${3:-}"
    ((FAIL++)) || true
    $JSON_MODE || printf "  ${RED}✘${RESET}  %s${DIM}%s${RESET}\n" "$msg" "${detail:+  → $detail}"
    [[ -n "$fix" ]] && ! $JSON_MODE && printf "     ${DIM}Fix: %s${RESET}\n" "$fix"
    FINDINGS+=("{\"status\":\"FAIL\",\"msg\":$(echo "$msg" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))'),\"detail\":$(echo "$detail" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))'),\"fix\":$(echo "$fix" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))')}")
}

bytes_to_mb() {
    echo $(( $1 / 1024 / 1024 ))
}

# Apply a sysctl fix (only in --fix mode)
apply_sysctl() {
    local key="$1" value="$2"
    if $FIX_MODE; then
        sysctl -w "${key}=${value}" > /dev/null 2>&1 && \
            echo -e "     ${GREEN}↳ Applied: ${key}=${value}${RESET}"
    fi
}

# ── Prerequisites ─────────────────────────────────────────────────────────────
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

# ── 1. Docker Daemon ──────────────────────────────────────────────────────────
check_docker_daemon() {
    log_section "1. Docker Daemon Configuration"

    local daemon_cfg
    daemon_cfg=$(docker info --format '{{json .}}' 2>/dev/null || echo "{}")

    # Logging driver
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

    # live-restore
    local live_restore
    live_restore=$(cat /etc/docker/daemon.json 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('live-restore',False))" \
        2>/dev/null || echo "false")
    [[ "$live_restore" == "True" || "$live_restore" == "true" ]] \
        && pass "live-restore: enabled (containers survive daemon restart)" \
        || fail "live-restore: disabled" \
                "Containers stop on daemon restart → downtime during Docker upgrades" \
                'Add to /etc/docker/daemon.json: "live-restore": true'

    # userland-proxy
    local uproxy
    uproxy=$(cat /etc/docker/daemon.json 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('userland-proxy',True))" \
        2>/dev/null || echo "true")
    [[ "$uproxy" == "False" || "$uproxy" == "false" ]] \
        && pass "userland-proxy: disabled (kernel NAT — faster)" \
        || warn "userland-proxy: enabled" \
                'Set "userland-proxy": false for better network performance'

    # Storage driver
    local storage_driver
    storage_driver=$(echo "$daemon_cfg" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('Driver','unknown'))
" 2>/dev/null || echo "unknown")
    [[ "$storage_driver" == "overlay2" ]] \
        && pass "Storage driver: overlay2" \
        || fail "Storage driver: '$storage_driver' (expected: overlay2)"

    # BuildKit GC
    local bk_gc
    bk_gc=$(cat /etc/docker/daemon.json 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print('enabled' if d.get('builder',{}).get('gc',{}).get('enabled',False) else 'disabled')" \
        2>/dev/null || echo "disabled")
    [[ "$bk_gc" == "enabled" ]] \
        && pass "BuildKit GC: enabled" \
        || warn "BuildKit GC: disabled" \
                "Docker build cache grows unbounded — add builder.gc config"

    # Docker disk usage summary
    local disk_info
    disk_info=$(docker system df --format '{{.Type}}\t{{.Size}}\t{{.Reclaimable}}' 2>/dev/null || echo "")
    if [[ -n "$disk_info" ]]; then
        $JSON_MODE || echo ""
        $JSON_MODE || echo -e "  ${DIM}Docker disk usage:${RESET}"
        while IFS=$'\t' read -r dtype dsize drec; do
            $JSON_MODE || printf "    ${DIM}%-14s %8s  (reclaimable: %s)${RESET}\n" "$dtype" "$dsize" "$drec"
        done <<< "$disk_info"
    fi

    # Dangling images warning
    local dangling
    dangling=$(docker images -f dangling=true -q 2>/dev/null | wc -l)
    (( dangling == 0 )) \
        && pass "No dangling images" \
        || warn "${dangling} dangling image(s) found" \
                "Run: docker image prune -f"
}

# ── 2. Linux Kernel (sysctl) ──────────────────────────────────────────────────
check_sysctl() {
    log_section "2. Linux Kernel / sysctl Parameters"

    check_sysctl_val "vm.swappiness"                  "$TARGET_SWAPPINESS"  "le" \
        "High swappiness degrades container performance on NVMe" \
        "sysctl -w vm.swappiness=${TARGET_SWAPPINESS} && echo 'vm.swappiness=${TARGET_SWAPPINESS}' >> /etc/sysctl.d/99-docker-perf.conf"

    check_sysctl_val "net.core.somaxconn"             "$TARGET_SOMAXCONN"   "ge" \
        "Low value limits concurrent connections to Nginx/Gunicorn" \
        "sysctl -w net.core.somaxconn=${TARGET_SOMAXCONN}"

    check_sysctl_val "net.ipv4.tcp_max_syn_backlog"   "$TARGET_SOMAXCONN"   "ge" \
        "Limits SYN queue depth under high load" \
        "sysctl -w net.ipv4.tcp_max_syn_backlog=${TARGET_SOMAXCONN}"

    check_sysctl_val "net.ipv4.tcp_tw_reuse"          "1"                   "eq" \
        "TIME_WAIT socket accumulation wastes ports" \
        "sysctl -w net.ipv4.tcp_tw_reuse=1"

    check_sysctl_val "vm.overcommit_memory"           "1"                   "eq" \
        "Required for Docker — prevents OOM killer false positives" \
        "sysctl -w vm.overcommit_memory=1"

    check_sysctl_val "fs.inotify.max_user_watches"    "$TARGET_INOTIFY_WATCHES" "ge" \
        "Insufficient for 7 apps + Docker watching files" \
        "sysctl -w fs.inotify.max_user_watches=${TARGET_INOTIFY_WATCHES}"

    check_sysctl_val "fs.inotify.max_user_instances"  "512"                 "ge" \
        "Limits number of inotify watchers" \
        "sysctl -w fs.inotify.max_user_instances=512"

    check_sysctl_val "fs.file-max"                    "$TARGET_FILE_MAX"    "ge" \
        "With 7 apps × 4 services each, file handles matter" \
        "sysctl -w fs.file-max=${TARGET_FILE_MAX}"
}

check_sysctl_val() {
    local key="$1" target="$2" op="$3" detail="$4" fix_cmd="$5"
    local current
    current=$(sysctl -n "$key" 2>/dev/null || echo "N/A")

    if [[ "$current" == "N/A" ]]; then
        warn "${key}: not available on this kernel"
        return
    fi

    local ok=false
    case "$op" in
        eq) [[ "$current" == "$target" ]]                        && ok=true ;;
        ge) (( current >= target ))                              && ok=true ;;
        le) (( current <= target ))                              && ok=true ;;
    esac

    if $ok; then
        pass "${key} = ${current} ✓"
        $FIX_MODE && apply_sysctl "$key" "$target"
    else
        fail "${key} = ${current} (target: ${op} ${target})" "$detail" "$fix_cmd"
        $FIX_MODE && apply_sysctl "$key" "$target"
    fi
}

# ── 3. Per-App Container Audit ────────────────────────────────────────────────
check_all_apps() {
    log_section "3. Container Resource Limits & Health"

    if [[ -n "$SINGLE_APP" ]]; then
        check_app "$SINGLE_APP" "${APPS[$SINGLE_APP]:-}"
        return
    fi

    for app in "${!APPS[@]}"; do
        check_app "$app" "${APPS[$app]}"
    done
}

check_app() {
    local app="$1" meta="$2"
    local port path
    port=$(echo "$meta" | cut -d: -f1)
    path=$(echo "$meta" | cut -d: -f2-)

    $JSON_MODE || echo ""
    $JSON_MODE || echo -e "  ${BOLD}▶ $app${RESET}  ${DIM}(port $port, $path)${RESET}"

    # Check compose file exists
    local compose_file="${path}/docker-compose.prod.yml"
    if [[ ! -f "$compose_file" ]]; then
        warn "$app: docker-compose.prod.yml not found at $path" "App may not be deployed yet"
        return
    fi

    # Check which containers are running
    local containers
    containers=$(docker ps --filter "name=${app//-/_}" --format '{{.Names}}' 2>/dev/null || true)
    if [[ -z "$containers" ]]; then
        # Try with hyphen naming
        containers=$(docker ps --filter "name=${app}" --format '{{.Names}}' 2>/dev/null || true)
    fi

    if [[ -z "$containers" ]]; then
        warn "$app: no running containers found"
        return
    fi

    # Check each container
    for container in $containers; do
        check_container_resources "$app" "$container"
    done

    # Check health endpoint
    check_health_endpoint "$app" "$port"

    # Check compose file ADR-022 compliance
    check_compose_compliance "$app" "$compose_file"
}

check_container_resources() {
    local app="$1" container="$2"

    local inspect
    inspect=$(docker inspect "$container" 2>/dev/null || echo "{}")

    if [[ "$inspect" == "{}" ]]; then
        warn "$app/$container: inspect failed"
        return
    fi

    # Memory limit
    local mem_limit_bytes
    mem_limit_bytes=$(echo "$inspect" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    data = data[0]
print(data.get('HostConfig', {}).get('Memory', 0))
" 2>/dev/null || echo "0")

    local mem_limit_mb
    mem_limit_mb=$(bytes_to_mb "$mem_limit_bytes")

    # Determine service type from container name
    local svc_type="web"
    [[ "$container" =~ worker ]] && svc_type="worker"
    [[ "$container" =~ db|postgres ]] && svc_type="db"
    [[ "$container" =~ redis ]] && svc_type="redis"
    [[ "$container" =~ migrate ]] && svc_type="migrate"
    [[ "$container" =~ beat ]] && svc_type="beat"

    if (( mem_limit_bytes == 0 )); then
        fail "$app/$container ($svc_type): NO memory limit set!" \
             "Container can consume all 8GB RAM → OOM-kills other apps" \
             "Add 'deploy.resources.limits.memory: ${TARGET_WEB_MEM_MB}M' to docker-compose.prod.yml"
    else
        case "$svc_type" in
            web)
                (( mem_limit_mb <= TARGET_WEB_MEM_MB )) \
                    && pass "$app/$container ($svc_type): memory limit ${mem_limit_mb}M ✓" \
                    || warn "$app/$container ($svc_type): memory limit ${mem_limit_mb}M (recommended: ≤${TARGET_WEB_MEM_MB}M)"
                ;;
            db)
                (( mem_limit_mb <= TARGET_DB_MEM_MB )) \
                    && pass "$app/$container ($svc_type): memory limit ${mem_limit_mb}M ✓" \
                    || warn "$app/$container ($svc_type): memory limit ${mem_limit_mb}M (recommended: ≤${TARGET_DB_MEM_MB}M)"
                ;;
            redis)
                (( mem_limit_mb <= TARGET_REDIS_MEM_MB )) \
                    && pass "$app/$container ($svc_type): memory limit ${mem_limit_mb}M ✓" \
                    || warn "$app/$container ($svc_type): memory limit ${mem_limit_mb}M (recommended: ≤${TARGET_REDIS_MEM_MB}M)"
                ;;
            worker)
                (( mem_limit_mb <= TARGET_WORKER_MEM_MB )) \
                    && pass "$app/$container ($svc_type): memory limit ${mem_limit_mb}M ✓" \
                    || warn "$app/$container ($svc_type): memory limit ${mem_limit_mb}M (recommended: ≤${TARGET_WORKER_MEM_MB}M)"
                ;;
        esac
    fi

    # CPU limit
    local cpu_quota
    cpu_quota=$(echo "$inspect" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    data = data[0]
print(data.get('HostConfig', {}).get('CpuQuota', 0))
" 2>/dev/null || echo "0")

    (( cpu_quota > 0 )) \
        && pass "$app/$container ($svc_type): CPU limit set (quota=${cpu_quota})" \
        || fail "$app/$container ($svc_type): NO CPU limit set!" \
                "One busy container can starve all other apps on 4-core host" \
                "Add 'deploy.resources.limits.cpus: \"1.0\"' to docker-compose.prod.yml"

    # Restart policy
    local restart_policy
    restart_policy=$(echo "$inspect" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    data = data[0]
r = data.get('HostConfig', {}).get('RestartPolicy', {})
print(r.get('Name', 'unknown'))
" 2>/dev/null || echo "unknown")

    case "$svc_type" in
        migrate)
            [[ "$restart_policy" == "no" ]] \
                && pass "$app/$container (migrate): restart=no ✓" \
                || fail "$app/$container (migrate): restart='$restart_policy' (must be 'no')" \
                        "migrate service MUST exit after running — loops are dangerous"
            ;;
        web|worker|db|redis|beat)
            [[ "$restart_policy" == "unless-stopped" || "$restart_policy" == "always" ]] \
                && pass "$app/$container ($svc_type): restart=$restart_policy ✓" \
                || warn "$app/$container ($svc_type): restart='$restart_policy' (recommended: unless-stopped)"
            ;;
    esac

    # Logging driver
    local log_driver
    log_driver=$(echo "$inspect" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    data = data[0]
print(data.get('HostConfig', {}).get('LogConfig', {}).get('Type', 'unknown'))
" 2>/dev/null || echo "unknown")

    [[ "$log_driver" == "json-file" ]] \
        && pass "$app/$container ($svc_type): logging=json-file ✓" \
        || fail "$app/$container ($svc_type): logging='$log_driver' (expected: json-file)" \
                "" "Add logging.driver=json-file to docker-compose.prod.yml"

    # Log max-size configured?
    local log_maxsize
    log_maxsize=$(echo "$inspect" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    data = data[0]
opts = data.get('HostConfig', {}).get('LogConfig', {}).get('Config', {})
print(opts.get('max-size', 'NOT SET'))
" 2>/dev/null || echo "NOT SET")

    [[ "$log_maxsize" != "NOT SET" ]] \
        && pass "$app/$container ($svc_type): log max-size=$log_maxsize ✓" \
        || fail "$app/$container ($svc_type): log max-size NOT configured" \
                "Logs can fill disk! ($path)" \
                "Add logging.options.max-size: '10m' to docker-compose.prod.yml"
}

check_health_endpoint() {
    local app="$1" port="$2"

    local livez_status
    livez_status=$(curl -so /dev/null -w "%{http_code}" \
        --connect-timeout 3 --max-time 5 \
        "http://127.0.0.1:${port}/livez/" 2>/dev/null || echo "000")

    case "$livez_status" in
        200) pass "$app: /livez/ → HTTP 200 ✓" ;;
        000) warn "$app: /livez/ unreachable (port ${port})" "App may be down or port wrong" ;;
        *)   fail "$app: /livez/ → HTTP ${livez_status}" \
                  "Expected 200" "Check Django healthz.py and url routing" ;;
    esac

    local healthz_status
    healthz_status=$(curl -so /dev/null -w "%{http_code}" \
        --connect-timeout 3 --max-time 5 \
        "http://127.0.0.1:${port}/healthz/" 2>/dev/null || echo "000")

    case "$healthz_status" in
        200) pass "$app: /healthz/ → HTTP 200 (DB connected) ✓" ;;
        000) warn "$app: /healthz/ unreachable" ;;
        503) fail "$app: /healthz/ → HTTP 503 (DB not healthy!)" "" "Check PostgreSQL container" ;;
        *)   warn "$app: /healthz/ → HTTP ${healthz_status}" ;;
    esac
}

check_compose_compliance() {
    local app="$1" compose_file="$2"

    # ADR-022: no 'version:' key (deprecated in Compose v2)
    if grep -q "^version:" "$compose_file" 2>/dev/null; then
        warn "$app: compose file has deprecated 'version:' key" \
             "Remove per ADR-022 (Compose v2 ignores it)"
    else
        pass "$app: compose file has no deprecated 'version:' ✓"
    fi

    # ADR-022: env_file not environment: with vars
    if grep -qP "^\s+environment:" "$compose_file" 2>/dev/null; then
        local env_lines
        env_lines=$(grep -A5 "^\s+environment:" "$compose_file" | grep '\${' || true)
        if [[ -n "$env_lines" ]]; then
            fail "$app: uses 'environment: \${VAR}' interpolation" \
                 "ADR-022 FORBIDS this — use env_file: .env.prod only" \
                 "Replace environment: block with env_file: .env.prod"
        fi
    fi

    # Port bound to localhost only (ADR-022: 127.0.0.1:<PORT>)
    if grep -qP "^\s+- \"\d+:\d+\"" "$compose_file" 2>/dev/null; then
        fail "$app: port exposed without 127.0.0.1 binding!" \
             "Port is publicly accessible — security risk" \
             "Change '- \"PORT:8000\"' to '- \"127.0.0.1:PORT:8000\"'"
    else
        pass "$app: ports bound to 127.0.0.1 only ✓"
    fi

    # migrate service exists
    if grep -q "migrate:" "$compose_file" 2>/dev/null; then
        pass "$app: migrate service defined ✓"
    else
        warn "$app: no 'migrate' service in compose file" \
             "ADR-022 requires separate migrate service to prevent race conditions"
    fi

    # shm_size for db
    if grep -q "shm_size" "$compose_file" 2>/dev/null; then
        pass "$app: shm_size configured for PostgreSQL ✓"
    else
        warn "$app: no shm_size in compose file" \
             "Add shm_size: '128m' to db service (PostgreSQL shared memory)"
    fi
}

# ── 4. PostgreSQL Configuration ───────────────────────────────────────────────
check_postgresql() {
    log_section "4. PostgreSQL Configuration"

    for app in "${!APPS[@]}"; do
        [[ -n "$SINGLE_APP" && "$app" != "$SINGLE_APP" ]] && continue

        # Find postgres container for this app
        local pg_container
        pg_container=$(docker ps --format '{{.Names}}' 2>/dev/null \
            | grep -i "${app//-/_}.*db\|${app//-/_}.*postgres\|${app}.*db" \
            | head -1 || true)

        [[ -z "$pg_container" ]] && continue

        $JSON_MODE || echo -e "  ${BOLD}▶ $app${RESET}  ${DIM}(container: $pg_container)${RESET}"

        check_pg_setting "$pg_container" "$app" "random_page_cost"    "1.1" \
            "NVMe SSDs need 1.1, not default 4.0 — wrong value causes seq scans over index scans"

        check_pg_setting "$pg_container" "$app" "max_connections"     "50" \
            "Default 100 wastes RAM across 7 DBs; 7×50=350 connections total is sufficient"

        check_pg_setting "$pg_container" "$app" "checkpoint_completion_target" "0.9" \
            "Spreads checkpoint I/O — reduces latency spikes"

        check_pg_setting "$pg_container" "$app" "log_min_duration_statement" "200" \
            "Logs slow queries >200ms — essential for debugging"
    done
}

check_pg_setting() {
    local container="$1" app="$2" setting="$3" target="$4" detail="$5"

    local current
    current=$(docker exec "$container" \
        psql -U postgres -Atc "SHOW ${setting};" 2>/dev/null || echo "ERROR")

    if [[ "$current" == "ERROR" ]]; then
        warn "$app/postgres: cannot read ${setting} (psql error)"
        return
    fi

    # Normalize (strip spaces, trailing zeros)
    local cur_norm tgt_norm
    cur_norm=$(echo "$current" | tr -d ' ')
    tgt_norm=$(echo "$target"  | tr -d ' ')

    if [[ "$cur_norm" == "$tgt_norm" ]]; then
        pass "$app/postgres: ${setting} = ${current} ✓"
    else
        fail "$app/postgres: ${setting} = ${current} (target: ${target})" \
             "$detail" \
             "docker exec $container psql -U postgres -c \"ALTER SYSTEM SET ${setting} = '${target}'; SELECT pg_reload_conf();\""
    fi
}

# ── 5. Redis Configuration ────────────────────────────────────────────────────
check_redis() {
    log_section "5. Redis Configuration"

    for app in "${!APPS[@]}"; do
        [[ -n "$SINGLE_APP" && "$app" != "$SINGLE_APP" ]] && continue

        local redis_container
        redis_container=$(docker ps --format '{{.Names}}' 2>/dev/null \
            | grep -i "${app//-/_}.*redis\|${app}.*redis" \
            | head -1 || true)

        [[ -z "$redis_container" ]] && continue

        $JSON_MODE || echo -e "  ${BOLD}▶ $app${RESET}  ${DIM}(container: $redis_container)${RESET}"

        local maxmem_bytes
        maxmem_bytes=$(docker exec "$redis_container" \
            redis-cli CONFIG GET maxmemory 2>/dev/null | tail -1 || echo "0")

        local maxmem_mb=0
        [[ "$maxmem_bytes" =~ ^[0-9]+$ ]] && maxmem_mb=$(bytes_to_mb "$maxmem_bytes")

        if (( maxmem_mb == 0 )); then
            fail "$app/redis: maxmemory NOT configured!" \
                 "Redis will grow unbounded and OOM-kill the server" \
                 "Add '--maxmemory ${TARGET_REDIS_MAXMEM_MB}mb' to redis command in docker-compose.prod.yml"
        elif (( maxmem_mb <= TARGET_REDIS_MAXMEM_MB )); then
            pass "$app/redis: maxmemory = ${maxmem_mb}MB ✓"
        else
            warn "$app/redis: maxmemory = ${maxmem_mb}MB (recommended: ≤${TARGET_REDIS_MAXMEM_MB}MB)"
        fi

        local eviction
        eviction=$(docker exec "$redis_container" \
            redis-cli CONFIG GET maxmemory-policy 2>/dev/null | tail -1 || echo "unknown")

        [[ "$eviction" == "allkeys-lru" ]] \
            && pass "$app/redis: maxmemory-policy = allkeys-lru ✓" \
            || fail "$app/redis: maxmemory-policy = '$eviction' (expected: allkeys-lru)" \
                    "Wrong eviction policy can cause OOM instead of graceful key eviction" \
                    "Add '--maxmemory-policy allkeys-lru' to redis command"

        # Persistence check (should be disabled on prod for perf)
        local rdb_save
        rdb_save=$(docker exec "$redis_container" \
            redis-cli CONFIG GET save 2>/dev/null | tail -1 || echo "unknown")

        [[ -z "$rdb_save" || "$rdb_save" == '""' ]] \
            && pass "$app/redis: RDB persistence disabled ✓ (performance)" \
            || warn "$app/redis: RDB persistence enabled (save='$rdb_save')" \
                    "Disable with '--save \"\"' for better write performance"
    done
}

# ── 6. Gunicorn Configuration ─────────────────────────────────────────────────
check_gunicorn() {
    log_section "6. Gunicorn / Web Worker Configuration"

    for app in "${!APPS[@]}"; do
        [[ -n "$SINGLE_APP" && "$app" != "$SINGLE_APP" ]] && continue

        local web_container
        web_container=$(docker ps --format '{{.Names}}' 2>/dev/null \
            | grep -i "${app//-/_}.*web\|${app}.*web" \
            | head -1 || true)

        [[ -z "$web_container" ]] && continue

        # Get gunicorn command
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

        $JSON_MODE || echo -e "  ${BOLD}▶ $app${RESET}  ${DIM}(container: $web_container)${RESET}"

        # max-requests (memory leak protection)
        if echo "$cmd $env_vars" | grep -q "max.requests"; then
            pass "$app/web: --max-requests configured ✓ (memory leak protection)"
        else
            fail "$app/web: --max-requests NOT configured" \
                 "Workers never recycle → gradual memory leak over days" \
                 "Add GUNICORN_MAX_REQUESTS=1000 to .env.prod"
        fi

        # worker-class
        if echo "$cmd $env_vars" | grep -q "gthread"; then
            pass "$app/web: worker-class=gthread ✓ (optimal for HTMX I/O workloads)"
        elif echo "$cmd $env_vars" | grep -q "gevent\|uvicorn"; then
            pass "$app/web: async worker class configured ✓"
        else
            warn "$app/web: worker-class not gthread" \
                 "Default 'sync' workers less efficient for HTMX long-polling — consider gthread"
        fi

        # keep-alive
        if echo "$cmd $env_vars" | grep -q "keep.alive\|keepalive"; then
            pass "$app/web: --keep-alive configured ✓"
        else
            warn "$app/web: --keep-alive not configured" \
                 "Add --keep-alive 5 to reduce connection overhead with Nginx"
        fi

        # Actual worker count from process
        local worker_count
        worker_count=$(docker exec "$web_container" \
            sh -c "pgrep -c gunicorn 2>/dev/null || ps aux | grep -c gunicorn" \
            2>/dev/null || echo "?")
        $JSON_MODE || echo -e "     ${DIM}Active gunicorn processes: ${worker_count}${RESET}"
    done
}

# ── 7. Disk & System Health ───────────────────────────────────────────────────
check_system_health() {
    log_section "7. Disk & System Health"

    # Disk usage
    local disk_usage
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')

    if (( disk_usage < 70 )); then
        pass "Root disk usage: ${disk_usage}% ✓"
    elif (( disk_usage < 85 )); then
        warn "Root disk usage: ${disk_usage}% (warning threshold: 70%)" \
             "Run: docker system prune -af --filter 'until=24h'"
    else
        fail "Root disk usage: ${disk_usage}% (critical!)" \
             "Server may fill up — Docker logs or images consuming space" \
             "docker system prune -af && journalctl --vacuum-time=7d"
    fi

    # Swap usage
    local swap_total swap_used
    swap_total=$(free -m | awk '/Swap/{print $2}')
    swap_used=$(free -m  | awk '/Swap/{print $3}')

    if (( swap_total == 0 )); then
        warn "No swap configured" \
             "Consider 2GB swap as OOM safety net: fallocate -l 2G /swapfile"
    elif (( swap_used > 0 )); then
        fail "Swap in use: ${swap_used}MB / ${swap_total}MB" \
             "Active swapping = performance degradation — check memory limits" \
             "Investigate with: docker stats --no-stream"
    else
        pass "Swap configured (${swap_total}MB), not in use ✓"
    fi

    # Memory pressure
    local mem_available_mb
    mem_available_mb=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
    if (( mem_available_mb > 512 )); then
        pass "Available RAM: ${mem_available_mb}MB ✓"
    elif (( mem_available_mb > 256 )); then
        warn "Available RAM low: ${mem_available_mb}MB" "Consider reviewing memory limits"
    else
        fail "Available RAM critically low: ${mem_available_mb}MB!" \
             "OOM kills imminent — reduce container memory limits immediately"
    fi

    # Load average vs CPUs
    local load1 ncpu
    load1=$(awk '{print $1}' /proc/loadavg)
    ncpu=$(nproc)
    local load_pct
    load_pct=$(python3 -c "print(int(float('$load1') / $ncpu * 100))")

    if (( load_pct < 70 )); then
        pass "Load average: ${load1} on ${ncpu} CPUs (${load_pct}%) ✓"
    elif (( load_pct < 90 )); then
        warn "Load average: ${load1} on ${ncpu} CPUs (${load_pct}%)" "System under pressure"
    else
        fail "Load average: ${load1} on ${ncpu} CPUs (${load_pct}%)" \
             "CPU saturation — check for runaway containers" \
             "docker stats --no-stream"
    fi

    # OOM killer events
    local oom_count
    oom_count=$(dmesg 2>/dev/null | grep -c "Out of memory" || echo "0")
    (( oom_count == 0 )) \
        && pass "No OOM killer events in dmesg ✓" \
        || fail "OOM killer triggered ${oom_count} time(s) in dmesg!" \
                "Containers were killed — check logs and reduce memory limits" \
                "journalctl -k | grep -i 'killed process'"
}

# ── 8. GitHub Actions Runner ──────────────────────────────────────────────────
check_runner() {
    log_section "8. Self-Hosted GitHub Actions Runner"

    # Check if runner is registered
    local runner_svc
    runner_svc=$(systemctl is-active actions.runner.* 2>/dev/null \
        || systemctl is-active github-runner 2>/dev/null \
        || echo "not-found")

    case "$runner_svc" in
        active)   pass "GitHub Actions Runner: active ✓" ;;
        inactive) warn "GitHub Actions Runner: inactive (stopped)" "Start: systemctl start actions.runner.*" ;;
        *)        warn "GitHub Actions Runner: not found as systemd service" \
                       "May be running as Docker container or not configured" ;;
    esac

    # Check runner container
    local runner_container
    runner_container=$(docker ps --format '{{.Names}}' | grep -i runner | head -1 || true)
    if [[ -n "$runner_container" ]]; then
        pass "Runner container running: $runner_container ✓"

        # CPU limit on runner
        local runner_cpu
        runner_cpu=$(docker inspect "$runner_container" 2>/dev/null \
            | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list): data = data[0]
print(data.get('HostConfig', {}).get('CpuQuota', 0))
" 2>/dev/null || echo "0")

        (( runner_cpu > 0 )) \
            && pass "Runner CPU limit: set (quota=${runner_cpu}) ✓" \
            || warn "Runner: no CPU limit" \
                    "Build jobs can saturate CPU and degrade PROD apps on same host"
    fi
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
    local total=$(( PASS + WARN + FAIL ))

    if $JSON_MODE; then
        python3 -c "
import json, sys
findings = [
$(IFS=,; echo "${FINDINGS[*]}")
]
summary = {
    'version': '${SCRIPT_VERSION}',
    'date': '$(date -Iseconds)',
    'hostname': '$(hostname)',
    'totals': {'pass': ${PASS}, 'warn': ${WARN}, 'fail': ${FAIL}, 'total': ${total}},
    'findings': findings
}
print(json.dumps(summary, indent=2))
"
        return
    fi

    echo ""
    echo -e "${BOLD}══════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}  AUDIT SUMMARY — $(hostname) — $(date '+%Y-%m-%d %H:%M')${RESET}"
    echo -e "${BOLD}══════════════════════════════════════════════${RESET}"
    echo ""
    printf "  ${GREEN}✔ PASS${RESET}  %3d\n" "$PASS"
    printf "  ${YELLOW}⚠ WARN${RESET}  %3d\n" "$WARN"
    printf "  ${RED}✘ FAIL${RESET}  %3d\n" "$FAIL"
    echo "  ─────────────"
    printf "    Total   %3d checks\n" "$total"
    echo ""

    if (( FAIL == 0 && WARN == 0 )); then
        echo -e "  ${GREEN}${BOLD}★ Perfect score! All checks passed.${RESET}"
    elif (( FAIL == 0 )); then
        echo -e "  ${YELLOW}${BOLD}Good shape — address warnings when possible.${RESET}"
    elif (( FAIL <= 3 )); then
        echo -e "  ${RED}${BOLD}Action needed — ${FAIL} critical issue(s) to fix.${RESET}"
    else
        echo -e "  ${RED}${BOLD}⚠ ${FAIL} critical issues — platform stability at risk!${RESET}"
    fi

    if $FIX_MODE; then
        echo ""
        echo -e "  ${CYAN}--fix mode was active: safe sysctl fixes were applied.${RESET}"
        echo -e "  ${DIM}Restart Docker daemon to apply daemon.json changes.${RESET}"
    else
        echo ""
        echo -e "  ${DIM}Tip: run with --fix to auto-apply safe sysctl corrections.${RESET}"
        echo -e "  ${DIM}     run with --json for CI/monitoring integration.${RESET}"
    fi
    echo ""

    # Exit code for CI integration
    (( FAIL > 0 )) && exit 2
    (( WARN > 0 )) && exit 1
    exit 0
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    $JSON_MODE || cat << 'BANNER'

  ╔══════════════════════════════════════════════╗
  ║  BF Agent Platform — Tuning Audit v1.0.0    ║
  ║  Hetzner / Docker Performance & Reliability  ║
  ╚══════════════════════════════════════════════╝
BANNER

    check_prerequisites
    check_docker_daemon
    check_sysctl
    check_all_apps
    check_postgresql
    check_redis
    check_gunicorn
    check_system_health
    check_runner
    print_summary
}

main
