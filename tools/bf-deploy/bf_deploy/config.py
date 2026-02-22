"""Application registry and configuration."""
from __future__ import annotations

from pathlib import Path

# ── Application Registry ─────────────────────────────────────────
# Each entry maps an app name to its GitHub repo and health URL.

APPS: dict[str, dict[str, str]] = {
    "bfagent": {
        "repo": "achimdehnert/bfagent",
        "workflow": "ci.yml",
        "health": "https://bfagent.iil.pet/health/", # noqa: hardcode
    },
    "travel-beat": {
        "repo": "achimdehnert/travel-beat",
        "workflow": "deploy.yml",
        "health": "https://drifttales.app/health/", # noqa: hardcode
    },
    "risk-hub": {
        "repo": "achimdehnert/risk-hub",
        "workflow": "docker-build.yml",
        "health": "https://demo.schutztat.de/health/", # noqa: hardcode
    },
    "weltenhub": {
        "repo": "achimdehnert/weltenhub",
        "workflow": "ci.yml",
        "health": "https://weltenforger.com/health/",
    },
    "pptx-hub": {
        "repo": "achimdehnert/pptx-hub",
        "workflow": "cd-production.yml",
        "health": "https://prezimo.de/health/",
    },
    "trading-hub": {
        "repo": "achimdehnert/trading-hub",
        "workflow": "ci-cd.yml",
        "health": "https://trading-hub.iil.pet/health/", # noqa: hardcode
    },
}

# ── Prod Server ──────────────────────────────────────────────
PROD_HOST = "88.198.191.108"  # noqa: hardcode
PROD_USER = "root"

# ── Debounce ─────────────────────────────────────────────────
DEBOUNCE_FILE = Path.home() / ".bf-deploy" / "debounce.json"
DEBOUNCE_SECONDS = 60
