"""Drill für die maschinenlesbare Aufgabenklasse->Tier-Tabelle (#2750 K2).

Parst policies/session-routing.md zwischen den routing-table-Markern (Vertrag
mit tools/claude-hooks/fable_delegation_reminder.sh) und prueft Form + Werte.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = REPO_ROOT / "policies" / "session-routing.md"

START_MARKER = "<!-- routing-table:start -->"
END_MARKER = "<!-- routing-table:end -->"

GUELTIGE_TIER = {"inline", "T2", "T3", "T4", "T5"}
GUELTIGE_MODEL = {"–", "haiku", "sonnet", "opus", "inline"}
# Von der Agent-Tool-Enum bekannte model-Werte (siehe Agent-Tool-Schema `model`).
AGENT_TOOL_MODELLE = {"sonnet", "opus", "haiku"}


def _tabellen_zeilen() -> list[str]:
    text = POLICY.read_text(encoding="utf-8")
    si = text.find(START_MARKER)
    ei = text.find(END_MARKER)
    assert si != -1 and ei != -1 and ei > si, "routing-table Marker fehlen"
    block = text[si + len(START_MARKER):ei].strip("\n")
    zeilen = [z for z in block.splitlines() if z.strip().startswith("|")]
    # Kopfzeile + Trennzeile (---) abschneiden, Rest sind Datenzeilen.
    return zeilen[2:]


def _parse(zeile: str) -> list[str]:
    teile = [t.strip() for t in zeile.strip().strip("|").split("|")]
    return teile


def test_should_genau_fuenf_datenzeilen_haben():
    zeilen = _tabellen_zeilen()
    assert len(zeilen) == 5


def test_should_jede_klasse_genau_einmal_haben():
    zeilen = _tabellen_zeilen()
    klassen = [_parse(z)[0] for z in zeilen]
    assert sorted(klassen) == sorted(set(klassen))
    assert set(klassen) == {"Trivial", "Mechanisch", "Umsetzung", "Schwer", "Urteil"}


def test_should_jede_zeile_genau_einen_gueltigen_tier_haben():
    zeilen = _tabellen_zeilen()
    for zeile in zeilen:
        felder = _parse(zeile)
        tier = felder[3]
        assert tier in GUELTIGE_TIER, f"unbekannter Tier in Zeile: {zeile}"


def test_should_jede_zeile_ein_gueltiges_model_haben():
    zeilen = _tabellen_zeilen()
    for zeile in zeilen:
        felder = _parse(zeile)
        model = felder[4]
        assert model in GUELTIGE_MODEL, f"unbekanntes model in Zeile: {zeile}"


def test_should_jedes_delegierbare_model_von_agent_tool_enum_bekannt_sein():
    zeilen = _tabellen_zeilen()
    for zeile in zeilen:
        felder = _parse(zeile)
        model = felder[4]
        if model in ("–", "inline"):
            continue
        assert model in AGENT_TOOL_MODELLE, f"model nicht in Agent-Tool-Enum: {zeile}"
