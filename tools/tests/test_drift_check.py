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

import contextlib
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


# --- Blind ist nicht gruen: unerreichbare Repos ------------------------------
#
# Realfall 2026-09-02: derselbe Stand ergab in Minuten 19, dann 10, dann 0 Errors.
# Der Null-Lauf sah am besten aus und war der wertloseste — hinter jedem der 26
# Repos stand „Repo nicht gefunden oder privat" (sekundaeres GitHub-Ratenlimit,
# sechs Sitzungen an einem Token). Ein unerreichbares Repo liefert 0 Befunde;
# sind ALLE unerreichbar, faellt die Bilanz auf null.


def _lauf(monkeypatch, capsys, repos, fehler_bei):
    """Laesst `main()` ueber `repos` laufen; `fehler_bei` = Repos ohne Zugriff."""

    def fake_check(repo, repo_type, token, iil_latest):
        d = dc.RepoDrift(repo=repo, repo_type=repo_type)
        if repo in fehler_bei:
            d.error = "Repo nicht gefunden oder privat"
        return d

    monkeypatch.setattr(dc, "check_repo", fake_check)
    monkeypatch.setattr(dc, "_github_token", lambda *a, **k: "t")
    monkeypatch.setattr(dc, "_load_iil_latest", lambda *a, **k: {})
    # Probe und Sperre sind nicht der Gegenstand DIESER Tests. Ohne die zwei
    # Zeilen misst der Test die Erreichbarkeit der Maschine statt der Drift-
    # Bilanz: in der CI gibt es kein angemeldetes `gh`, die Probe schlaegt fehl,
    # und `main()` liefert korrekt Exit 2 — lokal gruen, in der CI rot (gemessen
    # 2026-09-03, platform#2757). Die Verdrahtung selbst hat ihren eigenen Test.
    monkeypatch.setattr(dc, "probe", lambda *a, **k: True)
    monkeypatch.setattr(dc, "flotten_sperre", lambda *a, **k: contextlib.nullcontext())
    # Positionsargumente umgehen die Registry-Auswahl: Namen direkt aus dem Test.
    monkeypatch.setattr(sys, "argv", ["drift_check.py", *repos])
    code = dc.main()
    return code, capsys.readouterr()


def test_should_exit_2_when_the_probe_says_throttled(monkeypatch, capsys):
    """Die Verdrahtung selbst: sagt die Probe „gedrosselt", wird NICHT gescannt.

    Das ist der Test, der 2026-09-03 gefehlt hat — die beiden Bilanz-Tests oben
    haben ihn versehentlich mitgespielt und sind daran in der CI gescheitert.
    """
    gescannt = []
    monkeypatch.setattr(dc, "_github_token", lambda *a, **k: "t")
    monkeypatch.setattr(dc, "_load_iil_latest", lambda *a, **k: {})
    monkeypatch.setattr(dc, "flotten_sperre", lambda *a, **k: contextlib.nullcontext())
    monkeypatch.setattr(dc, "_scanne", lambda *a, **k: gescannt.append(1) or [])

    def wirft(*a, **k):
        raise dc.DrosselFehler("API rate limit exceeded for user ID 33293099")

    monkeypatch.setattr(dc, "probe", wirft)
    monkeypatch.setattr(sys, "argv", ["drift_check.py", "a-hub"])
    code = dc.main()
    assert code == 2, "gedrosselt ist ein Werkzeugfehler, kein leeres Ergebnis"
    assert gescannt == [], "bei Drosselung darf gar nicht erst gescannt werden"
    assert "rate limit" in capsys.readouterr().err


def test_should_exit_2_when_not_a_single_repo_was_reachable(monkeypatch, capsys):
    code, aus = _lauf(monkeypatch, capsys, ["a-hub", "b-hub"], {"a-hub", "b-hub"})
    assert code == 2, (
        "alle Repos unerreichbar muss ein Werkzeugfehler sein, kein 0-Befund"
    )
    assert "Werkzeugfehler" in aus.err


def test_should_name_unreachable_repos_as_unmeasured_not_clean(monkeypatch, capsys):
    """Gegenprobe: bei TEILWEISER Erreichbarkeit kein Exit 2 — aber ein Hinweis."""
    code, aus = _lauf(monkeypatch, capsys, ["a-hub", "b-hub"], {"b-hub"})
    assert code == 0
    assert "UNGEMESSEN" in aus.err and "b-hub" in aus.err


def test_should_stay_green_when_every_repo_was_reachable(monkeypatch, capsys):
    """Positivkontrolle: ohne Fehler kein Exit 2 und kein Hinweis."""
    code, aus = _lauf(monkeypatch, capsys, ["a-hub", "b-hub"], set())
    assert code == 0
    assert "Werkzeugfehler" not in aus.err and "UNGEMESSEN" not in aus.err
