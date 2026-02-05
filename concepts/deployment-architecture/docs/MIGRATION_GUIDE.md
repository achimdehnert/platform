# Migration Guide: To Platform Reusable Workflows

## Overview

This guide explains how to migrate your application from individual CI/CD workflows to the platform's reusable workflows.

## Before vs After

### Before: ~800 lines across 4 files

```
travel-beat/.github/workflows/
├── ci.yml              # ~120 lines - Lint, test, security
├── cd-production.yml   # ~130 lines - Deploy to production
├── deploy.yml          # ~525 lines - Full pipeline with rollback
└── security.yml        # ~45 lines  - Weekly security scan

Total: ~820 lines
```

### After: ~80 lines in 1 file

```
travel-beat/.github/workflows/
└── ci-cd.yml           # ~80 lines - Everything!

Total: ~80 lines (90% reduction!)
```

## Migration Steps

### Step 1: Add Platform as Dependency

Ensure your repository can access the platform workflows:

```yaml
# Your workflow can now use:
uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
```

### Step 2: Create Consolidated Workflow

Replace all existing workflows with a single file:

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  ci:
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
    with:
      python_version: "3.12"
      coverage_threshold: 70
    secrets: inherit

  security:
    uses: achimdehnert/platform/.github/workflows/_security-scan.yml@v1
    secrets: inherit

  build:
    needs: [ci]
    if: github.ref == 'refs/heads/main'
    uses: achimdehnert/platform/.github/workflows/_build-docker.yml@v1
    with:
      dockerfile: docker/Dockerfile
    secrets: inherit

  deploy:
    needs: [build, security]
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@v1
    with:
      app_name: your-app
      deploy_path: /opt/your-app
      health_url: https://your-app.example.com/health/
      enable_auto_healer: true
    secrets: inherit
```

### Step 3: Configure Secrets

Ensure these secrets are set in your repository:

| Secret | Description |
|--------|-------------|
| `HETZNER_HOST` | Hetzner server IP/hostname |
| `HETZNER_USER` | SSH username |
| `HETZNER_SSH_KEY` | Private SSH key |
| `ANTHROPIC_API_KEY` | (Optional) For AI error analysis |
| `SLACK_WEBHOOK_URL` | (Optional) For notifications |

### Step 4: Test in Non-Production First

1. Create a test branch
2. Push changes
3. Verify CI pipeline works
4. Test deploy to staging first

### Step 5: Remove Old Workflows

Once verified, delete the old workflow files:

```bash
git rm .github/workflows/ci.yml
git rm .github/workflows/cd-production.yml  
git rm .github/workflows/deploy.yml
git rm .github/workflows/security.yml
```

## Workflow Input Reference

### _ci-python.yml

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `python_version` | string | `3.12` | Python version |
| `coverage_threshold` | number | `70` | Minimum coverage % |
| `requirements_file` | string | `requirements.txt` | Main requirements |
| `dev_requirements_file` | string | `requirements/dev.txt` | Dev requirements |
| `source_dir` | string | `apps/` | Source directory |
| `django_settings_module` | string | `config.settings.test` | Django settings |
| `skip_tests` | boolean | `false` | Skip tests |
| `run_security_scan` | boolean | `true` | Run Bandit scan |

### _build-docker.yml

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `dockerfile` | string | `docker/Dockerfile` | Dockerfile path |
| `context` | string | `.` | Build context |
| `platforms` | string | `linux/amd64` | Target platforms |
| `push` | boolean | `true` | Push to registry |
| `scan_image` | boolean | `true` | Trivy scan |

### _deploy-hetzner.yml

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `app_name` | string | **required** | Application name |
| `deploy_path` | string | **required** | Server deploy path |
| `health_url` | string | **required** | Health check URL |
| `compose_file` | string | `docker-compose.prod.yml` | Compose file |
| `env_file` | string | `.env.prod` | Environment file |
| `enable_auto_healer` | boolean | `true` | AI error analysis |
| `auto_fix_enabled` | boolean | `false` | Auto-fix errors |
| `health_check_retries` | number | `10` | Health check retries |
| `deep_health_check` | boolean | `true` | Deep health checks |
| `notify_slack` | boolean | `true` | Slack notifications |

### _security-scan.yml

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `scan_filesystem` | boolean | `true` | Trivy filesystem scan |
| `scan_secrets` | boolean | `true` | Gitleaks scan |
| `scan_dependencies` | boolean | `true` | Safety scan |
| `severity` | string | `CRITICAL,HIGH` | Severity filter |
| `fail_on_vulnerability` | boolean | `false` | Fail on vulns |

## Customization

### Adding App-Specific Steps

You can add custom jobs that run after the reusable workflows:

```yaml
jobs:
  # ... reusable workflow jobs ...

  post-deploy:
    needs: [deploy]
    runs-on: ubuntu-latest
    steps:
      - name: Custom post-deploy step
        run: |
          # Your custom logic here
```

### Overriding Behavior

For special cases, you can still define custom jobs alongside reusable ones:

```yaml
jobs:
  ci:
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
    # ...

  # Custom integration tests
  integration-tests:
    needs: [ci]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: ./scripts/integration-tests.sh
```

## Troubleshooting

### Workflow Not Found

```
Error: achimdehnert/platform/.github/workflows/_ci-python.yml@v1 not found
```

**Solution**: Ensure the platform repository is public or you have access.

### Secrets Not Passed

```
Error: HETZNER_HOST is required
```

**Solution**: Add `secrets: inherit` to pass repository secrets.

### Version Mismatch

**Solution**: Use explicit versions: `@v1`, `@v2`, or `@main` for latest.

## Support

- Issues: [platform/issues](https://github.com/achimdehnert/platform/issues)
- ADR: [ADR-009: Deployment Architecture](docs/adr/ADR-009-deployment-architecture.md)
