# Deployment MCP

GitHub Actions & Deployment Tools Server.

## Installation

```bash
cd mcp-hub/deployment_mcp
pip install -e .
```

## Konfiguration

```json
{
  "mcpServers": {
    "deployment-mcp": {
      "command": "python",
      "args": ["-m", "deployment_mcp.server"],
      "env": {
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```

## Tools

### trigger_workflow

GitHub Actions Workflow starten.

```python
result = await trigger_workflow(
    repo="achimdehnert/bfagent",
    workflow="deploy.yml",
    ref="main",
    inputs={"environment": "production"},
)
```

### get_run_status

Status eines Workflow-Runs abrufen.

```python
result = await get_run_status(
    repo="achimdehnert/bfagent",
    run_id=12345,
)
```

### list_workflows

Alle Workflows eines Repos auflisten.

```python
result = await list_workflows(
    repo="achimdehnert/bfagent",
)
```

### get_deployment_status

Deployment-Status prüfen.

```python
result = await get_deployment_status(
    repo="achimdehnert/bfagent",
    environment="production",
)
```

## Use Cases

### CI/CD Automation

```python
# Workflow triggern
await trigger_workflow(
    repo="achimdehnert/bfagent",
    workflow="deploy.yml",
    ref="main",
)

# Status prüfen
status = await get_run_status(repo="achimdehnert/bfagent", run_id=run_id)
while status["status"] == "in_progress":
    await asyncio.sleep(30)
    status = await get_run_status(repo="achimdehnert/bfagent", run_id=run_id)

print(f"Deployment: {status['conclusion']}")
```
