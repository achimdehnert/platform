#!/usr/bin/env bash
# ============================================================================
# platform-setup.sh — Dev Machine Bootstrap (WSL / Linux / macOS)
# ============================================================================
#
# Brings a developer machine into a consistent, deployment-ready state.
# Idempotent — safe to run multiple times. Never overwrites existing keys.
#
# Usage:
#   cd platform/scripts/setup
#   chmod +x platform-setup.sh
#   ./platform-setup.sh              # Full setup
#   ./platform-setup.sh --git-only   # Only git config
#   ./platform-setup.sh --ssh-only   # Only SSH setup
#   ./platform-setup.sh --dry-run    # Show what would be done
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
GIT_ONLY=false
SSH_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)  DRY_RUN=true ;;
        --git-only) GIT_ONLY=true ;;
        --ssh-only) SSH_ONLY=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--git-only] [--ssh-only]"
            exit 0
            ;;
        *) echo "Unknown flag: $arg"; exit 1 ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────────

_CHANGES=0

info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
err()   { echo -e "\033[1;31m[ERROR]\033[0m $*"; }
skip()  { echo -e "\033[0;90m[SKIP]\033[0m  $*"; }
change(){ echo -e "\033[1;36m[SET]\033[0m   $*"; _CHANGES=$((_CHANGES + 1)); }

run_or_dry() {
    if $DRY_RUN; then
        echo -e "\033[0;90m  [dry-run] $*\033[0m"
    else
        bash -c "$*"
    fi
}

detect_env() {
    if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "wsl"
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        echo "macos"
    else
        echo "linux"
    fi
}

ENV_TYPE=$(detect_env)
info "Environment detected: $ENV_TYPE"

# ============================================================================
# PHASE 1: SSH Key Setup
# ============================================================================

setup_ssh_keys() {
    info "─── SSH Key Setup ───────────────────────────────"

    if [[ ! -d "$SSH_DIR" ]]; then
        change "Creating $SSH_DIR"
        run_or_dry "mkdir -p '$SSH_DIR' && chmod 700 '$SSH_DIR'"
    fi

    local dir_perms
    dir_perms=$(stat -c "%a" "$SSH_DIR" 2>/dev/null || stat -f "%Lp" "$SSH_DIR" 2>/dev/null)
    if [[ "$dir_perms" != "700" ]]; then
        change "Fixing $SSH_DIR permissions: $dir_perms → 700"
        run_or_dry "chmod 700 '$SSH_DIR'"
    fi

    local github_key="${SSH_DIR}/${SSH_KEY_GITHUB}"
    if [[ -f "$github_key" ]]; then
        ok "GitHub key exists: $github_key"
    else
        change "Generating GitHub SSH key: $github_key"
        run_or_dry "ssh-keygen -t $SSH_KEY_TYPE -C '${GIT_USER_EMAIL}' -f '$github_key' -N ''"
        echo ""
        warn ">>> Add this public key to GitHub → Settings → SSH Keys:"
        echo ""
        if ! $DRY_RUN && [[ -f "${github_key}.pub" ]]; then
            cat "${github_key}.pub"
        fi
        echo ""
    fi

    local server_key="${SSH_DIR}/${SSH_KEY_SERVER}"
    if [[ -f "$server_key" ]]; then
        ok "Server key exists: $server_key"
    else
        change "Generating Server SSH key: $server_key"
        run_or_dry "ssh-keygen -t $SSH_KEY_TYPE -C '${GIT_USER_EMAIL}-server' -f '$server_key' -N ''"
        echo ""
        warn ">>> Add this public key to server authorized_keys:"
        echo "    ssh-copy-id -i ${server_key}.pub ${SERVER_USER}@${SERVER_HOST}"
        echo ""
    fi

    for keyfile in "$github_key" "$server_key"; do
        if [[ -f "$keyfile" ]]; then
            local kperms
            kperms=$(stat -c "%a" "$keyfile" 2>/dev/null || stat -f "%Lp" "$keyfile" 2>/dev/null)
            if [[ "$kperms" != "600" ]]; then
                change "Fixing permissions on $(basename "$keyfile"): $kperms → 600"
                run_or_dry "chmod 600 '$keyfile'"
            fi
        fi
        if [[ -f "${keyfile}.pub" ]]; then
            run_or_dry "chmod 644 '${keyfile}.pub'"
        fi
    done
}

# ============================================================================
# PHASE 2: SSH Config
# ============================================================================

setup_ssh_config() {
    info "─── SSH Config ──────────────────────────────────"

    local ssh_config="${SSH_DIR}/config"
    local marker_start="# >>> platform-setup-begin >>>"
    local marker_end="# <<< platform-setup-end <<<"

    local server_blocks=""
    for entry in "${SERVERS[@]}"; do
        local alias="${entry%%|*}"
        local rest="${entry#*|}"
        local host="${rest%%|*}"
        rest="${rest#*|}"
        local user="${rest%%|*}"
        local port="${rest#*|}"

        server_blocks+="\n# Server: ${alias}\nHost ${alias}\n    HostName ${host}\n    User ${user}\n    Port ${port}\n    IdentityFile ${SSH_DIR}/${SSH_KEY_SERVER}\n    IdentitiesOnly yes\n    AddKeysToAgent yes\n    ServerAliveInterval 60\n    ServerAliveCountMax 3\n    ConnectTimeout 10\n\n# Direct IP: ${host}\nHost ${host}\n    User ${user}\n    Port ${port}\n    IdentityFile ${SSH_DIR}/${SSH_KEY_SERVER}\n    IdentitiesOnly yes\n    ServerAliveInterval 60\n    ServerAliveCountMax 3\n    ConnectTimeout 10\n"
    done

    local config_block
    config_block=$(printf '%s\n%s\n\n%s\n%s\n%s\n%s\n%s\n%b\n%s' \
        "$marker_start" \
        "# Managed by platform-setup.sh — do not edit manually." \
        "# GitHub" \
        "Host github.com" \
        "    HostName github.com" \
        "    User git" \
        "    IdentityFile ${SSH_DIR}/${SSH_KEY_GITHUB}" \
        "$server_blocks" \
        "$marker_end")

    if [[ -f "$ssh_config" ]] && grep -q "$marker_start" "$ssh_config"; then
        local tmp_config
        tmp_config=$(mktemp)
        awk -v start="$marker_start" -v end="$marker_end" '
            $0 == start { skip=1; next }
            $0 == end   { skip=0; next }
            !skip       { print }
        ' "$ssh_config" > "$tmp_config"
        echo "$config_block" >> "$tmp_config"
        if ! diff -q "$ssh_config" "$tmp_config" >/dev/null 2>&1; then
            change "Updating SSH config (platform block)"
            run_or_dry "cp '$tmp_config' '$ssh_config'"
        else
            ok "SSH config is up to date"
        fi
        rm -f "$tmp_config"
    elif [[ -f "$ssh_config" ]]; then
        change "Adding platform block to SSH config"
        if ! $DRY_RUN; then
            echo "" >> "$ssh_config"
            echo "$config_block" >> "$ssh_config"
        fi
    else
        change "Creating SSH config"
        if ! $DRY_RUN; then
            echo "$config_block" > "$ssh_config"
        fi
    fi
    run_or_dry "chmod 600 '$ssh_config'"
}

# ============================================================================
# PHASE 3: SSH Agent (WSL-specific)
# ============================================================================

setup_ssh_agent() {
    info "─── SSH Agent ───────────────────────────────────"
    if [[ "$ENV_TYPE" != "wsl" ]]; then
        skip "SSH agent auto-start: not WSL, skipping"
        return
    fi
    local bashrc="${HOME}/.bashrc"
    local marker="# platform-setup: ssh-agent"
    if grep -q "$marker" "$bashrc" 2>/dev/null; then
        ok "SSH agent auto-start already in .bashrc"
        return
    fi
    change "Adding SSH agent auto-start to .bashrc"
    if ! $DRY_RUN; then
        cat >> "$bashrc" <<'AGENT_EOF'

# platform-setup: ssh-agent
if [ -z "$SSH_AUTH_SOCK" ]; then
    eval "$(ssh-agent -s)" >/dev/null 2>&1
fi
for _key in ~/.ssh/*_ed25519; do
    [ -f "$_key" ] && ssh-add "$_key" 2>/dev/null
done
unset _key
AGENT_EOF
    fi
}

# ============================================================================
# PHASE 4: Git Config
# ============================================================================

setup_git_config() {
    info "─── Git Config ──────────────────────────────────"
    _set_git "user.name" "$GIT_USER_NAME"
    _set_git "user.email" "$GIT_USER_EMAIL"

    case "$GIT_PULL_STRATEGY" in
        rebase)
            _set_git "pull.rebase" "true"
            _set_git "rebase.autoStash" "true"
            ;;
        ff-only) _set_git "pull.ff" "only" ;;
        merge)   _set_git "pull.rebase" "false" ;;
    esac

    _set_git "init.defaultBranch" "$GIT_DEFAULT_BRANCH"

    for entry in "${GIT_EXTRAS[@]}"; do
        local key="${entry%%|*}"
        local value="${entry#*|}"
        _set_git "$key" "$value"
    done

    _set_git "core.sshCommand" "ssh"

    # Editor — environment-dependent
    if [[ "$(hostname)" == *"$SERVER_HOST"* ]] || [[ "$ENV_TYPE" == "linux" && ! -v DISPLAY ]]; then
        _set_git "core.editor" "$GIT_EDITOR_SERVER"
    elif command -v code &>/dev/null; then
        _set_git "core.editor" "$GIT_EDITOR_DEV"
    else
        ok "core.editor: not set (using \$EDITOR → \$VISUAL → vi fallback)"
    fi
}

_set_git() {
    local key="$1" value="$2"
    local current
    current=$(git config --global --get "$key" 2>/dev/null || echo "")
    if [[ "$current" == "$value" ]]; then
        ok "git $key = $value"
    else
        if [[ -n "$current" ]]; then
            change "git $key: '$current' → '$value'"
        else
            change "git $key = '$value'"
        fi
        run_or_dry "git config --global '$key' '$value'"
    fi
}

# ============================================================================
# PHASE 5: Connection Tests
# ============================================================================

test_connections() {
    info "─── Connection Tests ────────────────────────────"
    if $DRY_RUN; then
        skip "Connection tests skipped in dry-run mode"
        return
    fi

    echo -n "  Testing GitHub SSH... "
    local gh_out
    gh_out="$(ssh -T -o ConnectTimeout=5 git@github.com 2>&1 || true)"
    if echo "$gh_out" | grep -qE "successfully authenticated|Hi "; then
        ok "GitHub SSH works"
    else
        warn "GitHub SSH failed — have you added the public key?"
        warn "  Key: ${SSH_DIR}/${SSH_KEY_GITHUB}.pub"
    fi

    echo -n "  Testing Server SSH (${SERVER_ALIAS})... "
    if ssh -o ConnectTimeout=5 -o BatchMode=yes "${SERVER_ALIAS}" "echo OK" 2>/dev/null | grep -q "OK"; then
        ok "Server SSH works"
    else
        warn "Server SSH failed — is the public key in authorized_keys?"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║         Platform Bootstrap — Dev Machine             ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    if $DRY_RUN; then warn "DRY RUN — no changes will be made"; echo ""; fi

    if ! $GIT_ONLY; then
        setup_ssh_keys; echo ""
        setup_ssh_config; echo ""
        setup_ssh_agent; echo ""
    fi
    if ! $SSH_ONLY; then
        setup_git_config; echo ""
    fi
    if ! $GIT_ONLY && ! $SSH_ONLY && ! $DRY_RUN; then
        test_connections; echo ""
    fi

    echo "─── Summary ───────────────────────────────────────────"
    if [[ $_CHANGES -eq 0 ]]; then
        ok "Everything already configured — no changes needed."
    else
        info "$_CHANGES change(s) applied."
    fi
    echo ""
    info "Next steps:"
    echo "  1. If new keys were generated, add public keys to GitHub/Server"
    echo "  2. Run: ./verify.sh to check everything"
    echo "  3. For server setup: ./server-setup.sh"
    echo ""
}

main
