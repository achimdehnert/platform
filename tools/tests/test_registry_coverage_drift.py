"""R7 Fault-Injection für registry_coverage_drift (KONZ-001 §5 R7, Issue #488).

+/- Test: korrekte Lage → drift 0 (positiv); injizierter Enrollment-/Phantom-Defekt → MUSS
geflaggt werden (negativ). Genau das Muster, das KONZ-001 R7 von jedem erzwingenden Gate verlangt:
ein Gate, das für seine Defektklasse nie rot wird, ist No-Op-verdächtig.

Run: `python3 -m pytest tools/tests/test_registry_coverage_drift.py -q`
"""
import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "registry_coverage_drift.py"
_spec = importlib.util.spec_from_file_location("rcd", _SRC)
rcd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rcd)

ORG = {"achimdehnert/a", "achimdehnert/b", "achimdehnert/c"}


def test_should_classify_owner_migration_separately():
    # canonical sagt achimdehnert/a, Realität ist iilgmbh/a → MIGRATED, NICHT gap/phantom (Befund 2026-06-06)
    ground = {"iilgmbh/a", "achimdehnert/b"}
    canonical = {"achimdehnert/a", "achimdehnert/b"}
    res = rcd.compute_drift(ground, canonical)
    assert res["migrated"] == [{"repo": "a", "canonical": "achimdehnert/a", "reality": "iilgmbh/a"}]
    assert res["enrollment_gap"] == [] and res["phantom"] == []
    assert res["drift_score"] == 1  # Migration zählt als Drift (canonical-Owner stale)


def test_should_report_zero_drift_when_aligned():
    res = rcd.compute_drift(ORG, set(ORG))
    assert res["drift_score"] == 0
    assert res["enrollment_gap"] == [] and res["phantom"] == []


def test_should_flag_injected_unenrolled_repo():
    # Phantom-Org-Repo „c" NICHT in canonical → Enrollment-Gap MUSS anschlagen (R7 negativ)
    canon = {"achimdehnert/a", "achimdehnert/b"}
    res = rcd.compute_drift(ORG, canon)
    assert "achimdehnert/c" in res["enrollment_gap"]
    assert res["drift_score"] == 1


def test_should_flag_phantom_canonical_entry():
    # in SSoT, aber kein Org-Repo → PHANTOM MUSS anschlagen
    canon = ORG | {"achimdehnert/ghost"}
    res = rcd.compute_drift(ORG, canon)
    assert "achimdehnert/ghost" in res["phantom"]
    assert res["drift_score"] == 1


def test_should_count_covered_intersection():
    res = rcd.compute_drift(ORG, {"achimdehnert/a"})
    assert res["covered"] == ["achimdehnert/a"]
    assert res["drift_score"] == 2  # b,c fehlen in canonical
