"""Tests fuer pr_merge_sa (SA-M).

Zwei Dinge muessen bewiesen sein, nicht nur behauptet:
1. Die Positivkontrolle in BEIDE Richtungen — ein Werkzeug, das nur ablehnt,
   sieht sicher aus und waere wertlos.
2. Policy und Werkzeug bleiben synchron — die Regel hat genau eine Quelle.
"""

import base64
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pr_merge_sa import (  # noqa: E402
    Facts,
    Unklar,
    _paths_ignore_deckt_alles,
    classify,
    ist_doku,
    ist_governance,
    regeln,
)

REGELN = {
    "deckung": {"W0": "M0", "W1": "M1", "W2": "M2", "W3": "M3"},
    "doku_glob": ["*.md", "docs/**", "README*", "CHANGELOG*"],
    "governance_pfade": [
        ".github/",
        "docs/adr/",
        "policies/",
        "registry/",
        "packages/",
        "CODEOWNERS",
    ],
    "sync_only_repos": ["achimdehnert/platform"],
}


def _facts(**over) -> Facts:
    basis = dict(
        repo="achimdehnert/robo-lab",
        number=4,
        state="OPEN",
        is_draft=False,
        mergeable="MERGEABLE",
        merge_state="CLEAN",
        review_required=False,
        wirkung="W0",
        mandat="M1",
        files=["docs/x.md"],
        checks_total=0,
        checks_failing=0,
        checks_pending=0,
    )
    basis.update(over)
    return Facts(**basis)


# --- Positivkontrolle: es muss auch JA sagen koennen ---------------------------


def test_should_accept_doc_pr_in_repo_without_workflows():
    """W0 ist mandatsfrei — die getreue Uebersetzung von SA-1."""
    u = classify(_facts(mandat="M0"), REGELN)
    assert u.erlaubt is True


def test_should_accept_sync_repo_with_started_auftrag():
    u = classify(
        _facts(
            repo="achimdehnert/platform",
            wirkung="W1",
            files=["tools/x.py"],
            checks_total=3,
        ),
        REGELN,
    )
    assert u.erlaubt is True


def test_should_accept_staging_deploy_after_approval():
    u = classify(
        _facts(wirkung="W2", mandat="M2", files=["app/x.py"], checks_total=2), REGELN
    )
    assert u.erlaubt is True


def test_should_accept_prod_when_approval_names_it():
    u = classify(
        _facts(wirkung="W3", mandat="M3", files=["app/x.py"], checks_total=2), REGELN
    )
    assert u.erlaubt is True


# --- Ablehnungen: jede mit Grund ----------------------------------------------


def test_should_reject_prod_deploy_with_plain_approval():
    u = classify(
        _facts(wirkung="W3", mandat="M2", files=["app/x.py"], checks_total=2), REGELN
    )
    assert u.erlaubt is False and "fehlt: M3" in u.grund


def test_should_reject_doc_pr_in_prod_repo_without_named_approval():
    """Der Fall, an dem SA-6 zu weit war: Doku aendert nichts, der Deploy laeuft
    trotzdem."""
    u = classify(_facts(wirkung="W3", mandat="M1", files=["README.md"]), REGELN)
    assert u.erlaubt is False and "fehlt: M3" in u.grund


def test_should_reject_sync_repo_without_mandat():
    u = classify(
        _facts(
            repo="achimdehnert/platform",
            wirkung="W1",
            mandat="M0",
            files=["tools/x.py"],
            checks_total=3,
        ),
        REGELN,
    )
    assert u.erlaubt is False and "fehlt: M1" in u.grund


def test_should_reject_governance_path_without_approval():
    u = classify(_facts(files=["policies/beispiel.md"]), REGELN)
    assert u.erlaubt is False and "Governance-Pfad" in u.grund


def test_should_accept_governance_path_with_approval():
    u = classify(_facts(files=["policies/beispiel.md"], mandat="M2"), REGELN)
    assert u.erlaubt is True


def test_should_reject_code_pr_without_any_check():
    u = classify(_facts(files=["tools/x.py"]), REGELN)
    assert u.erlaubt is False and "kein einziger Check" in u.grund


def test_should_reject_failing_checks():
    u = classify(_facts(files=["a.py"], checks_total=2, checks_failing=1), REGELN)
    assert u.erlaubt is False


def test_should_reject_draft():
    assert classify(_facts(is_draft=True), REGELN).erlaubt is False


# --- Fail-closed: Unklarheit ist nie ein Ja -----------------------------------


def test_should_raise_unklar_when_file_list_is_empty():
    with pytest.raises(Unklar):
        classify(_facts(files=[]), REGELN)


def test_should_hand_pending_checks_to_auto_merge():
    """Laufende Checks sind kein Ablehnungsgrund mehr — GitHub merged, sobald sie
    gruen sind. Wartet einer rot, merged GitHub nicht."""
    u = classify(_facts(files=["a.py"], checks_total=2, checks_pending=1), REGELN)
    assert u.erlaubt is True and u.auto is True


def test_should_raise_unklar_when_mergeable_stays_unknown():
    with pytest.raises(Unklar):
        classify(_facts(mergeable="UNKNOWN"), REGELN)


def test_should_raise_unklar_on_unknown_wirkung():
    with pytest.raises(Unklar):
        classify(_facts(wirkung="W9"), REGELN)


def test_should_exit_3_when_api_fails(monkeypatch, capsys):
    import pr_merge_sa

    gemergt = []
    monkeypatch.setattr(pr_merge_sa, "regeln", lambda *_a, **_k: REGELN)
    monkeypatch.setattr(
        pr_merge_sa,
        "gather",
        lambda *_a, **_k: (_ for _ in ()).throw(Unklar("gh api: 503")),
    )
    monkeypatch.setattr(
        pr_merge_sa.subprocess, "run", lambda *a, **k: gemergt.append(a) or None
    )
    assert pr_merge_sa.main(["1", "owner/repo"]) == 3
    assert gemergt == []
    assert "UNKLAR" in capsys.readouterr().err


# --- Policy ist die einzige Quelle --------------------------------------------


def test_should_read_rules_from_the_policy_itself():
    """Der Sync-Test: was das Werkzeug anwendet, steht in der ratifizierten
    Policy — keine zweite Quelle, kein Drift."""
    aus_policy = regeln()
    assert aus_policy["deckung"] == REGELN["deckung"]
    assert set(aus_policy["governance_pfade"]) == set(REGELN["governance_pfade"])
    assert aus_policy.get("sync_only_repos") == REGELN["sync_only_repos"]


def test_should_raise_unklar_when_policy_has_no_rule_block(tmp_path):
    leer = tmp_path / "ohne.md"
    leer.write_text("# keine Regel hier\n")
    with pytest.raises(Unklar):
        regeln(leer)


# --- Hilfsfunktionen -----------------------------------------------------------


def test_should_treat_paths_ignore_as_no_effect():
    kopf = "on:\n  push:\n    branches: [main]\n    paths-ignore:\n      - '**.md'\n"
    assert _paths_ignore_deckt_alles(kopf, ["README.md", "docs/a.md"]) is True
    assert _paths_ignore_deckt_alles(kopf, ["README.md", "app/x.py"]) is False


@pytest.mark.parametrize(
    "pfad,erwartet", [("README.md", True), ("x.md", True), ("tools/x.py", False)]
)
def test_should_recognize_doc_paths(pfad, erwartet):
    assert ist_doku(pfad, REGELN["doku_glob"]) is erwartet


@pytest.mark.parametrize(
    "pfad", [".github/workflows/ci.yml", "CODEOWNERS", "policies/x.md"]
)
def test_should_recognize_governance_paths(pfad):
    assert ist_governance(pfad, REGELN["governance_pfade"]) is True


# --- Journal: ohne Zaehlung keine pruefbare Ratsche ---------------------------


def test_should_journal_every_decision(monkeypatch, tmp_path):
    import pr_merge_sa

    ziel = tmp_path / "journal.jsonl"
    monkeypatch.setattr(pr_merge_sa, "JOURNAL", ziel)
    monkeypatch.setattr(pr_merge_sa, "regeln", lambda *_a, **_k: REGELN)
    monkeypatch.setattr(pr_merge_sa, "gather", lambda *_a, **_k: _facts(mandat="M0"))
    assert pr_merge_sa.main(["7", "owner/repo", "--dry-run"]) == 0

    zeilen = [json.loads(z) for z in ziel.read_text().splitlines()]
    assert len(zeilen) == 1
    assert zeilen[0]["pr"] == 7 and zeilen[0]["erlaubt"] is True
    assert zeilen[0]["dry_run"] is True


def test_should_not_block_merge_when_journal_is_unwritable(monkeypatch, tmp_path):
    """Ein blindes Journal darf keinen gedeckten Merge verhindern."""
    import pr_merge_sa

    monkeypatch.setattr(pr_merge_sa, "JOURNAL", tmp_path / "nicht" / "da" / "x.jsonl")
    monkeypatch.setattr(
        pr_merge_sa.pathlib.Path,
        "mkdir",
        lambda *_a, **_k: (_ for _ in ()).throw(OSError("read-only")),
    )
    monkeypatch.setattr(pr_merge_sa, "regeln", lambda *_a, **_k: REGELN)
    monkeypatch.setattr(pr_merge_sa, "gather", lambda *_a, **_k: _facts())
    assert pr_merge_sa.main(["8", "owner/repo", "--dry-run"]) == 0


def test_should_fetch_workflows_once_per_repo(monkeypatch):
    """Der Cache spart die N Datei-Calls beim zweiten PR desselben Repos."""
    import pr_merge_sa

    pr_merge_sa._WORKFLOW_CACHE.clear()
    aufrufe = []

    def _fake(args):
        aufrufe.append(args[1])
        if args[1].endswith("/workflows"):
            return [{"name": "ci.yml", "url": "u1"}]
        return {
            "content": base64.b64encode(
                b"on:\n  push:\n    branches: [main]\njobs: {}\n"
            ).decode()
        }

    monkeypatch.setattr(pr_merge_sa, "_gh", _fake)
    pr_merge_sa.workflow_texte("owner/repo")
    pr_merge_sa.workflow_texte("owner/repo")
    assert len(aufrufe) == 2  # Verzeichnis + eine Datei, nicht viermal
