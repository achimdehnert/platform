"""Tests für tools/session_collision_meter.py (K5 aus platform#1944).

Die Netz-/git-Abhängigkeit sitzt allein in `fetch_prs` und `files_of`; alles
darunter ist rein rechnend und wird hier ohne beides geprüft.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "session_collision_meter.py"
_spec = importlib.util.spec_from_file_location("session_collision_meter", _SCRIPT)
scm = importlib.util.module_from_spec(_spec)
sys.modules["session_collision_meter"] = scm
_spec.loader.exec_module(scm)


T0 = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def _pr(number: int, created_h: int, merged_h: int, **extra) -> dict:
    pr = {
        "number": number,
        "title": f"PR {number}",
        "_created": T0 + timedelta(hours=created_h),
        "_merged": T0 + timedelta(hours=merged_h),
    }
    pr.update(extra)
    return pr


# --- overlaps ---------------------------------------------------------------


def test_should_detect_overlap_when_lifetimes_intersect():
    assert scm.overlaps(_pr(1, 0, 10), _pr(2, 5, 15)) is True


def test_should_not_detect_overlap_when_second_opens_after_first_merged():
    assert scm.overlaps(_pr(1, 0, 5), _pr(2, 6, 10)) is False


def test_should_detect_overlap_when_one_pr_fully_contains_the_other():
    assert scm.overlaps(_pr(1, 0, 20), _pr(2, 5, 10)) is True


# --- numbered_claims --------------------------------------------------------


def test_should_extract_konz_number_from_added_file():
    claims = scm.numbered_claims(["docs/konzepte/KONZ-platform-043-formatsatz.md"])
    assert claims == {("KONZ-PLATFORM", 43): "KONZ-platform-043-formatsatz.md"}


def test_should_extract_adr_number_from_added_file():
    claims = scm.numbered_claims(["docs/adr/ADR-294-llm-gateway.md"])
    assert claims == {("ADR", 294): "ADR-294-llm-gateway.md"}


def test_should_ignore_files_without_number_pattern():
    assert scm.numbered_claims(["docs/konzepte/README.md", "tools/x.py"]) == {}


# --- classify ---------------------------------------------------------------


def test_should_separate_generated_from_substantial_files():
    generated, substantial = scm.classify(
        {"docs/adr/INDEX.md", "tools/mail_agent/read_mail.py"}
    )
    assert generated == {"docs/adr/INDEX.md"}
    assert substantial == {"tools/mail_agent/read_mail.py"}


# --- analyse ----------------------------------------------------------------


@pytest.fixture
def no_git(monkeypatch):
    """files_of durch die im PR-Dict hinterlegten Listen ersetzen."""
    monkeypatch.setattr(
        scm, "files_of", lambda pr: (pr.get("files", []), pr.get("added", []))
    )


def test_should_count_number_collision_when_same_number_different_slug(no_git):
    prs = [
        _pr(1, 0, 10, added=["docs/konzepte/KONZ-platform-043-a.md"], files=[]),
        _pr(2, 5, 15, added=["docs/konzepte/KONZ-platform-043-b.md"], files=[]),
    ]
    result = scm.analyse(prs)
    assert result["N_number_collisions"] == 1
    assert result["R_collision_pairs"] == 1


def test_should_not_count_number_collision_when_both_touch_same_file(no_git):
    """Zwei PRs am selben Dokument sind eine Bearbeitung, keine Doppelvergabe."""
    same = ["docs/konzepte/KONZ-platform-043-a.md"]
    prs = [_pr(1, 0, 10, added=same, files=same), _pr(2, 5, 15, added=same, files=same)]
    result = scm.analyse(prs)
    assert result["N_number_collisions"] == 0
    assert result["S_substantial"] == 1


def test_should_not_count_collision_when_prs_never_overlapped(no_git):
    shared = ["tools/x.py"]
    prs = [_pr(1, 0, 5, files=shared, added=[]), _pr(2, 6, 10, files=shared, added=[])]
    result = scm.analyse(prs)
    assert result["R_collision_pairs"] == 0
    assert result["pairs_overlapping"] == 0


def test_should_classify_pair_as_generated_only_when_sole_shared_file_is_index(no_git):
    shared = ["docs/adr/INDEX.md"]
    prs = [_pr(1, 0, 10, files=shared, added=[]), _pr(2, 5, 15, files=shared, added=[])]
    result = scm.analyse(prs)
    assert result["G_generated_only"] == 1
    assert result["S_substantial"] == 0


def test_should_rank_hot_files_by_share_count(no_git):
    prs = [
        _pr(1, 0, 30, files=["a.py", "b.py"], added=[]),
        _pr(2, 1, 30, files=["a.py", "b.py"], added=[]),
        _pr(3, 2, 30, files=["a.py"], added=[]),
    ]
    result = scm.analyse(prs)
    assert result["hot_files"][0] == ("a.py", 3)


def test_should_report_zero_collisions_for_disjoint_file_sets(no_git):
    prs = [
        _pr(1, 0, 10, files=["a.py"], added=[]),
        _pr(2, 5, 15, files=["b.py"], added=[]),
    ]
    result = scm.analyse(prs)
    assert result["R_collision_pairs"] == 0
    assert result["pairs_overlapping"] == 1
