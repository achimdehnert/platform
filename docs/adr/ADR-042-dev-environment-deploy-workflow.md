---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-042: Development Environment & Deployment Workflow

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-16 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-009 (Centralized Deployment Architecture) |

---

## 1. Context

### 1.1 Current State

The BF Agent Platform currently deploys on every push to `main` via GitHub Actions. Each deployment triggers a full CI/CD pipeline (lint, test, build Docker image, push to GHCR, SSH deploy to Hetzner).

| Parameter | Value |
|-----------|-------|
| Applications | 7 (BFAgent, Travel-Beat, MCP-Hub, Risk-Hub, Weltenhub, PPTX-Hub, Trading-Hub) |
| Deploys/day | ~22 total across all repos |
| Pipeline duration | ~5 minutes per deploy |
| GitHub Actions minutes/day | ~110 minutes |
| Dev environment | WSL on Windows (Windsurf IDE) |
| Production | Single Hetzner Cloud VPS |

### 1.2 Pain Points

1. **Excessive deployment frequency**: Small changes (CSS fixes, typo corrections, config tweaks) each trigger a full ~5 minute pipeline. During active development, this creates constant pipeline runs that consume CI minutes and create unnecessary load on the production server.

2. **WSL instability for infrastructure tooling**: Running deploy daemons or background services on WSL is unreliable due to known limitations with inotify (filesystem events between Windows/WSL are inconsistent), systemd support (requires WSL2 with special configuration), and network stability (WSL network can break on Windows updates or VPN changes).

3. **Dev/Prod environment conflation**: All development and production workloads run on the same infrastructure topology. There is no isolated development environment for testing Docker Compose configurations, database migrations, or multi-service integration before deploying to production.

4. **No deployment batching**: Five commits in 10 minutes generate five separate pipeline runs. There is no mechanism to batch related changes into a single deployment.

5. **GitHub Actions minute consumption**: At ~22 deploys/day × ~5 minutes × 30 days = ~3,300 minutes/month. The GitHub Pro plan provides 3,000 minutes/month, creating budget pressure.

### 1.3 Requirements

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Decouple push from deploy | HIGH | Push to main must not auto-deploy |
| Async deployment in background | HIGH | Developer workflow must not block |
| Sequentialize deploys per app | HIGH | No parallel deploys for same app |
| Reduce GitHub Actions minutes | HIGH | Budget constraint at ~3000 min/month |
| Clean Dev/Prod separation | HIGH | DSGVO Art. 32 compliance |
| Maintain full CI/CD gate | HIGH | No untested code in production |
| Minimize local infrastructure dependency | MEDIUM | Avoid WSL-dependent services |
| Support Windsurf IDE workflow | MEDIUM | Primary IDE must integrate seamlessly |
| Enable future team scaling | LOW | Architecture must support >1 developer |

---

## 2. Decision

### 2.1 Architecture Choice

**We adopt a Three-Server Architecture with CLI-triggered deployments, Self-Hosted Runner, and Safety-Net (Hybrid approach).**

This combines:

1. **Dedicated Hetzner Dev Server** for development (Windsurf Remote-SSH)
2. **Self-Hosted GitHub Actions Runner** on the DEV server (eliminates CI minute costs, isolates CI from production)
3. **CLI-triggered deployments** with debounce logic (`bf deploy <app>`)
4. **Safety-Net cron** (every 2 hours) for undeployed commits

```text
┌─────────────────────────────────────────────────────────────────┐
│              Developer Workstation (Windows)                    │
│                                                                 │
│  ┌────────────────────────────────────────────┐                 │
│  │  Windsurf IDE                              │                 │
│  │  ├── Remote-SSH → Hetzner DEV              │                 │
│  │  ├── Cascade AI (full over SSH)            │                 │
│  │  └── Terminal → remote shell               │                 │
│  └────────────────────────────────────────────┘                 │
│                                                                 │
│  ┌────────────────────────────────────────────┐                 │
│  │  bf deploy CLI (local, lightweight)        │                 │
│  │  ├── Triggers workflow_dispatch via API    │                 │
│  │  ├── Debounce: 60s window per app          │                 │
│  │  └── Returns immediately (async)           │                 │
│  └────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
         │ SSH                         │ GitHub API (HTTPS)
         ▼                             ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│  Hetzner DEV Server          │    │  GitHub Actions              │
│  (CX32 — €6.80/month)       │    │                              │
│                              │    │  workflow_dispatch trigger   │
│  ├── Git Repos (clone)       │    │                              │
│  ├── Docker Dev-Stack        │    │  Safety-Net Cron (2h):       │
│  ├── PostgreSQL (dev)        │    │  "Undeployed on main?        │
│  ├── Pre-commit Hooks        │    │   → trigger deploy"          │
│  ├── Tests (local run)       │    │                              │
│  ├── Python 3.12 venv        │    └──────────────────────────────┘
│  │                           │               │
│  ├── Self-Hosted Runner ─────┼── picks up ───┘
│  │   ├── Lint, Test          │
│  │   ├── Docker Build        │
│  │   └── Push to GHCR        │
│  │                           │
│  └── git push origin main    │
└──────────────────────────────┘
              │ docker push to GHCR
              ▼
┌──────────────────────────────────────┐
│  Hetzner PROD Server                 │
│  (existing, 88.198.191.108)          │
│                                      │
│  ├── docker compose pull (from GHCR) │
│  ├── docker compose up -d            │
│  │                                   │
│  ├── Production Apps (Docker)        │
│  │   ├── BFAgent                     │
│  │   ├── Travel-Beat (DriftTales)    │
│  │   ├── MCP-Hub                     │
│  │   ├── Risk-Hub (Schutztat)        │
│  │   ├── Weltenhub (Weltenforger)    │
│  │   ├── PPTX-Hub                    │
│  │   └── Trading-Hub                 │
│  │                                   │
│  ├── Nginx + TLS                     │
│  └── Auto-Healer (ADR-009)          │
└──────────────────────────────────────┘
```

### 2.2 Rejected Alternatives

#### Option A: CLI-Trigger Only (no Safety-Net)

```
✗ Rejected because:
- Risk of forgotten deploys (Friday afternoon commits deployed Monday)
- No protection against developer oversight
- Acceptable for single-developer short-term, but not robust enough
  for production platform

→ Incorporated as: primary deploy path within the Hybrid approach
```

#### Option B: Local Deploy-Daemon on WSL

```
✗ Rejected because:
- WSL limitations with inotify, systemd, network stability
- Significant implementation effort (3-5 days) for fragile result
- Single point of failure tied to developer laptop
- Does not scale to team scenario
- Maintenance burden of local daemon infrastructure

→ Not incorporated. Dev server + Self-Hosted Runner achieves
  same benefits without WSL dependency.
```

#### Option C: Time-based Auto-Batch (Cron-Deploy every 15 min)

```
✗ Rejected as standalone because:
- GitHub Actions minute explosion: 5 repos × 4 checks/hour =
  480 workflow starts/day, ~480 minutes/day of CI budget
- Non-deterministic deploy timing (0-15 min latency)
- No prioritization between critical and trivial changes

→ Incorporated as: Safety-Net cron at relaxed 2h interval,
  combined with Self-Hosted Runner to eliminate minute costs
```

#### Option E: Develop Directly on Production Server

```
✗ Rejected because:
- Violates Dev/Prod separation (DSGVO Art. 32)
- Risk of accidental production impact (docker compose down, resource contention)
- No isolated testing of migrations or config changes
- No reproducible development environment
```

#### Option F: Continue with WSL Only (Status Quo)

```
✗ Rejected because:
- Does not address deployment frequency pain point
- WSL limitations prevent reliable infrastructure tooling
- No CI minute cost reduction
```

---

## 3. Implementation

### 3.1 Component Overview

| Component | Location | Purpose |
|-----------|----------|---------|
| Hetzner DEV Server (CX32) | Hetzner Cloud, nbg1 | Isolated development environment |
| Self-Hosted Runner | DEV Server (Docker container) | Execute GitHub Actions without CI minutes, build + push images to GHCR |
| `bf deploy` CLI | Developer workstation (pip install) | Trigger deployments via GitHub API |
| Safety-Net Workflow | GitHub Actions (schedule) | Auto-deploy forgotten commits |
| Windsurf Remote-SSH | Developer workstation → DEV Server | IDE integration |

### 3.2 Hetzner DEV Server Setup

**Server Specification:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Type | CX32 | 4 vCPU, 8 GB RAM, 80 GB NVMe — sufficient for 7 Django projects + Docker + Self-Hosted Runner |
| OS | Ubuntu 24.04 LTS | Consistent with PROD server |
| Location | nbg1 (Nuremberg) | Same datacenter as PROD → minimal latency |
| Monthly cost | €6.80 (excl. VAT) | |

**Provisioning Script:**

```bash
#!/usr/bin/env bash
# provision-dev-server.sh
# Run as root on fresh Hetzner CX32
set -euo pipefail

# ── 1. System update ─────────────────────────────────────────────
apt-get update && apt-get upgrade -y
apt-get install -y \
    git curl wget build-essential \
    python3.12 python3.12-venv python3.12-dev \
    postgresql-client libpq-dev \
    jq htop tmux

# ── 2. Docker ────────────────────────────────────────────────────
curl -fsSL https://get.docker.com | sh
systemctl enable docker

# ── 3. Deploy user ───────────────────────────────────────────────
adduser --disabled-password --gecos "Developer" deploy
usermod -aG docker deploy
usermod -aG sudo deploy

# Allow sudo without password for deploy user (dev server only!)
echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deploy
chmod 440 /etc/sudoers.d/deploy

# ── 4. SSH hardening ─────────────────────────────────────────────
# Copy authorized_keys from root to deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Disable root SSH login
sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd

# ── 5. Firewall ──────────────────────────────────────────────────
ufw allow 22/tcp   # SSH (only port open — Django dev server via SSH tunnel only)
ufw --force enable

# ── 6. Git configuration (as deploy user) ────────────────────────
su - deploy -c '
    git config --global user.name "Achim Dehnert"
    git config --global user.email "achim@dehnert.dev"
    git config --global pull.rebase true
    git config --global init.defaultBranch main

    # Generate SSH key for GitHub
    ssh-keygen -t ed25519 -C "dev-hetzner" -f ~/.ssh/id_ed25519 -N ""
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  Add this public key to GitHub SSH Keys:"
    echo "═══════════════════════════════════════════════"
    cat ~/.ssh/id_ed25519.pub
    echo "═══════════════════════════════════════════════"
'

# ── 7. SSH key for github-runner → PROD server ───────────────────
# The self-hosted runner needs SSH access to PROD for deployments.
# Create a dedicated key pair; public key must be added to PROD.
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
echo "   3. Clone repos as deploy user"
echo "   4. Configure Windsurf Remote-SSH"
```

**Repository Setup (as deploy user):**

```bash
#!/usr/bin/env bash
# setup-repos.sh — Run as deploy user on DEV server
set -euo pipefail

mkdir -p ~/projects && cd ~/projects

# Clone all platform repos
repos=(
    "achimdehnert/bfagent"
    "achimdehnert/travel-beat"
    "achimdehnert/mcp-hub"
    "achimdehnert/risk-hub"
    "achimdehnert/weltenhub"
    "achimdehnert/pptx-hub"
    "achimdehnert/trading-hub"
    "achimdehnert/platform"
)

for repo in "${repos[@]}"; do
    name=$(basename "$repo")
    if [ ! -d "$name" ]; then
        echo "Cloning $repo..."
        git clone "git@github.com:${repo}.git"
    else
        echo "Skipping $name (already exists)"
    fi
done

# Set up Python virtual environments (idempotent)
for name in bfagent travel-beat mcp-hub risk-hub weltenhub pptx-hub trading-hub; do
    if [ -d "$name" ]; then
        cd "$name"
        EXPECTED_PY="$(python3.12 --version 2>/dev/null)"
        CURRENT_PY="$(.venv/bin/python --version 2>/dev/null || echo 'none')"
        if [ "$EXPECTED_PY" != "$CURRENT_PY" ]; then
            echo "Creating venv for $name (${EXPECTED_PY})..."
            python3.12 -m venv .venv --clear
        else
            echo "Venv for $name OK (${CURRENT_PY}), skipping create."
        fi
        source .venv/bin/activate
        pip install --quiet --upgrade pip
        [ -f requirements.txt ] && pip install --quiet -r requirements.txt
        [ -f requirements-dev.txt ] && pip install --quiet -r requirements-dev.txt
        deactivate
        cd ..
    fi
done

echo "✅ All repos cloned and venvs created."
```

### 3.3 Windsurf IDE Configuration

**SSH Config (on developer workstation):**

File: `%USERPROFILE%\.ssh\config` (Windows) or `~/.ssh/config` (WSL)

```
# ── BF Agent Platform: Dev Server ────────────────────────────────
Host hetzner-dev
    HostName <DEV-SERVER-IP>
    User deploy
    IdentityFile ~/.ssh/id_ed25519
    ForwardAgent yes
    ServerAliveInterval 60
    ServerAliveCountMax 3

# ── BF Agent Platform: Prod Server (for emergencies only) ───────
Host hetzner-prod
    HostName <PROD-SERVER-IP>
    User deploy
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

**Connection workflow:**

1. Open Windsurf
2. Click "Open a Remote Window" (bottom-left corner) or `Ctrl+Shift+P` → "Remote-SSH: Connect to Host"
3. Select `hetzner-dev`
4. Windsurf installs its server component automatically on first connect
5. Open folder: `/home/deploy/projects/travel-beat` (or any project)
6. Full IDE features available: file explorer, terminal, Cascade AI, Git integration

**Port forwarding for Django dev server** (in Windsurf terminal or separate SSH session):

```bash
# Forward Django dev server to local browser
# Run in local terminal (not remote):
ssh -L 8000:localhost:8000 hetzner-dev

# Then access http://localhost:8000 in local browser
```

**NOTE:** Windsurf uses its own Remote-SSH implementation, not the Microsoft extension. The Microsoft "Remote - SSH" extension must NOT be installed as it conflicts. Windsurf's implementation supports Linux remote hosts only (which Hetzner Ubuntu satisfies).

### 3.4 Self-Hosted Runner on DEV Server

**Installation (on DEV server, as root):**

```bash
#!/usr/bin/env bash
# install-runner.sh — Run as root on DEV server
set -euo pipefail

RUNNER_VERSION="2.321.0"  # Check latest: github.com/actions/runner/releases
RUNNER_USER="github-runner"
RUNNER_DIR="/opt/github-runner"

# ── 1. Create dedicated user ─────────────────────────────────────
useradd -m -s /bin/bash "$RUNNER_USER"
usermod -aG docker "$RUNNER_USER"

# ── 2. Download runner ───────────────────────────────────────────
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

curl -o actions-runner-linux-x64.tar.gz -L \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"

tar xzf actions-runner-linux-x64.tar.gz
rm actions-runner-linux-x64.tar.gz
chown -R "$RUNNER_USER":"$RUNNER_USER" "$RUNNER_DIR"

# ── 3. Configure runner ──────────────────────────────────────────
# Get registration token from GitHub:
#   Settings → Actions → Runners → New self-hosted runner
#   OR via API: POST /orgs/{org}/actions/runners/registration-token

su - "$RUNNER_USER" -c "
    cd $RUNNER_DIR
    ./config.sh \
        --url https://github.com/achimdehnert \
        --token <REGISTRATION_TOKEN> \
        --name hetzner-dev-runner \
        --labels self-hosted,linux,x64,hetzner,dev \
        --work _work \
        --runnergroup Default \
        --unattended
"

# ── 4. Install as systemd service ────────────────────────────────
cd "$RUNNER_DIR"
./svc.sh install "$RUNNER_USER"
./svc.sh start

echo "✅ Self-hosted runner installed and running."
echo "   Verify at: GitHub → Settings → Actions → Runners"
```

**Security hardening for the runner:**

```bash
# ── Runner isolation ─────────────────────────────────────────────
# The runner user has Docker access but limited system access.
# Runner is registered at ORGANIZATION level, restricted to
# specific private repositories only.

# In GitHub: Settings → Actions → Runner groups
# Create group "hetzner-dev" with:
#   - Only selected repositories (all 7 app repos)
#   - No public repositories
#   - No fork pull requests

# ── Resource limits (systemd override) ───────────────────────────
mkdir -p /etc/systemd/system/actions.runner.*.service.d/
cat > /etc/systemd/system/actions.runner.achimdehnert.hetzner-dev-runner.service.d/override.conf << 'EOF'
[Service]
# Limit runner to 50% CPU and 4GB RAM (dev server has no production apps to protect)
CPUQuota=300%
MemoryMax=4G
MemoryHigh=3G
EOF

systemctl daemon-reload
systemctl restart actions.runner.achimdehnert.hetzner-dev-runner.service
```

**Workflow adaptation (per repository):**

```yaml
# .github/workflows/deploy.yml
# BEFORE: on push (every commit triggers deploy)
# AFTER:  on workflow_dispatch (explicit trigger only)

name: Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment Environment'
        required: true
        default: 'production'
        type: choice
        options:
          - staging
          - production

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  ci:
    # Runs on DEV server (not GitHub-hosted, not PROD)
    runs-on: [self-hosted, hetzner, dev]
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Lint & Test
        run: |
          set -euo pipefail
          # Isolate deps per job — self-hosted runner is shared across 7 apps
          python -m venv /tmp/ci-venv-$$
          source /tmp/ci-venv-$$/bin/activate
          pip install --quiet --upgrade pip
          pip install --quiet -r requirements-dev.txt
          ruff check .
          python -m pytest --tb=short
          deactivate
          rm -rf /tmp/ci-venv-$$

  build:
    needs: [ci]
    runs-on: [self-hosted, hetzner, dev]
    # Prevent parallel builds for the same app
    concurrency:
      group: build-${{ github.repository }}
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v4

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and Push Docker Image
        run: |
          set -euo pipefail
          IMAGE="${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}"
          SHA_TAG="sha-${GITHUB_SHA::7}"
          docker build -f docker/Dockerfile -t "${IMAGE}:latest" -t "${IMAGE}:${SHA_TAG}" .
          docker push "${IMAGE}:latest"
          docker push "${IMAGE}:${SHA_TAG}"

  deploy:
    needs: [build]
    runs-on: [self-hosted, hetzner, dev]
    environment: ${{ inputs.environment || 'production' }}
    concurrency:
      group: deploy-${{ github.repository }}
      cancel-in-progress: false
    steps:
      - name: Deploy to PROD via SSH
        run: |
          set -euo pipefail
          APP_DIR="/opt/$(basename ${{ github.repository }})"
          # SSH from DEV to PROD: pull new image + restart
          ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
            root@88.198.191.108 "
              cd ${APP_DIR} && \
              docker compose pull && \
              docker compose up -d --remove-orphans && \
              sleep 5
            "

      - name: Health Check
        run: |
          set -euo pipefail
          HEALTH_URL="${{ vars.HEALTH_URL }}"
          for i in $(seq 1 10); do
            if curl -sf "$HEALTH_URL" > /dev/null; then
              echo "Health check passed (attempt $i)"
              exit 0
            fi
            echo "Waiting... (attempt $i/10)"
            sleep 3
          done
          echo "Health check failed after 10 attempts"
          exit 1
```

### 3.5 `bf deploy` CLI Tool

**Package structure:**

```
bf-deploy/
├── pyproject.toml
├── README.md
└── bf_deploy/
    ├── __init__.py
    ├── cli.py          # Click-based CLI
    ├── github_api.py   # GitHub workflow_dispatch trigger
    ├── config.py       # App registry, defaults
    └── debounce.py     # Debounce logic (per-app, 60s window)
```

**Core implementation:**

```python
# bf_deploy/cli.py
"""
BF Agent Platform — Deploy CLI

Usage:
    bf deploy travel-beat          # Deploy single app
    bf deploy travel-beat bfagent  # Deploy multiple apps
    bf deploy --all                # Deploy all apps
    bf status                      # Show deploy status
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import click
import httpx

# ── Configuration ────────────────────────────────────────────────

APPS: dict[str, dict] = {
    "bfagent":     {"repo": "achimdehnert/bfagent",      "health": "https://bfagent.iil.pet/health/"},
    "travel-beat": {"repo": "achimdehnert/travel-beat",   "health": "https://drifttales.app/health/"},
    "mcp-hub":     {"repo": "achimdehnert/mcp-hub",       "health": "https://mcp-hub.iil.pet/health/"},
    "risk-hub":    {"repo": "achimdehnert/risk-hub",       "health": "https://schutztat.app/health/"},
    "weltenhub":   {"repo": "achimdehnert/weltenhub",     "health": "https://weltenforger.app/health/"},
    "pptx-hub":    {"repo": "achimdehnert/pptx-hub",      "health": "https://pptx-hub.iil.pet/health/"},
    "trading-hub": {"repo": "achimdehnert/trading-hub",   "health": "https://trading-hub.iil.pet/health/"},
}

DEBOUNCE_FILE = Path.home() / ".bf-deploy" / "debounce.json"
DEBOUNCE_SECONDS = 60

# ── GitHub API ───────────────────────────────────────────────────

def trigger_workflow(repo: str, token: str, ref: str = "main") -> int | None:
    """Trigger workflow_dispatch and return HTTP status code."""
    url = f"https://api.github.com/repos/{repo}/actions/workflows/deploy.yml/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"ref": ref, "inputs": {"environment": "production"}}

    resp = httpx.post(url, headers=headers, json=payload, timeout=10)
    return resp.status_code  # 204 = success

# ── Debounce ─────────────────────────────────────────────────────
# NOTE: No file-locking — acceptable for single-developer use.
# Parallel bf deploy calls may cause double-triggers. Use --force
# only when intentional.

def _load_debounce() -> dict:
    if DEBOUNCE_FILE.exists():
        return json.loads(DEBOUNCE_FILE.read_text())
    return {}

def _save_debounce(data: dict) -> None:
    DEBOUNCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEBOUNCE_FILE.write_text(json.dumps(data))

def is_debounced(app: str) -> bool:
    """Return True if app was triggered within DEBOUNCE_SECONDS."""
    data = _load_debounce()
    last = data.get(app, 0)
    return (time.time() - last) < DEBOUNCE_SECONDS

def mark_triggered(app: str) -> None:
    data = _load_debounce()
    data[app] = time.time()
    _save_debounce(data)

# ── CLI ──────────────────────────────────────────────────────────

def _get_token() -> str:
    """Read GitHub token from environment or ~/.bf-deploy/token."""
    import os
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    token_file = Path.home() / ".bf-deploy" / "token"
    if token_file.exists():
        return token_file.read_text().strip()
    click.echo("Error: Set GITHUB_TOKEN or create ~/.bf-deploy/token", err=True)
    sys.exit(1)


@click.group()
def cli():
    """BF Agent Platform — Deploy CLI."""


@cli.command()
@click.argument("apps", nargs=-1)
@click.option("--all", "deploy_all", is_flag=True, help="Deploy all apps")
@click.option("--force", is_flag=True, help="Ignore debounce window")
def deploy(apps: tuple[str, ...], deploy_all: bool, force: bool):
    """Trigger async deployment for one or more apps."""
    token = _get_token()

    targets = list(APPS.keys()) if deploy_all else list(apps)
    if not targets:
        click.echo("Usage: bf deploy <app> [<app>...] or bf deploy --all")
        sys.exit(1)

    for app in targets:
        if app not in APPS:
            click.echo(f"Unknown app: {app}. Available: {', '.join(APPS)}")
            continue

        if not force and is_debounced(app):
            click.echo(f"⏳ {app}: debounced (triggered <{DEBOUNCE_SECONDS}s ago, use --force to override)")
            continue

        status = trigger_workflow(APPS[app]["repo"], token)
        if status == 204:
            mark_triggered(app)
            click.echo(f"🚀 {app}: deploy triggered (async)")
        else:
            click.echo(f"❌ {app}: trigger failed (HTTP {status})")


@cli.command()
def status():
    """Show recent deploy status for all apps."""
    token = _get_token()
    for app, cfg in APPS.items():
        url = f"https://api.github.com/repos/{cfg['repo']}/actions/runs?per_page=1"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
        }
        resp = httpx.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            runs = resp.json().get("workflow_runs", [])
            if runs:
                run = runs[0]
                conclusion = run.get("conclusion") or run.get("status")
                sha = run["head_sha"][:7]
                emoji = {"success": "✅", "failure": "❌", "in_progress": "🔄"}.get(conclusion, "❓")
                click.echo(f"  {emoji} {app:15s} {conclusion:12s} ({sha})")
            else:
                click.echo(f"  ❓ {app:15s} no runs found")
        else:
            click.echo(f"  ❌ {app:15s} API error ({resp.status_code})")


@cli.command()
@click.argument("app")
@click.argument("sha_tag")
def rollback(app: str, sha_tag: str):
    """Rollback an app to a specific image tag.

    Usage: bf rollback travel-beat sha-abc1234
    """
    if app not in APPS:
        click.echo(f"Unknown app: {app}. Available: {', '.join(APPS)}")
        sys.exit(1)

    cfg = APPS[app]
    image = f"ghcr.io/{cfg['repo']}:{sha_tag}"
    click.echo(f"Rolling back {app} to {image}...")

    # SSH to PROD: pull specific tag, update compose, restart
    import subprocess
    cmd = (
        f"ssh -o BatchMode=yes root@88.198.191.108 '"
        f"cd /opt/{app} && "
        f"docker pull {image} && "
        f"docker tag {image} ghcr.io/{cfg[\"repo\"]}:latest && "
        f"docker compose up -d --force-recreate"
        f"'"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        click.echo(f"Rollback {app} -> {sha_tag} complete.")
    else:
        click.echo(f"Rollback failed: {result.stderr}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
```

**Installation:**

```toml
# bf-deploy/pyproject.toml
[project]
name = "bf-deploy"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["click>=8.0", "httpx>=0.25"]

[project.scripts]
bf = "bf_deploy.cli:cli"
```

```bash
pip install -e bf-deploy/
# or: pip install git+https://github.com/achimdehnert/platform.git#subdirectory=tools/bf-deploy
```

### 3.6 Safety-Net Workflow

```yaml
# platform/.github/workflows/safety-net-deploy.yml
#
# Runs every 2 hours. For each app, checks if there are
# undeployed commits on main. If yes, triggers deploy.
#
name: 🛡️ Safety-Net Deploy Check

on:
  schedule:
    - cron: '0 */2 * * *'  # Every 2 hours
  workflow_dispatch:        # Manual trigger for testing

jobs:
  check-and-deploy:
    runs-on: [self-hosted, hetzner, dev]
    strategy:
      matrix:
        app:
          - { name: bfagent,     repo: achimdehnert/bfagent,      workflow: deploy.yml }
          - { name: travel-beat, repo: achimdehnert/travel-beat,   workflow: deploy.yml }
          - { name: mcp-hub,     repo: achimdehnert/mcp-hub,      workflow: deploy.yml }
          - { name: risk-hub,    repo: achimdehnert/risk-hub,     workflow: deploy.yml }
          - { name: weltenhub,   repo: achimdehnert/weltenhub,    workflow: deploy.yml }
          - { name: pptx-hub,    repo: achimdehnert/pptx-hub,     workflow: deploy.yml }
          - { name: trading-hub, repo: achimdehnert/trading-hub,  workflow: deploy.yml }
      max-parallel: 1  # Sequential deploys

    steps:
      - name: Check for undeployed commits
        id: check
        env:
          GH_TOKEN: ${{ secrets.PLATFORM_DEPLOY_TOKEN }}
        run: |
          set -euo pipefail

          REPO="${{ matrix.app.repo }}"

          # Get SHA of last successful deploy (filter by deploy.yml workflow!)
          WORKFLOW="${{ matrix.app.workflow }}"
          LAST_DEPLOY_SHA=$(gh api \
            "repos/${REPO}/actions/workflows/${WORKFLOW}/runs?status=success&per_page=1&branch=main" \
            --jq '.workflow_runs[0].head_sha // empty' 2>/dev/null || echo "")

          # Get current HEAD of main
          MAIN_SHA=$(gh api "repos/${REPO}/git/ref/heads/main" \
            --jq '.object.sha' 2>/dev/null || echo "")

          if [ -z "$MAIN_SHA" ]; then
            echo "skip=true" >> "$GITHUB_OUTPUT"
            echo "⚠️  ${{ matrix.app.name }}: could not determine main SHA"
            exit 0
          fi

          if [ "$LAST_DEPLOY_SHA" = "$MAIN_SHA" ]; then
            echo "skip=true" >> "$GITHUB_OUTPUT"
            echo "✅ ${{ matrix.app.name }}: up to date ($MAIN_SHA)"
          else
            echo "skip=false" >> "$GITHUB_OUTPUT"
            echo "🔔 ${{ matrix.app.name }}: undeployed commits detected"
            echo "   Last deploy: ${LAST_DEPLOY_SHA:-none}"
            echo "   Current main: $MAIN_SHA"
          fi

      - name: Trigger deploy
        if: steps.check.outputs.skip != 'true'
        env:
          GH_TOKEN: ${{ secrets.PLATFORM_DEPLOY_TOKEN }}
        run: |
          set -euo pipefail
          echo "🚀 Triggering deploy for ${{ matrix.app.name }}..."
          gh workflow run "${{ matrix.app.workflow }}" \
            --repo "${{ matrix.app.repo }}" \
            --ref main \
            -f environment=production
```

---

## 4. Migration Plan

### Phase 1: Dev Server Setup (Day 1)

| Step | Task | Deliverable |
|------|------|-------------|
| 1 | Provision Hetzner CX32 via Cloud Console | Running server with SSH access |
| 2 | Run `provision-dev-server.sh` | Docker, Python, deploy user configured |
| 3 | Add SSH key to GitHub | Dev server can clone/push repos |
| 4 | Run `setup-repos.sh` | All repos cloned with venvs |
| 5 | Configure Windsurf SSH config | IDE connects to dev server |
| 6 | Test: Open project, edit, commit, push | End-to-end dev workflow verified |

### Phase 2: Self-Hosted Runner (Day 2)

| Step | Task | Deliverable |
|------|------|-------------|
| 1 | Create GitHub PAT with `admin:org` + `repo` scope | Token for runner registration |
| 2 | Run `install-runner.sh` on DEV server | Runner registered and running |
| 3 | Apply systemd resource limits | Runner isolated from production apps |
| 4 | Configure runner group (private repos only) | Security hardening complete |
| 5 | Test: Trigger workflow manually in GitHub UI | Job executes on self-hosted runner |

### Phase 3: Workflow Migration (Day 2-3)

| Step | Task | Deliverable |
|------|------|-------------|
| 1 | Update Travel-Beat workflow (pilot) | `on: workflow_dispatch`, `runs-on: self-hosted` |
| 2 | Test: Trigger via GitHub UI | Full pipeline on self-hosted runner |
| 3 | Migrate remaining 4 app workflows | All apps using workflow_dispatch |
| 4 | Remove `on: push` triggers | Push no longer auto-deploys |

### Phase 4: CLI + Safety-Net (Day 3-4)

| Step | Task | Deliverable |
|------|------|-------------|
| 1 | Implement `bf-deploy` CLI package | `bf deploy <app>` working |
| 2 | Install CLI on dev workstation | `pip install -e bf-deploy/` |
| 3 | Test: `bf deploy travel-beat` | Async deploy trigger verified |
| 4 | Deploy safety-net workflow to platform repo | Cron running every 2h |
| 5 | Test: Push without deploy, wait 2h | Safety-net auto-deploys |

### Phase 5: Validation (Day 5)

| Step | Task | Deliverable |
|------|------|-------------|
| 1 | Full workflow test: edit → push → bf deploy → verify | End-to-end validated |
| 2 | Safety-net test: push without deploy, observe | Auto-deploy after ≤2h |
| 3 | Verify zero GitHub Actions minutes consumed | Cost reduction confirmed |
| 4 | Document runbooks for common operations | Operational docs complete |

---

## 5. Consequences

### 5.1 Positive

- **Zero GitHub Actions minute consumption**: Self-hosted runner eliminates the ~3,300 minutes/month budget pressure entirely. All CI/CD runs execute on owned infrastructure at no marginal cost.
- **Clean Dev/Prod separation**: Dedicated development server with isolated Docker environment, PostgreSQL instance, and Git configuration. Compliant with DSGVO Art. 32 requirements for separation of processing environments.
- **Elimination of WSL limitations**: Native Linux development environment eliminates inotify, systemd, and network instability issues. All infrastructure tooling (Docker, systemd services, cron) works reliably.
- **Faster deploy cycles**: Self-hosted runner on DEV builds images and pushes to GHCR. PROD only pulls and restarts. No GitHub-hosted runner queue wait. Deploy time reduced from ~5 minutes to ~1-2 minutes.
- **Deployment batching**: CLI debounce logic (60s window) automatically batches rapid successive deploys. Safety-net prevents forgotten commits from lingering undeployed.
- **~60% reduction in deploys/day**: From ~22 push-triggered deploys to ~8-10 intentional deploys via CLI, reducing production server churn and enabling larger, more coherent changesets.
- **Always-on development environment**: Dev server runs 24/7 on Hetzner, independent of developer laptop state. Long-running tasks (tests, builds) continue when laptop sleeps.

### 5.2 Negative

- **Additional monthly cost**: €6.80/month for CX32 dev server. Offset by GitHub Actions minute savings (avoided overage charges or plan upgrades).
- **Network dependency for development**: All coding requires SSH connection to dev server. If Hetzner has an outage or internet is unavailable, development is blocked. Mitigation: keep local Git clone as fallback.
- **Self-hosted runner security responsibility**: Runner maintenance (updates within 30 days required by GitHub), security monitoring, and resource isolation become the developer's responsibility. Mitigated by systemd resource limits and restricted runner groups.
- **Two deploy paths to understand**: CLI (primary) and Safety-Net (automatic fallback). Requires clear documentation for any future team members.
- **Windsurf Remote-SSH limitations**: Windsurf's SSH implementation lacks some features of the Microsoft extension (e.g., automatic port forwarding). Manual SSH tunnels may be needed for Django dev server access.

### 5.3 Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Dev server down | Low | Medium | Local Git clone as fallback; Hetzner SLA 99.9% |
| Runner compromised | Very Low | High | Private repos only; runner group restrictions; systemd isolation; regular updates |
| Safety-net deploys unwanted code | Low | Low | Only deploys what's already on `main`; full CI gate still runs |
| Forgotten `bf deploy` (before safety-net kicks in) | Medium | Low | Safety-net catches within 2h; Slack alert on auto-deploy |
| Windsurf SSH connection drops | Medium | Low | `ServerAliveInterval` keeps connection; auto-reconnect on reopen |
| Runner update required (30-day GitHub policy) | Certain | Low | Calendar reminder; automated update script |

---

## 6. Metrics & Success Criteria

### 6.1 Quantitative

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| GitHub Actions minutes/month | ~3,300 | 0 | GitHub billing dashboard |
| Deploys/day | ~22 (push-triggered) | ~8-10 (intentional) | GitHub Actions run count |
| Deploy latency (trigger → live) | ~5 min | <1 min | Workflow run duration |
| Monthly infrastructure cost delta | €0 | +€6.80 | Hetzner invoice |
| WSL-related dev issues/week | ~2-3 | 0 | Developer experience |
| Undeployed commits >2h | Unknown | 0 | Safety-net logs |

### 6.2 Qualitative

- [ ] All 7 app workflows migrated to `workflow_dispatch` + self-hosted runner
- [ ] `bf deploy` CLI installed and working on developer workstation
- [ ] Windsurf Remote-SSH connects reliably to dev server
- [ ] Safety-net cron successfully auto-deploys at least once (validated)
- [ ] Self-hosted runner passes health check for 7 consecutive days
- [ ] No production incidents caused by migration
- [ ] Developer subjective experience: "faster and less friction"

---

## 7. Security Considerations

### 7.1 Self-Hosted Runner Security

GitHub's security documentation explicitly warns about self-hosted runners on public repositories. This ADR addresses those concerns:

| Concern | Applicability | Mitigation |
|---------|---------------|------------|
| Untrusted code execution | **Low** — all repos private, single developer | Runner group restricted to listed private repos |
| Fork-based attacks | **N/A** — no external contributors | Fork pull requests disabled for runner group |
| Persistent compromise | **Low** — no public workflow triggers | systemd resource limits; regular runner updates |
| Secret exposure | **Medium** — runner has Docker access | Secrets stored in GitHub Environments, not on runner filesystem |
| Lateral movement | **Low** — runner on DEV server (not PROD) | Dedicated `github-runner` user; no sudo; limited to Docker group; no production data on DEV |

### 7.2 Dev Server Security

| Measure | Implementation |
|---------|----------------|
| SSH hardening | Key-only auth, root login disabled |
| Firewall | UFW: only 22/tcp open |
| No production data | Dev databases use synthetic/anonymized data |
| Separation from PROD | Different server, different IP, no shared credentials |
| DSGVO compliance | No real customer data on dev server |

---

## 8. References

- [GitHub Actions Self-Hosted Runners](https://docs.github.com/en/actions/hosting-your-own-runners)
- [GitHub Self-Hosted Runner Security](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Workflow Dispatch API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
- [Windsurf Remote-SSH Documentation](https://docs.windsurf.com/windsurf/advanced)
- [Hetzner Cloud CX Series](https://www.hetzner.com/cloud/)
- [ADR-009: Centralized Deployment Architecture](./ADR-009-deployment-architecture.md)
- [Platform Architecture Master](../PLATFORM_ARCHITECTURE_MASTER.md)
- [Hetzner Deployment Prompt](../../concepts/hetzner_deployment_prompt.md)

---

## 9. Appendix

### A. Cost Comparison

| Item | Current (monthly) | After Migration (monthly) |
|------|-------------------|---------------------------|
| GitHub Actions minutes | ~3,300 (risk of overage) | 0 |
| Hetzner PROD server | existing | existing (unchanged) |
| Hetzner DEV server | — | €6.80 |
| Developer time (WSL issues) | ~2-4h | 0 |
| **Net effect** | | **+€6.80/month, -3,300 CI minutes, -2-4h/month dev time** |

### B. Compatibility with ADR-009

This ADR is fully compatible with ADR-009 (Centralized Deployment Architecture). The self-hosted runner executes the same reusable workflows defined in the platform repository. The only changes are:

1. `runs-on` changes from `ubuntu-latest` to `[self-hosted, hetzner, dev]`
2. `on: push` changes to `on: workflow_dispatch`
3. Build runs on DEV server, deploy step uses SSH from DEV to PROD for `docker compose pull && up`

ADR-009's reusable workflows, deployment-core package, and auto-healer integration remain unchanged.

---

## 10. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-16 | Achim Dehnert | Initial draft |
| 2026-02-16 | Cascade Review | R1: Runner PROD→DEV, Port 8000 entfernt, 7 Apps, Docker Build+Push Step, SSH-Deploy |
| 2026-02-16 | Cascade Review | R2: B-01 SSH-Key DEV→PROD, B-02 venv-Isolation CI, B-03 idempotente venvs, B-04 Debounce-Doku, B-05 Safety-Net Workflow-Filter, B-06 Rollback-CLI |
