"""Drill fuer tools/messungen/gate_bilanz_2374.py (platform#2374 Ziel A, Rev 2).

Prueft die Stellen, an denen die Messung kippen kann und an denen Rev 1 gekippt ist:
Tabellen-Parser (SURVIVES zaehlt, REFUTED nicht, Bau-Tag nicht; Zeilen UND Retros),
`covers`-Alias getrennt vom eigenen Slug, `gates_caught` wird nicht abgezogen, striktes
Kill-Gate (Gleichstand = verworfen) mit deklariertem Tie-Break, Entscheidungstag im
Pruefdatensatz getrennt von "nach".
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "messungen" / "gate_bilanz_2374.py"
_spec = importlib.util.spec_from_file_location("gate_bilanz_2374", _QUELLE)
gb = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gb)

_KOPF = "| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |\n|---|---|---|---|---|---|---|\n"


def _retro(tmp: Path, datum: str, zeilen: str, fm: str = "recurring_findings: []\n"):
    (tmp / f"session-retro-{datum}-platform-abc123.md").write_text(
        f"---\ndate: {datum}\n{fm}---\n\n## 2. Befund-Tabelle\n\n{_KOPF}{zeilen}",
        encoding="utf-8",
    )


def test_should_count_rows_and_retros_after_built_but_not_refuted_or_build_day(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(gb, "RETROS", str(tmp_path))
    _retro(tmp_path, "2026-08-10", "| 1 | x | k | hoch | SURVIVES | b | `foo-bar` |\n")
    _retro(
        tmp_path,
        "2026-08-12",
        "| 1 | y | k | hoch | SURVIVES (kommandobelegt) | b | `foo-bar` ×2 |\n"
        "| 2 | y2 | k | hoch | **SURVIVES** | b \\| c | `foo-bar` |\n"
        "| 3 | z | k | hoch | **REFUTED** | b | `foo-bar` |\n",
    )
    _retro(tmp_path, "2026-08-11", "| 1 | w | k | hoch | SURVIVES | b | foo-bar |\n")
    gates = [{"slug": "foo-bar", "built": "2026-08-10", "mode": "advisory"}]
    (r,) = gb.rueckwaerts(gates, gb.lies_retros(), {})
    # 08-10 ist Bau-Tag, REFUTED zaehlt nicht: 3 Zeilen in 2 Retros
    assert r["nach_built_zeilen_eigen"] == 3
    assert r["nach_built_retros_eigen"] == 2
    assert r["fenster_retros"] == 2


def test_should_separate_own_slug_from_covers_alias_and_not_subtract_caught(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(gb, "RETROS", str(tmp_path))
    _retro(tmp_path, "2026-08-11", "| 1 | w | k | hoch | SURVIVES | b | `alt-name` |\n")
    _retro(
        tmp_path,
        "2026-08-12",
        "| 1 | w | k | hoch | SURVIVES | b | `foo-bar` |\n",
        fm="recurring_findings: [foo-bar]\ngates_caught: [foo-bar]\n",
    )
    gates = [
        {
            "slug": "foo-bar",
            "built": "2026-08-10",
            "covers": ["alt-name"],
            "mode": "advisory",
        }
    ]
    (r,) = gb.rueckwaerts(gates, gb.lies_retros(), {})
    assert r["nach_built_retros_eigen"] == 1
    assert r["nach_built_retros_alias"] == 2
    assert r["frontmatter_gefangen_retros"] == 1
    assert r["rueckfaellig_alias"] and r["rueckfaellig_eigen"]
    assert r["rueckfaellig_netto"]  # 08-11 bleibt auch ohne die gates_caught-Retro


def _rang(*eintraege):
    rows = [
        {"slug": s, "score": sc, "alter_tage": a, "rang": i + 1}
        for i, (s, sc, a) in enumerate(eintraege)
    ]
    for i, r in enumerate(sorted(rows, key=lambda r: (-r["alter_tage"], r["slug"])), 1):
        r["rang_basis"] = i
    return rows


def test_should_discard_instrument_on_tie_with_age_baseline():
    rang = _rang(("a", 2.0, 5), ("b", 1.0, 9))
    rueck = [
        {"slug": "a", "rueckfaellig_alias": True, "rueckfall_retros_alias": 1},
        {"slug": "b", "rueckfaellig_alias": True, "rueckfall_retros_alias": 2},
    ]
    kg = gb.kill_gate(rang, rueck)
    assert kg["top5_treffer_instrument"] == kg["top5_treffer_grundlinie"] == 2
    assert kg["instrument_schlaegt_grundlinie"] is False


def test_should_expose_tie_break_direction_in_top_n(monkeypatch):
    monkeypatch.setattr(gb, "TOP_N", 1)
    rang = _rang(("a", 1.0, 5), ("b", 1.0, 5))
    rueck = [
        {"slug": "a", "rueckfaellig_alias": False, "rueckfall_retros_alias": 0},
        {"slug": "b", "rueckfaellig_alias": True, "rueckfall_retros_alias": 3},
    ]
    az = gb.kill_gate(rang, rueck, tie="az")
    za = gb.kill_gate(rang, rueck, tie="za")
    assert az["top5_instrument"] == ["a"] and za["top5_instrument"] == ["b"]
    assert az["top5_treffer_instrument"] == 0 and za["top5_treffer_instrument"] == 1


def test_should_keep_decision_day_apart_from_after(tmp_path, monkeypatch):
    monkeypatch.setattr(gb, "RETROS", str(tmp_path))
    _retro(tmp_path, "2026-08-22", "| 1 | w | k | hoch | SURVIVES | b | `x-y` |\n")
    _retro(tmp_path, "2026-08-23", "| 1 | w | k | hoch | SURVIVES | b | `x-y` |\n")
    reg = {"declined": [], "widerrufen": [{"slug": "x-y", "declined_am": "2026-08-23"}]}
    (r,) = gb.pruefdatensatz(reg, gb.lies_retros())
    assert (r["vor_entscheidung"], r["am_tag"], r["nach_entscheidung"]) == (1, 1, 0)


def test_should_compute_spearman_with_ties():
    assert abs(gb._spearman([1, 2, 3], [1, 2, 3]) - 1.0) < 1e-9
    assert abs(gb._spearman([1, 2, 3], [3, 2, 1]) + 1.0) < 1e-9
    assert abs(gb._spearman([1, 1, 2], [1, 2, 2])) < 1.0
