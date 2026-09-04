"""Tests der Bot-Review-Auswahl — vor allem des Zwillings-Falls aus #2674.

Die Regeln lagen bis 2026-09-02 als Heredoc im Workflow und waren damit nicht
pruefbar. Diese Datei existiert, damit der naechste Fehler in der Auswahl hier
auffaellt und nicht daran, dass ein PR unerklaerlich liegenbleibt.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_review_kandidaten import (  # noqa: E402
    juengste_je_name,
    nicht_gruene_checks,
    waehle_kandidaten,
)

BOT = "IIL-Lotse"
OWNER = "achimdehnert"


def check(name: str, conclusion: str, completed: str) -> dict:
    return {"name": name, "conclusion": conclusion, "completedAt": completed}


def pr(**felder) -> dict:
    grund = {
        "number": 1,
        "isDraft": False,
        "author": {"login": OWNER},
        "mergeStateStatus": "BLOCKED",
        "reviewDecision": "",
        "reviews": [],
        "files": [{"path": "infra/ports.yaml"}],
        "statusCheckRollup": [check("gate", "SUCCESS", "2026-09-02T11:33:38Z")],
    }
    grund.update(felder)
    return grund


def test_should_ignore_cancelled_twin_of_the_same_check():
    """Realfall #2674: abgebrochener Zwilling + gruener Lauf desselben Gates."""
    checks = [
        check("Aufgeschobene Arbeit", "CANCELLED", "2026-09-02T11:33:19Z"),
        check("Aufgeschobene Arbeit", "SUCCESS", "2026-09-02T11:33:38Z"),
    ]
    assert nicht_gruene_checks(checks) == []


def test_should_ignore_failed_rerun_of_a_superseded_run():
    """`gh run rerun` spielt die alte Nutzlast ab und macht aus CANCELLED FAILURE.

    Der Eintrag ist aelter als der gruene Lauf und darf nicht mehr zaehlen.
    """
    checks = [
        check("Aufgeschobene Arbeit", "SUCCESS", "2026-09-02T11:43:32Z"),
        check("Aufgeschobene Arbeit", "FAILURE", "2026-09-02T11:42:09Z"),
    ]
    assert nicht_gruene_checks(checks) == []


def test_should_still_block_when_the_newest_run_is_red():
    """Die Bereinigung darf echtes Rot nicht verschlucken — Gegenprobe."""
    checks = [
        check("Aufgeschobene Arbeit", "SUCCESS", "2026-09-02T11:33:38Z"),
        check("Aufgeschobene Arbeit", "FAILURE", "2026-09-02T11:50:00Z"),
    ]
    assert nicht_gruene_checks(checks) == ["Aufgeschobene Arbeit"]


def test_should_block_when_a_different_check_is_red():
    checks = [
        check("gate", "SUCCESS", "2026-09-02T11:33:38Z"),
        check("gitleaks", "FAILURE", "2026-09-02T11:33:40Z"),
    ]
    assert nicht_gruene_checks(checks) == ["gitleaks"]


def test_should_keep_newest_per_name_across_several_names():
    checks = [
        check("a", "FAILURE", "2026-09-02T10:00:00Z"),
        check("a", "SUCCESS", "2026-09-02T11:00:00Z"),
        check("b", "SUCCESS", "2026-09-02T10:30:00Z"),
    ]
    namen = sorted((c["name"], c["conclusion"]) for c in juengste_je_name(checks))
    assert namen == [("a", "SUCCESS"), ("b", "SUCCESS")]


def test_should_select_a_clean_owner_pr():
    kandidaten, _ = waehle_kandidaten([pr()], BOT, OWNER)
    assert kandidaten == [1]


def test_should_select_pr_whose_only_red_entry_is_a_superseded_twin():
    """Der Fall, an dem #2674 haengenblieb — Ende-zu-Ende durch die Auswahl."""
    p = pr(
        statusCheckRollup=[
            check("gate", "CANCELLED", "2026-09-02T11:33:19Z"),
            check("gate", "SUCCESS", "2026-09-02T11:33:38Z"),
        ]
    )
    kandidaten, protokoll = waehle_kandidaten([p], BOT, OWNER)
    assert kandidaten == [1], protokoll


def test_should_skip_draft():
    kandidaten, protokoll = waehle_kandidaten([pr(isDraft=True)], BOT, OWNER)
    assert kandidaten == []
    assert "Draft" in protokoll[0]


def test_should_skip_foreign_author():
    kandidaten, protokoll = waehle_kandidaten(
        [pr(author={"login": "jemand-anders"})], BOT, OWNER
    )
    assert kandidaten == []
    assert "nur Owner-PRs" in protokoll[0]


def test_should_skip_when_bot_already_approved():
    p = pr(reviews=[{"author": {"login": BOT}, "state": "APPROVED"}])
    kandidaten, protokoll = waehle_kandidaten([p], BOT, OWNER)
    assert kandidaten == []
    assert "bereits von" in protokoll[0]


def test_should_skip_tabu_path():
    p = pr(files=[{"path": ".github/workflows/bot-review.yml"}])
    kandidaten, protokoll = waehle_kandidaten([p], BOT, OWNER)
    assert kandidaten == []
    assert "Tabu-Pfad" in protokoll[0]


def test_should_skip_when_the_selection_module_itself_changes():
    """Der Bot gibt die Regel nicht frei, nach der er selbst urteilt."""
    p = pr(files=[{"path": "tools/bot_review_kandidaten.py"}])
    kandidaten, _ = waehle_kandidaten([p], BOT, OWNER)
    assert kandidaten == []


def test_should_skip_without_any_check():
    kandidaten, protokoll = waehle_kandidaten([pr(statusCheckRollup=[])], BOT, OWNER)
    assert kandidaten == []
    assert "keine Checks" in protokoll[0]


def test_should_skip_when_not_review_blocked():
    kandidaten, protokoll = waehle_kandidaten([pr(mergeStateStatus="CLEAN")], BOT, OWNER)
    assert kandidaten == []
    assert "nicht review-blockiert" in protokoll[0]
