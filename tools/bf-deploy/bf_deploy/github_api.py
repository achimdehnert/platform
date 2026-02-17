"""GitHub API interactions for workflow dispatch."""
from __future__ import annotations

import httpx


def trigger_workflow(
    repo: str,
    token: str,
    workflow: str = "deploy.yml",
    ref: str = "main",
    environment: str = "production",
) -> int:
    """Trigger workflow_dispatch and return HTTP status code.

    Returns 204 on success.
    """
    url = (
        f"https://api.github.com/repos/{repo}"
        f"/actions/workflows/{workflow}/dispatches"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"ref": ref, "inputs": {"environment": environment}}

    resp = httpx.post(url, headers=headers, json=payload, timeout=10)
    return resp.status_code


def get_latest_run(
    repo: str,
    token: str,
) -> dict | None:
    """Get latest workflow run for a repo."""
    url = (
        f"https://api.github.com/repos/{repo}"
        f"/actions/runs?per_page=1"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }
    resp = httpx.get(url, headers=headers, timeout=10)
    if resp.status_code == 200:
        runs = resp.json().get("workflow_runs", [])
        return runs[0] if runs else None
    return None
