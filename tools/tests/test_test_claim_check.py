"""Unit tests for tools/test_claim_check.py (session-retro Gate 1).

The gate that demands tests ships with tests — and these run in CI via
.github/workflows/test-claim-check.yml (step 1, blocking). Naming: test_should_*.
"""
import importlib

tcc = importlib.import_module("tools.test_claim_check")


# --- claim detection -------------------------------------------------------
def test_should_detect_unit_getestet_claim():
    assert tcc.find_test_claims("Tool ist unit-getestet.") == ["unit-getestet"]


def test_should_detect_strong_english_claim():
    assert tcc.find_test_claims("Tests added for the new path.") == ["Tests added"]


def test_should_detect_unittests_and_coverage():
    assert tcc.find_test_claims("Added unittests, test coverage up.")


def test_should_ignore_negated_unit_claim():
    # negation window guard: "nicht unit-getestet" must not count
    assert tcc.find_test_claims("Noch nicht unit-getestet, kommt später.") == []


def test_should_ignore_manual_test_disclaimer():
    # "manuell ... kein Unit-Test" -> negation window suppresses the unit match
    assert tcc.find_test_claims("Nur manuell getestet, kein Unit-Test.") == []


def test_should_not_match_bare_verifiziert():
    # "verifiziert" alone is a FP magnet (manual/content verification) -> excluded
    assert tcc.find_test_claims("Portabilität verifiziert via PR #429.") == []


def test_should_not_match_bare_getestet_prose():
    # empirically a FP source (#437: '"Rückgabefähig" = getestet, nicht behauptet')
    # -> bare "getestet"/"tested" is intentionally NOT a claim
    assert tcc.find_test_claims('"Rückgabefähig" = getestet, nicht behauptet.') == []
    assert tcc.find_test_claims("Behaviour is tested in CI.") == []


def test_should_not_match_untested_substring():
    assert tcc.find_test_claims("Dieser Pfad ist ungetestet.") == []
    assert tcc.find_test_claims("This path is untested.") == []


# --- test-file detection ---------------------------------------------------
def test_should_recognize_test_paths():
    paths = [
        "src/app.py",
        "tools/tests/test_ref_sweep.py",
        "frontend/x.spec.ts",
        "pkg/foo_test.go",
        "tests/conftest.py",
        "README.md",
    ]
    found = tcc.changed_test_files(paths)
    assert "src/app.py" not in found
    assert "README.md" not in found
    assert "tools/tests/test_ref_sweep.py" in found
    assert "frontend/x.spec.ts" in found
    assert "pkg/foo_test.go" in found
    assert "tests/conftest.py" in found


def test_should_not_flag_docs_dir_named_protests():
    # word-ish boundary: a path like "protests/" must not match the tests/ rule
    assert tcc.changed_test_files(["docs/protests/notes.md"]) == []


# --- end-to-end verdict ----------------------------------------------------
def test_should_warn_on_claim_without_test_file():
    r = tcc.analyze("Vollständig unit-getestet.", "", ["tools/foo.py"])
    assert r["verdict"] == "warn"
    assert r["should_comment"] is True


def test_should_pass_when_test_file_present():
    r = tcc.analyze("Unit-getestet.", "", ["tools/foo.py", "tools/tests/test_foo.py"])
    assert r["verdict"] == "ok"
    assert r["should_comment"] is False


def test_should_pass_when_no_claim_at_all():
    r = tcc.analyze("Reiner Docs-Fix, Tippfehler.", "", ["docs/x.md"])
    assert r["verdict"] == "ok"


def test_should_detect_claim_in_commit_messages():
    r = tcc.analyze("", "fix(x): behoben, unit-getestet", ["src/x.py"])
    assert r["verdict"] == "warn"
