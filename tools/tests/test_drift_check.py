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


# ── #2761: weitere Layout-Fehlalarme (travel-beat, ttz-hub) ──────────────────
#
# Gemessen 2026-09-04 (--severity=error --skip-pypi --format json): travel-beat
# haelt Dockerfile unter docker/Dockerfile und Deps unter requirements/base.txt
# — beides gelebte Praxis, kein Ausreisser. ttz-hub haelt den Dockerfile-Build
# unter services/aifw_service/, referenziert per docker-compose.prod.yml
# build.dockerfile — ein Pfad, der in keinem statischen Kandidaten-Tupel steht.


def test_should_accept_dockerfile_under_docker_root(monkeypatch):
    """docker/Dockerfile erfuellt die Regel — Layout von travel-beat (#2761)."""
    drifts = _required_files_with(
        {"docker/Dockerfile": "FROM python:3.12\n"}, monkeypatch
    )
    assert not _findings_for(drifts, "Dockerfile")


def test_should_accept_requirements_under_requirements_base(monkeypatch):
    """requirements/base.txt erfuellt die Regel — Layout von travel-beat (#2761)."""
    drifts = _required_files_with(
        {"requirements/base.txt": "django>=5.0\n"}, monkeypatch
    )
    assert not _findings_for(drifts, "requirements.txt")


COMPOSE_WITH_CUSTOM_DOCKERFILE = (
    "services:\n"
    "  web:\n"
    "    build:\n"
    "      context: services/aifw_service\n"
    "      dockerfile: Dockerfile\n"
)


def test_should_accept_dockerfile_referenced_by_compose_build_dockerfile(monkeypatch):
    """ttz-hub: Dockerfile liegt unter services/aifw_service/, referenziert per
    docker-compose.prod.yml build.dockerfile (#2761)."""
    drifts = _required_files_with(
        {
            "docker-compose.prod.yml": COMPOSE_WITH_CUSTOM_DOCKERFILE,
            "services/aifw_service/Dockerfile": "FROM python:3.12\n",
        },
        monkeypatch,
    )
    assert not _findings_for(drifts, "Dockerfile")


def test_should_still_flag_when_compose_dockerfile_path_does_not_exist(monkeypatch):
    """Negativprobe: compose nennt einen Pfad, der nicht existiert — bleibt error."""
    drifts = _required_files_with(
        {"docker-compose.prod.yml": COMPOSE_WITH_CUSTOM_DOCKERFILE}, monkeypatch
    )
    found = _findings_for(drifts, "Dockerfile")
    assert len(found) == 1
    assert found[0].severity == "error"


def test_should_accept_requirements_next_to_compose_build_context(monkeypatch):
    """ttz-hub real: pyproject.toml hat KEINE [project].dependencies (Odoo-Addon-
    Repo) — das echte Manifest liegt unter services/aifw_service/requirements.txt,
    neben dem dortigen Dockerfile (#2761, gemessen 2026-09-04)."""
    drifts = _required_files_with(
        {
            "docker-compose.prod.yml": COMPOSE_WITH_CUSTOM_DOCKERFILE,
            "services/aifw_service/Dockerfile": "FROM python:3.12\n",
            "services/aifw_service/requirements.txt": "django>=5.0\n",
            "pyproject.toml": PYPROJECT_WITHOUT_DEPS,
        },
        monkeypatch,
    )
    assert not _findings_for(drifts, "requirements.txt")


def test_should_still_flag_requirements_when_compose_context_has_none_either(
    monkeypatch,
):
    """Negativprobe: Compose-Kontext ohne requirements.txt UND ohne pyproject-Deps
    bleibt ein error."""
    drifts = _required_files_with(
        {
            "docker-compose.prod.yml": COMPOSE_WITH_CUSTOM_DOCKERFILE,
            "services/aifw_service/Dockerfile": "FROM python:3.12\n",
            "pyproject.toml": PYPROJECT_WITHOUT_DEPS,
        },
        monkeypatch,
    )
    found = _findings_for(drifts, "requirements.txt")
    assert len(found) == 1
    assert found[0].severity == "error"


def test_should_ignore_root_compose_context_for_requirements_satisfier(monkeypatch):
    """Root-Kontext (`.`) zaehlt nicht — dafuer gibt es bereits die Wurzel-
    Kandidaten und den pyproject-Satisfier; sonst wuerde jede Root-Compose
    versehentlich requirements.txt selbst als eigenen Kontext lesen."""
    compose_root_context = "services:\n  web:\n    build:\n      context: .\n      dockerfile: Dockerfile\n"
    drifts = _required_files_with(
        {
            "docker-compose.prod.yml": compose_root_context,
            "Dockerfile": "FROM python:3.12\n",
            "pyproject.toml": PYPROJECT_WITHOUT_DEPS,
        },
        monkeypatch,
    )
    found = _findings_for(drifts, "requirements.txt")
    assert len(found) == 1
    assert found[0].severity == "error"


# ── #2761: Registry-Typ gewinnt — Django-Pflichtdateien nur fuer type: django ─
#
# lastwar-bot (type: bot) bekam faelschlich "Docker Build fehlt" +
# "Prod-Compose fehlt" gemeldet: REQUIRED_FILES_DJANGO ist trotz des generischen
# SCAFFOLD_TYPES-Gates Django-spezifisch, ein Telegram/Discord-Bot hat legitim
# kein manage.py-Deployment.


def _check_repo_mit_gemockten_subchecks(monkeypatch, repo_type, called):
    monkeypatch.setattr(
        dc, "_api_get", lambda *a, **k: {"name": "x", "archived": False}
    )
    monkeypatch.setattr(
        dc, "check_required_files", lambda *a, **k: called.append("required") or []
    )
    for name in (
        "check_file_contents",
        "check_banned_patterns",
        "check_actions_versions",
        "check_iil_package_versions",
        "check_python_version",
        "check_shared_ci_tag_drift",
    ):
        monkeypatch.setattr(dc, name, lambda *a, **k: [])
    return dc.check_repo("dummy-repo", repo_type, "tok", {})


def test_should_skip_required_files_for_non_django_registry_type(monkeypatch):
    """type: bot bekommt keine Django-Pflichtdateien-Checks (lastwar-bot, #2761)."""
    called: list[str] = []
    result = _check_repo_mit_gemockten_subchecks(monkeypatch, "bot", called)
    assert called == [], "check_required_files darf fuer type=bot nicht laufen"
    skip_notes = [d for d in result.drifts if d.rule == "required-file-skip"]
    assert len(skip_notes) == 1
    assert skip_notes[0].severity == "info"
    assert "bot" in skip_notes[0].file
    assert not result.errors, "der Skip-Hinweis selbst darf kein Error sein"


def test_should_still_run_required_files_for_django_type(monkeypatch):
    """Gegenprobe: type: django bleibt unveraendert gecheckt."""
    called: list[str] = []
    result = _check_repo_mit_gemockten_subchecks(monkeypatch, "django", called)
    assert called == ["required"]
    assert not any(d.rule == "required-file-skip" for d in result.drifts)


# --- Blind ist nicht gruen: unerreichbare Repos ------------------------------
#
# Realfall 2026-09-02: derselbe Stand ergab in Minuten 19, dann 10, dann 0 Errors.
# Der Null-Lauf sah am besten aus und war der wertloseste — hinter jedem der 26
# Repos stand „Repo nicht gefunden oder privat" (sekundaeres GitHub-Ratenlimit,
# sechs Sitzungen an einem Token). Ein unerreichbares Repo liefert 0 Befunde;
# sind ALLE unerreichbar, faellt die Bilanz auf null.


def _lauf(monkeypatch, capsys, repos, fehler_bei):
    """Laesst `main()` ueber `repos` laufen; `fehler_bei` = Repos ohne Zugriff."""

    def fake_check(repo, repo_type, token, iil_latest, registry_archived=False):
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


# ── #2761: SHA-Pinning vs Tag ist Port-Mechanik, kein Drift (shared-ci#67) ───
#
# platform pinnt Actions per SHA + Versions-Kommentar
# (`uses: owner/action@<sha> # vX.Y.Z`), shared-ci hatte bislang Tags
# (`uses: owner/action@vX.Y.Z`) — reine Haertung, kein Verhaltensunterschied.
# Ohne Normalisierung waere JEDER SHA-Pin ein Dauer-shared-ci-tag-stale-Error.

_SHA = "a" * 40


def _mini_workflow(uses_value: str) -> str:
    return (
        "name: sample\n"
        "on:\n"
        "  push: {}\n"
        "jobs:\n"
        "  build:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        f"      - uses: {uses_value}\n"
    )


def test_should_treat_sha_pin_with_matching_version_as_equivalent_to_tag():
    """`@<sha> # v4.37.9` deckt `@v4.37.9` — reine Pinning-Form, kein Drift."""
    tagged = _mini_workflow(f"actions/checkout@{_SHA} # v4.37.9")
    canonical = _mini_workflow("actions/checkout@v4.37.9")
    assert dc.shared_ci_deckt_kanon(tagged, canonical)


def test_should_still_flag_a_real_version_difference_behind_the_pin():
    """Unterschiedliche Versions-Kommentare bleiben ein echter Drift."""
    tagged = _mini_workflow(f"actions/checkout@{_SHA} # v4.37.6")
    canonical = _mini_workflow("actions/checkout@v4.37.9")
    assert not dc.shared_ci_deckt_kanon(tagged, canonical)


def test_should_normalize_pin_comment_before_measuring_direction():
    """kanon_richtung zaehlt nach Normalisierung 0 Zeilen Unterschied fuer reine Pin-Form."""
    tagged = _mini_workflow(f"actions/checkout@{_SHA} # v4.37.9")
    canonical = _mini_workflow("actions/checkout@v4.37.9")
    assert dc.kanon_richtung(tagged, canonical) == (0, 0)


# ── #2761: Kanon-Abgleich nur fuer Reusables + geteilte Gate-Workflows ───────
#
# validate-workflows.yml ist auf beiden Seiten repo-eigene CI (platform:
# publish_gate-Pfade; shared-ci: compose-Auswahl-Job) — kein Reusable, ein
# Abgleich dagegen ist ein Dauer-Fehlalarm ohne moeglichen Fix.


def test_should_include_reusables_and_named_gates_in_kanon_abgleich():
    for name in (
        "_build-docker.yml",
        "_deploy-unified.yml",
        "_ci-pypi.yml",
        "handoff-banner-gate.yml",
        "deploy-config-lint.yml",
    ):
        assert dc._im_kanon_abgleich(name), name


def test_should_exclude_validate_workflows_from_kanon_abgleich():
    """validate-workflows.yml ist repo-eigene CI auf beiden Seiten, kein Reusable."""
    assert not dc._im_kanon_abgleich("validate-workflows.yml")


def test_should_exclude_other_non_reusable_gate_workflows_from_kanon_abgleich():
    assert not dc._im_kanon_abgleich("doc-profile-guard.yml")
    assert not dc._im_kanon_abgleich("silent-failure-lint.yml")


# ── #2761: archivierte Repos zaehlen nicht ───────────────────────────────────
#
# wedding-hub (Registry-Feld `archived: true`) und recruiting-hub (auf
# GitHub archiviert, aber OHNE `archived:`-Feld in der Registry — gemessen
# 2026-09-04) lieferten zusammen 5 der 55 Drift-Errors, an denen niemand mehr
# etwas aendern kann. Registry-Feld gewinnt, wenn gesetzt; sonst entscheidet
# das `archived`-Feld der ohnehin schon geladenen Repo-API-Antwort (kein
# zweiter Call).


def test_should_skip_repo_marked_archived_in_registry_without_any_api_call(monkeypatch):
    """wedding-hub: registry-`archived: true` gewinnt — kein API-Call noetig."""
    calls: list[str] = []
    monkeypatch.setattr(dc, "_api_get", lambda *a, **k: calls.append(a) or None)
    result = dc.check_repo("wedding-hub", "django", "tok", {}, registry_archived=True)
    assert result.archived
    assert calls == [], "archiviert laut Registry darf keinen API-Call ausloesen"
    assert not result.error
    assert result.drifts == []
    assert result.status_icon == "⏸"


def test_should_skip_repo_archived_on_github_but_not_in_registry(monkeypatch):
    """recruiting-hub: kein `archived:` in der Registry, aber GitHub sagt True."""
    monkeypatch.setattr(
        dc, "_api_get", lambda *a, **k: {"name": "recruiting-hub", "archived": True}
    )
    result = dc.check_repo(
        "recruiting-hub", "django", "tok", {}, registry_archived=False
    )
    assert result.archived
    assert not result.error
    assert result.drifts == []


def test_should_still_scan_repos_that_are_not_archived(monkeypatch):
    """Negativprobe: ein normales Repo bleibt vollstaendig gecheckt."""
    monkeypatch.setattr(
        dc, "_api_get", lambda *a, **k: {"name": "x", "archived": False}
    )
    for name in (
        "check_required_files",
        "check_file_contents",
        "check_banned_patterns",
        "check_actions_versions",
        "check_iil_package_versions",
        "check_python_version",
        "check_shared_ci_tag_drift",
    ):
        monkeypatch.setattr(dc, name, lambda *a, **k: [])
    result = dc.check_repo("ttz-hub", "django", "tok", {}, registry_archived=False)
    assert not result.archived
    assert result.status_icon != "⏸"


def test_should_print_archived_repos_as_skipped_not_as_errors(capsys):
    """print_report zeigt archivierte Repos immer, unabhaengig vom severity-Filter."""
    archived = dc.RepoDrift(repo="wedding-hub", repo_type="django", archived=True)
    dc.print_report([archived], severity_filter="error", show_fix_hints=False)
    out = capsys.readouterr().out
    assert "⏸  **wedding-hub** — archiviert — uebersprungen" in out
    assert "🔴  **wedding-hub**" not in out
