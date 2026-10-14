"""Tests zu KONZ-platform-070 Z4 „Branch-Schutz als Deklaration“ (Mandat #3903 WP5).

Abgedeckt: Profil-Ableitung aus der Registry (`registry_api.review_profil`/`review_soll`),
Pilot-Repos, die generierten Wave-Views, der Meter-Report (Befehl je Drift-Repo,
nie anwenden) und die Melder-Register-Konsistenz der Phase 0.7.34.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import branch_protection_meter as bpm  # noqa: E402
import registry_api as reg  # noqa: E402

PROFILE = yaml.safe_load((ROOT / "registry" / "review-profile.yaml").read_text())


def _canon(**repos) -> dict:
    """Minimale canonical.yaml-Struktur: name → (flat, rich, lifecycle) oder Eintrag."""
    return {
        "meta": {
            "sitzungs_klasse": {
                "demo-business": "business",
                "demo-plattform": "plattform",
                "demo-lib": "bibliothek",
            }
        },
        "repos": repos,
    }


def _eintrag(
    owner="demo-owner", archived=False, deployed=False, lifecycle=None, **rich
) -> dict:
    e = {
        "in_flat": True,
        "in_rich": True,
        "flat": {"archived": archived},
        "rich": {"deployed": deployed, "github": f"{owner}/x", **rich},
        "domain": "demo",
    }
    if lifecycle:
        e["lifecycle"] = lifecycle
    return e


# ── Ableitung ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "eintrag", "erwartet"),
    [
        ("demo-archiv", _eintrag(archived=True, deployed=True), "keins"),
        ("demo-frozen", _eintrag(lifecycle="frozen", deployed=True), "keins"),
        ("demo-prod", _eintrag(deployed=True), "deployed"),
        ("demo-plattform", _eintrag(), "plattform"),
        ("demo-lib", _eintrag(), "library"),
        ("demo-business", _eintrag(), "static"),
    ],
)
def test_should_derive_profile_from_registry_fields(name, eintrag, erwartet):
    canon = _canon(**{name: eintrag})
    assert reg.review_profil(name, canon, PROFILE) == erwartet


def test_should_let_explicit_override_win_over_every_rule():
    canon = _canon(**{"demo-prod": _eintrag(deployed=True, review_profile="library")})
    assert reg.review_profil("demo-prod", canon, PROFILE) == "library"


def test_should_reject_override_that_names_no_declared_profile():
    canon = _canon(**{"demo-prod": _eintrag(deployed=True, review_profile="geheim")})
    with pytest.raises(KeyError):
        reg.review_profil("demo-prod", canon, PROFILE)


def test_should_return_none_for_unknown_repo():
    assert reg.review_profil("gibt-es-nicht", _canon(), PROFILE) is None


def test_should_resolve_aus_ci_to_default_or_repo_check():
    canon = _canon(
        **{
            "demo-prod": _eintrag(deployed=True),
            "demo-lib": _eintrag(review_check="Quality Gate"),
        }
    )
    assert reg.review_soll("demo-prod", canon, PROFILE)["required_checks"] == [
        PROFILE["defaults"]["ci_gate_check"]
    ]
    assert reg.review_soll("demo-lib", canon, PROFILE)["required_checks"] == [
        "Quality Gate"
    ]


def test_should_derive_pilot_repos_to_measurable_profiles():
    """Mandat #3903 O2: platform, risk-hub, writing-hub — ohne Override deployed/plattform."""
    canon = reg.load_canonical()
    for name in reg.review_pilot(PROFILE):
        soll = reg.review_soll(name, canon, PROFILE)
        assert soll is not None, name
        assert soll["profil"] in ("deployed", "plattform"), (name, soll["profil"])
        assert soll["messen"] is True
        assert soll["approvals"] == 1
        assert soll["owner"], name


def test_should_only_allow_declared_profiles_as_zuordnung_targets():
    ziele = {r.get("profil", r.get("sonst")) for r in PROFILE["zuordnung"]}
    assert ziele <= set(PROFILE["profile"])


# ── Engine-Profil (Ledger L1, #3903) ────────────────────────────────────────────


def test_should_declare_engine_profile_known_to_rule_engine_for_every_profile():
    """Jedes Registry-Profil nennt ein Engine-Profil aus review_regeln.PROFILE oder null —
    sonst laeuft die Engine mit einem Profil, das keine Regel kennt (Realfall platform
    `plattform` → Workflow musste `deployed` raten)."""
    import review_regeln as rr

    for name, p in PROFILE["profile"].items():
        assert "engine_profil" in p, name
        assert p["engine_profil"] is None or p["engine_profil"] in rr.PROFILE, name


@pytest.mark.parametrize(
    ("name", "eintrag", "erwartet"),
    [
        ("demo-prod", _eintrag(deployed=True), "deployed"),
        ("demo-plattform", _eintrag(), "deployed"),
        ("demo-lib", _eintrag(), "library"),
        ("demo-business", _eintrag(), "default"),
        ("demo-archiv", _eintrag(archived=True), None),
    ],
)
def test_should_map_registry_profile_to_engine_profile(name, eintrag, erwartet):
    canon = _canon(**{name: eintrag})
    assert reg.review_engine_profil(name, canon, PROFILE) == erwartet


def test_should_return_none_engine_profile_for_unknown_repo():
    assert reg.review_engine_profil("gibt-es-nicht", _canon(), PROFILE) is None


def test_should_print_engine_profile_of_platform_via_cli():
    """review-check.yml ruft genau diese Zeile; platform ist Pilot (O2) und traegt `plattform`."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "registry_api.py"), "engine-profil", "platform"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "deployed"
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "registry_api.py"), "engine-profil", "gibt-es-nicht"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3


# ── Views ───────────────────────────────────────────────────────────────────────


def test_should_keep_wave_views_identical_to_registry_derivation():
    """governance/rulesets/wave*-repos.json sind generierte Views — Drift-Test wie
    registry-canonical verify. Reparatur: `branch_protection_meter.py --views schreiben`."""
    for pfad, soll in bpm.view_eintraege().items():
        assert json.loads(pfad.read_text()) == soll, pfad.name


def test_should_not_list_archived_repos_in_any_view():
    canon = reg.load_canonical()
    for eintraege in bpm.view_eintraege().values():
        for e in eintraege:
            assert reg.review_profil(e["repo"], canon, PROFILE) != "keins", e["repo"]


# ── Meter: Soll gegen Ist, Befehl je Drift-Repo, nichts anwenden ──────────────


def _soll(**override) -> dict:
    s = {
        "repo": "demo-prod",
        "owner": "demo-owner",
        "profil": "deployed",
        "required_checks": ["ci / gate"],
        "approvals": 1,
        "bot_zaehlt": True,
        "linear_history": False,
        "force_push": True,
        "messen": True,
    }
    s.update(override)
    return s


def _ruleset(check="ci / gate", approvals=0, enforcement="active") -> dict:
    rules = [
        {
            "type": "required_status_checks",
            "parameters": {"required_status_checks": [{"context": check}]},
        }
    ]
    if approvals:
        rules.append(
            {
                "type": "pull_request",
                "parameters": {"required_approving_review_count": approvals},
            }
        )
    return {
        "id": 42,
        "name": bpm.RULESET_NAME,
        "enforcement": enforcement,
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "rules": rules,
    }


def _ist(rulesets, classic=None) -> dict:
    ist = bpm.ist_zusammenfassen(rulesets, classic)
    ist["rulesets"] = rulesets
    return ist


def test_should_pass_when_ruleset_covers_check_and_approval():
    e = bpm.bewerte(_soll(), _ist([_ruleset(approvals=1)]))
    assert e["status"] == bpm.STATUS_OK
    assert e["befehl"] is None


def test_should_count_classic_branch_protection_as_ist():
    classic = {
        "required_status_checks": {"contexts": ["ci / gate"]},
        "required_pull_request_reviews": {"required_approving_review_count": 1},
    }
    e = bpm.bewerte(_soll(), _ist([], classic))
    assert e["status"] == bpm.STATUS_OK


def test_should_not_flag_more_protection_than_soll_as_drift():
    e = bpm.bewerte(
        _soll(profil="library", approvals=0, bot_zaehlt=False),
        _ist([_ruleset(approvals=2)]),
    )
    assert e["status"] == bpm.STATUS_OK


def test_should_flag_missing_approval_and_offer_gh_api_command():
    e = bpm.bewerte(_soll(), _ist([_ruleset(approvals=0)]))
    assert e["status"] == bpm.STATUS_DRIFT
    assert e["gruende"] == ["approvals 0 < 1"]
    assert e["befehl"].startswith("printf ")
    assert "gh api repos/demo-owner/demo-prod/rulesets/42 -X PATCH" in e["befehl"]


def test_should_keep_existing_rules_when_building_target_ruleset():
    """Ein PATCH ersetzt `rules` komplett — bestehende Checks duerfen nicht verschwinden."""
    bestehend = _ruleset(check="guardian")
    bestehend["rules"][0]["parameters"]["required_status_checks"].append(
        {"context": "gitleaks"}
    )
    ziel = bpm.ruleset_ziel(_soll(required_checks=["guardian"]), bestehend)
    kontexte = {
        c["context"]
        for r in ziel["rules"]
        if r["type"] == "required_status_checks"
        for c in r["parameters"]["required_status_checks"]
    }
    assert kontexte == {"guardian", "gitleaks"}
    pr = next(r for r in ziel["rules"] if r["type"] == "pull_request")
    assert pr["parameters"]["required_approving_review_count"] == 1
    assert ziel["enforcement"] == "active"
    assert "id" not in ziel


def test_should_offer_apply_script_when_only_check_is_missing():
    e = bpm.bewerte(
        _soll(profil="library", approvals=0, bot_zaehlt=False),
        _ist([_ruleset(check="anderer")]),
    )
    assert e["status"] == bpm.STATUS_DRIFT
    assert e["befehl"] == "bash tools/apply-branch-protection.sh --repo demo-prod"


def test_should_render_one_command_per_drift_repo():
    results = [
        bpm.bewerte(_soll(repo="a-hub"), _ist([_ruleset(approvals=1)])),
        bpm.bewerte(_soll(repo="b-hub"), _ist([_ruleset(approvals=0)])),
        bpm.bewerte(
            _soll(repo="c-hub", profil="library", approvals=0, bot_zaehlt=False),
            _ist([]),
        ),
    ]
    report = bpm.render_report(results)
    assert "| Repo | Profil | Soll | Ist | Drift |" in report
    assert (
        "**b-hub**" in report and "gh api repos/demo-owner/b-hub/rulesets/42" in report
    )
    assert "`bash tools/apply-branch-protection.sh --repo c-hub`" in report
    assert report.count("- **") == 2  # genau ein Befehlsblock je Drift-Repo


def test_should_never_apply_anything_itself():
    """Das Skript misst nur: kein schreibender API-Aufruf im Quelltext."""
    quelle = (ROOT / "tools" / "branch_protection_meter.py").read_text()
    for verb in ("urlopen(req, data", '-X PATCH"', 'method="PATCH"', 'method="POST"'):
        assert verb not in quelle
    assert "urllib.request.Request(" in quelle  # nur GET ohne data/method


def test_should_report_nicht_messbar_separately_from_drift(monkeypatch):
    monkeypatch.setattr(
        bpm, "fetch_rulesets", lambda o, r, t: (_ for _ in ()).throw(TimeoutError("x"))
    )
    results = bpm.messen([_soll()], token="t")
    assert results[0]["status"] == bpm.STATUS_NICHT_MESSBAR
    assert "nicht messbar" in bpm.render_kurz(results, "Test")


def test_should_render_kurz_ok_line_without_drift():
    results = [bpm.bewerte(_soll(), _ist([_ruleset(approvals=1)]))]
    assert bpm.render_kurz(results, "Pilot").startswith("OK: 1/1")


def test_should_select_pilot_plus_all_deployed_in_pilot_mode():
    liste = bpm.soll_aus_registry(pilot=True)
    namen = {s["repo"] for s in liste}
    assert set(reg.review_pilot(PROFILE)) <= namen
    assert all(s["profil"] in ("deployed", "plattform") for s in liste)
    assert all(s["messen"] for s in liste)


def test_should_print_soll_json_with_required_check_for_apply_script():
    res = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "branch_protection_meter.py"),
            "--soll-json",
            "--repos",
            "platform",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, res.stderr
    daten = json.loads(res.stdout)
    assert [d["repo"] for d in daten] == ["platform"]
    assert daten[0]["required_check"] == daten[0]["required_checks"][0]


# ── Registry-View & Melder-Register ────────────────────────────────────────────


def test_should_propagate_review_check_into_rich_view():
    """`rich.review_check` ueberlebt die Projektion (`gen_rich` = die eine Implementierung
    hinter der rich-View). Dass die View-Datei der Projektion entspricht, prueft das
    Drift-Gate `registry-canonical.py verify` — kein Direct-Read der View (ADR-234 §11.1)."""
    canon = reg.load_canonical()
    view_by_name = {
        s["name"]: s for d in reg.gen_rich(canon)["domains"] for s in d["systems"]
    }
    assert view_by_name, "Projektion liefert keine Repo-Eintraege"
    for name, e in canon["repos"].items():
        if reg.REVIEW_CHECK_FELD in e.get("rich", {}):
            assert (
                view_by_name[name].get(reg.REVIEW_CHECK_FELD)
                == e["rich"][reg.REVIEW_CHECK_FELD]
            ), name


def test_should_register_phase_0_7_34_with_named_reader():
    register = yaml.safe_load(
        (ROOT / "governance" / "melder-register.yaml").read_text()
    )
    eintraege = [
        m for m in register["melder"] if m["phase"] == "0.7.34 review-profil-drift"
    ]
    assert len(eintraege) == 1
    assert "Owner" in eintraege[0]["leser"]
    assert eintraege[0]["runbook"] == "0.R#0.7.34"
    runner = (ROOT / "tools" / "session_start_checks.sh").read_text()
    assert 'record "0.7.34 review-profil-drift"' in runner


def test_should_pass_melder_register_check_kurz():
    res = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "melder_register_check.py"), "--kurz"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(ROOT),
    )
    assert res.returncode == 0, res.stdout + res.stderr


def test_should_not_mutate_profile_dict_across_calls():
    vorher = copy.deepcopy(PROFILE)
    reg.review_soll("platform", reg.load_canonical(), PROFILE)
    bpm.soll_aus_registry(pilot=True, profile=PROFILE)
    assert PROFILE == vorher
