"""Tests for the libcst-based code inserter."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

pytest.importorskip("libcst")

from docs_agent.generator.code_inserter import insert_docstrings  # noqa: E402


@pytest.fixture()
def sample_file(tmp_path: Path) -> Path:
    """Create a Python file without docstrings."""
    code = dedent('''\
        class MyModel:
            pass


        def process_data(items):
            return [x for x in items if x]


        class Service:
            def handle(self, request):
                return None

            def validate(self, data):
                """Already documented."""
                return True
    ''')
    py_file = tmp_path / "sample.py"
    py_file.write_text(code)
    return py_file


def test_should_insert_function_docstring(sample_file: Path) -> None:
    """Insert a docstring into an undocumented function."""
    result = insert_docstrings(
        sample_file,
        {"process_data": "Process and filter data items."},
        dry_run=True,
    )

    assert result.changed
    assert result.items_inserted == 1
    assert '"""Process and filter data items."""' in result.modified_source


def test_should_insert_class_docstring(sample_file: Path) -> None:
    """Insert a docstring into an undocumented class."""
    result = insert_docstrings(
        sample_file,
        {"MyModel": "A data model."},
        dry_run=True,
    )

    assert result.changed
    assert result.items_inserted == 1
    assert '"""A data model."""' in result.modified_source


def test_should_skip_already_documented(sample_file: Path) -> None:
    """Skip items that already have a docstring."""
    result = insert_docstrings(
        sample_file,
        {"validate": "Validate the data."},
        dry_run=True,
    )

    assert result.items_skipped == 1
    # Original docstring should be preserved
    assert '"""Already documented."""' in result.modified_source


def test_should_insert_multiple(sample_file: Path) -> None:
    """Insert multiple docstrings in one pass."""
    result = insert_docstrings(
        sample_file,
        {
            "MyModel": "A data model.",
            "process_data": "Process items.",
            "handle": "Handle a request.",
        },
        dry_run=True,
    )

    assert result.items_inserted == 3
    assert '"""A data model."""' in result.modified_source
    assert '"""Process items."""' in result.modified_source
    assert '"""Handle a request."""' in result.modified_source


def test_should_not_write_in_dry_run(sample_file: Path) -> None:
    """Dry run should not modify the file on disk."""
    original = sample_file.read_text()

    insert_docstrings(
        sample_file,
        {"MyModel": "A model."},
        dry_run=True,
    )

    assert sample_file.read_text() == original


def test_should_write_when_not_dry_run(sample_file: Path) -> None:
    """Non-dry-run should write changes to disk."""
    insert_docstrings(
        sample_file,
        {"MyModel": "A model."},
        dry_run=False,
    )

    content = sample_file.read_text()
    assert '"""A model."""' in content
