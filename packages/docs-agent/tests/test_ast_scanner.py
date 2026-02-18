"""Tests for the AST docstring coverage scanner."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from docs_agent.analyzer.ast_scanner import scan_module, scan_repo
from docs_agent.models import ItemKind


@pytest.fixture()
def tmp_py_file(tmp_path: Path) -> Path:
    """Create a temporary Python file with mixed documentation."""
    code = dedent('''\
        """Module docstring."""


        class MyModel:
            """A documented class."""

            def documented_method(self):
                """This method has a docstring."""
                pass

            def undocumented_method(self):
                pass

            def _private_method(self):
                pass

            def __str__(self):
                return "skip me"


        def public_function():
            pass


        def documented_function():
            """Has a docstring."""
            pass


        async def async_undocumented():
            pass
    ''')
    py_file = tmp_path / "sample.py"
    py_file.write_text(code)
    return py_file


@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    """Create a temporary repo structure with apps/."""
    apps = tmp_path / "apps" / "core"
    apps.mkdir(parents=True)

    (apps / "__init__.py").write_text("")
    (apps / "models.py").write_text(dedent('''\
        """Core models."""


        class Organization:
            """An organization."""
            pass


        class User:
            pass
    '''))
    (apps / "services.py").write_text(dedent('''\
        def create_org():
            """Create an organization."""
            pass


        def delete_org():
            pass
    '''))

    # migrations should be skipped
    mig = apps / "migrations"
    mig.mkdir()
    (mig / "0001_initial.py").write_text("pass")

    return tmp_path


def test_should_scan_module_with_mixed_docs(tmp_py_file: Path) -> None:
    """Scan a module with both documented and undocumented items."""
    result = scan_module(tmp_py_file)

    assert result.total_items > 0
    assert result.documented_items > 0
    assert result.documented_items < result.total_items

    names = {item.name for item in result.items}
    assert "MyModel" in names
    assert "documented_method" in names
    assert "undocumented_method" in names
    assert "public_function" in names

    # Private methods should be excluded
    assert "_private_method" not in names
    # Dunder __str__ should be skipped
    assert "__str__" not in names


def test_should_report_correct_coverage(tmp_py_file: Path) -> None:
    """Coverage percentage should reflect documented ratio."""
    result = scan_module(tmp_py_file)

    documented_names = {
        item.name for item in result.items if item.has_docstring
    }
    assert "sample" in documented_names  # module docstring
    assert "MyModel" in documented_names
    assert "documented_method" in documented_names
    assert "documented_function" in documented_names

    assert 0 < result.coverage_pct < 100


def test_should_identify_undocumented_items(tmp_py_file: Path) -> None:
    """Undocumented property should list items without docstrings."""
    result = scan_module(tmp_py_file)

    undoc_names = {item.name for item in result.undocumented}
    assert "undocumented_method" in undoc_names
    assert "public_function" in undoc_names
    assert "async_undocumented" in undoc_names


def test_should_assign_correct_kinds(tmp_py_file: Path) -> None:
    """Items should have correct ItemKind."""
    result = scan_module(tmp_py_file)

    kind_map = {item.name: item.kind for item in result.items}
    assert kind_map["sample"] == ItemKind.MODULE
    assert kind_map["MyModel"] == ItemKind.CLASS


def test_should_scan_repo_apps_only(tmp_repo: Path) -> None:
    """Repo scan with apps_only should only include apps/ files."""
    result = scan_repo(tmp_repo, apps_only=True)

    assert len(result.modules) >= 2  # models.py + services.py
    assert result.total_items > 0

    # migrations should be excluded
    module_files = {m.file_path.name for m in result.modules}
    assert "0001_initial.py" not in module_files
    assert "__init__.py" not in module_files


def test_should_handle_syntax_error(tmp_path: Path) -> None:
    """Files with syntax errors should be skipped gracefully."""
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def broken(:\n  pass")

    result = scan_module(bad_file)
    assert result.total_items == 0


def test_should_handle_empty_module(tmp_path: Path) -> None:
    """Empty files should still report module-level coverage."""
    empty = tmp_path / "empty.py"
    empty.write_text("")

    result = scan_module(empty)
    assert result.total_items == 1  # module itself
    assert result.documented_items == 0
