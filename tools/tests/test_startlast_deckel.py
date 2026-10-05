"""Deckel auf die Startlast der Session-Skills (V2, platform#3785).

Die Diaet vom 2026-09-02 (#2690) kuerzte die drei Session-Skills von 130 KB auf
66,6 KB. Am 2026-10-05 waren es wieder 96,8 KB, ohne dass ein Check rot wurde:
eine einmalige Kuerzung waechst nach. Diese Tests machen daraus eine Ratsche.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DECKEL = json.loads(
    (REPO / "docs/governance/startlast-deckel.json").read_text(encoding="utf-8")
)
SKILL_QUELLE = REPO / ".windsurf/workflows"

#: Summe der Deckel bei Einfuehrung. Die Ratsche verbietet, den Deckel in der
#: JSON-Datei still anzuheben: wer das will, muss auch diese Zahl aendern.
SUMME_BEI_EINFUEHRUNG = 96818


def test_should_keep_every_session_skill_under_its_cap() -> None:
    zu_gross = {}
    for name, deckel in DECKEL["skills"].items():
        groesse = (SKILL_QUELLE / f"{name}.md").stat().st_size
        if groesse > deckel:
            zu_gross[name] = f"{groesse} > {deckel}"
    assert zu_gross == {}, (
        f"Skill ueber dem Deckel: {zu_gross}. Herleitung, Realfall und Messung gehoeren "
        "nach docs/governance/session-skills-lehren/, nicht in den Skill."
    )


def test_should_never_raise_the_cap_above_its_starting_sum() -> None:
    assert sum(DECKEL["skills"].values()) <= SUMME_BEI_EINFUEHRUNG


def test_should_keep_the_target_below_the_current_cap() -> None:
    assert DECKEL["ziel_summe"] <= sum(DECKEL["skills"].values())


def test_should_cap_every_session_skill_that_exists() -> None:
    vorhanden = {p.stem for p in SKILL_QUELLE.glob("session-*.md")}
    assert {"session-start", "session-ende", "session-retro"} <= vorhanden
    assert set(DECKEL["skills"]) <= vorhanden
