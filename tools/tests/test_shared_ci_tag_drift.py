"""Tests für die shared-ci-Tag-Drift-Regeln in scripts/drift_check.py.

🌀 Drift-Klasse „Tag ≠ main" (3 Vorfälle, zuletzt 2026-06-12 ADR-242 Phase 3):
shared-ci-Tags wurden vor Fixes in der kanonischen platform-Quelle geschnitten
bzw. Consumer pinnen veraltete Tags. Zwei Regeln:
  shared-ci-tag-outdated (warn)  — Consumer pinnt nicht-neuesten Tag
  shared-ci-tag-stale    (error) — neuester Tag ≠ platform-main-Kanon

Rein (kein Token nötig): GitHub-Zugriffe werden gemockt bzw. der State
explizit injiziert.
"""

from __future__ import annotations

import importlib.util
import sys

import yaml
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "drift_check.py"
_spec = importlib.util.spec_from_file_location("drift_check", _SCRIPT)
dc = importlib.util.module_from_spec(_spec)
sys.modules["drift_check"] = dc
_spec.loader.exec_module(dc)


CI_YML = (
    "jobs:\n  ci:\n    uses: iilgmbh/shared-ci/.github/workflows/_ci-python.yml@{ref}\n"
)


def _mock_repo_files(monkeypatch, content):
    monkeypatch.setattr(dc, "_get_dir_files", lambda repo, path, token: ["ci.yml"])
    monkeypatch.setattr(dc, "_get_file_content", lambda repo, path, token: content)


def test_should_parse_pins_with_file_and_ref():
    pins = dc.parse_shared_ci_pins(CI_YML.format(ref="v1.0.4"))
    assert pins == [("_ci-python.yml", "v1.0.4")]


def test_should_pick_latest_tag_by_semver_not_list_order():
    assert dc.latest_shared_ci_tag(["v1.0.4", "v1.0.10", "v1.0.2"]) == "v1.0.10"
    assert dc.latest_shared_ci_tag(["egal", "kein-semver"]) is None


def test_should_warn_on_outdated_pin(monkeypatch):
    _mock_repo_files(monkeypatch, CI_YML.format(ref="v1.0.2"))
    state = {"latest_tag": "v1.0.5", "stale_files": []}
    drifts = dc.check_shared_ci_tag_drift("demo-hub", "", state=state)
    assert [d.rule for d in drifts] == ["shared-ci-tag-outdated"]
    assert drifts[0].severity == "warn"
    assert "v1.0.5" in drifts[0].message
    assert "v1.0.2" in drifts[0].fix_hint


def test_should_pass_when_pin_is_latest_and_tag_matches_canon(monkeypatch):
    _mock_repo_files(monkeypatch, CI_YML.format(ref="v1.0.5"))
    state = {"latest_tag": "v1.0.5", "stale_files": []}
    assert dc.check_shared_ci_tag_drift("demo-hub", "", state=state) == []


def test_should_error_when_latest_tag_is_stale_vs_canon(monkeypatch):
    _mock_repo_files(monkeypatch, CI_YML.format(ref="v1.0.5"))
    state = {"latest_tag": "v1.0.5", "stale_files": ["_ci-python.yml"]}
    drifts = dc.check_shared_ci_tag_drift("demo-hub", "", state=state)
    assert [d.rule for d in drifts] == ["shared-ci-tag-stale"]
    assert drifts[0].severity == "error"
    assert "Kanon" in drifts[0].message


def test_should_not_warn_on_branch_refs_only_semver_tags(monkeypatch):
    # @main-Pins sind kein Tag-Drift (eigene Konvention: Kanon direkt)
    _mock_repo_files(monkeypatch, CI_YML.format(ref="main"))
    state = {"latest_tag": "v1.0.5", "stale_files": []}
    assert dc.check_shared_ci_tag_drift("demo-hub", "", state=state) == []


def test_should_return_empty_for_repos_without_pins(monkeypatch):
    _mock_repo_files(monkeypatch, "jobs:\n  test:\n    runs-on: ubuntu-latest\n")
    called = {"n": 0}

    def boom(token):
        called["n"] += 1
        raise AssertionError("state darf ohne Pins nicht berechnet werden")

    monkeypatch.setattr(dc, "_shared_ci_state", boom)
    assert dc.check_shared_ci_tag_drift("demo-hub", "") == []
    assert called["n"] == 0


def test_should_not_flag_mirror_path_rewrite_as_stale(monkeypatch):
    """Der shared-ci-Mirror schreibt nur Repo-Pfade um — das ist kein Drift."""
    canonical = "uses: achimdehnert/platform/.github/actions/x@main\n"
    mirrored = "uses: iilgmbh/shared-ci/.github/actions/x@main\n"

    def fake_api_get(path, token):
        if path.endswith("/tags"):
            return [{"name": "v1.0.4"}]
        if "contents/.github/workflows?ref=" in path:
            return [{"name": "_ci-python.yml", "type": "file"}]
        return None

    def fake_content_at(owner_repo, path, ref, token):
        return canonical if owner_repo.endswith("/platform") else mirrored

    monkeypatch.setattr(dc, "_api_get", fake_api_get)
    monkeypatch.setattr(dc, "_get_content_at", fake_content_at)
    monkeypatch.setattr(dc, "_SHARED_CI_STATE", None)
    state = dc._shared_ci_state("")
    assert state == {"latest_tag": "v1.0.4", "stale_files": []}


def test_should_flag_genuine_content_difference_as_stale(monkeypatch):
    def fake_api_get(path, token):
        if path.endswith("/tags"):
            return [{"name": "v1.0.4"}]
        if "contents/.github/workflows?ref=" in path:
            return [{"name": "_ci-python.yml", "type": "file"}]
        return None

    def fake_content_at(owner_repo, path, ref, token):
        if owner_repo.endswith("/platform"):
            return "jobs:\n  gate:\n    runs-on: x\n"
        return "jobs: {}\n"

    monkeypatch.setattr(dc, "_api_get", fake_api_get)
    monkeypatch.setattr(dc, "_get_content_at", fake_content_at)
    monkeypatch.setattr(dc, "_SHARED_CI_STATE", None)
    assert dc._shared_ci_state("")["stale_files"] == ["_ci-python.yml"]


# ── Kanon-Abgleich: struktureller Vergleich statt Text-Ersetzung ─────────────
#
# Die Fixtures unten sind gekuerzte, aber woertliche Auszuege aus dem Bestand
# (shared-ci@v1.1.2 gegen platform-main, gemessen 2026-08-04). Jede von ihnen
# stand fuer einen realen Dauer-Fehlalarm der frueheren `str.replace()`-Loesung.

_SHARED = "iilgmbh/shared-ci"
_KANON = "achimdehnert/platform"


def _workflow(
    repo: str, verzeichnis: str, *, step_name="Checkout", run=None, extra=None
):
    """Minimaler, aber echter Workflow mit Selbst-Checkout."""
    step = {
        "name": step_name,
        "uses": "actions/checkout@v4",
        "with": {"repository": repo, "path": verzeichnis},
    }
    schritte = [step]
    if run:
        schritte.append({"name": "Pruefen", "run": run})
    if extra:
        schritte.append(extra)
    return yaml.safe_dump(
        {"name": "wf", "jobs": {"j": {"steps": schritte}}}, sort_keys=False
    )


def test_should_accept_a_pure_checkout_directory_rename():
    """`_shared_ci_checks` -> `_platform_checks` ist Port-Mechanik, kein Drift."""
    tagged = _workflow(
        _SHARED, "_shared_ci_checks", run="python3 _shared_ci_checks/scripts/x.py"
    )
    kanon = _workflow(
        _KANON, "_platform_checks", run="python3 _platform_checks/scripts/x.py"
    )
    assert dc.shared_ci_deckt_kanon(tagged, kanon)


def test_should_accept_a_canon_directory_with_leading_underscore():
    """`_platform` (statt `platform`) — an einer Token-Liste scheiterte genau das.

    Realfall `doc-profile-guard.yml`: der Kanon checkt nach `_platform` aus,
    die fruehere Abbildung lieferte `platform` und meldete die Datei dauerhaft.
    """
    tagged = _workflow(_SHARED, "_shared_ci", run="bash _shared_ci/scripts/check.sh")
    kanon = _workflow(_KANON, "_platform", run="bash _platform/scripts/check.sh")
    assert dc.shared_ci_deckt_kanon(tagged, kanon)


def test_should_ignore_the_directory_word_inside_a_step_name():
    """Realfall `deploy-config-lint.yml`: Kanon-Verzeichnis heisst schlicht `platform`.

    Das Wort steht auch im Step-Namen ("Checkout platform (Lint-Script)"). Eine
    Ersetzung ueber den ganzen Text traf ihn mit und erzeugte den Fehlalarm.
    """
    name = "Checkout platform (Lint-Script)"
    tagged = _workflow(
        _SHARED, "_shared_ci", step_name=name, run="python3 _shared_ci/tools/l.py"
    )
    kanon = _workflow(
        _KANON, "platform", step_name=name, run="python3 platform/tools/l.py"
    )
    assert dc.shared_ci_deckt_kanon(tagged, kanon)


def test_should_ignore_an_issue_reference_in_free_text():
    """Realfall `handoff-banner-gate.yml`: "achimdehnert/platform#913" im Fixture.

    Die Referenz meint eine platform-Issue und steht auf BEIDEN Seiten gleich —
    bis eine Repo-Ersetzung sie anfasst.
    """
    run = "printf 'Live-Status: achimdehnert/platform#913'"
    tagged = _workflow(_SHARED, "_shared_ci_checks", run=run)
    kanon = _workflow(_KANON, "_platform_checks", run=run)
    assert dc.shared_ci_deckt_kanon(tagged, kanon)


def test_should_ignore_comments_because_they_do_not_run():
    """Realfall `_ci-pypi.yml`/`validate-workflows.yml`: Drift nur im Kommentar.

    Dort ist "iilgmbh/shared-ci" der Gegenstand des Satzes, kein Pfad.
    """
    tagged = "# SSoT ist iilgmbh/shared-ci\n" + _workflow(_SHARED, "_shared_ci")
    kanon = "# ganz anderer Kommentar\n" + _workflow(_KANON, "platform")
    assert dc.shared_ci_deckt_kanon(tagged, kanon)


def test_should_still_flag_a_real_behaviour_difference():
    """Beisskraft: ein zusaetzlicher Schritt bleibt sichtbar.

    Der einzige echte Fund im Bestand (`_deploy-unified.yml`, GHCR-Login) ist
    von dieser Form — dem Kanon fehlte ein `env:`-Block.
    """
    tagged = _workflow(
        _SHARED, "_shared_ci", extra={"name": "Deploy", "env": {"GHCR_TOKEN": "x"}}
    )
    kanon = _workflow(_KANON, "platform", extra={"name": "Deploy"})
    assert not dc.shared_ci_deckt_kanon(tagged, kanon)


def test_should_still_flag_a_changed_command():
    """Beisskraft: ein geaendertes Kommando ist Drift, kein Pfad-Rauschen."""
    tagged = _workflow(_SHARED, "_shared_ci", run="python3 _shared_ci/tools/neu.py")
    kanon = _workflow(_KANON, "platform", run="python3 platform/tools/alt.py")
    assert not dc.shared_ci_deckt_kanon(tagged, kanon)


def test_should_fall_back_to_text_comparison_on_unparsable_yaml():
    """Kaputtes YAML darf nicht still gruen werden."""
    assert not dc.shared_ci_deckt_kanon("{{ kein yaml", "name: wf\n")
    assert dc.shared_ci_deckt_kanon("{{ kein yaml", "{{ kein yaml")


def test_should_read_the_checkout_directory_from_the_file_itself():
    """Die Abbildung wird abgeleitet, nicht geraten — Kern des Umbaus."""
    tree = yaml.safe_load(_workflow(_SHARED, "_irgendwas_eigenes"))
    assert dc._eigenes_checkout_verzeichnis(tree, _SHARED) == "_irgendwas_eigenes"
    assert dc._eigenes_checkout_verzeichnis(tree, "fremd/repo") is None
