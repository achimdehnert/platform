"""Unit tests for scripts/drift_check.py HEALTHCHECK rule (ADR-078).

ADR-078 (amends ADR-021 §2.3) reversed the old "HEALTHCHECK required in
Dockerfile" convention: the healthcheck belongs per-service in
docker-compose.prod.yml, never in the image-global Dockerfile. drift_check.py
still enforced the *old* rule and thus contradicted accepted ADR-078 and the
REFLEX plugin compose.healthcheck_in_dockerfile (issue #549). These tests pin
the corrected behaviour. Pure (no GitHub API / token needed).
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "drift_check.py"
_spec = importlib.util.spec_from_file_location("drift_check", _SCRIPT)
dc = importlib.util.module_from_spec(_spec)
sys.modules["drift_check"] = dc  # let @dataclass resolve forward refs
_spec.loader.exec_module(dc)


def test_should_not_require_healthcheck_in_dockerfile():
    """The stale ADR-021 rule (HEALTHCHECK *required* in Dockerfile) is gone."""
    for filepath, pattern, _severity, _msg in dc.REQUIRED_FILE_CONTENT_CHECKS:
        assert not (filepath == "Dockerfile" and "HEALTHCHECK" in pattern), (
            "drift_check still requires HEALTHCHECK in the Dockerfile — "
            "contradicts accepted ADR-078"
        )


def _healthcheck_banned_rule():
    for pattern, severity, msg in dc.BANNED_PATTERNS:
        if "HEALTHCHECK" in pattern:
            return pattern, severity, msg
    return None


def test_should_ban_healthcheck_in_dockerfile():
    """An inverted rule now flags HEALTHCHECK *in* the Dockerfile as an error."""
    rule = _healthcheck_banned_rule()
    assert rule is not None, "expected a banned-pattern rule for HEALTHCHECK"
    pattern, severity, msg = rule
    assert severity == "error"
    assert "ADR-078" in msg
    dockerfile = (
        "FROM python:3.12-slim\n"
        "HEALTHCHECK CMD curl -f http://localhost:8000/livez/ || exit 1\n"
    )
    assert re.search(pattern, dockerfile, re.MULTILINE)


def test_should_not_flag_compose_healthcheck_key():
    """The compose per-service `healthcheck:` key must NOT trip the rule."""
    pattern, _severity, _msg = _healthcheck_banned_rule()
    compose = (
        "services:\n"
        "  web:\n"
        "    image: app:latest\n"
        "    healthcheck:\n"
        "      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8000/livez/\"]\n"
    )
    assert not re.search(pattern, compose, re.MULTILINE)
