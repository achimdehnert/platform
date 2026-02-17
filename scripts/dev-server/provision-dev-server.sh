#!/usr/bin/env bash
# provision-dev-server.sh
# Run as root on fresh Hetzner CX32
# See ADR-042 for context.
set -euo pipefail

echo "=== ADR-042: Provisioning DEV Server ==="

# ── 1. System update ─────────────────────────────────────────────
echo "[1/7] System update..."
apt-get update && apt-get upgrade -y
apt-get install -y \
    git curl wget build-essential \
    python3.12 python3.12-venv python3.12-dev \
    postgresql-client libpq-dev \
    jq htop tmux

# ── 2. Docker ────────────────────────────────────────────────────
echo "[2/7] Installing Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
else
    echo "Docker already installed, skipping."
fi

# ── 3. Deploy user ───────────────────────────────────────────────
echo "[3/7] Creating deploy user..."
id deploy &>/dev/null || adduser --disabled-password --gecos "Developer" deploy
usermod -aG docker deploy
usermod -aG sudo deploy

# Allow sudo without password for deploy user (dev server only!)
echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deploy
chmod 440 /etc/sudoers.d/deploy

# ── 4. SSH hardening ─────────────────────────────────────────────
echo "[4/7] SSH hardening..."
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Disable root SSH login
sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
# Ubuntu 24.04 uses ssh.service, not sshd.service
systemctl restart ssh || systemctl restart sshd || true

# ── 5. Firewall ──────────────────────────────────────────────────
echo "[5/7] Configuring firewall..."
ufw allow 22/tcp   # SSH only — Django dev server via SSH tunnel
ufw --force enable

# ── 6. Git configuration (as deploy user) ────────────────────────
echo "[6/7] Configuring git for deploy user..."
su - deploy -c '
    git config --global user.name "Achim Dehnert"
    git config --global user.email "achim@dehnert.dev"
    git config --global pull.rebase true
    git config --global init.defaultBranch main
    git config --global url."git@github.com:".insteadOf "https://github.com/"

    # Generate SSH key for GitHub (idempotent)
    if [ ! -f ~/.ssh/id_ed25519 ]; then
        ssh-keygen -t ed25519 -C "dev-hetzner" -f ~/.ssh/id_ed25519 -N ""
    fi
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  Add this public key to GitHub SSH Keys:"
    echo "═══════════════════════════════════════════════"
    cat ~/.ssh/id_ed25519.pub
    echo "═══════════════════════════════════════════════"
'

# ── 7. SSH key for github-runner → PROD server ───────────────────
echo "[7/7] Creating github-runner user + SSH key for PROD access..."
useradd -m -s /bin/bash github-runner 2>/dev/null || true
usermod -aG docker github-runner
su - github-runner -c '
    mkdir -p ~/.ssh && chmod 700 ~/.ssh
    if [ ! -f ~/.ssh/id_ed25519 ]; then
        ssh-keygen -t ed25519 -C "github-runner@dev-hetzner" -f ~/.ssh/id_ed25519 -N ""
    fi
    # Pre-accept PROD host key to avoid interactive prompt
    ssh-keyscan -H 88.198.191.108 >> ~/.ssh/known_hosts 2>/dev/null
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  Add this key to PROD /root/.ssh/authorized_keys:"
    echo "═══════════════════════════════════════════════"
    cat ~/.ssh/id_ed25519.pub
    echo "═══════════════════════════════════════════════"
'

echo ""
echo "✅ Dev server provisioned. Next steps:"
echo "   1. Add deploy user SSH key to GitHub"
echo "   2. Add github-runner SSH key to PROD server authorized_keys"
echo "   3. Run setup-repos.sh as deploy user"
echo "   4. Configure Windsurf Remote-SSH"
