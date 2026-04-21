"""pytest-Plugin: Hardcoding-Guard als parametrized Tests.

Einbinden per conftest.py im Repo-Root:

    # tests/conftest.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parents[2] / "platform" / "scripts"))
    from hardcoded_url_pytest_plugin import *  # noqa: F401,F403

Dann werden alle .html-Templates und apps/**/*.py automatisch als
separate Test-Cases registriert und in `pytest` angezeigt.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# ── Gemeinsame Konfiguration (identisch zu check_hardcoded_urls.py) ───────────

_ALLOWED_TOKENS = [
    "/admin/", "https://", "http://", "{{ ", "{% url", "{% static",
]

_SKIP_DIRS = {
    ".venv", "node_modules", "__pycache__", "site-packages",
    ".git", "dist", "build", "migrations",
}

_TEMPLATE_RULES = [
    ("TEMPLATE-01", re.compile(r'href="(/[a-zA-Z0-9_-])'),    "href mit hartkodiertem Pfad → {{% url 'app:name' %}}"),
    ("TEMPLATE-02", re.compile(r'action="(/[a-zA-Z0-9_-])'),  "action mit hartkodiertem Pfad → {{% url 'app:name' %}}"),
    ("TEMPLATE-03", re.compile(r'src="(/[a-zA-Z0-9_-])'),     "src mit hartkodiertem Pfad → {{% static 'path' %}}"),
]

_PYTHON_RULES = [
    ("PYTHON-01",  re.compile(r'redirect\(\s*["\']\/[a-zA-Z]'),     "redirect() mit hartkodiertem Pfad → reverse()"),
    ("PYTHON-02",  re.compile(r'HttpResponseRedirect\(\s*["\']\/'),  "HttpResponseRedirect() mit hartkodiertem Pfad"),
]


def _is_allowed(line: str) -> bool:
    return any(tok in line for tok in _ALLOWED_TOKENS)


def _should_skip(path: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.parts)


def _collect_templates(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.html")
        if not _should_skip(p)
    )


def _collect_python_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.py")
        if not _should_skip(p)
        and not p.name.startswith("test_")
        and p.name != "conftest.py"
        and "migrations" not in p.parts
    )


# ── pytest-Parametrisierung ───────────────────────────────────────────────────

def _get_repo_root() -> Path:
    return Path(__file__).parent.parent.parent


_REPO_ROOT = _get_repo_root()
_TEMPLATES = _collect_templates(_REPO_ROOT / "templates") if (_REPO_ROOT / "templates").exists() else []
_PY_FILES  = _collect_python_files(_REPO_ROOT / "apps") if (_REPO_ROOT / "apps").exists() else []


@pytest.mark.parametrize(
    "template_path",
    _TEMPLATES,
    ids=lambda p: str(p.relative_to(_REPO_ROOT)),
)
def test_should_not_contain_hardcoded_urls_in_template(template_path: Path) -> None:
    """TEMPLATE-01/02/03: Keine href/action/src mit hartkodiertem Pfad."""
    content = template_path.read_text(encoding="utf-8", errors="ignore")
    violations: list[str] = []

    for lineno, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("{#") or stripped.startswith("<!--"):
            continue
        if _is_allowed(line):
            continue
        for rule_id, pattern, description in _TEMPLATE_RULES:
            if pattern.search(line):
                violations.append(f"[{rule_id}] Zeile {lineno}: {description}\n    → {stripped}")

    assert not violations, (
        f"\nHardcoding-Violations in {template_path.relative_to(_REPO_ROOT)}:\n"
        + "\n".join(violations)
    )


@pytest.mark.parametrize(
    "py_path",
    _PY_FILES,
    ids=lambda p: str(p.relative_to(_REPO_ROOT / "apps")),
)
def test_should_not_contain_hardcoded_redirects_in_views(py_path: Path) -> None:
    """PYTHON-01/02: Keine redirect() / HttpResponseRedirect() mit hartkodiertem Pfad."""
    content = py_path.read_text(encoding="utf-8", errors="ignore")
    violations: list[str] = []

    for lineno, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for rule_id, pattern, description in _PYTHON_RULES:
            if pattern.search(line):
                violations.append(f"[{rule_id}] Zeile {lineno}: {description}\n    → {stripped}")

    assert not violations, (
        f"\nHardcoding-Violations in {py_path.relative_to(_REPO_ROOT)}:\n"
        + "\n".join(violations)
    )
