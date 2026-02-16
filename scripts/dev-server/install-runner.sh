#!/usr/bin/env bash
# install-runner.sh — Run as root on DEV server
# See ADR-042 for context.
set -euo pipefail

RUNNER_VERSION="2.321.0"  # Check latest: github.com/actions/runner/releases
RUNNER_USER="github-runner"
RUNNER_DIR="/opt/github-runner"

echo "=== ADR-042: Installing Self-Hosted Runner ==="

# ── 1. Create dedicated user (idempotent) ─────────────────────────
echo "[1/5] Creating runner user..."
id "$RUNNER_USER" &>/dev/null || useradd -m -s /bin/bash "$RUNNER_USER"
usermod -aG docker "$RUNNER_USER"

# ── 2. Download runner ───────────────────────────────────────────
echo "[2/5] Downloading runner v${RUNNER_VERSION}..."
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

if [ ! -f "./config.sh" ]; then
    curl -o actions-runner-linux-x64.tar.gz -L \
        "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
    tar xzf actions-runner-linux-x64.tar.gz
    rm actions-runner-linux-x64.tar.gz
else
    echo "Runner already downloaded, skipping."
fi
chown -R "$RUNNER_USER":"$RUNNER_USER" "$RUNNER_DIR"

# ── 3. Configure runner ──────────────────────────────────────────
echo "[3/5] Configuring runner..."
echo ""
echo "Get a registration token from GitHub:"
echo "  Settings → Actions → Runners → New self-hosted runner"
echo "  OR: gh api -X POST /orgs/achimdehnert/actions/runners/registration-token"
echo ""
read -rp "Enter registration token: " REG_TOKEN

su - "$RUNNER_USER" -c "
    cd $RUNNER_DIR
    ./config.sh \
        --url https://github.com/achimdehnert \
        --token $REG_TOKEN \
        --name hetzner-dev-runner \
        --labels self-hosted,linux,x64,hetzner,dev \
        --work _work \
        --runnergroup Default \
        --unattended
"

# ── 4. Install as systemd service ────────────────────────────────
echo "[4/5] Installing systemd service..."
cd "$RUNNER_DIR"
./svc.sh install "$RUNNER_USER"
./svc.sh start

# ── 5. Apply resource limits ─────────────────────────────────────
echo "[5/5] Applying resource limits..."
SVC_DIR="/etc/systemd/system/actions.runner.achimdehnert.hetzner-dev-runner.service.d"
mkdir -p "$SVC_DIR"
cat > "$SVC_DIR/override.conf" << 'EOF'
[Service]
# Limit runner to 75% CPU and 4GB RAM
CPUQuota=300%
MemoryMax=4G
MemoryHigh=3G
EOF

systemctl daemon-reload
systemctl restart actions.runner.achimdehnert.hetzner-dev-runner.service

echo ""
echo "✅ Self-hosted runner installed and running."
echo "   Verify at: GitHub → Settings → Actions → Runners"
