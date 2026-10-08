"""Tests fuer pr_merge_sa (SA-M).

Zwei Dinge muessen bewiesen sein, nicht nur behauptet:
1. Die Positivkontrolle in BEIDE Richtungen — ein Werkzeug, das nur ablehnt,
   sieht sicher aus und waere wertlos.
2. Policy und Werkzeug bleiben synchron — die Regel hat genau eine Quelle.
"""

import base64
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pr_merge_sa import (  # noqa: E402
    FREIGABE_VERMERK,
    Facts,
    Unklar,
    _paths_ignore_deckt_alles,
    classify,
    ist_doku,
    ist_governance,
    regeln,
    regeln_fuer,
    review_ist_pflicht,
)

REGELN = {
    # W3: M1 seit 2026-08-27 (Pruefrage), Block angeglichen 2026-09-16 (#3244)
    "deckung": {"W0": "M0", "W1": "M1", "W2": "M2", "W3": "M1"},
    "doku_glob": ["*.md", "docs/**", "README*", "CHANGELOG*"],
    "governance_pfade": [
        ".github/",
        "docs/adr/",
        "policies/",
        "registry/",
        "packages/",
        "docs/governance/",
        "docs/konzepte/KONZ-platform-025-lotsen-charta.md",
        "CODEOWNERS",
        "tools/pr_merge_sa.py",
        "tools/sandbox/",
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


DOKU_FREI = {**REGELN, "doku_ohne_mandat": True}


def test_should_accept_doc_only_pr_in_deploy_repo_without_mandate():
    """Owner-Wort 2026-10-05: reine Doku braucht kein Mandat, auch wenn der
    Merge einen Deploy anstoesst."""
    for wirkung in ("W1", "W2", "W3"):
        u = classify(
            _facts(wirkung=wirkung, mandat="M0", files=["docs/x.md", "README.md"]),
            DOKU_FREI,
        )
        assert u.erlaubt is True, wirkung


def test_should_keep_mandate_for_doc_only_pr_when_switch_is_off():
    u = classify(_facts(wirkung="W2", mandat="M0", files=["docs/x.md"]), REGELN)
    assert u.erlaubt is False
    assert "M2" in u.grund


def test_should_keep_mandate_when_one_file_is_not_doc():
    u = classify(
        _facts(
            wirkung="W2", mandat="M0", files=["docs/x.md", "app/x.py"], checks_total=2
        ),
        DOKU_FREI,
    )
    assert u.erlaubt is False


def test_should_keep_approval_for_governance_doc_despite_switch():
    u = classify(
        _facts(wirkung="W1", mandat="M0", files=["docs/adr/ADR-001.md"]), DOKU_FREI
    )
    assert u.erlaubt is False
    assert "Governance-Pfad" in u.grund


def test_should_keep_deploy_word_for_doc_pr_with_publish_workflow():
    u = classify(
        _facts(
            wirkung="W3",
            mandat="M0",
            files=["README.md"],
            pruef_pflicht=["Publish-Workflow"],
        ),
        DOKU_FREI,
    )
    assert u.erlaubt is False
    assert "M3" in u.grund


def test_should_accept_prod_when_approval_names_it():
    u = classify(
        _facts(wirkung="W3", mandat="M3", files=["app/x.py"], checks_total=2), REGELN
    )
    assert u.erlaubt is True


# --- Ablehnungen: jede mit Grund ----------------------------------------------


def test_should_reject_prod_deploy_with_plain_approval_when_pruefrage_greift():
    """Greift die Pruefrage (hier: Datenmigration), reicht ein plain Approval nicht."""
    u = classify(
        _facts(
            wirkung="W3",
            mandat="M2",
            files=["app/x.py"],
            checks_total=2,
            pruef_pflicht=["Datenmigration im Diff"],
        ),
        REGELN,
    )
    assert u.erlaubt is False and "fehlt: M3" in u.grund


def test_should_accept_doc_pr_in_prod_repo_with_auftrag():
    """Bis 2026-08-27 brauchte das M3 (SA-6 war zu weit, Auto-Deploy lief trotzdem).
    Seit der Pruefrage ist Auto-Deploy Normalbetrieb: Auftrag (M1) genuegt, wenn
    keine der vier Klassen greift."""
    u = classify(_facts(wirkung="W3", mandat="M1", files=["README.md"]), REGELN)
    assert u.erlaubt is True


def test_should_name_the_deploy_vermerk_path_when_w3_lacks_m3():
    """#2812 (b): die Meldung nennt beide Wege zu M3, nicht nur den generischen
    Ablehnungssatz."""
    u = classify(
        _facts(
            wirkung="W3",
            mandat="M0",
            files=["app/x.py"],
            checks_total=2,
            pruef_pflicht=["Publish-Workflow auf main (irreversibel)"],
        ),
        REGELN,
    )
    assert u.erlaubt is False
    assert "fehlt: M3" in u.grund
    assert "#2812" in u.grund
    assert "verlinkten Issue" in u.grund


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


# --- docs/governance/ + Charta (Retro c36878 Befund 1, Issue #2654) ---------
# Vor dem Fix waren beide Pfade in KEINER Liste: ein PR mit nur einer dieser
# Dateien lief als CLEAN durch, obwohl dort die Vollmachten des Agenten geregelt
# werden. Die drei Tests unten waren vor dem Fix rot.


def test_should_reject_docs_governance_without_approval():
    u = classify(_facts(files=["docs/governance/model-rebaseline-runbook.md"]), REGELN)
    assert u.erlaubt is False
    assert "Governance-Pfad" in u.grund


def test_should_reject_lotsen_charta_without_approval():
    u = classify(
        _facts(files=["docs/konzepte/KONZ-platform-025-lotsen-charta.md"]), REGELN
    )
    assert u.erlaubt is False
    assert "Governance-Pfad" in u.grund


def test_should_still_accept_plain_retro_report():
    """Gegenprobe: docs/retros/ bleibt bewusst ungeschuetzt — ein Retro-Bericht
    bringt keinen Machtzuwachs, ein Review dort waere reine Reibung."""
    u = classify(
        _facts(files=["docs/retros/session-retro-2026-09-02-platform-x.md"]), REGELN
    )
    assert u.erlaubt is True


def test_should_still_accept_ordinary_konzept():
    """Gegenprobe: nur die Charta-DATEI ist geschuetzt, nicht docs/konzepte/."""
    u = classify(_facts(files=["docs/konzepte/KONZ-platform-038-irgendwas.md"]), REGELN)
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


def test_should_keep_base_rules_outside_profiled_orgs():
    r = {**REGELN, "org_profile": {"iilsandbox": {"actions_aus": True}}}
    gerufen = []
    profil, repo_id = regeln_fuer(
        "achimdehnert/platform", r, aufloesen=lambda x: gerufen.append(x)
    )
    assert profil is r and repo_id is None and gerufen == []


# --- Org-Profil (ADR-308 §4.4): Sandbox-Org mit M0, nur wenn gemessen -------------

SANDBOX = {**REGELN, "org_profile": {"iilsandbox": {"actions_aus": True}}}


def _profil(repo="iilsandbox/dev-hub", aufgeloest=None, an=False):
    return regeln_fuer(
        repo,
        SANDBOX,
        aufloesen=lambda x: (aufgeloest or x, 4711),
        actions=lambda x: an,
    )


def test_should_merge_sandbox_code_pr_without_checks_and_mandat():
    profil, repo_id = _profil()
    assert repo_id == 4711
    u = classify(
        _facts(repo="iilsandbox/dev-hub", mandat="M0", files=["apps/x.py"]), profil
    )
    assert u.erlaubt is True


def test_should_still_reject_code_pr_without_checks_outside_profile():
    u = classify(_facts(mandat="M0", files=["apps/x.py"]), REGELN)
    assert u.erlaubt is False


def test_should_keep_governance_paths_under_approval_in_sandbox():
    profil, _ = _profil()
    u = classify(
        _facts(repo="iilsandbox/platform", mandat="M0", files=["policies/x.md"]),
        profil,
    )
    assert u.erlaubt is False and "Governance" in u.grund


def test_should_refuse_profile_when_repo_was_transferred_out_of_sandbox():
    with pytest.raises(Unklar, match="achimdehnert/dev-hub"):
        _profil(aufgeloest="achimdehnert/dev-hub")


def test_should_refuse_profile_when_actions_run_in_sandbox():
    with pytest.raises(Unklar, match="Actions"):
        _profil(an=True)


# --- Profil-Negativtests ADR-308 §8.2 (Rest steht oben und in selbstpruefung) ----


@pytest.mark.parametrize(
    "repo", ["achimdehnert/platform", "iilgmbh/risk-hub", "iilsandbox-fake/dev-hub"]
)
def test_should_apply_production_rules_to_production_targets(repo):
    profil, repo_id = regeln_fuer(
        repo, SANDBOX, aufloesen=pytest.fail, actions=pytest.fail
    )
    assert profil is SANDBOX and repo_id is None
    u = classify(_facts(repo=repo, mandat="M0", files=["apps/x.py"]), profil)
    assert u.erlaubt is False


@pytest.mark.parametrize(
    "org_profile",
    [
        {"iilsandbox": {"actions_aus": True}, "IILSandbox": {"actions_aus": True}},
        {"iilsandbox": {"actions_aus": True, "deckung": {"W3": "M0"}}},
        {"iilsandbox": {"action_aus": True}},
        {"iilsandbox": {"actions_aus": False}},
        {"iilsandbox": {}},
        {"iilsandbox": True},
        ["iilsandbox"],
    ],
)
def test_should_refuse_contradictory_or_unknown_profile(org_profile):
    r = {**REGELN, "org_profile": org_profile}
    for repo in ("iilsandbox/dev-hub", "achimdehnert/platform"):
        with pytest.raises(Unklar, match="org_profile"):
            regeln_fuer(repo, r, aufloesen=pytest.fail, actions=pytest.fail)


def test_should_accept_the_ratified_profile_from_the_policy():
    profil, repo_id = regeln_fuer(
        "iilsandbox/dev-hub",
        regeln(),
        aufloesen=lambda x: (x, 1),
        actions=lambda x: False,
    )
    assert profil["actions_aus"] is True and repo_id == 1


def test_should_not_merge_when_repo_target_changed_after_check(monkeypatch, capsys):
    import pr_merge_sa

    gemergt = []
    ids = iter([4711, 9999])
    monkeypatch.setattr(pr_merge_sa, "regeln", lambda *_a, **_k: SANDBOX)
    monkeypatch.setattr(pr_merge_sa, "aufgeloestes_repo", lambda x: (x, next(ids)))
    monkeypatch.setattr(pr_merge_sa, "actions_an", lambda x: False)
    monkeypatch.setattr(
        pr_merge_sa,
        "gather",
        lambda *_a, **_k: _facts(repo="iilsandbox/dev-hub", mandat="M0"),
    )
    monkeypatch.setattr(pr_merge_sa, "journal", lambda *_a, **_k: None)
    monkeypatch.setattr(
        pr_merge_sa.subprocess, "run", lambda *a, **k: gemergt.append(a) or None
    )
    assert pr_merge_sa.main(["1", "iilsandbox/dev-hub"]) == 3
    assert gemergt == []
    assert "Ziel gewechselt" in capsys.readouterr().err


class _Lauf:
    returncode = 0
    stderr = ""


def _merge_main(monkeypatch, repo, fakten, regeln_block=REGELN):
    import pr_merge_sa

    befehle = []
    monkeypatch.setattr(pr_merge_sa, "regeln", lambda *_a, **_k: regeln_block)
    monkeypatch.setattr(pr_merge_sa, "aufgeloestes_repo", lambda x: (x, 4711))
    monkeypatch.setattr(pr_merge_sa, "gather", lambda *_a, **_k: fakten)
    monkeypatch.setattr(pr_merge_sa, "journal", lambda *_a, **_k: None)
    monkeypatch.setattr(
        pr_merge_sa.subprocess, "run", lambda b, **k: befehle.append(b) or _Lauf()
    )
    return pr_merge_sa.main(["1", repo]), befehle


def test_should_pin_merge_to_checked_head_commit(monkeypatch):
    code, befehle = _merge_main(
        monkeypatch, "owner/repo", _facts(mandat="M0", head_sha="abc123")
    )
    assert code == 0
    befehl = befehle[0]
    assert befehl[befehl.index("--match-head-commit") + 1] == "abc123"


def test_should_not_merge_when_head_commit_is_unknown(monkeypatch, capsys):
    code, befehle = _merge_main(monkeypatch, "owner/repo", _facts(mandat="M0"))
    assert code == 3
    assert befehle == []
    assert "Kopf-Commit" in capsys.readouterr().err


def test_should_not_merge_when_actions_turned_on_after_check(monkeypatch, capsys):
    import pr_merge_sa

    messungen = iter([False, True])
    monkeypatch.setattr(pr_merge_sa, "actions_an", lambda x: next(messungen))
    code, befehle = _merge_main(
        monkeypatch,
        "iilsandbox/dev-hub",
        _facts(repo="iilsandbox/dev-hub", mandat="M0", head_sha="abc123"),
        SANDBOX,
    )
    assert code == 3
    assert befehle == []
    assert "Actions an" in capsys.readouterr().err


def test_should_merge_sandbox_pr_when_actions_stay_off(monkeypatch):
    import pr_merge_sa

    monkeypatch.setattr(pr_merge_sa, "actions_an", lambda x: False)
    code, befehle = _merge_main(
        monkeypatch,
        "iilsandbox/dev-hub",
        _facts(repo="iilsandbox/dev-hub", mandat="M0", head_sha="abc123"),
        SANDBOX,
    )
    assert code == 0
    assert "--match-head-commit" in befehle[0]


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
    "pfad",
    [
        ".github/workflows/ci.yml",
        "CODEOWNERS",
        "policies/x.md",
        "tools/sandbox/waechter.py",
        "tools/sandbox/selbstpruefung.py",
    ],
)
def test_should_recognize_governance_paths(pfad):
    assert ist_governance(pfad, REGELN["governance_pfade"]) is True


@pytest.mark.parametrize(
    "pfad", ["tools/sandbox_hilfe.py", "tools/tests/test_sandbox_waechter.py"]
)
def test_should_not_treat_sandbox_lookalikes_as_governance(pfad):
    assert ist_governance(pfad, REGELN["governance_pfade"]) is False


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
    assert datetime.fromisoformat(zeilen[0]["ts"]).tzinfo is not None


class _Abgelehnt:
    returncode = 1
    stderr = "GraphQL: Head branch was modified. Review and try the merge again."


def _journal_nach_merge(monkeypatch, fakten, lauf, zeilen):
    """main() mit echtem Merge-Pfad; Journalzeilen landen in `zeilen`."""
    import pr_merge_sa

    monkeypatch.setattr(pr_merge_sa, "regeln", lambda *_a, **_k: REGELN)
    monkeypatch.setattr(pr_merge_sa, "aufgeloestes_repo", lambda x: (x, 4711))
    monkeypatch.setattr(pr_merge_sa, "gather", lambda *_a, **_k: fakten)
    monkeypatch.setattr(pr_merge_sa, "journal", zeilen.append)
    monkeypatch.setattr(pr_merge_sa.subprocess, "run", lauf)
    return pr_merge_sa.main(["1", "owner/repo"])


def test_should_journal_rejected_merge_as_not_merged(monkeypatch):
    """Realfall S9-Gegenprobe (#3724): GitHub lehnte ab, das Journal sagte nur
    „erlaubt“ — und der Sandbox-Benchmark zaehlte es als Merge."""
    zeilen = []
    code = _journal_nach_merge(
        monkeypatch,
        _facts(mandat="M0", head_sha="abc123"),
        lambda b, **k: _Abgelehnt(),
        zeilen,
    )
    assert code == 3
    assert len(zeilen) == 1
    assert zeilen[0]["erlaubt"] is True
    assert (zeilen[0]["ergebnis"], zeilen[0]["exit"]) == ("abgelehnt", 3)


def test_should_journal_merged_result_after_successful_merge(monkeypatch):
    import pr_merge_sa

    zeilen = []
    code = _journal_nach_merge(
        monkeypatch,
        _facts(mandat="M0", head_sha="abc123"),
        lambda b, **k: _Lauf(),
        zeilen,
    )
    assert code == 0
    assert len(zeilen) == 1
    assert zeilen[0]["ergebnis"] == pr_merge_sa.ERGEBNIS_GEMERGT


def test_should_journal_auto_merge_when_checks_still_run(monkeypatch):
    import pr_merge_sa

    zeilen = []
    code = _journal_nach_merge(
        monkeypatch,
        _facts(mandat="M0", head_sha="abc123", checks_total=1, checks_pending=1),
        lambda b, **k: _Lauf(),
        zeilen,
    )
    assert code == 0
    assert zeilen[0]["ergebnis"] == pr_merge_sa.ERGEBNIS_AUTO_MERGE


def test_should_journal_unklar_when_check_before_merge_fails(monkeypatch):
    zeilen, gerufen = [], []
    code = _journal_nach_merge(
        monkeypatch, _facts(mandat="M0"), lambda b, **k: gerufen.append(b), zeilen
    )
    assert code == 3
    assert gerufen == []
    assert (zeilen[0]["ergebnis"], zeilen[0]["exit"]) == ("unklar", 3)


def test_should_journal_once_even_when_merge_call_crashes(monkeypatch):
    def _absturz(b, **k):
        raise FileNotFoundError("gh")

    zeilen = []
    with pytest.raises(FileNotFoundError):
        _journal_nach_merge(
            monkeypatch, _facts(mandat="M0", head_sha="abc123"), _absturz, zeilen
        )
    assert len(zeilen) == 1
    assert zeilen[0]["ergebnis"] == "abgebrochen"


def _journal_in_datei(monkeypatch, tmp_path, fakten):
    """main() ohne Merge-Pfad gegen ein Journal in tmp_path; gibt dessen Zeilen zurueck."""
    import pr_merge_sa

    ziel = tmp_path / "journal.jsonl"
    monkeypatch.setattr(pr_merge_sa, "JOURNAL", ziel)
    monkeypatch.setattr(pr_merge_sa, "regeln", lambda *_a, **_k: REGELN)
    monkeypatch.setattr(pr_merge_sa, "gather", lambda *_a, **_k: fakten)

    def lauf(*argumente):
        code = pr_merge_sa.main(["7", "owner/repo", *argumente])
        return code, [json.loads(z) for z in ziel.read_text().splitlines()]

    return lauf


def test_should_journal_already_merged_pr_apart_from_missing_mandate(
    monkeypatch, tmp_path
):
    """Rueckschau platform#3685: 49 von 353 „Abbruechen“ trafen einen PR, der
    schon gemergt war — das Ziel war erreicht, kein Mandat fehlte."""
    import pr_merge_sa

    lauf = _journal_in_datei(monkeypatch, tmp_path, _facts(state="MERGED"))
    code, zeilen = lauf()
    assert code == 2
    assert zeilen[0]["erlaubt"] is False
    assert zeilen[0]["ergebnis"] == pr_merge_sa.ERGEBNIS_BEREITS_GEMERGT


def test_should_mark_repeat_when_previous_attempt_had_same_reason(
    monkeypatch, tmp_path, capsys
):
    """Rueckschau platform#3685: 72 Abbrueche trugen woertlich den Grund des
    vorigen Versuchs auf denselben PR."""
    import pr_merge_sa

    lauf = _journal_in_datei(monkeypatch, tmp_path, _facts(wirkung="W1", mandat="M0"))
    code, zeilen = lauf()
    assert code == 2 and "wiederholung" not in zeilen[0]
    assert pr_merge_sa.HINWEIS_WIEDERHOLUNG not in capsys.readouterr().err

    code, zeilen = lauf()
    assert code == 2 and zeilen[1]["wiederholung"] is True
    assert zeilen[1]["ergebnis"] == "nicht_gedeckt"
    assert pr_merge_sa.HINWEIS_WIEDERHOLUNG in capsys.readouterr().err


def test_should_not_mark_repeat_for_dry_run_or_changed_reason(monkeypatch, tmp_path):
    import pr_merge_sa

    lauf = _journal_in_datei(monkeypatch, tmp_path, _facts(wirkung="W1", mandat="M0"))
    lauf()
    _, zeilen = lauf("--dry-run")
    assert "wiederholung" not in zeilen[1]

    # Ein Trockenlauf dazwischen unterbricht die Kette nicht: der juengste
    # echte Versuch bleibt der Massstab.
    _, zeilen = lauf()
    assert zeilen[2]["wiederholung"] is True

    monkeypatch.setattr(
        pr_merge_sa, "gather", lambda *_a, **_k: _facts(wirkung="W3", mandat="M0")
    )
    _, zeilen = lauf()
    assert "wiederholung" not in zeilen[3]


def test_should_not_mark_repeat_when_journal_is_unreadable(monkeypatch, tmp_path):
    import pr_merge_sa

    monkeypatch.setattr(pr_merge_sa, "JOURNAL", tmp_path / "fehlt.jsonl")
    assert pr_merge_sa.ist_wiederholung("owner/repo", 7, "egal") is False


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


# --- Approval erkennen, auch ohne erzwungenes Review ---------------------------


def test_should_read_approval_from_latest_reviews():
    """platform#2348: reviewDecision leer, latestReviews approved, State CLEAN."""
    import pr_merge_sa

    pr = {"reviewDecision": None, "latestReviews": [{"state": "APPROVED", "body": ""}]}
    assert pr_merge_sa.mandat_des_prs("owner/repo", 1, pr) == "M2"


def test_should_read_m3_when_approval_names_prod():
    import pr_merge_sa

    pr = {
        "reviewDecision": None,
        "latestReviews": [{"state": "APPROVED", "body": "ok, deploy nach prod"}],
    }
    assert pr_merge_sa.mandat_des_prs("owner/repo", 1, pr) == "M3"


def test_should_not_read_mandat_from_a_changes_requested_review(monkeypatch):
    import pr_merge_sa

    monkeypatch.setattr(
        pr_merge_sa, "_gh", lambda *_a, **_k: {"body": "", "state": "OPEN"}
    )
    pr = {
        "reviewDecision": None,
        "latestReviews": [{"state": "CHANGES_REQUESTED"}],
        "body": "",
    }
    assert pr_merge_sa.mandat_des_prs("owner/repo", 1, pr) == "M0"


# --- #2440: Regel-Existenz ist nicht Review-Pflicht ---------------------------


def test_should_not_require_review_when_github_leaves_decision_empty():
    """Der Fall #2438: Regel liegt, aber GitHub verlangt fuer diese Dateien
    kein Approval — reviewDecision leer bei CLEAN. Wer nur die Regel liest,
    macht jeden solchen PR unmergebar."""
    pr = {"reviewDecision": "", "mergeStateStatus": "CLEAN"}
    assert review_ist_pflicht(pr, hat_regel=True) is False


def test_should_require_review_when_github_says_review_required():
    pr = {"reviewDecision": "REVIEW_REQUIRED", "mergeStateStatus": "BLOCKED"}
    assert review_ist_pflicht(pr, hat_regel=True) is True


def test_should_require_review_when_blocked_without_red_or_pending_checks():
    """Leerer reviewDecision + BLOCKED + alles gruen: es blockt etwas anderes
    als das CI — konservativ als Review-Pflicht lesen."""
    pr = {"reviewDecision": "", "mergeStateStatus": "BLOCKED"}
    assert review_ist_pflicht(pr, hat_regel=True, checks_failing=0) is True


def test_should_not_call_pending_checks_a_missing_review():
    """BLOCKED, weil Checks noch laufen — das ist kein fehlendes Approval."""
    pr = {"reviewDecision": "", "mergeStateStatus": "BLOCKED"}
    assert review_ist_pflicht(pr, hat_regel=True, checks_pending=2) is False


def test_should_never_require_review_without_a_rule():
    pr = {"reviewDecision": "REVIEW_REQUIRED", "mergeStateStatus": "BLOCKED"}
    assert review_ist_pflicht(pr, hat_regel=False) is False


def _rules_fehler(meldung: str):
    import pr_merge_sa

    def _fake(args):
        raise pr_merge_sa.Unklar(f"gh {' '.join(args[:3])} …: {meldung}")

    return _fake


def test_should_read_no_rule_when_plan_has_no_rulesets(monkeypatch):
    """Live-Test S9 (#3724), Wortlaut gemessen an iilsandbox/chat-hub#1: der
    Free-Plan kennt keine Rulesets fuer private Repos, also gibt es keine Regel."""
    import pr_merge_sa

    monkeypatch.setattr(
        pr_merge_sa,
        "_gh",
        _rules_fehler(
            "gh: Upgrade to GitHub Pro or make this repository public to enable"
            " this feature. (HTTP 403)"
        ),
    )
    assert pr_merge_sa.pull_request_regel("iilsandbox/chat-hub", "main") is False


@pytest.mark.parametrize(
    "meldung",
    [
        "gh: API rate limit exceeded for user. (HTTP 403)",
        "gh: Resource not accessible by personal access token (HTTP 403)",
    ],
)
def test_should_stay_unklar_on_other_403_from_rules(monkeypatch, meldung):
    import pr_merge_sa

    monkeypatch.setattr(pr_merge_sa, "_gh", _rules_fehler(meldung))
    with pytest.raises(pr_merge_sa.Unklar):
        pr_merge_sa.pull_request_regel("iilsandbox/chat-hub", "main")


def test_should_merge_clean_doc_pr_that_github_does_not_block():
    """Die Wirkung des Fixes am Urteil, nicht nur an der Hilfsfunktion:
    #2438-Form (nur AGENT_HANDOVER.md, CLEAN, kein Approval) ist erlaubt."""
    u = classify(
        _facts(
            repo="achimdehnert/platform",
            mandat="M0",
            wirkung="W0",
            files=["AGENT_HANDOVER.md"],
            review_required=False,
            checks_total=9,
        ),
        REGELN,
    )
    assert u.erlaubt is True


# --- M1-Vermerk: Schreibweise darf die Sache nicht verdecken (#2603) ---------


@pytest.mark.parametrize(
    "body",
    [
        "Freigabe: akzeptiert durch Owner 2026-09-01, Kapitäns-Kanal",
        "**Freigabe:** akzeptiert durch Owner 2026-09-01, Kapitäns-Kanal",
        "**Freigabe**: akzeptiert durch Owner 2026-09-01",
        "freigabe:   Akzeptiert Durch Owner heute",
    ],
)
def test_should_read_freigabe_vermerk_in_plain_and_bold(body):
    assert FREIGABE_VERMERK.search(body)


@pytest.mark.parametrize(
    "body",
    [
        "Freigabe: noch offen — akzeptiert durch Owner steht aus",
        "akzeptiert durch Owner",
        "Freigabe angefragt",
    ],
)
def test_should_not_read_freigabe_vermerk_from_lookalikes(body):
    assert not FREIGABE_VERMERK.search(body)


# --- #2784: gather() wertet nur den juengsten Lauf je Check-Name -------------
#
# Realfall #2781 (2026-09-03): ein Zwilling aus altem rotem und neuem gruenem
# Lauf desselben Checks im statusCheckRollup meldete faelschlich "1 rot",
# obwohl `gh pr checks` und `mergeStateStatus=CLEAN` nichts Rotes zeigten. Die
# Auswahl ist dieselbe wie beim Review-Bot (#2679, bot_review_kandidaten.
# juengste_je_name) — keine zweite Kopie.

_GATHER_REPO = "achimdehnert/_test-only-repo"
_GATHER_REGELN = {**REGELN, "sync_only_repos": [_GATHER_REPO]}


def _gather_pr(rollup: list) -> dict:
    return {
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "reviewDecision": "APPROVED",
        "latestReviews": [{"state": "APPROVED", "body": ""}],
        "files": [{"path": "tools/x.py"}],
        "baseRefName": "main",
        "statusCheckRollup": rollup,
        "state": "OPEN",
        "isDraft": False,
        "body": "",
    }


def _gather_fake_gh(pr_dict: dict):
    def _fake(args):
        if args[:2] == ["pr", "view"]:
            return pr_dict
        if args[0] == "api" and "rules/branches" in args[1]:
            return []
        raise AssertionError(f"unerwarteter gh-Aufruf im Test: {args}")

    return _fake


def test_should_count_old_red_twin_as_green_when_newer_run_is_green(monkeypatch):
    import pr_merge_sa

    rollup = [
        {
            "name": "guardian",
            "conclusion": "FAILURE",
            "startedAt": "2026-09-03T11:09:00Z",
        },
        {
            "name": "guardian",
            "conclusion": "SUCCESS",
            "startedAt": "2026-09-03T11:33:00Z",
        },
    ]
    monkeypatch.setattr(pr_merge_sa, "_gh", _gather_fake_gh(_gather_pr(rollup)))
    f = pr_merge_sa.gather(_GATHER_REPO, 2781, _GATHER_REGELN)
    assert f.checks_failing == 0
    assert f.checks_total == 1


def test_should_still_count_new_red_twin_when_newer_run_is_red(monkeypatch):
    """Gegenprobe: bleibt der JUENGSTE Lauf rot, darf die Dedup-Logik das nicht
    verschlucken — sonst waere der Fix schlimmer als der Fehler."""
    import pr_merge_sa

    rollup = [
        {
            "name": "guardian",
            "conclusion": "SUCCESS",
            "startedAt": "2026-09-03T11:09:00Z",
        },
        {
            "name": "guardian",
            "conclusion": "FAILURE",
            "startedAt": "2026-09-03T11:33:00Z",
        },
    ]
    monkeypatch.setattr(pr_merge_sa, "_gh", _gather_fake_gh(_gather_pr(rollup)))
    f = pr_merge_sa.gather(_GATHER_REPO, 2782, _GATHER_REGELN)
    assert f.checks_failing == 1
    assert f.checks_total == 1


def test_should_not_crash_on_status_contexts_without_started_at(monkeypatch):
    """Alte Status-Contexts (statt CheckRuns) tragen weder `startedAt` noch
    `name` — nur `context`/`state`. Die Auswahl darf daran nicht abstuerzen."""
    import pr_merge_sa

    rollup = [
        {"context": "ci/legacy", "state": "SUCCESS"},
        {"context": "ci/legacy", "state": "FAILURE"},
    ]
    monkeypatch.setattr(pr_merge_sa, "_gh", _gather_fake_gh(_gather_pr(rollup)))
    f = pr_merge_sa.gather(_GATHER_REPO, 2783, _GATHER_REGELN)
    assert f.checks_total == 1


# --- #2812 (b): Deploy-Vermerk je PR-Nummer deckt W3 als M3-Aequivalent ------
#
# GitHub laesst kein Approve-Review auf einen eigenen PR zu — der M3-Weg per
# Review ist auf Owner-eigenen PRs strukturell unerreichbar. Owner-Entscheid
# 2026-09-04: ein Vermerk im verlinkten Issue deckt W3 als M3-Aequivalent, wenn
# DIESELBE Zeile den Freigabe-Vermerk, ein Deploy-Wort UND diese PR-Nummer
# traegt. Fehlt eine Bedingung, bleibt es beim bestehenden M1.


def _issue_view_fake(body: str):
    def _fake(args):
        assert args[:2] == ["issue", "view"]
        return {"body": body, "state": "OPEN"}

    return _fake


def test_should_read_m3_when_vermerk_names_deploy_and_this_pr_number(monkeypatch):
    import pr_merge_sa

    body = "Freigabe: akzeptiert durch Owner — deploy #2804"
    monkeypatch.setattr(pr_merge_sa, "_gh", _issue_view_fake(body))
    pr = {"reviewDecision": None, "latestReviews": [], "body": "Refs #2812"}
    assert pr_merge_sa.mandat_des_prs("owner/repo", 2804, pr) == "M3"


def test_should_read_m1_when_vermerk_names_deploy_for_a_different_pr(monkeypatch):
    import pr_merge_sa

    body = "Freigabe: akzeptiert durch Owner — deploy #99"
    monkeypatch.setattr(pr_merge_sa, "_gh", _issue_view_fake(body))
    pr = {"reviewDecision": None, "latestReviews": [], "body": "Refs #2812"}
    assert pr_merge_sa.mandat_des_prs("owner/repo", 2804, pr) == "M1"


def test_should_read_m1_when_vermerk_has_number_but_no_deploy_word(monkeypatch):
    import pr_merge_sa

    body = "Freigabe: akzeptiert durch Owner, betrifft PR #2804"
    monkeypatch.setattr(pr_merge_sa, "_gh", _issue_view_fake(body))
    pr = {"reviewDecision": None, "latestReviews": [], "body": "Refs #2812"}
    assert pr_merge_sa.mandat_des_prs("owner/repo", 2804, pr) == "M1"


def test_should_not_let_a_number_prefix_match_a_longer_pr_number(monkeypatch):
    """#280 darf PR 2804 nicht decken — Wortgrenze auf beiden Seiten."""
    import pr_merge_sa

    body = "Freigabe: akzeptiert durch Owner — deploy #280"
    monkeypatch.setattr(pr_merge_sa, "_gh", _issue_view_fake(body))
    pr = {"reviewDecision": None, "latestReviews": [], "body": "Refs #2812"}
    assert pr_merge_sa.mandat_des_prs("owner/repo", 2804, pr) == "M1"


def test_should_not_read_m3_from_prod_marker_words_in_the_vermerk(monkeypatch):
    """Review-Befund zu #2814: PROD_IM_APPROVAL matcht auch "prod"/"release"/
    "publish" — ein M1-Vermerk, der die PR-Nummer nur im Kontext von
    "Prod-Rueckstand" nennt, darf NICHT versehentlich M3 werden. Der
    Vermerk-Pfad prueft ausschliesslich das Wort "deploy"."""
    import pr_merge_sa

    body = "Freigabe: akzeptiert durch Owner, PR #2804 (Prod-Rueckstand)"
    monkeypatch.setattr(pr_merge_sa, "_gh", _issue_view_fake(body))
    pr = {"reviewDecision": None, "latestReviews": [], "body": "Refs #2812"}
    assert pr_merge_sa.mandat_des_prs("owner/repo", 2804, pr) == "M1"


def test_should_prefer_review_m3_over_vermerk_and_never_read_the_issue(monkeypatch):
    """Pruefreihenfolge: Reviews zuerst, dann Vermerke — liegt schon ein
    Review-M3 vor, wird das verlinkte Issue gar nicht erst gelesen."""
    import pr_merge_sa

    aufrufe = []

    def _fake(args):
        aufrufe.append(args)
        raise AssertionError(
            "Issue darf bei vorliegendem Review-M3 nicht gelesen werden"
        )

    monkeypatch.setattr(pr_merge_sa, "_gh", _fake)
    pr = {
        "reviewDecision": None,
        "latestReviews": [{"state": "APPROVED", "body": "ok, deploy nach prod"}],
        "body": "Refs #2812",
    }
    assert pr_merge_sa.mandat_des_prs("owner/repo", 2804, pr) == "M3"
    assert aufrufe == []


# ── Pruefrage (#3244): W3 braucht M1, M3 nur bei mechanisch erkannter Klasse ──


def test_should_cover_w3_with_m1_when_pruefrage_finds_nothing():
    """Auto-Deploy ist Normalbetrieb (Policy 2026-08-27): CI-gruen + Auftrag reicht."""
    f = _facts(wirkung="W3", mandat="M1", files=["apps/core/x.py"], checks_total=3)
    v = classify(f, REGELN)
    assert v.erlaubt, v.grund


def test_should_still_need_m3_for_w3_when_migration_in_diff():
    f = _facts(
        wirkung="W3",
        mandat="M1",
        files=["apps/core/x.py"],
        checks_total=3,
        pruef_pflicht=["Datenmigration im Diff"],
    )
    v = classify(f, REGELN)
    assert not v.erlaubt
    assert "M3" in v.grund and "Datenmigration" in v.grund


def test_should_find_migration_and_publish_as_pruef_pflicht(monkeypatch):
    import pr_merge_sa

    publish = (
        "on:\n  push:\n    branches: [main]\njobs:\n  p:\n    run: twine upload pypi\n"
    )
    monkeypatch.setattr(pr_merge_sa, "workflow_texte", lambda repo: [publish])
    gruende = pr_merge_sa.pruef_pflicht_gruende(
        "owner/app", ["apps/x/migrations/0002_y.py"], REGELN
    )
    assert gruende == [
        "Datenmigration im Diff",
        "Publish-Workflow auf main (irreversibel)",
    ]
    assert pr_merge_sa.pruef_pflicht_gruende("owner/app", ["docs/x.md"], REGELN) == [
        "Publish-Workflow auf main (irreversibel)"
    ]
    monkeypatch.setattr(pr_merge_sa, "workflow_texte", lambda repo: [])
    assert pr_merge_sa.pruef_pflicht_gruende("owner/app", ["docs/x.md"], REGELN) == []


_PUSH_MAIN = "on:\n  push:\n    branches: [main]\n  pull_request:\njobs:\n  t:\n"


def _urteil(monkeypatch, *texte):
    """Wirkung und Pruef-Pflicht eines Code-PR bei den gegebenen Workflow-Texten."""
    import pr_merge_sa

    monkeypatch.setattr(pr_merge_sa, "workflow_texte", lambda repo: list(texte))
    return (
        pr_merge_sa.wirkung_des_merges("owner/app", ["app/x.py"], REGELN),
        pr_merge_sa.pruef_pflicht_gruende("owner/app", ["app/x.py"], REGELN),
    )


def test_should_not_treat_a_deploy_directory_in_a_test_run_as_deploy(monkeypatch):
    """Realfall robo-lab: der Testlauf checkt Dateien unter `/deploy/…` aus."""
    text = _PUSH_MAIN + (
        "    run: git sparse-checkout set --no-cone /deploy/pre_train/g1/motion.pt\n"
        "    run: shellcheck deploy/*.sh && ruff check deploy/ tests/\n"
    )
    assert _urteil(monkeypatch, text) == ("W0", [])


def test_should_ignore_marker_words_in_comments(monkeypatch):
    text = (
        "# Der Deploy laeuft NICHT automatisch, Prod bleibt unberuehrt.\n"
        + _PUSH_MAIN
        + "    run: pytest  # vgl. publish-pypi.yml, ghcr.io\n"
    )
    assert _urteil(monkeypatch, text) == ("W0", [])


def test_should_not_count_main_in_a_comment_as_trigger(monkeypatch):
    """Realfall illustration-hub: `KEIN Trigger auf main` stand nur im Kommentar."""
    text = (
        "# KEIN Trigger auf `main`.\non:\n  push:\n    tags: ['v*']\n"
        "jobs:\n  deploy:\n    name: Deploy production\n"
    )
    assert _urteil(monkeypatch, text) == ("W0", [])


def test_should_not_treat_the_shared_package_test_run_as_publish(monkeypatch):
    text = _PUSH_MAIN + (
        "    uses: iilgmbh/shared-ci/.github/workflows/_ci-pypi.yml@v1.1.11\n"
    )
    assert _urteil(monkeypatch, text) == ("W0", [])


def test_should_keep_deploy_and_publish_for_workflows_that_act(monkeypatch):
    publish = ["Publish-Workflow auf main (irreversibel)"]
    deploy = _PUSH_MAIN + "    name: Deploy\n    run: ./deploy.sh\n"
    assert _urteil(monkeypatch, deploy) == ("W2", [])
    prod = _PUSH_MAIN + "    run: docker build --target production .\n"
    assert _urteil(monkeypatch, prod) == ("W3", [])
    twine = _PUSH_MAIN + "    run: twine upload --repository pypi dist/*\n"
    assert _urteil(monkeypatch, twine) == ("W3", publish)
    eigener = _PUSH_MAIN + "    uses: ./.github/workflows/publish-pypi.yml\n"
    assert _urteil(monkeypatch, eigener) == ("W3", publish)


def test_should_treat_the_shared_image_build_as_publish(monkeypatch):
    """Realfall: der Aufruf nennt kein Marker-Wort, schiebt aber ein Image."""
    text = _PUSH_MAIN + (
        "    uses: iilgmbh/shared-ci/.github/workflows/_build-docker.yml@v1.1.18\n"
        "    with:\n      image_name: app-web   # -> ghcr.io/owner/app-web\n"
    )
    assert _urteil(monkeypatch, text) == (
        "W3",
        ["Publish-Workflow auf main (irreversibel)"],
    )


def test_should_read_the_auftrag_from_a_cross_repo_issue_reference(monkeypatch):
    """Realfall dev-hub#357: der Auftrag liegt in platform#3234, der PR in dev-hub."""
    import pr_merge_sa

    gelesen = []

    def _fake(args):
        gelesen.append(args[args.index("-R") + 1])
        return {"body": "Freigabe: akzeptiert durch Owner 2026-09-16", "state": "OPEN"}

    monkeypatch.setattr(pr_merge_sa, "_gh", _fake)
    pr = {
        "reviewDecision": None,
        "latestReviews": [],
        "body": "Zahlt ein auf achimdehnert/platform#3234",
    }
    assert pr_merge_sa.mandat_des_prs("achimdehnert/dev-hub", 357, pr) == "M1"
    assert gelesen == ["achimdehnert/platform"]


# --- Review-Bot statt Owner-Schritt (Realfall #3802) ----------------------------
# "fehlt: ein Approval" wurde als "wartet auf Review" an den Owner gemeldet,
# obwohl der Review-Bot den PR Minuten spaeter approvte. Das Urteil nennt jetzt
# den Weg; --warte-auf-bot geht ihn.

PLATFORM = "achimdehnert/platform"
# CODEOWNERS gelesen, keine Datei mit Code-Owner ohne den Bot
BOT = dict(repo=PLATFORM, ohne_bot_owner=[])


def test_should_name_bot_review_when_bot_can_approve_governance_path():
    u = classify(_facts(**BOT, files=[".github/workflows/x.yml"], mandat="M0"), REGELN)
    assert u.erlaubt is False
    assert u.grund.startswith("fehlt: ein Approval (Governance-Pfad")
    assert "--warte-auf-bot" in u.grund


def test_should_not_name_bot_review_for_bot_tabu_path():
    u = classify(_facts(**BOT, files=["policies/x.md"], mandat="M0"), REGELN)
    assert u.erlaubt is False and "--warte-auf-bot" not in u.grund


def test_should_not_name_bot_review_in_repo_without_bot():
    u = classify(_facts(files=[".github/workflows/x.yml"], mandat="M0"), REGELN)
    assert u.erlaubt is False and "--warte-auf-bot" not in u.grund


def _uhr_und_schlaf():
    t = [0.0]
    return (lambda: t[0]), (lambda s: t.__setitem__(0, t[0] + s))


def test_should_wait_for_bot_approval_and_then_allow():
    import pr_merge_sa

    # Checks gruen: sonst sperrt nach dem Approve "kein einziger Check"
    gemeinsam = dict(**BOT, files=[".github/workflows/x.yml"], checks_total=3)
    ohne = _facts(mandat="M0", **gemeinsam)
    mit = _facts(mandat="M2", **gemeinsam)
    folge = iter([ohne, ohne, mit])
    starts = []
    uhr, schlaf = _uhr_und_schlaf()

    def pruefen():
        f = next(folge)
        return f, classify(f, REGELN)

    f, u = pr_merge_sa.warte_auf_bot_review(
        pruefen, lambda: starts.append(1), schlafen=schlaf, uhr=uhr
    )
    assert u.erlaubt is True and f.mandat == "M2"
    assert starts == [1]


def test_should_stop_waiting_at_deadline_and_keep_rejection():
    import pr_merge_sa

    ohne = _facts(**BOT, files=[".github/workflows/x.yml"], mandat="M0")
    starts = []
    uhr, schlaf = _uhr_und_schlaf()
    f, u = pr_merge_sa.warte_auf_bot_review(
        lambda: (ohne, classify(ohne, REGELN)),
        lambda: starts.append(1),
        minuten=12,
        schlafen=schlaf,
        uhr=uhr,
    )
    assert u.erlaubt is False
    # alle 5 min ein Dispatch: bei 0, 5 und 10 min
    assert len(starts) == 3


def test_should_not_wait_when_bot_cannot_approve():
    import pr_merge_sa

    tabu = _facts(**BOT, files=["policies/x.md"], mandat="M0")
    starts, schlaf_aufrufe = [], []
    f, u = pr_merge_sa.warte_auf_bot_review(
        lambda: (tabu, classify(tabu, REGELN)),
        lambda: starts.append(1),
        schlafen=schlaf_aufrufe.append,
    )
    assert u.erlaubt is False and starts == [] and schlaf_aufrufe == []


# --- CODEOWNERS ohne Bot (Realfall #3809) ---------------------------------------
# Der Bot approvte, GitHub blieb BLOCKED: `require_code_owner_review` und
# `/tools/pr_merge_sa.py` nennt nur Menschen. Dort ist Warten sinnlos.

CODEOWNERS = """\
# Kommentar
/.github/     @achimdehnert @wirdigital @iil-lotse
/tools/pr_merge_sa.py  @achimdehnert @wirdigital
"""


def test_should_list_file_whose_codeowners_line_lacks_the_bot():
    from pr_merge_sa import dateien_ohne_bot_owner

    assert dateien_ohne_bot_owner(
        ["tools/pr_merge_sa.py", ".github/workflows/x.yml", "tools/frei.py"],
        CODEOWNERS,
    ) == ["tools/pr_merge_sa.py"]


def test_should_use_last_matching_codeowners_line():
    from pr_merge_sa import codeowner_der_datei

    text = CODEOWNERS + "/.github/CODEOWNERS @achimdehnert\n"
    assert codeowner_der_datei(".github/CODEOWNERS", text) == ["achimdehnert"]
    assert "iil-lotse" in codeowner_der_datei(".github/ci.yml", text)


def test_should_treat_wildcard_codeowners_as_unknown():
    from pr_merge_sa import dateien_ohne_bot_owner

    assert dateien_ohne_bot_owner(["docs/x.md"], "*.md @achimdehnert\n") is None


def test_should_not_name_bot_review_when_codeowner_lacks_bot():
    u = classify(
        _facts(
            repo=PLATFORM,
            files=["tools/pr_merge_sa.py"],
            mandat="M0",
            review_required=True,
            ohne_bot_owner=["tools/pr_merge_sa.py"],
        ),
        REGELN,
    )
    assert u.erlaubt is False and "--warte-auf-bot" not in u.grund


def test_should_not_name_bot_review_when_codeowners_unreadable():
    u = classify(
        _facts(repo=PLATFORM, files=[".github/workflows/x.yml"], mandat="M0"),
        REGELN,
    )
    assert u.erlaubt is False and "--warte-auf-bot" not in u.grund


# --- Repo-Positivliste fuer Merges mit OWNER_WORT (platform#3804 K7) ----------

MIT_WORT = {"OWNER_WORT": "RA 2026-10-08 05:00Z"}


def test_should_allow_listed_repo_with_owner_wort():
    from pr_merge_sa import pruefe_owner_wort_repo

    assert pruefe_owner_wort_repo("iilgmbh/risk-hub", MIT_WORT) is None
    assert pruefe_owner_wort_repo("achimdehnert/writing-hub", MIT_WORT) is None


@pytest.mark.parametrize("repo", ["meiki-lra/meiki-hub", "ttz-lif/ttz-hub"])
def test_should_reject_excluded_repo_with_owner_wort(repo):
    from pr_merge_sa import pruefe_owner_wort_repo

    grund = pruefe_owner_wort_repo(repo, MIT_WORT)
    assert grund and "Positivliste" in grund and repo in grund


def test_should_not_check_repo_without_owner_wort():
    from pr_merge_sa import pruefe_owner_wort_repo

    assert pruefe_owner_wort_repo("meiki-lra/meiki-hub", {}) is None
    assert pruefe_owner_wort_repo("meiki-lra/meiki-hub", {"OWNER_WORT": " "}) is None


def test_should_reject_with_owner_wort_when_list_file_missing(tmp_path):
    from pr_merge_sa import pruefe_owner_wort_repo

    with pytest.raises(Unklar):
        pruefe_owner_wort_repo(
            "iilgmbh/risk-hub", MIT_WORT, tmp_path / "gibt-es-nicht.yaml"
        )


def test_should_reject_with_owner_wort_when_list_is_empty(tmp_path):
    from pr_merge_sa import pruefe_owner_wort_repo

    leer = tmp_path / "leer.yaml"
    leer.write_text("repos: []\n")
    with pytest.raises(Unklar):
        pruefe_owner_wort_repo("iilgmbh/risk-hub", MIT_WORT, leer)


def test_should_exit_2_for_excluded_repo_with_owner_wort_before_any_api_call(
    monkeypatch, capsys
):
    import pr_merge_sa

    monkeypatch.setenv("OWNER_WORT", "RA 2026-10-08 05:00Z")
    monkeypatch.setattr(pr_merge_sa, "regeln", lambda *_a, **_k: REGELN)
    monkeypatch.setattr(
        pr_merge_sa,
        "gather",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("kein API-Zugriff")),
    )
    assert pr_merge_sa.main(["1", "meiki-lra/meiki-hub"]) == 2
    assert "Positivliste" in capsys.readouterr().err


def test_should_exit_3_with_owner_wort_when_list_file_missing(
    monkeypatch, tmp_path, capsys
):
    import pr_merge_sa

    monkeypatch.setenv("OWNER_WORT", "RA 2026-10-08 05:00Z")
    monkeypatch.setattr(pr_merge_sa, "OWNER_WORT_REPOS", tmp_path / "fehlt.yaml")
    monkeypatch.setattr(pr_merge_sa, "regeln", lambda *_a, **_k: REGELN)
    assert pr_merge_sa.main(["1", "iilgmbh/risk-hub"]) == 3
    assert "UNKLAR" in capsys.readouterr().err
