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
        '      test: ["CMD", "curl", "-f", "http://localhost:8000/livez/"]\n'
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
        dc,
        "_get_file_content",
        lambda repo, filepath, token: files.get(filepath),
    )
    drifts = dc.check_banned_patterns("dummy-repo", "dummy-token")
    hc = [d for d in drifts if "HEALTHCHECK" in d.message]
    assert len(hc) == 1, (
        f"erwartet genau 1 HEALTHCHECK-Flag, got {[d.message for d in hc]}"
    )
    assert hc[0].file == "Dockerfile"
    assert hc[0].rule == "banned-file-pattern"


# ── required-file: Alternativpfade + pyproject-Deps (#1469) ───────────────────
#
# Vorher meldete die Regel `error` für Repos, die den Docker-Build unter
# docker/app/ halten (risk-hub, odoo-hub, pptx-hub) bzw. ihre Deps im pyproject
# tragen statt in requirements.txt. Beides ist im Fleet gelebte Praxis; die
# Dauer-Errors entwerteten den Check. Die zwei Negativproben unten sind der
# eigentliche Wert der Lockerung — ohne sie wäre sie wertlos.


def _required_files_with(files: dict, monkeypatch):
    """Führt check_required_files gegen eine gefälschte Dateiliste aus."""
    monkeypatch.setattr(
        dc,
        "_get_file_content",
        lambda repo, filepath, token: files.get(filepath),
    )
    return dc.check_required_files("dummy-repo", "dummy-token")


def _findings_for(drifts, path):
    return [d for d in drifts if d.file == path]


PYPROJECT_WITH_DEPS = '[project]\nname = "x"\ndependencies = ["django>=5.0"]\n'
PYPROJECT_WITHOUT_DEPS = '[project]\nname = "x"\n\n[tool.ruff]\nline-length = 100\n'


def test_should_accept_dockerfile_under_docker_app(monkeypatch):
    """docker/app/Dockerfile erfüllt die Regel — Layout von risk-hub/odoo-hub/pptx-hub."""
    drifts = _required_files_with(
        {"docker/app/Dockerfile": "FROM python:3.12\n"}, monkeypatch
    )
    assert not _findings_for(drifts, "Dockerfile")


def test_should_still_accept_dockerfile_in_repo_root(monkeypatch):
    """Regression: das Wurzel-Layout (dev-hub, weltenhub) bleibt gültig."""
    drifts = _required_files_with({"Dockerfile": "FROM python:3.12\n"}, monkeypatch)
    assert not _findings_for(drifts, "Dockerfile")


def test_should_still_flag_when_no_dockerfile_exists_anywhere(monkeypatch):
    """Negativprobe: ohne Docker-Build bleibt es ein error — sonst ist die Regel zahnlos."""
    drifts = _required_files_with({}, monkeypatch)
    found = _findings_for(drifts, "Dockerfile")
    assert len(found) == 1, "fehlender Docker-Build muss weiterhin genau einmal flaggen"
    assert found[0].severity == "error"


def test_should_report_a_single_finding_when_both_layouts_exist(monkeypatch):
    """trading-hub hält beide Varianten — das darf kein Doppel-Finding erzeugen."""
    drifts = _required_files_with(
        {
            "Dockerfile": "FROM python:3.12\n",
            "docker/app/Dockerfile": "FROM python:3.12\n",
        },
        monkeypatch,
    )
    assert not _findings_for(drifts, "Dockerfile")


def test_should_accept_dependencies_declared_in_pyproject(monkeypatch):
    """Kein requirements.txt noetig, wenn das pyproject die Deps traegt."""
    drifts = _required_files_with({"pyproject.toml": PYPROJECT_WITH_DEPS}, monkeypatch)
    assert not _findings_for(drifts, "requirements.txt")


def test_should_still_flag_when_dependencies_are_declared_nowhere(monkeypatch):
    """Negativprobe: pyproject OHNE dependencies rettet die Regel nicht."""
    drifts = _required_files_with(
        {"pyproject.toml": PYPROJECT_WITHOUT_DEPS}, monkeypatch
    )
    found = _findings_for(drifts, "requirements.txt")
    assert len(found) == 1
    assert found[0].severity == "error"


def test_should_only_read_dependencies_from_the_project_table():
    """`dependencies` in einer anderen Tabelle beantwortet die Frage nicht."""
    assert dc._pyproject_declares_dependencies(PYPROJECT_WITH_DEPS)
    assert not dc._pyproject_declares_dependencies(PYPROJECT_WITHOUT_DEPS)
    assert not dc._pyproject_declares_dependencies(
        '[tool.poetry]\ndependencies = ["django"]\n'
    )


def test_should_name_the_alternative_in_the_fix_hint(monkeypatch):
    """Der Hinweis nennt den zweiten Kandidaten — sonst raet der Leser."""
    drifts = _required_files_with({}, monkeypatch)
    found = _findings_for(drifts, "Dockerfile")
    assert "docker/app/Dockerfile" in found[0].fix_hint


# ── shared-ci Port-Normalisierung (risk-hub#496) ─────────────────────────────
#
# Der Mirror platform → shared-ci schreibt zwei Dinge um: den Repo-Pfad und das
# lokale Checkout-Verzeichnis. Die Normalisierung kannte nur das erste, also
# meldete der Kanon-Abgleich jede Datei mit eigenem Checkout-Pfad dauerhaft als
# "stale" — ein Dauer-Error, der echten Drift untergehen laesst. Die Fixtures
# unten sind gekuerzte, aber woertliche Auszuege aus dem Realfall vom 2026-08-03
# (shared-ci@v1.1.2 gegen platform-main).

CANON_WITH_CHECKOUT_PATH = """\
      - uses: actions/checkout@v4
        with:
          repository: achimdehnert/platform
          path: _platform_checks
      - run: python3 _platform_checks/scripts/checks/handoff_banner_check.py
"""

MIRRORED_WITH_CHECKOUT_PATH = """\
      - uses: actions/checkout@v4
        with:
          repository: iilgmbh/shared-ci
          path: _shared_ci_checks
      - run: python3 _shared_ci_checks/scripts/checks/handoff_banner_check.py
"""

CANON_SHORT_CHECKOUT_PATH = """\
      - uses: actions/checkout@v4
        with:
          path: platform
      - run: python3 platform/tools/deploy_config_lint.py caller/.github/workflows
"""

MIRRORED_SHORT_CHECKOUT_PATH = """\
      - uses: actions/checkout@v4
        with:
          path: _shared_ci
      - run: python3 _shared_ci/tools/deploy_config_lint.py caller/.github/workflows
"""


def test_should_not_flag_pure_checkout_path_rewrites_as_drift():
    """`_shared_ci_checks` → `_platform_checks` ist Port-Mechanik, kein Drift."""
    assert (
        dc.normalize_shared_ci_port(MIRRORED_WITH_CHECKOUT_PATH)
        == CANON_WITH_CHECKOUT_PATH
    )


def test_should_normalize_the_short_checkout_path_too():
    """Auch das kuerzere `_shared_ci` (ohne `_checks`) muss zurueckgedreht werden."""
    assert (
        dc.normalize_shared_ci_port(MIRRORED_SHORT_CHECKOUT_PATH)
        == CANON_SHORT_CHECKOUT_PATH
    )


def test_should_apply_the_longer_prefix_first():
    """Reihenfolge-Falle: `_shared_ci` darf `_shared_ci_checks` nicht anfressen.

    Ohne Longest-First wuerde `_shared_ci_checks` zu `platform_checks` statt zu
    `_platform_checks` — der Vergleich bliebe ungleich und die Datei weiter stale.
    """
    assert "platform_checks" not in dc.normalize_shared_ci_port(
        "_shared_ci_checks"
    ).replace("_platform_checks", "")
    assert dc.normalize_shared_ci_port("_shared_ci_checks") == "_platform_checks"


def test_should_still_flag_real_content_drift():
    """Beisskraft: eine echte inhaltliche Abweichung bleibt sichtbar.

    Negativprobe zur Normalisierung — sie darf nur Pfade zurueckdrehen, nicht
    Inhalt einebnen. Hier fehlt dem Kanon der GHCR_TOKEN-Block (genau der
    Realfall, den shared-ci@v1.1.2 gegenueber platform-main voraus hat).
    """
    mirrored = MIRRORED_SHORT_CHECKOUT_PATH + "        env:\n          GHCR_TOKEN: x\n"
    assert dc.normalize_shared_ci_port(mirrored) != CANON_SHORT_CHECKOUT_PATH


def test_should_normalize_the_repo_path_as_before():
    """Regression: die urspruengliche Repo-Pfad-Umschreibung wirkt weiterhin."""
    assert dc.normalize_shared_ci_port("uses: iilgmbh/shared-ci/x.yml@v1") == (
        "uses: achimdehnert/platform/x.yml@v1"
    )
