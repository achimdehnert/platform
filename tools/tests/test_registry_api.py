"""Tests fuer tools/registry_api.py — Owner-Aufloesung (ADR-234/255).

Regression-Guard fuer den gen_project_facts-Bug: der Owner wurde hart auf
`achimdehnert` kodiert → 404-GitHub-URL in den always_on-Rules jedes
nicht-achimdehnert-Repos. owner() loest jetzt aus der kanonischen Registry auf
(per-Repo github-Feld zuerst, dann repo_owner-Map, Prefix-Regeln, Default).
"""

import importlib.util
import pathlib
import sys

_SPEC = importlib.util.spec_from_file_location(
    "registry_api",
    pathlib.Path(__file__).resolve().parents[1] / "registry_api.py",
)
reg = importlib.util.module_from_spec(_SPEC)
sys.modules["registry_api"] = reg
_SPEC.loader.exec_module(reg)


_CANON = {
    "meta": {
        "server": {"github_org": "achimdehnert"},
        "repo_owner": {"illustration-fw": "iilgmbh", "iil-klickdummy": "iilgmbh"},
        "owner_prefix_rules": [
            {"prefix": "meiki-", "owner": "meiki-lra"},
            {"prefix": "ttz-", "owner": "ttz-lif"},
            {"prefix": "bahn-", "owner": "bahn-sqf"},
        ],
    },
    "repos": {
        "risk-hub": {"rich": {"github": "iilgmbh/risk-hub"}},
        "137-hub": {"rich": {"github": "achimdehnert/137-hub"}},
        "illustration-fw": {},  # kein github-Feld → repo_owner-Map greift
        "meiki-hub": {},        # kein github-Feld → Prefix greift
        "some-known-hub": {},   # registriert, aber ohne github/override/prefix-Treffer
    },
}


def test_should_resolve_owner_from_per_repo_github_field_first():
    assert reg.owner("risk-hub", _CANON) == "iilgmbh"
    assert reg.owner("137-hub", _CANON) == "achimdehnert"


def test_should_resolve_explicit_repo_owner_override_when_no_github_field():
    assert reg.owner("illustration-fw", _CANON) == "iilgmbh"


def test_should_resolve_owner_by_prefix_rule():
    assert reg.owner("meiki-hub", _CANON) == "meiki-lra"
    assert reg.owner("ttz-anything", _CANON) == "ttz-lif"
    assert reg.owner("bahn-anything", _CANON) == "bahn-sqf"


def test_should_fall_back_to_github_org_default_for_known_repo_without_specifics():
    # "some-known-hub" STEHT in canon["repos"] (registriert), hat aber weder
    # github-Feld noch repo_owner-Override noch Prefix-Treffer → Default ist
    # hier plausibel (kein Raten, sondern die einzig verbleibende, explizit
    # konfigurierte Option für ein bekanntes Repo).
    assert reg.owner("some-known-hub", _CANON) == "achimdehnert"


def test_should_not_guess_default_for_genuinely_unknown_repo_name():
    # F-5 (repo-optimize 2026-07-03): "some-new-hub" ist WEDER in canon["repos"]
    # registriert NOCH trifft eine Prefix-Regel → None statt stillem Default-Rate
    # (Regression gegen den alten Bug, der genau das noch als "achimdehnert" ausgab).
    assert reg.owner("some-new-hub", _CANON) is None


def test_should_return_none_when_meta_and_repos_are_empty():
    assert reg.owner("whatever", {}) is None


def test_should_still_apply_prefix_rule_for_unregistered_repo():
    # Prefix-Regeln sind explizite Konfiguration, kein Raten — sie gelten auch
    # fuer ein Repo, das noch nicht in canon["repos"] auftaucht (Onboarding-Fall).
    assert reg.owner("meiki-not-yet-registered", _CANON) == "meiki-lra"


def test_should_return_none_for_unknown_repo_name_without_strict():
    assert reg.repo("totally-made-up-repo-xyz") is None


def test_should_raise_keyerror_for_unknown_repo_name_with_strict(capsys):
    # X-13 (repo-optimize 2026-07-03): strict=True macht einen Typo laut statt
    # ihn als "keine Daten" durchgehen zu lassen.
    try:
        reg.repo("totally-made-up-repo-xyz", strict=True)
        raised = False
    except KeyError:
        raised = True
    assert raised
    assert "totally-made-up-repo-xyz" in capsys.readouterr().err


def test_should_resolve_real_canonical_non_achimdehnert_repos_not_to_404():
    """Regression gegen den echten Datenstand: jeder Repo, dessen kanonischer
    Owner != achimdehnert ist, muss auch so aufgeloest werden (sonst 404)."""
    canon = reg.load_canonical()
    checked_non_default = 0
    for name in canon["repos"]:
        resolved = reg.owner(name, canon)
        entry = canon["repos"][name]
        gh = (entry.get("rich") or {}).get("github") or (entry.get("flat") or {}).get("github")
        if gh and "/" in gh:
            assert resolved == gh.split("/", 1)[0]
            if resolved != "achimdehnert":
                checked_non_default += 1
    # canonical enthaelt mindestens risk-hub + nl2iot-hub unter iilgmbh
    assert checked_non_default >= 1
