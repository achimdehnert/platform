"""audit_platform: Bewertungslogik, Owner-Aufloesung und lokaler Scan.

Das Werkzeug entscheidet mit, welches Repo als gesund gilt — ein falsches Urteil
hier wandert in Dashboards und Rollout-Listen. Getestet wird deshalb die
Bewertung (Punktzahl, Statuszeichen) und die Abbildung von Dateibestand auf
Befund, nicht die GitHub-Anbindung selbst.

`_api_get` und `subprocess` werden ersetzt: der Testgegenstand ist die Auswertung
der Antwort, nicht das Netz. Ein Test, der gegen die echte GitHub-API laeuft,
waere langsam, flatterig und wuerde in der CI ein Token verlangen.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "audit_platform.py"
_spec = importlib.util.spec_from_file_location("audit_platform", _SRC)
ap = importlib.util.module_from_spec(_spec)
# VOR exec_module registrieren — das Modul definiert eine @dataclass, und der
# Decorator schlaegt waehrend der Klassendefinition sys.modules[__module__] nach.
sys.modules[_spec.name] = ap
_spec.loader.exec_module(ap)


def audit(**over):
    a = ap.RepoAudit(repo="beispiel-hub", repo_type="django")
    for k, v in over.items():
        setattr(a, k, v)
    return a


# --- inventory_score ---------------------------------------------------------


def test_should_score_zero_for_an_empty_repo():
    assert audit().inventory_score == 0


def test_should_score_five_when_every_component_is_present():
    a = audit(
        has_scaffold=True, has_req_test=True, has_pyproject=True,
        workflow_count=3, test_file_count=12,
    )

    assert a.inventory_score == 5


@pytest.mark.parametrize(
    "feld,wert",
    [("has_scaffold", True), ("has_req_test", True), ("has_pyproject", True),
     ("workflow_count", 1), ("test_file_count", 1)],
)
def test_should_count_each_component_exactly_once(feld, wert):
    assert audit(**{feld: wert}).inventory_score == 1


def test_should_not_score_counts_of_zero():
    # workflow_count/test_file_count zaehlen ueber >0, nicht ueber Wahrheitswert
    assert audit(workflow_count=0, test_file_count=0).inventory_score == 0


# --- status_icon: die Reihenfolge der Regeln ist die eigentliche Aussage -----


def test_should_show_warning_when_an_error_is_set():
    assert audit(error="Repo nicht gefunden").status_icon == "⚠️"


def test_should_let_the_error_win_over_a_passing_test_run():
    a = audit(error="kaputt", tests_run=True, tests_passed=True)

    assert a.status_icon == "⚠️"


def test_should_show_green_for_a_passing_test_run():
    assert audit(tests_run=True, tests_passed=True).status_icon == "✅"


def test_should_show_red_cross_for_a_failing_test_run():
    assert audit(tests_run=True, tests_passed=False).status_icon == "❌"


def test_should_show_yellow_at_the_inventory_threshold():
    a = audit(has_scaffold=True, has_req_test=True, has_pyproject=True)

    assert a.inventory_score == 3
    assert a.status_icon == "🟡"


def test_should_show_red_below_the_inventory_threshold():
    a = audit(has_scaffold=True, has_req_test=True)

    assert a.inventory_score == 2
    assert a.status_icon == "🔴"


# --- Owner-Aufloesung --------------------------------------------------------


def test_should_take_the_owner_from_the_registry(monkeypatch):
    monkeypatch.setattr(ap.reg, "owner", lambda repo: "meiki-lra")

    assert ap._repo_owner("meiki-hub") == "meiki-lra"


def test_should_fall_back_to_the_default_org_for_unknown_repos(monkeypatch):
    """F-5: reg.owner() liefert None fuer nicht registrierte Namen."""
    monkeypatch.setattr(ap.reg, "owner", lambda repo: None)

    assert ap._repo_owner("gibt-es-nicht") == ap.GITHUB_ORG


# --- API-Auswertung (Netz ersetzt) -------------------------------------------


def test_should_treat_a_present_file_as_existing(monkeypatch):
    monkeypatch.setattr(ap, "_api_get", lambda pfad, token: {"name": "conftest.py"})

    assert ap._file_exists("beispiel-hub", "tests/conftest.py", "t") is True


def test_should_treat_a_missing_file_as_absent(monkeypatch):
    monkeypatch.setattr(ap, "_api_get", lambda pfad, token: None)

    assert ap._file_exists("beispiel-hub", "tests/conftest.py", "t") is False


def test_should_count_only_files_with_the_wanted_suffix(monkeypatch):
    monkeypatch.setattr(ap, "_api_get", lambda pfad, token: [
        {"name": "ci.yml"}, {"name": "deploy.yml"}, {"name": "README.md"}, {"name": "x.yaml"},
    ])

    assert ap._count_files("beispiel-hub", ".github/workflows", ".yml", "t") == 2


def test_should_count_zero_when_the_directory_is_not_a_list(monkeypatch):
    # die API liefert bei fehlendem Verzeichnis ein Objekt oder None, keine Liste
    monkeypatch.setattr(ap, "_api_get", lambda pfad, token: {"message": "Not Found"})

    assert ap._count_files("beispiel-hub", "tests", ".py", "t") == 0


def test_should_count_url_patterns_from_the_decoded_file(monkeypatch):
    import base64

    quelle = "urlpatterns = [\n  path('a/', v),\n  re_path(r'^b/', v),\n  # path('kommentar/', v),\n]\n"
    kodiert = base64.b64encode(quelle.encode()).decode()
    monkeypatch.setattr(ap, "_api_get", lambda pfad, token: {"content": kodiert})

    # drei Zeilen enthalten path( bzw. re_path( — auch die auskommentierte;
    # die Heuristik ist bewusst grob, das haelt dieser Fall fest
    assert ap._count_url_lines("beispiel-hub", "t") == 3


def test_should_return_zero_url_patterns_when_no_urls_file_exists(monkeypatch):
    monkeypatch.setattr(ap, "_api_get", lambda pfad, token: None)

    assert ap._count_url_lines("beispiel-hub", "t") == 0


def test_should_return_zero_url_patterns_on_undecodable_content(monkeypatch):
    monkeypatch.setattr(ap, "_api_get", lambda pfad, token: {"content": "kein base64!!"})

    assert ap._count_url_lines("beispiel-hub", "t") == 0


def test_should_stop_early_when_the_repo_is_missing(monkeypatch):
    """Fehlendes Repo darf keine weiteren API-Aufrufe ausloesen."""
    aufrufe = []

    def fake(pfad, token):
        aufrufe.append(pfad)
        return None

    monkeypatch.setattr(ap, "_api_get", fake)

    a = ap.scan_via_api("weg-hub", "django", "", "t")

    assert "nicht gefunden" in a.error
    assert len(aufrufe) == 1


# --- lokaler Scan ------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path):
    def _datei(rel: str, inhalt: str = "x\n"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(inhalt, encoding="utf-8")
        return p

    return tmp_path, _datei


def test_should_report_an_error_for_a_missing_directory(tmp_path):
    a = ap.scan_local(tmp_path / "gibtsnicht", "beispiel-hub", "django", "")

    assert "Lokaler Pfad nicht gefunden" in a.error
    assert a.inventory_score == 0


def test_should_map_a_complete_repo_to_a_full_score(repo):
    wurzel, datei = repo
    datei("tests/conftest.py")
    datei("requirements-test.txt")
    datei("pyproject.toml")
    datei(".github/workflows/ci.yml")
    datei("tests/test_alpha.py")

    a = ap.scan_local(wurzel, "beispiel-hub", "django", "")

    assert a.inventory_score == 5
    assert a.error == ""


def test_should_find_tests_in_nested_directories(repo):
    wurzel, datei = repo
    datei("tests/unit/test_a.py")
    datei("tests/integration/test_b.py")

    assert ap.scan_local(wurzel, "beispiel-hub", "django", "").test_file_count == 2


def test_should_count_only_yml_workflows_not_yaml(repo):
    wurzel, datei = repo
    datei(".github/workflows/ci.yml")
    datei(".github/workflows/deploy.yaml")

    assert ap.scan_local(wurzel, "beispiel-hub", "django", "").workflow_count == 1


def test_should_prefer_config_urls_over_root_urls(repo):
    wurzel, datei = repo
    datei("config/urls.py", "path('a/', v)\npath('b/', v)\n")
    datei("urls.py", "path('c/', v)\n")

    assert ap.scan_local(wurzel, "beispiel-hub", "django", "").url_count == 2


def test_should_count_services_one_level_below_apps(repo):
    wurzel, datei = repo
    datei("apps/kunden/services.py")
    datei("apps/rechnungen/services.py")
    datei("apps/tief/verschachtelt/services.py")  # zwei Ebenen -> zaehlt nicht

    assert ap.scan_local(wurzel, "beispiel-hub", "django", "").service_count == 2


# --- Interpreter-Wahl --------------------------------------------------------


def test_should_prefer_a_dot_venv_interpreter(repo):
    wurzel, datei = repo
    datei(".venv/bin/python")

    assert ap._find_python(wurzel) == str(wurzel / ".venv" / "bin" / "python")


def test_should_fall_back_to_the_running_interpreter(tmp_path):
    assert ap._find_python(tmp_path) == sys.executable
