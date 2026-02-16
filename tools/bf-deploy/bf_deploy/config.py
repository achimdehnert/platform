"""Application registry and configuration."""
from __future__ import annotations

from pathlib import Path

# ── Application Registry ─────────────────────────────────────────
# Each entry maps an app name to its GitHub repo and health URL.

APPS: dict[str, dict[str, str]] = {
    "bfagent": {
        "repo": "achimdehnert/bfagent",
        "health": "https://bfagent.iil.pet/health/",
    },
    "travel-beat": {
        "repo": "achimdehnert/travel-beat",
        "health": "https://drifttales.app/health/",
    },
    "mcp-hub": {
        "repo": "achimdehnert/mcp-hub",
        "health": "https://mcp-hub.iil.pet/health/",
    },
    "risk-hub": {
        "repo": "achimdehnert/risk-hub",
        "health": "https://schutztat.app/health/",
    },
    "weltenhub": {
        "repo": "achimdehnert/weltenhub",
        "health": "https://weltenforger.app/health/",
    },
    "pptx-hub": {
        "repo": "achimdehnert/pptx-hub",
        "health": "https://pptx-hub.iil.pet/health/",
    },
    "trading-hub": {
        "repo": "achimdehnert/trading-hub",
        "health": "https://trading-hub.iil.pet/health/",
    },
}

# ── Prod Server ──────────────────────────────────────────────────
PROD_HOST = "88.198.191.108"
PROD_USER = "root"

# ── Debounce ─────────────────────────────────────────────────────
DEBOUNCE_FILE = Path.home() / ".bf-deploy" / "debounce.json"
DEBOUNCE_SECONDS = 60

# ── Deploy Workflow ──────────────────────────────────────────────
DEPLOY_WORKFLOW = "deploy.yml"
