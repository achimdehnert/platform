from __future__ import annotations

from pathlib import Path

from ..exceptions import CADSecurityError


def validate_file_path(file_path: Path, allowed_extensions: set[str]) -> Path:
    if file_path.suffix.lower() not in allowed_extensions:
        raise CADSecurityError(
            code="INVALID_EXTENSION",
            message=f"Erlaubt: {allowed_extensions}, erhalten: {file_path.suffix}",
        )

    if file_path.is_symlink():
        raise CADSecurityError(code="SYMLINK_NOT_ALLOWED", message="Symlinks sind nicht erlaubt")

    resolved = file_path.resolve()

    return resolved
