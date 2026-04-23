"""AST-based docstring coverage scanner.

Scans Python modules via the `ast` module and reports undocumented items:
classes, functions, methods. No LLM required — pure static analysis.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from docs_agent.models import CodeItem, ItemKind, ModuleCoverage, RepoCoverage

logger = logging.getLogger(__name__)

SKIP_DIRS: set[str] = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "migrations",
    "_build",
    "_archive",
    "static",
    "staticfiles",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    "eggs",
    "*.egg-info",
}

SKIP_FILES: set[str] = {
    "__init__.py",
    "conftest.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
}


def _should_skip_dir(dirname: str) -> bool:
    """Check if directory should be skipped."""
    return dirname in SKIP_DIRS or dirname.startswith(".")


def _should_skip_file(filename: str) -> bool:
    """Check if file should be skipped."""
    return filename in SKIP_FILES or filename.startswith("test_")


def _has_docstring(node: ast.AST) -> bool:
    """Check if an AST node has a docstring."""
    if not hasattr(node, "body") or not node.body:
        return False
    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        return isinstance(first.value.value, str)
    return False


def _is_private(name: str) -> bool:
    """Check if name is private (single underscore prefix, not dunder)."""
    return name.startswith("_") and not name.startswith("__")


def _is_dunder(name: str) -> bool:
    """Check if name is a dunder method."""
    return name.startswith("__") and name.endswith("__")


SKIP_DUNDERS: set[str] = {
    "__init__",
    "__str__",
    "__repr__",
    "__eq__",
    "__hash__",
    "__lt__",
    "__le__",
    "__gt__",
    "__ge__",
    "__len__",
    "__bool__",
    "__contains__",
    "__iter__",
    "__next__",
    "__enter__",
    "__exit__",
    "__call__",
    "__getattr__",
    "__setattr__",
    "__delattr__",
    "__getitem__",
    "__setitem__",
    "__delitem__",
}


def scan_module(file_path: Path) -> ModuleCoverage:
    """Scan a single Python module for docstring coverage.

    Args:
        file_path: Path to the Python file.

    Returns:
        ModuleCoverage with all documentable items and their status.
    """
    coverage = ModuleCoverage(file_path=file_path)

    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Cannot read %s: %s", file_path, exc)
        return coverage

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        logger.warning("Syntax error in %s: %s", file_path, exc)
        return coverage

    # Module-level docstring
    has_module_doc = _has_docstring(tree)
    coverage.items.append(
        CodeItem(
            name=file_path.stem,
            kind=ItemKind.MODULE,
            line=1,
            has_docstring=has_module_doc,
            file_path=file_path,
        )
    )
    coverage.total_items += 1
    coverage.documented_items += int(has_module_doc)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            has_doc = _has_docstring(node)
            coverage.items.append(
                CodeItem(
                    name=node.name,
                    kind=ItemKind.CLASS,
                    line=node.lineno,
                    has_docstring=has_doc,
                    file_path=file_path,
                )
            )
            coverage.total_items += 1
            coverage.documented_items += int(has_doc)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name

            if _is_dunder(name) and name in SKIP_DUNDERS:
                continue
            if _is_private(name):
                continue

            # Determine if method or function
            is_method = any(
                isinstance(parent, ast.ClassDef)
                for parent in ast.walk(tree)
                if isinstance(getattr(parent, "body", None), list)
                and node in parent.body
            )
            kind = ItemKind.METHOD if is_method else ItemKind.FUNCTION

            has_doc = _has_docstring(node)
            coverage.items.append(
                CodeItem(
                    name=name,
                    kind=kind,
                    line=node.lineno,
                    has_docstring=has_doc,
                    file_path=file_path,
                )
            )
            coverage.total_items += 1
            coverage.documented_items += int(has_doc)

    return coverage


def scan_repo(
    repo_path: Path,
    *,
    apps_only: bool = False,
) -> RepoCoverage:
    """Scan an entire repository for docstring coverage.

    Args:
        repo_path: Root path of the repository.
        apps_only: If True, only scan `apps/` subdirectory.

    Returns:
        RepoCoverage with per-module and aggregate statistics.
    """
    repo_path = repo_path.resolve()
    result = RepoCoverage(repo_path=repo_path)

    search_root = repo_path
    if apps_only:
        apps_dir = repo_path / "apps"
        if apps_dir.is_dir():
            search_root = apps_dir
        else:
            src_apps = repo_path / "src" / "apps"
            if src_apps.is_dir():
                search_root = src_apps

    for py_file in sorted(search_root.rglob("*.py")):
        # Skip excluded directories
        if any(
            _should_skip_dir(part)
            for part in py_file.relative_to(repo_path).parts
        ):
            continue

        # Skip excluded files
        if _should_skip_file(py_file.name):
            continue

        module_cov = scan_module(py_file)
        if module_cov.total_items > 0:
            result.modules.append(module_cov)

    return result
