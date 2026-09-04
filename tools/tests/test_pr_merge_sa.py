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
    FREIGABE_VERMERK,
    Facts,
    Unklar,
    _paths_ignore_deckt_alles,
    classify,
    ist_doku,
    ist_governance,
    regeln,
    review_ist_pflicht,
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
        "docs/governance/",
        "docs/konzepte/KONZ-platform-025-lotsen-charta.md",
        "CODEOWNERS",
        "tools/pr_merge_sa.py",
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


def test_should_name_the_deploy_vermerk_path_when_w3_lacks_m3():
    """#2812 (b): die Meldung nennt beide Wege zu M3, nicht nur den generischen
    Ablehnungssatz."""
    u = classify(
        _facts(wirkung="W3", mandat="M0", files=["app/x.py"], checks_total=2), REGELN
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
