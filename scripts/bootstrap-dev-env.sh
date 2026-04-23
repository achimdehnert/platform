#!/usr/bin/env bash
# =============================================================================
# bootstrap-dev-env.sh — IIL Platform Development Environment Setup
# =============================================================================
#
# Setzt eine neue Entwicklungsumgebung auf Ubuntu oder Windows 11 (WSL2) auf.
# Klont alle Repos, installiert Dependencies, konfiguriert SSH-Tunnel.
#
# USAGE:
#   curl -sSL https://raw.githubusercontent.com/achimdehnert/platform/main/scripts/bootstrap-dev-env.sh | bash
#   # oder lokal:
#   bash scripts/bootstrap-dev-env.sh
#
# OPTIONEN:
#   --minimal     Nur platform + mcp-hub (für schnellen Start)
#   --full        Alle 25+ Repos klonen
#   --remote      Setup auf Dev-Server (88.99.38.75) vorbereiten
#   --no-clone    Nur Dependencies installieren, keine Repos klonen
#   --dry-run     Zeigt was gemacht würde, ohne Änderungen
#
# VORAUSSETZUNGEN:
#   - Ubuntu 22.04+ oder Windows 11 mit WSL2 (Ubuntu)
#   - GitHub SSH-Key konfiguriert (ssh -T git@github.com funktioniert)
#   - sudo-Rechte für apt install
#
# =============================================================================
set -euo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────
readonly GITHUB_ORG="achimdehnert"
readonly GITHUB_BASE="${HOME}/github"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Server IPs (aus ports.yaml)
readonly PROD_SERVER="88.198.191.108"
readonly STAGING_SERVER="178.104.184.168"
readonly DEV_SERVER="88.99.38.75"  # Remote Development + Staging

# Development-Modi:
#   1. Lokal (Ubuntu/WSL2) — Code lokal, DB via SSH-Tunnel
#   2. Remote (88.99.38.75) — Code auf Server, VS Code Remote SSH
#   3. Hybrid — Code lokal, Services auf Dev-Server

# Core repos (immer klonen)
readonly CORE_REPOS=(
    platform
    mcp-hub
)

# App-Hub repos
readonly APP_REPOS=(
    bfagent
    risk-hub
    travel-beat
    weltenhub
    coach-hub
    billing-hub
    trading-hub
    pptx-hub
    cad-hub
    writing-hub
    research-hub
    wedding-hub
    137-hub
    illustration-hub
    dev-hub
    ausschreibungs-hub
    learn-hub
    tax-hub
    recruiting-hub
    dms-hub
    odoo-hub
)

# Framework/Library repos
readonly LIB_REPOS=(
    aifw
    promptfw
    authoringfw
    weltenfw
    illustration-fw
    testkit
    infra-deploy
)

# ── Logging ───────────────────────────────────────────────────────────────────
_BOLD='\033[1m'; _GREEN='\033[0;32m'; _YELLOW='\033[1;33m'
_RED='\033[0;31m'; _CYAN='\033[0;36m'; _RESET='\033[0m'

log()    { echo -e "${_CYAN}[bootstrap]${_RESET} $*"; }
header() { echo -e "\n${_BOLD}═══ $* ═══${_RESET}"; }
ok()     { echo -e "${_GREEN}✓${_RESET} $*"; }
warn()   { echo -e "${_YELLOW}⚠${_RESET} $*" >&2; }
err()    { echo -e "${_RED}✗${_RESET} $*" >&2; exit 1; }

# ── Detect OS ─────────────────────────────────────────────────────────────────
detect_os() {
    if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "wsl2"
    elif [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "${ID:-linux}"
    else
        echo "unknown"
    fi
}

# ── Check Prerequisites ───────────────────────────────────────────────────────
check_prerequisites() {
    header "Checking Prerequisites"
    
    local os
    os="$(detect_os)"
    log "Detected OS: $os"
    
    # Git
    if command -v git &>/dev/null; then
        ok "git $(git --version | cut -d' ' -f3)"
    else
        err "git not found. Install with: sudo apt install git"
    fi
    
    # GitHub SSH
    log "Testing GitHub SSH access..."
    if ssh -o BatchMode=yes -o ConnectTimeout=5 -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
        ok "GitHub SSH access configured"
    else
        warn "GitHub SSH not configured. Run: ssh-keygen -t ed25519 && cat ~/.ssh/id_ed25519.pub"
        warn "Then add the key to https://github.com/settings/keys"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] || exit 1
    fi
    
    # Python
    if command -v python3 &>/dev/null; then
        ok "python3 $(python3 --version | cut -d' ' -f2)"
    else
        warn "python3 not found. Will install."
    fi
    
    # Docker
    if command -v docker &>/dev/null; then
        ok "docker $(docker --version | cut -d' ' -f3 | tr -d ',')"
    else
        warn "docker not found. Will install."
    fi
}

# ── Install System Dependencies ───────────────────────────────────────────────
install_dependencies() {
    header "Installing System Dependencies"
    
    local os
    os="$(detect_os)"
    
    if [[ "$os" == "ubuntu" || "$os" == "wsl2" ]]; then
        log "Updating apt..."
        sudo apt update -qq
        
        log "Installing packages..."
        sudo apt install -y -qq \
            git \
            python3 \
            python3-pip \
            python3-venv \
            docker.io \
            docker-compose-v2 \
            postgresql-client \
            redis-tools \
            jq \
            yq \
            curl \
            wget \
            htop \
            ncdu \
            tree
        
        # Add user to docker group
        if ! groups | grep -q docker; then
            sudo usermod -aG docker "$USER"
            warn "Added to docker group. Log out and back in, or run: newgrp docker"
        fi
        
        ok "System packages installed"
    else
        warn "Unsupported OS: $os. Install dependencies manually."
    fi
}

# ── Install Python Tools ──────────────────────────────────────────────────────
install_python_tools() {
    header "Installing Python Tools"
    
    log "Installing pipx..."
    python3 -m pip install --user --quiet pipx
    python3 -m pipx ensurepath
    
    log "Installing development tools..."
    python3 -m pipx install ruff
    python3 -m pipx install hatch
    python3 -m pipx install pre-commit
    
    ok "Python tools installed (ruff, hatch, pre-commit)"
}

# ── Clone Repos ───────────────────────────────────────────────────────────────
clone_repos() {
    local mode="${1:-full}"
    
    header "Cloning Repositories ($mode mode)"
    
    mkdir -p "$GITHUB_BASE"
    cd "$GITHUB_BASE"
    
    local repos_to_clone=()
    
    case "$mode" in
        minimal)
            repos_to_clone=("${CORE_REPOS[@]}")
            ;;
        full)
            repos_to_clone=("${CORE_REPOS[@]}" "${APP_REPOS[@]}" "${LIB_REPOS[@]}")
            ;;
    esac
    
    local cloned=0 skipped=0 failed=0
    
    for repo in "${repos_to_clone[@]}"; do
        if [[ -d "$repo/.git" ]]; then
            ok "$repo — already cloned"
            ((skipped++))
        else
            log "Cloning $repo..."
            if git clone --quiet "git@github.com:${GITHUB_ORG}/${repo}.git" 2>/dev/null; then
                ok "$repo — cloned"
                ((cloned++))
            else
                warn "$repo — clone failed (repo may not exist or no access)"
                ((failed++))
            fi
        fi
    done
    
    log "Summary: $cloned cloned, $skipped already present, $failed failed"
}

# ── Setup SSH Tunnel for pgvector ─────────────────────────────────────────────
setup_ssh_tunnel() {
    header "Setting up SSH Tunnel (pgvector)"
    
    local tunnel_service="/etc/systemd/system/ssh-tunnel-postgres.service"
    
    if [[ -f "$tunnel_service" ]]; then
        ok "SSH tunnel service already exists"
        return 0
    fi
    
    log "Creating systemd service for PostgreSQL tunnel..."
    
    sudo tee "$tunnel_service" > /dev/null <<EOF
[Unit]
Description=SSH Tunnel to Production PostgreSQL (pgvector)
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/bin/ssh -N -L 15435:localhost:5432 root@${PROD_SERVER}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable ssh-tunnel-postgres
    
    ok "SSH tunnel service created"
    log "Start with: sudo systemctl start ssh-tunnel-postgres"
    log "PostgreSQL will be available at localhost:15435"
}

# ── Setup SSH Config ──────────────────────────────────────────────────────────
setup_ssh_config() {
    header "Setting up SSH Config"
    
    local ssh_config="$HOME/.ssh/config"
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    
    if grep -q "Host hetzner-prod" "$ssh_config" 2>/dev/null; then
        ok "SSH config already contains hetzner hosts"
        return 0
    fi
    
    log "Adding server aliases to SSH config..."
    
    cat >> "$ssh_config" <<EOF

# IIL Platform Servers
Host hetzner-prod
    HostName ${PROD_SERVER}
    User root
    IdentityFile ~/.ssh/id_ed25519

Host hetzner-staging
    HostName ${STAGING_SERVER}
    User root
    IdentityFile ~/.ssh/id_ed25519

Host hetzner-dev
    HostName ${DEV_SERVER}
    User root
    IdentityFile ~/.ssh/id_ed25519
EOF

    chmod 600 "$ssh_config"
    ok "SSH config updated"
}

# ── Setup Platform Package ────────────────────────────────────────────────────
setup_platform_package() {
    header "Setting up Platform Package"
    
    local platform_dir="$GITHUB_BASE/platform"
    
    if [[ ! -d "$platform_dir" ]]; then
        warn "platform repo not cloned. Skipping package setup."
        return 0
    fi
    
    cd "$platform_dir"
    
    # Create venv if not exists
    if [[ ! -d ".venv" ]]; then
        log "Creating virtual environment..."
        python3 -m venv .venv
    fi
    
    log "Installing platform-context package..."
    .venv/bin/pip install --quiet -e packages/platform-context
    
    log "Installing development dependencies..."
    .venv/bin/pip install --quiet pytest pytest-django ruff
    
    ok "Platform packages installed"
}

# ── Setup Windsurf Workflows ──────────────────────────────────────────────────
setup_windsurf_workflows() {
    header "Setting up Windsurf Workflows"
    
    local platform_dir="$GITHUB_BASE/platform"
    
    if [[ ! -f "$platform_dir/scripts/sync-workflows.sh" ]]; then
        warn "sync-workflows.sh not found. Skipping."
        return 0
    fi
    
    log "Syncing workflows to all repos..."
    GITHUB_DIR="$GITHUB_BASE" bash "$platform_dir/scripts/sync-workflows.sh" 2>&1 | grep -E "LINK|REPLACE" | head -10 || true
    
    ok "Windsurf workflows synced"
}

# ── Setup Remote Dev Server ───────────────────────────────────────────────────
setup_remote_dev() {
    header "Setting up Remote Development on Dev-Server"
    
    log "Checking SSH access to Dev-Server..."
    if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "root@${DEV_SERVER}" true 2>/dev/null; then
        err "Cannot reach Dev-Server (${DEV_SERVER}). Check SSH key."
    fi
    ok "Dev-Server reachable"
    
    log "Creating devuser and github directory on Dev-Server..."
    ssh "root@${DEV_SERVER}" bash <<'REMOTE'
set -euo pipefail

# Create devuser if not exists
if ! id devuser &>/dev/null; then
    useradd -m -s /bin/bash devuser
    echo "Created user: devuser"
fi

# Setup github directory
mkdir -p /home/devuser/github
chown devuser:devuser /home/devuser/github

# Copy SSH keys for GitHub access
if [[ -f /root/.ssh/id_ed25519 ]]; then
    mkdir -p /home/devuser/.ssh
    cp /root/.ssh/id_ed25519* /home/devuser/.ssh/ 2>/dev/null || true
    chown -R devuser:devuser /home/devuser/.ssh
    chmod 600 /home/devuser/.ssh/id_ed25519 2>/dev/null || true
fi

echo "Dev-Server ready for development"
REMOTE

    ok "Dev-Server configured"
    
    log "Cloning repos on Dev-Server..."
    ssh "root@${DEV_SERVER}" bash <<REMOTE
set -euo pipefail
cd /home/devuser/github

for repo in platform mcp-hub bfagent risk-hub; do
    if [[ -d "\$repo/.git" ]]; then
        echo "✓ \$repo already cloned"
    else
        sudo -u devuser git clone git@github.com:${GITHUB_ORG}/\$repo.git 2>/dev/null && echo "✓ \$repo cloned" || echo "⚠ \$repo failed"
    fi
done
REMOTE

    ok "Repos cloned on Dev-Server"
    
    echo ""
    echo "  🖥️  Remote Development ready!"
    echo ""
    echo "  Connect with VS Code:"
    echo "     1. Install 'Remote - SSH' extension"
    echo "     2. Cmd+Shift+P → 'Remote-SSH: Connect to Host' → hetzner-dev"
    echo "     3. Open folder: /home/devuser/github/<repo>"
    echo ""
    echo "  Or via terminal:"
    echo "     ssh hetzner-dev"
    echo "     cd /home/devuser/github/risk-hub"
    echo ""
}

# ── Print Summary ─────────────────────────────────────────────────────────────
print_summary() {
    header "Setup Complete!"
    
    echo ""
    echo "  📁 Repos cloned to: $GITHUB_BASE"
    echo ""
    echo "  🔧 Next steps:"
    echo "     1. Open Windsurf/VS Code in $GITHUB_BASE/platform"
    echo "     2. Start SSH tunnel: sudo systemctl start ssh-tunnel-postgres"
    echo "     3. Run /session-start workflow"
    echo ""
    echo "  🌐 Servers:"
    echo "     Production: ssh hetzner-prod"
    echo "     Staging:    ssh hetzner-staging"
    echo "     Dev:        ssh hetzner-dev (Remote Development)"
    echo ""
    echo "  💡 Development Options:"
    echo "     Local:  Code here, DB via SSH-Tunnel"
    echo "     Remote: VS Code Remote SSH → hetzner-dev"
    echo "     Hybrid: Code here, Services on Dev-Server"
    echo ""
    echo "  📚 Documentation:"
    echo "     ADRs:       $GITHUB_BASE/platform/docs/adr/"
    echo "     Workflows:  $GITHUB_BASE/platform/.windsurf/workflows/"
    echo "     Ports:      $GITHUB_BASE/platform/infra/ports.yaml"
    echo "     Multi-Env:  $GITHUB_BASE/platform/docs/MULTI_ENV_SETUP.md"
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    local mode="full"
    local dry_run=false
    local no_clone=false
    local setup_remote=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --minimal)  mode="minimal"; shift ;;
            --full)     mode="full"; shift ;;
            --remote)   setup_remote=true; shift ;;
            --no-clone) no_clone=true; shift ;;
            --dry-run)  dry_run=true; shift ;;
            --help|-h)
                sed -n '3,30p' "${BASH_SOURCE[0]}"
                exit 0
                ;;
            *)
                err "Unknown option: $1"
                ;;
        esac
    done
    
    header "IIL Platform Bootstrap"
    log "Mode: $mode"
    log "Target: $GITHUB_BASE"
    
    if [[ "$dry_run" == true ]]; then
        log "DRY RUN — no changes will be made"
        log "Would clone: ${#CORE_REPOS[@]} core + ${#APP_REPOS[@]} app + ${#LIB_REPOS[@]} lib repos"
        exit 0
    fi
    
    check_prerequisites
    install_dependencies
    install_python_tools
    
    if [[ "$no_clone" != true ]]; then
        clone_repos "$mode"
    fi
    
    setup_ssh_config
    setup_ssh_tunnel
    setup_platform_package
    setup_windsurf_workflows
    
    # Optional: Setup Remote Dev Server
    if [[ "$setup_remote" == true ]]; then
        setup_remote_dev
    fi
    
    print_summary
}

main "$@"
