"""Drill für das Gate `parallel-subagents-brief-overlap` (platform#3167).

Realfall: Retro 2026-09-14 apo-hub (40c069) Befunde #5 und #6 — acht parallele
Fix-Subagenten, zwei schrieben denselben Scratchpad-Dateinamen (apo-hub#117
bekam den fremden PR-Body), drei Import-Konflikte in `apps/web/views.py` und
`apps/web/forms.py`, weil kein Brief den Dateikopf zuordnete.

Positivkontrolle ist Teil des Drills: Briefe, die der Hook NICHT blocken darf,
stehen unten mit eigener Begründung.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import subagent_brief_gate as g  # noqa: E402

VIEWS = "apps/web/views.py"
FORMS = "apps/web/forms.py"


def brief(slug: str, *dateien: str, importe: str = "", extra: str = "") -> str:
    zeilen = [
        f"Behebe Befund {slug} in apo-hub.",
        "Dateien: " + ", ".join(dateien),
        f"Schreibe nur unter $SCRATCHPAD/{slug}/ und lege dort pr-body.md ab.",
        "Kein `git stash`; Rot-Messung per `git show HEAD:<datei> > <datei>`.",
    ]
    if importe:
        zeilen.append(f"Importe: {importe}")
    if extra:
        zeilen.append(extra)
    return "\n".join(zeilen)


def eintrag(slug: str, *dateien: str, importe: tuple[str, ...] = ()) -> dict:
    return {
        "slug": slug,
        "dateien": list(dateien),
        "importe": list(importe),
        "scratch": slug,
    }


def test_should_have_the_registered_slug():
    assert g.SLUG == "parallel-subagents-brief-overlap"


# ── Realfall + Familie ───────────────────────────────────────────────────────


def test_should_deny_realfall_two_briefs_same_file_without_assignment():
    """#6: views.py in beiden Briefs, keiner bekommt den Importblock."""
    grund = g.entscheide(brief("b116", VIEWS), [eintrag("b115", VIEWS)])
    assert grund is not None
    assert VIEWS in grund and "Importblock" in grund


def test_should_deny_when_both_briefs_claim_the_import_block():
    grund = g.entscheide(
        brief("b120", FORMS, importe=FORMS), [eintrag("b119", FORMS, importe=(FORMS,))]
    )
    assert grund is not None
    assert "beide Briefs" in grund


def test_should_deny_realfall_shared_scratch_dir():
    """#5: zweiter Brief schreibt in dasselbe Unterverzeichnis wie der erste."""
    grund = g.entscheide(brief("fix", VIEWS), [eintrag("fix", FORMS)])
    assert grund is not None
    assert "Scratch-Unterverzeichnis" in grund


def test_should_deny_brief_without_scratch_dir():
    prompt = f"Behebe Befund in {VIEWS}. Lege den PR-Body als pr-body.md ab."
    grund = g.entscheide(prompt, [])
    assert grund is not None
    assert "Scratch-Unterverzeichnis" in grund


def test_should_deny_brief_recommending_git_stash():
    """#4 auf Brief-Ebene: der Brief darf den Griff nicht empfehlen."""
    prompt = f"Ändere {VIEWS}. Schreibe unter $SCRATCHPAD/b1/. Für die Rot-Messung: git stash, Test, git stash pop."
    grund = g.entscheide(prompt, [])
    assert grund is not None
    assert "git stash" in grund


# ── Positivkontrolle: was durch muss ─────────────────────────────────────────


def test_should_allow_shared_file_when_exactly_one_brief_owns_the_imports():
    """Die Zuordnung ist genau das, was #6 verhindert hätte."""
    assert (
        g.entscheide(brief("b116", VIEWS), [eintrag("b115", VIEWS, importe=(VIEWS,))])
        is None
    )
    assert (
        g.entscheide(brief("b116", VIEWS, importe=VIEWS), [eintrag("b115", VIEWS)])
        is None
    )


def test_should_allow_disjoint_files_with_own_scratch_dirs():
    assert g.entscheide(brief("b116", FORMS), [eintrag("b115", VIEWS)]) is None


def test_should_allow_solo_brief_with_scratch_dir():
    assert g.entscheide(brief("solo", VIEWS, FORMS), []) is None


def test_should_allow_brief_that_forbids_git_stash():
    """Die Verneinung ist die gewünschte Formulierung, kein Treffer."""
    assert (
        g.entscheide(brief("b1", VIEWS, extra="Nie `git stash` verwenden."), []) is None
    )


def test_should_allow_brief_without_file_mentions():
    """Fail-open: ohne Dateinennung ist es kein Umsetzungs-Brief."""
    assert g.entscheide("Fasse die offenen Issues des Repos zusammen.", []) is None


def test_should_read_scratch_dir_in_both_spellings():
    assert (
        g.lies_brief("Schreibe nach /tmp/x/scratchpad/agent-a/ und ändere apps/a.py")[
            "scratch"
        ]
        == "agent-a"
    )
    assert (
        g.lies_brief("Schreibe nach ${SCRATCHPAD}/agent-b und ändere apps/a.py")[
            "scratch"
        ]
        == "agent-b"
    )


# ── Zustand + Einstieg über stdin ────────────────────────────────────────────


def _lauf(monkeypatch, daten: dict) -> int:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(daten)))
    return g.main()


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "STATE_DIR", tmp_path / "briefs")
    return tmp_path / "briefs"


def test_should_remember_allowed_brief_and_block_the_colliding_second(
    state_dir, monkeypatch
):
    basis = {"tool_name": "Agent", "session_id": "s1", "cwd": "/repo"}
    erster = {
        **basis,
        "tool_input": {
            "prompt": brief("b115", VIEWS),
            "subagent_type": "general-purpose",
        },
    }
    assert _lauf(monkeypatch, erster) == 0
    assert (state_dir / "s1.json").exists()
    zweiter = {
        **basis,
        "tool_input": {
            "prompt": brief("b116", VIEWS),
            "subagent_type": "general-purpose",
        },
    }
    assert _lauf(monkeypatch, zweiter) == 2


def test_should_not_see_briefs_of_another_session_or_repo(state_dir, monkeypatch):
    g.merke("s1", "/repo-a", g.lies_brief(brief("b115", VIEWS)), "b115")
    assert g.lade_fruehere("s2", "/repo-a") == []
    assert g.lade_fruehere("s1", "/repo-b") == []
    assert len(g.lade_fruehere("s1", "/repo-a")) == 1


def test_should_forget_briefs_older_than_the_window(state_dir):
    g.merke("s1", "/repo", g.lies_brief(brief("alt", VIEWS)), "alt", jetzt=1000.0)
    assert g.lade_fruehere("s1", "/repo", jetzt=1000.0 + g.FENSTER_S + 1) == []


def test_should_ignore_read_only_agents_and_other_tools(state_dir, monkeypatch):
    daten = {
        "tool_name": "Agent",
        "session_id": "s1",
        "cwd": "/repo",
        "tool_input": {"prompt": f"Suche in {VIEWS}", "subagent_type": "Explore"},
    }
    assert _lauf(monkeypatch, daten) == 0
    assert (
        _lauf(
            monkeypatch,
            {"tool_name": "Bash", "tool_input": {"command": "git stash pop"}},
        )
        == 0
    )


def test_should_fail_open_on_invalid_json(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("kein json"))
    assert g.main() == 0
