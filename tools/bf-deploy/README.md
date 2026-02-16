# bf-deploy

CLI tool for deploying BF Agent Platform applications.

See [ADR-042](../../docs/adr/ADR-042-dev-environment-deploy-workflow.md) for architecture details.

## Installation

```bash
pip install -e tools/bf-deploy/
```

## Usage

```bash
# Deploy a single app
bf deploy travel-beat

# Deploy multiple apps
bf deploy travel-beat bfagent

# Deploy all apps
bf deploy --all

# Force deploy (ignore debounce)
bf deploy --force travel-beat

# Show deploy status
bf status

# Rollback to a specific image tag
bf rollback travel-beat sha-abc1234
```

## Configuration

Set your GitHub token:

```bash
# Option A: environment variable
export GITHUB_TOKEN=ghp_...

# Option B: token file
mkdir -p ~/.bf-deploy
echo "ghp_..." > ~/.bf-deploy/token
chmod 600 ~/.bf-deploy/token
```
