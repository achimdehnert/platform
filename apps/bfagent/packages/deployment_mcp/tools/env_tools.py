"""Environment Variable and Secret Tools for MCP."""

from typing import Any

from ..clients.env_client import EnvClient
from ..clients.ssh_client import SSHClient
from ..settings import settings


def _get_env_client(host: str | None = None) -> tuple[SSHClient, EnvClient]:
    """Get SSH and Env clients."""
    ssh = SSHClient(host=host or settings.ssh_host)
    env = EnvClient(ssh)
    return ssh, env


# =============================================================================
# ENVIRONMENT VARIABLE TOOLS
# =============================================================================


async def env_list(
    env_file: str,
    host: str | None = None,
    mask_sensitive: bool = True,
) -> dict[str, Any]:
    """List environment variables from .env file."""
    ssh, env = _get_env_client(host)
    try:
        await ssh.connect()
        variables = await env.list_env_vars(env_file, mask_sensitive)
        return {
            "success": True,
            "count": len(variables),
            "env_file": env_file,
            "variables": [
                {
                    "key": v.key,
                    "value": v.value,
                    "masked": v.masked,
                }
                for v in variables
            ],
        }
    finally:
        await ssh.disconnect()


async def env_get(
    env_file: str,
    key: str,
    host: str | None = None,
    mask_sensitive: bool = True,
) -> dict[str, Any]:
    """Get specific environment variable."""
    ssh, env = _get_env_client(host)
    try:
        await ssh.connect()
        var = await env.get_env_var(env_file, key, mask_sensitive)

        if not var:
            return {"success": False, "error": f"Variable '{key}' not found"}

        return {
            "success": True,
            "variable": {
                "key": var.key,
                "value": var.value,
                "masked": var.masked,
            },
        }
    finally:
        await ssh.disconnect()


async def env_set(
    env_file: str,
    key: str,
    value: str,
    host: str | None = None,
) -> dict[str, Any]:
    """Set environment variable."""
    ssh, env = _get_env_client(host)
    try:
        await ssh.connect()
        success = await env.set_env_var(env_file, key, value)
        return {
            "success": success,
            "message": f"Variable '{key}' set in {env_file}",
        }
    finally:
        await ssh.disconnect()


async def env_delete(
    env_file: str,
    key: str,
    host: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete environment variable."""
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to delete variable.",
            "would_delete": key,
        }

    ssh, env = _get_env_client(host)
    try:
        await ssh.connect()
        success = await env.delete_env_var(env_file, key)

        if not success:
            return {"success": False, "error": f"Variable '{key}' not found"}

        return {
            "success": True,
            "message": f"Variable '{key}' deleted from {env_file}",
        }
    finally:
        await ssh.disconnect()


# =============================================================================
# SECRET TOOLS
# =============================================================================


async def secret_list(
    env_file: str,
    host: str | None = None,
) -> dict[str, Any]:
    """List secrets (sensitive env vars) without values."""
    ssh, env = _get_env_client(host)
    try:
        await ssh.connect()
        secrets = await env.list_secrets(env_file)
        return {
            "success": True,
            "count": len(secrets),
            "env_file": env_file,
            "secrets": [
                {
                    "key": s.key,
                    "masked_value": s.masked_value,
                }
                for s in secrets
            ],
        }
    finally:
        await ssh.disconnect()


async def secret_set(
    env_file: str,
    key: str,
    value: str,
    host: str | None = None,
) -> dict[str, Any]:
    """Set a secret (sensitive env var)."""
    ssh, env = _get_env_client(host)
    try:
        await ssh.connect()
        success = await env.set_secret(env_file, key, value)
        return {
            "success": success,
            "message": f"Secret '{key}' set in {env_file}",
        }
    finally:
        await ssh.disconnect()


async def secret_delete(
    env_file: str,
    key: str,
    host: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete a secret."""
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to delete secret.",
            "would_delete": key,
        }

    ssh, env = _get_env_client(host)
    try:
        await ssh.connect()
        success = await env.delete_secret(env_file, key)

        if not success:
            return {"success": False, "error": f"Secret '{key}' not found"}

        return {
            "success": True,
            "message": f"Secret '{key}' deleted from {env_file}",
        }
    finally:
        await ssh.disconnect()


# =============================================================================
# VALIDATION TOOLS
# =============================================================================


async def env_validate(
    env_file: str,
    required_keys: list[str],
    host: str | None = None,
) -> dict[str, Any]:
    """Validate required environment variables are set."""
    ssh, env = _get_env_client(host)
    try:
        await ssh.connect()
        result = await env.validate_required_vars(env_file, required_keys)
        return {
            "success": result["valid"],
            "valid": result["valid"],
            "missing": result["missing"],
            "empty": result["empty"],
        }
    finally:
        await ssh.disconnect()
