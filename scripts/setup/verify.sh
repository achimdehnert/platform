#!/usr/bin/env bash
# ============================================================================
# verify.sh — Platform Configuration Smoke Test
# ============================================================================
#
# Checks if everything is correctly configured on the current machine.
# Outputs a clear report. No changes are made.
#
# Usage:
#   ./verify.sh                  # Full check (local + server)
#   ./verify.sh --local-only     # Skip server checks
#   ./verify.sh --json           # Output as JSON (for CI)
#
# Exit codes: 0 = all passed, 1 = one or more failed
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF_FILE="${SCRIPT_DIR}/platform.conf"

if [[ ! -f "$CONF_FILE" ]]; then
    echo "ERROR: platform.conf not found at $CONF_FILE"
    exit 1
fi

source "$CONF_FILE"

LOCAL_ONLY=false
JSON_OUTPUT=false

for arg in "$@"; do
    case "$arg" in
        --local-only) LOCAL_ONLY=true ;;
        --json)       JSON_OUTPUT=true ;;
        --help|-h)    echo "Usage: $0 [--local-only] [--json]"; exit 0 ;;
    esac
done

_PASS=0; _FAIL=0; _WARN=0; _RESULTS=()

check_pass() {
    _PASS=$((_PASS + 1)); _RESULTS+=("PASS|$1")
    if ! $JSON_OUTPUT; then echo -e "  \033[1;32m[PASS]\033[0m $1"; fi
}
check_fail() {
    _FAIL=$((_FAIL + 1)); _RESULTS+=("FAIL|$1")
    if ! $JSON_OUTPUT; then echo -e "  \033[1;31m[FAIL]\033[0m $1"; fi
}
check_warn() {
    _WARN=$((_WARN + 1)); _RESULTS+=("WARN|$1")
    if ! $JSON_OUTPUT; then echo -e "  \033[1;33m[WARN]\033[0m $1"; fi
}
section() {
    if ! $JSON_OUTPUT; then echo ""; echo -e "\033[1;34m-- $1 --\033[0m"; fi
}

# CHECK 1: SSH Keys
check_ssh_keys() {
    section "SSH Keys"
    local github_key="${SSH_DIR}/${SSH_KEY_GITHUB}"
    local server_key="${SSH_DIR}/${SSH_KEY_SERVER}"

    if [[ -f "$github_key" ]]; then check_pass "GitHub key exists: $(basename "$github_key")"
    else check_fail "GitHub key missing: $github_key"; fi

    if [[ -f "$server_key" ]]; then check_pass "Server key exists: $(basename "$server_key")"
    else check_fail "Server key missing: $server_key"; fi

    for keyfile in "$github_key" "$server_key"; do
        if [[ -f "$keyfile" ]]; then
            local perms
            perms=$(stat -c "%a" "$keyfile" 2>/dev/null || stat -f "%Lp" "$keyfile" 2>/dev/null)
            if [[ "$perms" == "600" ]]; then check_pass "$(basename "$keyfile") permissions: 600"
            else check_fail "$(basename "$keyfile") permissions: $perms (expected 600)"; fi
        fi
    done

    local dir_perms
    dir_perms=$(stat -c "%a" "$SSH_DIR" 2>/dev/null || stat -f "%Lp" "$SSH_DIR" 2>/dev/null)
    if [[ "$dir_perms" == "700" ]]; then check_pass "~/.ssh permissions: 700"
    else check_fail "~/.ssh permissions: $dir_perms (expected 700)"; fi
}

# CHECK 2: SSH Config
check_ssh_config() {
    section "SSH Config"
    local ssh_config="${SSH_DIR}/config"
    if [[ ! -f "$ssh_config" ]]; then check_fail "SSH config missing"; return; fi
    check_pass "SSH config exists"
    if grep -q "platform-setup-begin" "$ssh_config"; then check_pass "Platform block present"
    else check_fail "Platform block missing"; fi
    if grep -q "Host github.com" "$ssh_config"; then check_pass "GitHub host configured"
    else check_fail "GitHub host not in SSH config"; fi
    if grep -q "Host ${SERVER_ALIAS}" "$ssh_config"; then check_pass "Server alias '${SERVER_ALIAS}' configured"
    else check_fail "Server alias '${SERVER_ALIAS}' not in SSH config"; fi
}

# CHECK 3: Git Config
check_git_config() {
    section "Git Config"
    local name; name=$(git config --global user.name 2>/dev/null || echo "")
    if [[ "$name" == "$GIT_USER_NAME" ]]; then check_pass "git user.name = $GIT_USER_NAME"
    else check_fail "git user.name = '$name' (expected '$GIT_USER_NAME')"; fi

    local email; email=$(git config --global user.email 2>/dev/null || echo "")
    if [[ "$email" == "$GIT_USER_EMAIL" ]]; then check_pass "git user.email = $GIT_USER_EMAIL"
    else check_fail "git user.email = '$email' (expected '$GIT_USER_EMAIL')"; fi

    case "$GIT_PULL_STRATEGY" in
        rebase)
            local pr; pr=$(git config --global pull.rebase 2>/dev/null || echo "")
            if [[ "$pr" == "true" ]]; then check_pass "git pull.rebase = true"
            else check_fail "git pull.rebase = '$pr' (expected 'true')"; fi
            local as; as=$(git config --global rebase.autoStash 2>/dev/null || echo "")
            if [[ "$as" == "true" ]]; then check_pass "git rebase.autoStash = true"
            else check_fail "git rebase.autoStash = '$as' (expected 'true')"; fi
            ;;
    esac

    local db; db=$(git config --global init.defaultBranch 2>/dev/null || echo "")
    if [[ "$db" == "$GIT_DEFAULT_BRANCH" ]]; then check_pass "git init.defaultBranch = $GIT_DEFAULT_BRANCH"
    else check_fail "git init.defaultBranch = '$db' (expected '$GIT_DEFAULT_BRANCH')"; fi

    for entry in "${GIT_EXTRAS[@]}"; do
        local key="${entry%%|*}" expected="${entry#*|}"
        local actual; actual=$(git config --global "$key" 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then check_pass "git $key = $expected"
        else check_warn "git $key = '$actual' (expected '$expected')"; fi
    done
}

# CHECK 4: Connectivity
check_connectivity() {
    section "Connectivity"
    local gh_out
    gh_out="$(ssh -T -o ConnectTimeout=5 git@github.com 2>&1 || true)"
    if echo "$gh_out" | grep -qE "successfully authenticated|Hi "; then check_pass "GitHub SSH: authenticated"
    else check_fail "GitHub SSH: not authenticated"; fi

    if $LOCAL_ONLY; then check_warn "Server checks skipped (--local-only)"; return; fi

    if ssh -o ConnectTimeout=5 -o BatchMode=yes "${SERVER_ALIAS}" "echo OK" 2>/dev/null | grep -q "OK"; then
        check_pass "Server SSH (${SERVER_ALIAS}): connected"
    else check_fail "Server SSH (${SERVER_ALIAS}): connection failed"; fi

    if ssh -o ConnectTimeout=5 -o BatchMode=yes "${SERVER_HOST}" "echo OK" 2>/dev/null | grep -q "OK"; then
        check_pass "Server SSH (${SERVER_HOST}): connected"
    else check_fail "Server SSH (${SERVER_HOST}): connection failed"; fi
}

# CHECK 5: Server-side
check_server() {
    if $LOCAL_ONLY; then return; fi
    section "Server Configuration"
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${SERVER_ALIAS}" "echo OK" 2>/dev/null | grep -q "OK"; then
        check_fail "Cannot reach server"; return
    fi
    local srv_name
    srv_name=$(ssh "${SERVER_ALIAS}" "git config --global user.name 2>/dev/null || echo ''" 2>/dev/null)
    if [[ "$srv_name" == "$GIT_USER_NAME" ]]; then check_pass "Server git user.name = $GIT_USER_NAME"
    else check_fail "Server git user.name = '$srv_name' (expected '$GIT_USER_NAME')"; fi

    local dk; dk=$(ssh "${SERVER_ALIAS}" "test -f ~/.ssh/github_deploy_ed25519 && echo yes || echo no" 2>/dev/null)
    if [[ "$dk" == "yes" ]]; then check_pass "Server deploy key exists"
    else check_warn "Server deploy key missing (run server-setup.sh)"; fi

    local doc; doc=$(ssh "${SERVER_ALIAS}" "docker info >/dev/null 2>&1 && echo yes || echo no" 2>/dev/null)
    if [[ "$doc" == "yes" ]]; then check_pass "Server Docker running"
    else check_warn "Server Docker not available"; fi

    for entry in "${PLATFORM_REPOS[@]}"; do
        local slug="${entry%%|*}"
        local rest="${entry#*|}"
        local server_path="${rest%%|*}"
        rest="${rest#*|}"
        local branch="${rest%%|*}"
        local deploy_model="${rest#*|}"
        if [[ "$server_path" == "NONE" ]]; then continue; fi
        if [[ "$deploy_model" == "none" ]]; then continue; fi
        if [[ "$deploy_model" == "git-clone" ]]; then
            local ex; ex=$(ssh "${SERVER_ALIAS}" "test -d '$server_path/.git' && echo yes || echo no" 2>/dev/null)
            if [[ "$ex" == "yes" ]]; then check_pass "Repo $slug -> $server_path (git-clone)"
            else check_warn "Repo $slug not found at $server_path"; fi
        else
            local ex; ex=$(ssh "${SERVER_ALIAS}" "test -d '$server_path' && echo yes || echo no" 2>/dev/null)
            if [[ "$ex" == "yes" ]]; then check_pass "Repo $slug -> $server_path ($deploy_model)"
            else check_warn "Repo $slug: $server_path missing ($deploy_model)"; fi
        fi
    done
}

output_json() {
    echo "{"
    echo "  \"passed\": $_PASS,"
    echo "  \"failed\": $_FAIL,"
    echo "  \"warnings\": $_WARN,"
    echo "  \"success\": $([ $_FAIL -eq 0 ] && echo "true" || echo "false"),"
    echo "  \"checks\": ["
    local first=true
    for result in "${_RESULTS[@]}"; do
        local status="${result%%|*}" message="${result#*|}"
        if $first; then first=false; else echo ","; fi
        printf '    {"status": "%s", "message": "%s"}' "$status" "$message"
    done
    echo ""
    echo "  ]"
    echo "}"
}

output_summary() {
    echo ""
    echo "======================================================="
    echo -e "  \033[1;32mPassed: $_PASS\033[0m    \033[1;31mFailed: $_FAIL\033[0m    \033[1;33mWarnings: $_WARN\033[0m"
    echo "======================================================="
    echo ""
    if [[ $_FAIL -eq 0 ]]; then echo -e "  \033[1;32mAll critical checks passed!\033[0m"
    else echo -e "  \033[1;31m$_FAIL check(s) failed. Run platform-setup.sh to fix.\033[0m"; fi
    echo ""
}

main() {
    if ! $JSON_OUTPUT; then
        echo ""
        echo "Platform Configuration Verify"
        echo "============================="
    fi
    check_ssh_keys
    check_ssh_config
    check_git_config
    check_connectivity
    check_server
    if $JSON_OUTPUT; then output_json; else output_summary; fi
    [[ $_FAIL -eq 0 ]] && exit 0 || exit 1
}

main
