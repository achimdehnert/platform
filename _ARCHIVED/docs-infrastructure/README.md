# Docs Infrastructure

Unified documentation system for BF Agent Platform with:
- **Sphinx** for documentation generation
- **GitHub Actions** for CI/CD
- **Hetzner** for hosting with immutable releases
- **Docker** for containerized serving
- **Host-Nginx** for TLS termination and caching

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  https://docs.iil.pet/                           │
├─────────────────────────────────────────────────────────────────┤
│  /                  → Landing Page (links to all docs)          │
│  /platform/         → Platform & Creative Services              │
│  /bfagent/          → BF Agent Core                             │
│  /mcp-hub/          → MCP Hub (MCP Server Collection)           │
│  /travel-beat/      → Travel Beat                               │
│  /api/              → Combined API Reference (AutoAPI)          │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Host Nginx (TLS termination, caching, routing)                 │
│  - SSL via Let's Encrypt Wildcard                               │
│  - Cache: HTML no-cache, assets 30d immutable                   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Docker: nginx:alpine (port 8081)                               │
│  - Read-only mount: /var/www/docs/current                       │
│  - Healthcheck every 30s                                        │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  /var/www/docs/                                                 │
│  ├── current -> releases/<latest-sha>  (atomic symlink)         │
│  ├── releases/                                                  │
│  │   ├── abc123/  (immutable, SHA-based)                        │
│  │   └── def456/                                                │
│  └── versions/                                                  │
│      ├── v1.0.0/  (tagged releases)                             │
│      └── v1.1.0/                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. GitHub Secrets

Repository → Settings → Secrets and variables → Actions:

| Secret | Description |
|--------|-------------|
| `HETZNER_HOST` | Server IP or hostname |
| `HETZNER_USER` | Deploy user (e.g., `deploy`) |
| `HETZNER_SSH_KEY` | Private SSH key |
| `HETZNER_PORT` | SSH port (optional, default 22) |

### 2. Server Setup

```bash
# On Hetzner server
sudo mkdir -p /var/www/docs/{releases,versions,current}
sudo mkdir -p /var/www/letsencrypt

# Create deploy user
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
sudo chown -R deploy:deploy /var/www/docs

# Start docs container
cd /opt/docs
sudo docker compose up -d

# Setup nginx vhost
sudo cp nginx/docs.bfagent.de.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/docs.bfagent.de.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 3. Local Development

```bash
# Install dependencies
pip install -r docs/requirements.txt

# Build HTML
sphinx-build -W -b html docs/source docs/_build/html

# Link check
sphinx-build -b linkcheck docs/source docs/_build/linkcheck

# Live preview
sphinx-autobuild docs/source docs/_build/html --port 8000
```

## Workflow

### Pull Request
1. Build docs with `-W` (warnings as errors)
2. Run linkcheck
3. Upload artifact for review

### Merge to main
1. Build docs
2. Deploy to `/var/www/docs/releases/<sha>/`
3. Atomic switch: `current` symlink
4. Cleanup: keep last 20 releases

### Tag (v*)
1. Build docs
2. Deploy to `/var/www/docs/versions/<tag>/`
3. No symlink switch (versioned docs persist)

## Rollback

```bash
# List recent releases
ls -1dt /var/www/docs.iil.pet/releases/* | head

# Switch to previous release
ln -sfn /var/www/docs.iil.pet/releases/<OLD_SHA> /var/www/docs.iil.pet/current

# Verify
curl -s https://docs.iil.pet/build-info.txt
```

## File Structure

```
docs-infrastructure/
├── README.md                           # This file
├── .github/
│   └── workflows/
│       └── docs.yml                    # CI/CD workflow
├── docs/
│   ├── requirements.txt                # Sphinx dependencies
│   └── source/
│       ├── conf.py                     # Sphinx configuration
│       ├── index.md                    # Landing page
│       ├── _static/                    # Static assets
│       ├── _templates/                 # Custom templates
│       ├── platform/                   # Platform docs
│       ├── bfagent/                    # BFAgent docs
│       └── api/                        # API reference
└── server/
    ├── docker-compose.yml              # Docs container
    ├── nginx/
    │   └── docs.bfagent.de.conf        # Nginx vhost
    └── SETUP_SERVER.md                 # Server setup guide
```
