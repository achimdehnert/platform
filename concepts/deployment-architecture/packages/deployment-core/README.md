# deployment-core

Shared deployment utilities for the BF Agent Platform.

## Features

- **Health Checks**: HTTP, TCP, and command-based probes with retry logic
- **AI Error Analysis**: Claude-powered error categorization and fix recommendations
- **Smart Rollback**: Deployment history tracking with automatic rollback
- **Notifications**: Slack, Email, and custom notification channels

## Installation

```bash
# Basic installation
pip install deployment-core

# With Claude AI support
pip install deployment-core[anthropic]

# With all features
pip install deployment-core[all]
```

## Quick Start

### Health Checks

```python
import asyncio
from deployment_core import HealthChecker, HTTPProbe, TCPProbe

async def check_health():
    checker = HealthChecker(timeout=60, retries=5, interval=10)
    
    # Add probes
    checker.add_probe(HTTPProbe("https://myapp.example.com/health/"))
    checker.add_probe(TCPProbe("localhost", 5432, name="postgres"))
    checker.add_probe(TCPProbe("localhost", 6379, name="redis"))
    
    result = await checker.run()
    
    if result.is_healthy:
        print("✅ All checks passed!")
    else:
        print(f"❌ Health check failed: {result.error}")
    
    return result

asyncio.run(check_health())
```

### Error Analysis

```python
import asyncio
import os
from deployment_core import ErrorAnalyzer

async def analyze_error():
    analyzer = ErrorAnalyzer(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    error_log = """
    Error: OOMKilled - Container exceeded memory limit
    Exit code: 137
    """
    
    analysis = await analyzer.analyze(
        error_log=error_log,
        context={"app": "travel-beat", "deploy_path": "/opt/travel-beat"}
    )
    
    print(f"Category: {analysis.category.value}")
    print(f"Severity: {analysis.severity.value}")
    print(f"Confidence: {analysis.confidence}%")
    print(f"Root Cause: {analysis.root_cause}")
    
    if analysis.can_auto_fix:
        print("Auto-fix available:")
        for cmd in analysis.fix.commands:
            print(f"  $ {cmd}")
    
    return analysis

asyncio.run(analyze_error())
```

### Rollback Management

```python
import asyncio
from deployment_core import RollbackManager

async def manage_deployment():
    manager = RollbackManager(
        deploy_path="/opt/travel-beat",
        app_name="travel-beat",
        compose_file="docker-compose.prod.yml",
        env_file=".env.prod"
    )
    
    # Record new deployment
    deployment_id = await manager.record_deployment(
        image_tag="abc123",
        previous_tag="def456",
        triggered_by="github-actions"
    )
    
    # ... deployment logic ...
    
    # On failure, rollback
    if deployment_failed:
        result = await manager.rollback(deployment_id)
        print(f"Rollback: {'Success' if result.success else 'Failed'}")
    else:
        await manager.mark_success(deployment_id)

asyncio.run(manage_deployment())
```

### Notifications

```python
import asyncio
from deployment_core import SlackNotifier

async def notify():
    notifier = SlackNotifier(
        webhook_url=os.environ["SLACK_WEBHOOK_URL"],
        channel="#deployments"
    )
    
    await notifier.notify_deployment_success(
        app="travel-beat",
        tag="v1.0.0",
        environment="production",
        url="https://travel-beat.iil.pet"
    )

asyncio.run(notify())
```

## CLI Tools

### Health Check

```bash
# Basic health check
deploy-health https://myapp.example.com/health/

# With retries and JSON output
deploy-health https://myapp.example.com/health/ --retries 5 --interval 10 --json

# Deep health check (includes DB, Redis)
deploy-health https://myapp.example.com/health/ --deep
```

### Error Analysis

```bash
# Analyze error log file
deploy-analyze error.log

# With context
deploy-analyze error.log --app travel-beat --deploy-path /opt/travel-beat

# Use Claude AI for analysis
deploy-analyze error.log --use-ai

# Output as JSON
deploy-analyze error.log --json
```

## GitHub Actions Integration

See the reusable workflows in `.github/workflows/`:

```yaml
# In your app's workflow
jobs:
  deploy:
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@v1
    with:
      app_name: my-app
      deploy_path: /opt/my-app
      health_url: https://my-app.example.com/health/
      enable_auto_healer: true
    secrets: inherit
```

## Error Patterns

The analyzer includes built-in patterns for common deployment errors:

| Pattern | Category | Auto-Fix |
|---------|----------|----------|
| OOMKilled | RUNTIME | No |
| Disk full | INFRASTRUCTURE | Yes |
| Image not found | BUILD | Yes |
| Connection refused | NETWORK | No |
| Permission denied (SSH) | PERMISSION | Yes |
| Rate limit | INFRASTRUCTURE | Retry |

## Architecture

```
deployment-core/
├── deployment_core/
│   ├── __init__.py       # Public API
│   ├── health.py         # Health check probes
│   ├── healing.py        # AI error analysis
│   ├── rollback.py       # Rollback management
│   ├── notify.py         # Notifications
│   └── cli.py            # CLI tools
├── tests/
│   ├── test_health.py
│   ├── test_healing.py
│   └── test_rollback.py
└── pyproject.toml
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .

# Type checking
mypy deployment_core
```

## License

MIT
