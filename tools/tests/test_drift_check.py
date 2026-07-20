"""Tests für scripts/drift_check.py HEALTHCHECK-Regel (ADR-078).

ADR-078 (amends ADR-021 §2.3) kehrte die alte „HEALTHCHECK required im
Dockerfile"-Konvention um: der Healthcheck gehört pro-Service in
docker-compose.prod.yml, nie ins image-globale Dockerfile. drift_check.py
erzwang die alte Regel und widersprach damit accepted ADR-078 + REFLEX
compose.healthcheck_in_dockerfile (Issue #549).

Liegt unter tools/tests/ (nicht repo-root tests/), damit der generische
`tools-tests.yml`-Gate den Test ausführt — repo-root tests/ wird von KEINEM
CI-Workflow gestartet (Session-Retro 2026-06-12 F1). Rein (kein GitHub-API/Token
nötig); der End-to-End-Test mockt `_get_file_content`.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "drift_check.py"
_spec = importlib.util.spec_from_file_location("drift_check", _SCRIPT)
dc = importlib.util.module_from_spec(_spec)
sys.modules["drift_check"] = dc  # let @dataclass resolve forward refs
_spec.loader.exec_module(dc)


def test_should_not_require_healthcheck_in_dockerfile():
    """Die stale ADR-021-Regel (HEALTHCHECK *required* im Dockerfile) ist weg."""
    for filepath, pattern, _severity, _msg in dc.REQUIRED_FILE_CONTENT_CHECKS:
        assert not (filepath == "Dockerfile" and "HEALTHCHECK" in pattern), (
            "drift_check verlangt noch HEALTHCHECK im Dockerfile — "
            "widerspricht accepted ADR-078"
        )


def _healthcheck_scoped_rule():
    for scoped_file, pattern, severity, msg in dc.BANNED_FILE_PATTERNS:
        if "HEALTHCHECK" in pattern:
            return scoped_file, pattern, severity, msg
    return None


def test_should_ban_healthcheck_as_dockerfile_scoped_rule():
    """Die inverse Regel ist file-scoped auf Dockerfile (nicht global)."""
    # Nicht mehr in der globalen Liste (sonst feuert sie auf alle 4 Dateien)
    assert all("HEALTHCHECK" not in pat for pat, _s, _m in dc.BANNED_PATTERNS)
    rule = _healthcheck_scoped_rule()
    assert rule is not None, "erwartete file-scoped HEALTHCHECK-Regel"
    scoped_file, pattern, severity, msg = rule
    assert scoped_file == "Dockerfile"
    assert severity == "error"
    assert "ADR-078" in msg
    dockerfile = (
        "FROM python:3.12-slim\n"
        "HEALTHCHECK CMD curl -f http://localhost:8000/livez/ || exit 1\n"
    )
    assert re.search(pattern, dockerfile, re.MULTILINE)


def test_should_not_flag_compose_healthcheck_key():
    """Der compose `healthcheck:`-Key darf die Regel nicht triggern."""
    _f, pattern, _s, _m = _healthcheck_scoped_rule()
    compose = (
        "services:\n"
        "  web:\n"
        "    image: app:latest\n"
        "    healthcheck:\n"
        "      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8000/livez/\"]\n"
    )
    assert not re.search(pattern, compose, re.MULTILINE)


def test_should_flag_healthcheck_only_in_dockerfile_end_to_end(monkeypatch):
    """End-to-end: HEALTHCHECK im Dockerfile flaggt, dieselbe Zeile in compose NICHT.

    Beweist den File-Scope-Fix: vor dem Fix lag die Regel in der globalen
    BANNED_PATTERNS und hätte ein zeilenstartendes `HEALTHCHECK` AUCH in
    docker-compose.prod.yml geflaggt (mit der widersprüchlichen Msg
    „…im Dockerfile … in docker-compose.prod.yml").
    """
    files = {
        # gültige Dockerfile-Instruktion → muss flaggen
        "Dockerfile": "FROM python:3.12\nHEALTHCHECK CMD curl -f http://x/livez/\n",
        # identisches zeilenstartendes Token, aber in der FALSCHEN Datei → kein Flag
        "docker-compose.prod.yml": "services:\n  web:\n    image: app\nHEALTHCHECK bogus\n",
    }
    monkeypatch.setattr(
        dc, "_get_file_content",
        lambda repo, filepath, token: files.get(filepath),
    )
    drifts = dc.check_banned_patterns("dummy-repo", "dummy-token")
    hc = [d for d in drifts if "HEALTHCHECK" in d.message]
    assert len(hc) == 1, f"erwartet genau 1 HEALTHCHECK-Flag, got {[d.message for d in hc]}"
    assert hc[0].file == "Dockerfile"
    assert hc[0].rule == "banned-file-pattern"
