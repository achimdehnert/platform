"""R7 Fault-Injection für registry_coverage_drift v2 (KONZ-001 §5 R7, Issue #488).

+/- Tests über die reine `compute_drift`: aligned → drift 0; injizierter Defekt je Klasse
(enrollment-gap, owner-migration, basename-ambiguity, production-phantom, schema-incomplete)
MUSS geflaggt werden. Genau das Muster, das KONZ-001 R7 von jedem erzwingenden Gate verlangt.

Run: `python3 -m pytest tools/tests/test_registry_coverage_drift.py -q`
(läuft jetzt zusätzlich im generischen tools-tests.yml Gate)
"""
import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "registry_coverage_drift.py"
_spec = importlib.util.spec_from_file_location("rcd", _SRC)
rcd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rcd)


def _canon(*entries):
    """entries: (fullname, lifecycle, deployed, owner_explicit) → canonical-dict."""
    return {fn: {"name": fn.split("/")[-1], "lifecycle": lc, "deployed": dep, "owner_explicit": oe}
            for fn, lc, dep, oe in entries}


def test_should_report_zero_drift_when_aligned():
    res = rcd.compute_drift({"achimdehnert/a"}, _canon(("achimdehnert/a", "production", True, True)))
    assert res["drift_score"] == 0
    assert res["severity"] == {"critical": 0, "warn": 0, "info": 0}


def test_should_flag_unenrolled_repo_as_warn():
    canon = _canon(("achimdehnert/a", "production", True, True))
    res = rcd.compute_drift({"achimdehnert/a", "achimdehnert/b"}, canon)
    assert "achimdehnert/b" in res["enrollment_gap"]
    assert res["severity"]["warn"] == 1 and res["severity"]["critical"] == 0


def test_should_classify_owner_migration_single_candidate():
    res = rcd.compute_drift({"iilgmbh/a"}, _canon(("achimdehnert/a", "experimental", False, True)))
    assert res["migrated"] == [{"repo": "a", "canonical": "achimdehnert/a", "reality": "iilgmbh/a"}]
    assert res["ambiguous"] == [] and res["phantom"] == []


def test_should_flag_ambiguous_basename_collision_not_silent_migration():
    # zwei Owner mit gleichem basename → AMBIGUOUS (kritisch), NICHT still MIGRATED (AD-4)
    canon = _canon(("achimdehnert/a", "production", True, True))
    res = rcd.compute_drift({"iilgmbh/a", "pactive-de/a"}, canon)
    assert len(res["ambiguous"]) == 1 and res["ambiguous"][0]["repo"] == "a"
    assert res["migrated"] == []
    assert res["severity"]["critical"] == 1


def test_should_weight_production_phantom_as_critical():
    res = rcd.compute_drift(set(), _canon(("achimdehnert/ghost", "production", True, True)))
    assert "achimdehnert/ghost" in res["phantom"]
    assert res["severity"]["critical"] == 1


def test_should_weight_experimental_phantom_as_warn_not_critical():
    res = rcd.compute_drift(set(), _canon(("achimdehnert/old", "experimental", False, True)))
    assert res["severity"]["critical"] == 0 and res["severity"]["warn"] == 1


def test_should_flag_schema_incomplete_when_no_explicit_owner():
    res = rcd.compute_drift({"achimdehnert/x"}, _canon(("achimdehnert/x", None, None, False)))
    assert res["schema_incomplete"] == ["achimdehnert/x"]
    assert res["severity"]["info"] == 1
    assert res["drift_score"] == 0  # Schema-Incomplete ist info, nicht blockierend
