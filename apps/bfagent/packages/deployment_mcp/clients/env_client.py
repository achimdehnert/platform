"""Environment Client for managing environment variables and secrets via SSH."""

import re
from typing import Any

from ..models import EnvVariable, Secret
from .ssh_client import SSHClient


class EnvClient:
    """Client for environment variable and secret management via SSH."""

    # Keys that should always be masked
    SENSITIVE_PATTERNS = [
        r".*password.*",
        r".*secret.*",
        r".*token.*",
        r".*api.?key.*",
        r".*private.*",
        r".*credential.*",
        r".*auth.*",
    ]

    def __init__(self, ssh_client: SSHClient):
        """Initialize environment client."""
        self.ssh = ssh_client

    def _is_sensitive(self, key: str) -> bool:
        """Check if key is sensitive and should be masked."""
        key_lower = key.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if re.match(pattern, key_lower):
                return True
        return False

    def _mask_value(self, value: str) -> str:
        """Mask sensitive value."""
        if len(value) <= 4:
            return "****"
        return value[:2] + "*" * (len(value) - 4) + value[-2:]

    # =========================================================================
    # ENV FILE OPERATIONS
    # =========================================================================

    async def list_env_vars(
        self,
        env_file: str,
        mask_sensitive: bool = True,
    ) -> list[EnvVariable]:
        """List environment variables from .env file."""
        if not await self.ssh.file_exists(env_file):
            return []

        content = await self.ssh.read_file(env_file)
        variables = []

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                is_sensitive = self._is_sensitive(key)
                display_value = self._mask_value(value) if (is_sensitive and mask_sensitive) else value

                variables.append(
                    EnvVariable(
                        key=key,
                        value=display_value,
                        masked=is_sensitive and mask_sensitive,
                    )
                )

        return variables

    async def get_env_var(
        self,
        env_file: str,
        key: str,
        mask_sensitive: bool = True,
    ) -> EnvVariable | None:
        """Get specific environment variable."""
        variables = await self.list_env_vars(env_file, mask_sensitive)
        for var in variables:
            if var.key == key:
                return var
        return None

    async def set_env_var(
        self,
        env_file: str,
        key: str,
        value: str,
    ) -> bool:
        """Set environment variable in .env file."""
        # SECURITY: Do not read/rewrite the full env file over SSH via an `echo` command.
        # That would leak secrets into local logs. Instead, update in-place on the server.

        # IMPORTANT: Keep this as a single-line shell script.
        # Do NOT embed literal newlines into the SSH command string, as that breaks quoting
        # and leads to confusing remote errors.

        # Escape value for inclusion in a double-quoted shell string and sed replacement.
        # NOTE: This doesn't try to be a perfect shell-escape for arbitrary binary data; it's
        # sufficient for typical env values (tokens, urls, tags).
        shell_value = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("$", "\\$")
        )

        cmd = (
            "sh -lc "
            "'"
            f"FILE=\"{env_file}\"; "
            f"KEY=\"{key}\"; "
            f"VALUE=\"{shell_value}\"; "
            "LINE=\"$KEY=\\\"$VALUE\\\"\"; "
            "if [ -f \"$FILE\" ]; then "
            "  if grep -q -E \"^$KEY=\" \"$FILE\"; then "
            "    sed -i -E \"s|^$KEY=.*|$LINE|\" \"$FILE\"; "
            "  else "
            "    printf \\\"\\\\n%s\\\\n\\\" \"$LINE\" >> \"$FILE\"; "
            "  fi; "
            "else "
            "  printf \\\"%s\\\\n\\\" \"$LINE\" > \"$FILE\"; "
            "fi; "
            "chmod 600 \"$FILE\""
            "'"
        )
        await self.ssh.run_checked(cmd)
        return True

    async def delete_env_var(self, env_file: str, key: str) -> bool:
        """Delete environment variable from .env file."""
        if not await self.ssh.file_exists(env_file):
            return False

        content = await self.ssh.read_file(env_file)
        lines = content.split("\n")

        new_lines = [
            line for line in lines
            if not line.strip().startswith(f"{key}=")
        ]

        if len(new_lines) == len(lines):
            return False  # Key not found

        new_content = "\n".join(new_lines)
        if not new_content.endswith("\n"):
            new_content += "\n"

        await self.ssh.write_file(env_file, new_content, mode="600")
        return True

    # =========================================================================
    # SECRET OPERATIONS
    # =========================================================================

    async def list_secrets(self, env_file: str) -> list[Secret]:
        """List secrets (sensitive env vars) without values."""
        variables = await self.list_env_vars(env_file, mask_sensitive=False)

        secrets = []
        for var in variables:
            if self._is_sensitive(var.key):
                secrets.append(
                    Secret(
                        key=var.key,
                        exists=True,
                        masked_value=self._mask_value(var.value),
                    )
                )
        return secrets

    async def set_secret(self, env_file: str, key: str, value: str) -> bool:
        """Set a secret (same as set_env_var but for sensitive values)."""
        return await self.set_env_var(env_file, key, value)

    async def delete_secret(self, env_file: str, key: str) -> bool:
        """Delete a secret."""
        return await self.delete_env_var(env_file, key)

    async def secret_exists(self, env_file: str, key: str) -> bool:
        """Check if a secret exists."""
        var = await self.get_env_var(env_file, key, mask_sensitive=False)
        return var is not None

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    async def set_env_vars_batch(
        self,
        env_file: str,
        variables: dict[str, str],
    ) -> int:
        """Set multiple environment variables at once."""
        count = 0
        for key, value in variables.items():
            if await self.set_env_var(env_file, key, value):
                count += 1
        return count

    async def export_env(self, env_file: str) -> dict[str, str]:
        """Export all env vars as dict (unmasked)."""
        variables = await self.list_env_vars(env_file, mask_sensitive=False)
        return {var.key: var.value for var in variables}

    async def import_env(
        self,
        env_file: str,
        variables: dict[str, str],
        overwrite: bool = True,
    ) -> int:
        """Import env vars from dict."""
        if not overwrite:
            existing = await self.export_env(env_file)
            variables = {k: v for k, v in variables.items() if k not in existing}

        return await self.set_env_vars_batch(env_file, variables)

    # =========================================================================
    # VALIDATION
    # =========================================================================

    async def validate_required_vars(
        self,
        env_file: str,
        required_keys: list[str],
    ) -> dict[str, Any]:
        """Validate that required env vars are set."""
        variables = await self.export_env(env_file)

        missing = []
        empty = []

        for key in required_keys:
            if key not in variables:
                missing.append(key)
            elif not variables[key]:
                empty.append(key)

        return {
            "valid": not missing and not empty,
            "missing": missing,
            "empty": empty,
        }
