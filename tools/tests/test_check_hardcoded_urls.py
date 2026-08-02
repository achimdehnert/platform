"""check_hardcoded_urls: Regelanwendung und die Ausnahmen drumherum.

Bei einem Scanner ist der Fehlalarm die teure Fehlrichtung. Ein uebersehener
Befund kostet einen Fund; ein Scanner, der bei jedem Django-Boilerplate anschlaegt,
kostet seine eigene Glaubwuerdigkeit — danach liest niemand mehr seine Ausgabe,
auch nicht die echten Treffer. Die Ausnahmen (Tests, Migrationen, Template-
Whitelist, IP-Whitelist, setdefault, noqa) sind deshalb der eigentliche
Testgegenstand, nicht die Regex.

Jede Ausnahme hat hier ihren Gegenfall: dass sie greift, UND dass sie nicht
breiter greift als gemeint.
"""

import importlib.util
import pathlib
import re
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "check_hardcoded_urls.py"
_spec = importlib.util.spec_from_file_location("check_hardcoded_urls", _SRC)
chu = importlib.util.module_from_spec(_spec)
# VOR exec_module registrieren — siehe test_hardcode_scanner.py: @dataclass
# schlaegt waehrend der Klassendefinition sys.modules[cls.__module__] nach.
sys.modules[_spec.name] = chu
_spec.loader.exec_module(chu)


def regel(**over) -> "chu.Rule":
    basis = dict(
        rule_id="V-TEST-01",
        category="VERMEIDBAR",
        description="Testregel",
        pattern=re.compile(r"TREFFER"),
        suffixes=(".py",),
        alternative="etwas anderes",
    )
    basis.update(over)
    return chu.Rule(**basis)


P = pathlib.Path


# --- Pfad-Filter -------------------------------------------------------------


@pytest.mark.parametrize("teil", ["node_modules", ".venv", "__pycache__", ".git", ".claude"])
def test_should_skip_paths_inside_vendored_or_generated_dirs(teil):
    assert chu._should_skip_path(P(f"repo/{teil}/modul.py"))


def test_should_not_skip_a_normal_source_path():
    assert not chu._should_skip_path(P("repo/apps/views.py"))


def test_should_not_skip_a_dir_that_merely_contains_a_skip_name():
    # 'buildtools' ist nicht 'build' — Teilstring darf nicht ausreichen
    assert not chu._should_skip_path(P("repo/buildtools/modul.py"))


def test_should_recognise_test_files_and_conftest():
    assert chu._is_test_file(P("test_views.py"))
    assert chu._is_test_file(P("conftest.py"))
    assert not chu._is_test_file(P("views_test.py"))  # Suffix-Form zaehlt nicht


def test_should_recognise_migrations_by_directory_not_by_name():
    assert chu._is_migration(P("apps/kunden/migrations/0001_initial.py"))
    assert not chu._is_migration(P("apps/kunden/migration_helper.py"))


def test_should_recognise_seed_and_fixture_files():
    assert chu._is_seed_or_fixture(P("factories.py"))
    assert chu._is_seed_or_fixture(P("seed_kunden.py"))
    assert chu._is_seed_or_fixture(P("bootstrap_daten.py"))
    assert not chu._is_seed_or_fixture(P("views.py"))


def test_should_treat_vendor_and_github_as_info_skip_paths():
    assert chu._in_skip_path(P("repo/vendor/lib.py"))
    assert chu._in_skip_path(P("repo/.github/workflows/ci.yml"))
    assert not chu._in_skip_path(P("repo/apps/views.py"))


@pytest.mark.parametrize("zeile", ['href="/admin/"', 'href="https://x"', "{{ url }}", "{% url 'a' %}"])
def test_should_allow_whitelisted_template_tokens(zeile):
    assert chu._tmpl_allowed(zeile)


def test_should_not_allow_a_plain_hardcoded_template_path():
    assert not chu._tmpl_allowed('href="/kunden/liste/"')


# --- _check_line: greift die Regel? -----------------------------------------


def test_should_match_a_plain_violation():
    assert chu._check_line(regel(), "x = TREFFER", P("apps/views.py"))


def test_should_not_match_a_line_without_the_pattern():
    assert not chu._check_line(regel(), "x = harmlos", P("apps/views.py"))


@pytest.mark.parametrize("praefix", ["#", "//", "{#", "<!--"])
def test_should_ignore_the_finding_in_a_comment(praefix):
    assert not chu._check_line(regel(), f"{praefix} TREFFER", P("apps/views.py"))


@pytest.mark.parametrize("marker", ["# noqa", "# nosec", "hardcoded-ok"])
def test_should_honour_an_explicit_opt_out(marker):
    assert not chu._check_line(regel(), f"x = TREFFER  {marker}", P("apps/views.py"))


def test_should_skip_a_test_file_by_default():
    assert not chu._check_line(regel(), "x = TREFFER", P("test_views.py"))


def test_should_scan_a_test_file_when_the_rule_opts_in():
    assert chu._check_line(regel(skip_in_tests=False), "x = TREFFER", P("test_views.py"))


def test_should_respect_skip_filenames():
    r = regel(skip_filenames=frozenset({"settings.py"}))

    assert not chu._check_line(r, "x = TREFFER", P("config/settings.py"))
    assert chu._check_line(r, "x = TREFFER", P("config/urls.py"))


def test_should_respect_only_filenames():
    r = regel(only_filenames=frozenset({"settings.py"}))

    assert chu._check_line(r, "x = TREFFER", P("config/settings.py"))
    assert not chu._check_line(r, "x = TREFFER", P("config/urls.py"))


def test_should_skip_info_rules_in_vendor_but_not_avoidable_ones():
    pfad = P("repo/vendor/lib.py")

    assert not chu._check_line(regel(category="INFO"), "x = TREFFER", pfad)
    assert chu._check_line(regel(category="VERMEIDBAR"), "x = TREFFER", pfad)


def test_should_skip_seed_files_only_for_the_two_config_rules():
    pfad = P("apps/factories.py")

    assert not chu._check_line(regel(rule_id="I-CFG-03", category="INFO"), "x = TREFFER", pfad)
    assert not chu._check_line(regel(rule_id="I-CFG-04", category="INFO"), "x = TREFFER", pfad)
    # eine andere INFO-Regel greift dort weiterhin
    assert chu._check_line(regel(rule_id="I-CFG-09", category="INFO"), "x = TREFFER", pfad)


@pytest.mark.parametrize("adresse", ["127.0.0.1", "localhost", "0.0.0.0", "172.17.0.2", "192.168.1.5"])
def test_should_whitelist_local_addresses_for_the_ip_rule(adresse):
    r = regel(rule_id="I-CFG-02", category="INFO")

    assert not chu._check_line(r, f"HOST = '{adresse}' TREFFER", P("config/settings.py"))


def test_should_still_flag_a_public_ip_for_the_ip_rule():
    r = regel(rule_id="I-CFG-02", category="INFO")

    assert chu._check_line(r, "HOST = '203.0.113.7' TREFFER", P("config/settings.py"))


def test_should_allow_environ_setdefault_in_boilerplate_rules():
    for rid in ("V-CFG-01", "V-CFG-02"):
        r = regel(rule_id=rid)
        assert not chu._check_line(r, "os.environ.setdefault('X', 'TREFFER')", P("manage.py"))
        assert chu._check_line(r, "os.environ['X'] = 'TREFFER'", P("manage.py"))


# --- V-CFG-02: nur .get OHNE Default ist "ohne Fallback-Logik" ----------------
# Realfall 2026-08-02 (Megatest-Lauf 30619024656): die alte Regex flaggte JEDEN
# os.environ.get(-Aufruf — auch mit Default, also das von der Regel selbst
# empfohlene Muster. Fünf Budget-0-Repos fielen fast nur dadurch durch.


def _echte_regel(rule_id: str) -> "chu.Rule":
    return next(r for r in chu.RULES if r.rule_id == rule_id)


def test_should_flag_environ_get_without_default():
    r = _echte_regel("V-CFG-02")
    assert chu._check_line(r, 'wert = os.environ.get("MAIL_AGENT_TOOLS")', P("apps/x.py"))
    assert chu._check_line(r, "wert = os.environ.get('CACHE_DIR')", P("apps/x.py"))


def test_should_not_flag_environ_get_with_default():
    r = _echte_regel("V-CFG-02")
    assert not chu._check_line(r, 'creds = os.environ.get("MAIL_GRAPH_CREDS", "")', P("apps/x.py"))
    assert not chu._check_line(r, "t = float(os.environ.get('TIMEOUT', '15'))", P("apps/x.py"))


def test_should_not_flag_undecidable_get_calls():
    r = _echte_regel("V-CFG-02")
    # mehrzeiliger Aufruf: das Default-Argument steht auf der Folgezeile
    assert not chu._check_line(r, "mcp_url = os.environ.get(", P("apps/x.py"))
    # Variablen-Argument: zeilenweise nicht entscheidbar
    assert not chu._check_line(r, "raw = os.environ.get(name)", P("apps/x.py"))


def test_should_apply_the_template_whitelist_only_to_html_files():
    zeile = 'href="https://extern" TREFFER'

    assert not chu._check_line(regel(), zeile, P("templates/seite.html"))
    assert chu._check_line(regel(), zeile, P("apps/views.py"))
