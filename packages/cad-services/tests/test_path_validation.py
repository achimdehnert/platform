from pathlib import Path

import pytest

from cad_services.exceptions import CADSecurityError
from cad_services.utils.path_validation import validate_file_path


def test_validate_file_path_rejects_extension(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(CADSecurityError) as e:
        validate_file_path(p, allowed_extensions={".ifc"})
    assert e.value.code == "INVALID_EXTENSION"


def test_validate_file_path_rejects_symlink(tmp_path: Path):
    target = tmp_path / "a.ifc"
    target.write_text("x", encoding="utf-8")

    link = tmp_path / "link.ifc"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")

    with pytest.raises(CADSecurityError) as e:
        validate_file_path(link, allowed_extensions={".ifc"})
    assert e.value.code == "SYMLINK_NOT_ALLOWED"
