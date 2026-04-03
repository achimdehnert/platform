#!/usr/bin/env bash
# ============================================================================
# server-setup.sh — Production Server Bootstrap
# ============================================================================
#
# Runs LOCALLY, pushes configuration to the production server via SSH.
# Configures git, SSH deploy keys, and repo directories on the server.
#
# Prerequisites:
#   - platform-setup.sh has been run (SSH keys + config exist)
#   - SSH access to server works: ssh prod echo OK
#
# Usage:
#   ./server-setup.sh              # Full server setup
#   ./server-setup.sh --dry-run    # Show what would be done
#
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF_FILE="${SCRIPT_DIR}/platform.conf"

if [[ ! -f "$CONF_FILE" ]]; then
    echo "ERROR: platform.conf not found at $CONF_FILE"
    exit 1
fi

# shellcheck source=platform.conf
source "$CONF_FILE"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

_CHANGES=0
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
err()   { echo -e "\033[1;31m[ERROR]\033[0m $*"; }
change(){ echo -e "\033[1;36m[SET]\033[0m   $*"; _CHANGES=$((_CHANGES + 1)); }

remote() {
    if $DRY_RUN; then
        echo -e "\033[0;90m  [dry-run] ssh ${SERVER_ALIAS}: $*\033[0m"
        return 0
    fi
    ssh -o ConnectTimeout=10 -o BatchMode=yes "${SERVER_ALIAS}" "$@"
}

preflight() {
    info "─── Preflight Checks ────────────────────────────"
    if $DRY_RUN; then
        ok "Dry-run mode — skipping SSH connectivity check"
        return
    fi
    echo -n "  Testing SSH to ${SERVER_ALIAS}... "
    if ssh -o ConnectTimeout=5 -o BatchMode=yes "${SERVER_ALIAS}" "echo OK" 2>/dev/null | grep -q "OK"; then
        ok "SSH connection works"
    else
        err "Cannot SSH to ${SERVER_ALIAS}. Run platform-setup.sh first."
        exit 1
    fi
}

# ============================================================================
# PHASE 1: Git Config on Server
# ============================================================================

setup_server_git() {
    info "─── Server Git Config ───────────────────────────"
    _set_remote_git "user.name" "$GIT_USER_NAME"
    _set_remote_git "user.email" "$GIT_USER_EMAIL"
    _set_remote_git "pull.rebase" "true"
    _set_remote_git "rebase.autoStash" "true"
    _set_remote_git "init.defaultBranch" "main"
    _set_remote_git "push.autoSetupRemote" "true"
    _set_remote_git "push.default" "current"
    _set_remote_git "fetch.prune" "true"
    _set_remote_git "rerere.enabled" "true"

    for entry in "${PLATFORM_REPOS[@]}"; do
        local slug="${entry%%|*}"
        local rest="${entry#*|}"
        local server_path="${rest%%|*}"
        if [[ "$server_path" != "NONE" ]]; then
            remote "git config --global --add safe.directory '$server_path'" 2>/dev/null || true
            ok "safe.directory: $server_path"
        fi
    done
}

_set_remote_git() {
    local key="$1" value="$2"
    local current
    current=$(remote "git config --global --get '$key' 2>/dev/null || echo ''")
    if [[ "$current" == "$value" ]]; then
        ok "Server git $key = $value"
    else
        change "Server git $key: '${current:-<unset>}' → '$value'"
        remote "git config --global '$key' '$value'"
    fi
}

# ============================================================================
# PHASE 2: GitHub Deploy Key on Server
# ============================================================================

setup_server_deploy_key() {
    info "─── Server GitHub Deploy Key ────────────────────"
    local has_key
    has_key=$(remote "test -f ~/.ssh/github_deploy_ed25519 && echo yes || echo no")
    if [[ "$has_key" == "yes" ]]; then
        ok "Server deploy key exists"
    else
        change "Generating GitHub deploy key on server"
        remote "ssh-keygen -t ed25519 -C 'deploy@${SERVER_HOST}' -f ~/.ssh/github_deploy_ed25519 -N ''"
        echo ""
        warn ">>> Add this DEPLOY KEY to GitHub → Repo Settings → Deploy Keys:"
        echo ""
        if ! $DRY_RUN; then
            remote "cat ~/.ssh/github_deploy_ed25519.pub"
        fi
        echo ""
    fi

    local has_config
    has_config=$(remote "grep -c 'Host github.com' ~/.ssh/config 2>/dev/null || echo 0")
    if [[ "$has_config" -gt 0 ]]; then
        ok "Server SSH config for github.com exists"
    else
        change "Adding GitHub SSH config on server"
        remote "mkdir -p ~/.ssh && cat >> ~/.ssh/config" <<'SSHEOF'

# GitHub Deploy Key (managed by platform server-setup.sh)
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_deploy_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
SSHEOF
        remote "chmod 600 ~/.ssh/config"
    fi

    if ! $DRY_RUN; then
        echo -n "  Testing GitHub from server... "
        local gh_out
        gh_out=$(remote "ssh -T git@github.com 2>&1 || true")
        if echo "$gh_out" | grep -qE "successfully authenticated|Hi "; then
            ok "Server → GitHub SSH works"
        else
            warn "Server → GitHub SSH not working yet (deploy key might not be added)"
        fi
    fi
}

# ============================================================================
# PHASE 3: Repo Directories
# ============================================================================

setup_server_repos() {
    info "─── Server Repo Directories ─────────────────────"
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
            local exists
            exists=$(remote "test -d '$server_path/.git' && echo yes || echo no")
            if [[ "$exists" == "yes" ]]; then
                ok "$slug → $server_path (git-clone)"
                local current_url
                current_url=$(remote "cd '$server_path' && git remote get-url origin 2>/dev/null || echo ''")
                local expected_url="git@github.com:${GITHUB_USER}/${slug}.git"
                if [[ "$current_url" == *"https://"* ]]; then
                    change "$slug: Switching remote from HTTPS to SSH"
                    remote "cd '$server_path' && git remote set-url origin '$expected_url'"
                fi
            else
                warn "$slug → $server_path (not cloned)"
                info "  To clone: ssh ${SERVER_ALIAS} 'git clone git@github.com:${GITHUB_USER}/${slug}.git $server_path'"
            fi
        else
            local exists
            exists=$(remote "test -d '$server_path' && echo yes || echo no")
            if [[ "$exists" == "yes" ]]; then
                ok "$slug → $server_path ($deploy_model)"
            else
                warn "$slug → $server_path missing ($deploy_model)"
            fi
        fi
    done
}

# ============================================================================
# PHASE 4: Docker / GHCR Login
# ============================================================================

setup_server_docker() {
    info "─── Server Docker / GHCR ────────────────────────"
    local docker_ok
    docker_ok=$(remote "docker info >/dev/null 2>&1 && echo yes || echo no")
    if [[ "$docker_ok" == "yes" ]]; then
        ok "Docker is running"
    else
        warn "Docker not available on server"
        return
    fi
    local ghcr_ok
    ghcr_ok=$(remote "cat ~/.docker/config.json 2>/dev/null | grep -c 'ghcr.io' || echo 0")
    if [[ "$ghcr_ok" -gt 0 ]]; then
        ok "GHCR login configured"
    else
        warn "GHCR not logged in. To configure:"
        echo "    ssh ${SERVER_ALIAS}"
        echo "    echo \$GITHUB_TOKEN | docker login ghcr.io -u ${GITHUB_USER} --password-stdin"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║       Platform Bootstrap — Production Server         ║"
    echo "║       Target: ${SERVER_USER}@${SERVER_HOST}                  ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    if $DRY_RUN; then warn "DRY RUN — no changes will be made"; echo ""; fi

    preflight; echo ""
    setup_server_git; echo ""
    setup_server_deploy_key; echo ""
    setup_server_repos; echo ""
    setup_server_docker; echo ""

    echo "─── Summary ───────────────────────────────────────────"
    if [[ $_CHANGES -eq 0 ]]; then
        ok "Server already configured — no changes needed."
    else
        info "$_CHANGES change(s) applied to server."
    fi
    echo ""
}

main
