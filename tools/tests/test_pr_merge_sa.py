"""Tests fuer pr_merge_sa — die Klassifikation ist rein, also ohne Netz pruefbar.

Kriterium 2 aus platform#2338 verlangt die Positivkontrolle in BEIDE Richtungen:
ein Wrapper, der nur ablehnt, sieht sicher aus und waere wertlos.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pr_merge_sa import Facts, Unklar, classify, ist_doku, ist_governance  # noqa: E402


def _facts(**over) -> Facts:
    basis = dict(
        repo="achimdehnert/robo-lab",
        number=3,
        state="OPEN",
        is_draft=False,
        mergeable="MERGEABLE",
        merge_state="CLEAN",
        review_decision="",
        review_required=False,
        auto_deploy=False,
        files=["docs/beschaffung.md", "README.md"],
        checks_total=0,
        checks_failing=0,
        checks_pending=0,
    )
    basis.update(over)
    return Facts(**basis)


# --- Positivkontrolle: es muss auch JA sagen koennen ---------------------------


def test_should_accept_pure_doc_pr_without_ci():
    urteil = classify(_facts())
    assert urteil.erlaubt is True
    assert urteil.klasse == "SA-5"


def test_should_accept_code_pr_with_green_checks():
    urteil = classify(_facts(files=["sim/policy.py"], checks_total=3))
    assert urteil.erlaubt is True
    assert urteil.klasse == "SA-1"


# --- Ablehnungen: jede mit Grund ----------------------------------------------


def test_should_reject_when_repo_deploys_on_main():
    urteil = classify(_facts(auto_deploy=True))
    assert urteil.erlaubt is False
    assert "Gate 2" in urteil.grund


def test_should_reject_governance_path_even_when_markdown():
    urteil = classify(_facts(files=["policies/beispiel-regel.md"]))
    assert urteil.erlaubt is False
    assert "Governance" in urteil.grund


def test_should_reject_code_pr_without_any_check():
    urteil = classify(_facts(files=["tools/x.py"], checks_total=0))
    assert urteil.erlaubt is False
    assert "gruenes CI" in urteil.grund


def test_should_reject_when_review_is_required():
    urteil = classify(_facts(review_required=True))
    assert urteil.erlaubt is False


def test_should_reject_failing_checks():
    urteil = classify(_facts(files=["a.py"], checks_total=2, checks_failing=1))
    assert urteil.erlaubt is False


def test_should_reject_draft():
    assert classify(_facts(is_draft=True)).erlaubt is False


# --- Fail-closed: Unklarheit ist nie ein Ja -----------------------------------


def test_should_raise_unklar_when_file_list_is_empty():
    with pytest.raises(Unklar):
        classify(_facts(files=[]))


def test_should_raise_unklar_when_checks_still_running():
    with pytest.raises(Unklar):
        classify(_facts(files=["a.py"], checks_total=2, checks_pending=1))


def test_should_raise_unklar_when_mergeable_stays_unknown():
    with pytest.raises(Unklar):
        classify(_facts(mergeable="UNKNOWN"))


def test_should_exit_3_when_api_fails(monkeypatch, capsys):
    """Kriterium 3: eine ausfallende API fuehrt zu Exit 3, nie zu einem Merge."""
    import pr_merge_sa

    def _boom(*_a, **_k):
        raise Unklar("gh api: 503 Service Unavailable")

    gemergt = []
    monkeypatch.setattr(pr_merge_sa, "gather", _boom)
    monkeypatch.setattr(
        pr_merge_sa.subprocess, "run", lambda *a, **k: gemergt.append(a) or None
    )
    assert pr_merge_sa.main(["1", "owner/repo"]) == 3
    assert gemergt == []
    assert "UNKLAR" in capsys.readouterr().err


# --- Pfad-Muster ---------------------------------------------------------------


@pytest.mark.parametrize(
    "pfad,erwartet",
    [
        ("docs/x.md", True),
        ("README.md", True),
        ("CHANGELOG", True),
        ("notes.rst", True),
        ("tools/x.py", False),
        ("docs.py", False),
    ],
)
def test_should_recognize_doc_paths(pfad, erwartet):
    assert ist_doku(pfad) is erwartet


@pytest.mark.parametrize(
    "pfad",
    [".github/workflows/ci.yml", "CODEOWNERS", "docs/adr/ADR-1.md", "policies/x.md"],
)
def test_should_recognize_governance_paths(pfad):
    assert ist_governance(pfad) is True
