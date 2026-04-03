"""Zentraler Secret-Resolver für alle Platform-Infra-Scripts.

Single Source of Truth für Secret-Auflösung. Jedes infra/scripts/*.py
importiert von hier statt eigene Token-Logik zu implementieren.

Auflösungs-Reihenfolge (First Match gewinnt):
  1. os.environ[ENV_VAR]
  2. os.environ[MCP_ENV_VAR]  (falls MCP den Token anders benennt)
  3. ~/.secrets/<canonical_file>
  4. ~/.secrets/<alternative_files>  (Legacy-Namen)
  5. MCP-Prozess-Env (liest /proc/<pid>/environ)

Nutzung:
    from infra.lib.secrets import get_secret, require_secret

    token = get_secret("cloudflare")
    token = require_secret("cloudflare")  # raises if missing

    # Alle Secrets auf einen Blick:
    python -m infra.lib.secrets

Referenz: ADR-157, ADR-156 §8
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SECRETS_DIR = Path.home() / ".secrets"

# ─── Kanonisches Secret-Registry ──────────────────────────────
# Jeder Eintrag: logical_name → {
#   env: primäre Env-Var,
#   mcp_env: Env-Var im MCP-Prozess (falls anders),
#   file: kanonischer Dateiname unter ~/.secrets/,
#   alt_files: alternative/legacy Dateinamen,
#   mcp_process: MCP-Prozessname zum Env-Scan,
#   description: Beschreibung,
#   test_url: optionale URL zum Validieren,
# }

REGISTRY: dict[str, dict] = {
    "cloudflare": {
        "env": "CLOUDFLARE_API_TOKEN",
        "mcp_env": (
            "DEPLOYMENT_MCP_CLOUDFLARE_API_TOKEN"
        ),
        "file": "cloudflare_api_token",
        "alt_files": [
            "cloudflare_write_token",
        ],
        "mcp_process": "deployment_mcp",
        "description": "Cloudflare DNS/Zone API",
        "test_url": (
            "https://api.cloudflare.com"
            "/client/v4/user/tokens/verify"
        ),
    },
    "cloudflare_access": {
        "env": "CLOUDFLARE_ACCESS_TOKEN",
        "mcp_env": (
            "DEPLOYMENT_MCP_CLOUDFLARE"
            "_ACCESS_TOKEN"
        ),
        "file": "cloudflare_access_token",
        "alt_files": [],
        "mcp_process": "deployment_mcp",
        "description": "Cloudflare Zero Trust",
    },
    "hetzner": {
        "env": "HETZNER_CLOUD_TOKEN",
        "mcp_env": (
            "DEPLOYMENT_MCP_HETZNER_CLOUD_TOKEN"
        ),
        "file": "hetzner_cloud_token",
        "alt_files": [],
        "mcp_process": "deployment_mcp",
        "description": "Hetzner Cloud API",
    },
    "github": {
        "env": "GITHUB_TOKEN",
        "mcp_env": (
            "GITHUB_PERSONAL_ACCESS_TOKEN"
        ),
        "file": "github_token",
        "alt_files": [],
        "mcp_process": None,
        "description": "GitHub PAT",
    },
    "ionos": {
        "env": "IONOS_API_KEY",
        "mcp_env": "DEPLOYMENT_MCP_IONOS_API_KEY",
        "file": "ionos_api_key",
        "alt_files": [],
        "mcp_process": "deployment_mcp",
        "description": "IONOS DNS API",
    },
    "openai": {
        "env": "OPENAI_API_KEY",
        "mcp_env": None,
        "file": "openai_api_key",
        "alt_files": [],
        "mcp_process": None,
        "description": "OpenAI API",
    },
    "anthropic": {
        "env": "ANTHROPIC_API_KEY",
        "mcp_env": None,
        "file": "anthropic_api_key",
        "alt_files": [],
        "mcp_process": None,
        "description": "Anthropic API",
    },
    "groq": {
        "env": "GROQ_API_KEY",
        "mcp_env": None,
        "file": "groq_api_key",
        "alt_files": ["groq_api_token"],
        "mcp_process": None,
        "description": "Groq API",
    },
    "together": {
        "env": "TOGETHER_API_KEY",
        "mcp_env": None,
        "file": "together_api_key",
        "alt_files": [],
        "mcp_process": None,
        "description": "Together AI API",
    },
    "pypi": {
        "env": "PYPI_TOKEN",
        "mcp_env": None,
        "file": "pypi_iildehnert_token",
        "alt_files": [],
        "mcp_process": None,
        "description": "PyPI Upload Token",
    },
    "dvelop": {
        "env": "DVELOP_API_KEY",
        "mcp_env": None,
        "file": "dvelop_api_key",
        "alt_files": [],
        "mcp_process": None,
        "description": "d.velop DMS API",
    },
    "paperless": {
        "env": "PAPERLESS_API_TOKEN",
        "mcp_env": "PAPERLESS_API_TOKEN",
        "file": None,
        "alt_files": [],
        "mcp_process": None,
        "description": "Paperless-ngx API",
    },
}


def _read_file(path: Path) -> str:
    """Read secret file, return stripped content."""
    try:
        if path.exists():
            return path.read_text(
                encoding="utf-8",
            ).strip()
    except (OSError, PermissionError):
        pass
    return ""


def _read_mcp_env(
    process_name: str,
    env_var: str,
) -> str:
    """Read env var from running MCP process."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", process_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        pids = result.stdout.strip().splitlines()
        if not pids:
            return ""
        pid = pids[0].strip()
        env_path = Path(f"/proc/{pid}/environ")
        if not env_path.exists():
            return ""
        raw = env_path.read_bytes()
        for entry in raw.split(b"\x00"):
            decoded = entry.decode(
                "utf-8", errors="replace",
            )
            if decoded.startswith(f"{env_var}="):
                return decoded.split("=", 1)[1]
    except (
        subprocess.TimeoutExpired,
        OSError,
        PermissionError,
    ):
        pass
    return ""


def get_secret(
    name: str,
    default: str = "",
) -> str:
    """Resolve a secret by logical name.

    Args:
        name: Logical name from REGISTRY
              (e.g. "cloudflare", "github")
        default: Fallback value

    Returns:
        Secret value or default
    """
    entry = REGISTRY.get(name)
    if not entry:
        return default

    # 1. Primary env var
    env_var = entry.get("env", "")
    if env_var:
        val = os.environ.get(env_var, "")
        if val:
            return val

    # 2. MCP env var name
    mcp_env = entry.get("mcp_env", "")
    if mcp_env and mcp_env != env_var:
        val = os.environ.get(mcp_env, "")
        if val:
            return val

    # 3. Canonical secret file
    canonical = entry.get("file", "")
    if canonical:
        val = _read_file(SECRETS_DIR / canonical)
        if val:
            return val

    # 4. Alternative/legacy files
    for alt in entry.get("alt_files", []):
        val = _read_file(SECRETS_DIR / alt)
        if val:
            return val

    # 5. MCP process env (last resort)
    proc = entry.get("mcp_process", "")
    if proc and mcp_env:
        val = _read_mcp_env(proc, mcp_env)
        if val:
            # Cache to file for next time
            if canonical:
                _cache_secret(canonical, val)
            return val

    return default


def _cache_secret(
    filename: str,
    value: str,
) -> None:
    """Write secret to ~/.secrets/ for caching."""
    path = SECRETS_DIR / filename
    try:
        path.write_text(value + "\n")
        path.chmod(0o600)
    except OSError:
        pass


def require_secret(name: str) -> str:
    """Get secret or raise RuntimeError."""
    val = get_secret(name)
    if not val:
        entry = REGISTRY.get(name, {})
        raise RuntimeError(
            f"Secret '{name}' nicht gefunden.\n"
            f"  Env: {entry.get('env', '?')}\n"
            f"  File: ~/.secrets/"
            f"{entry.get('file', '?')}\n"
            f"  MCP: {entry.get('mcp_env', '-')}"
        )
    return val


def verify_token(name: str) -> bool:
    """Test if a token actually works."""
    import urllib.request
    import json

    entry = REGISTRY.get(name, {})
    test_url = entry.get("test_url", "")
    if not test_url:
        return bool(get_secret(name))

    token = get_secret(name)
    if not token:
        return False

    try:
        req = urllib.request.Request(test_url)
        req.add_header(
            "Authorization", f"Bearer {token}",
        )
        resp = urllib.request.urlopen(
            req, timeout=10,
        )
        data = json.loads(resp.read())
        return data.get("success", False)
    except Exception:
        return False


def status_all() -> dict[str, dict]:
    """Check status of all known secrets."""
    results = {}
    for name, entry in REGISTRY.items():
        val = get_secret(name)
        results[name] = {
            "found": bool(val),
            "preview": (
                f"{val[:8]}..." if val else ""
            ),
            "description": entry.get(
                "description", "",
            ),
            "env": entry.get("env", ""),
            "file": entry.get("file", ""),
        }
    return results


def print_status() -> None:
    """Print status of all secrets to stdout."""
    print("Secret-Status (infra/lib/secrets.py)")
    print("=" * 60)
    for name, info in status_all().items():
        icon = "✅" if info["found"] else "❌"
        preview = info["preview"] or "MISSING"
        print(
            f"  {icon}  {name:20}"
            f" {preview:15}"
            f" {info['description']}"
        )


if __name__ == "__main__":
    print_status()

    # Validate Cloudflare token
    print("\n--- Token-Validierung ---")
    if get_secret("cloudflare"):
        ok = verify_token("cloudflare")
        icon = "✅" if ok else "❌"
        print(
            f"  {icon}  cloudflare"
            " API-Token funktioniert"
            if ok
            else f"  {icon}  cloudflare"
            " API-Token UNGÜLTIG!"
        )
    else:
        print("  ⏭  cloudflare: kein Token")

    sys.exit(0)
