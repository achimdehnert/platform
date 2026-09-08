"""Zwei Pruefungen auf `implementation_status` (platform#2931).

Beide Richtungen je Pruefung: eine Regel, die nur findet, belegt nichts —
sie muss auch schweigen koennen, wo nichts ist.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import adr_umsetzungsstand_check as check  # noqa: E402

KOPF = """---
id: ADR-{nr}
title: "Probe"
status: {status}
decision_date: 2026-09-08
deciders: [Achim Dehnert]
domains: [governance]
implementation_status: {impl}
---

# ADR-{nr}: Probe

{body}
"""


def _adr(tmp_path: Path, nr: str, status: str, impl: str, body: str = "Text.") -> Path:
    p = tmp_path / f"ADR-{nr}-probe.md"
    p.write_text(
        KOPF.format(nr=nr, status=status, impl=impl, body=body), encoding="utf-8"
    )
    return p


def test_should_flag_a_value_outside_the_schema_vocabulary(tmp_path):
    """`not_started` ist kein Schema-Wert — der Schema-Pruefer nimmt ihn trotzdem an."""
    _adr(tmp_path, "101", "accepted", "not_started")
    befunde = check.sammle(tmp_path)
    assert [b["art"] for b in befunde].count("wert") == 1


def test_should_stay_silent_on_every_valid_value(tmp_path):
    """Gegenprobe: alle acht erlaubten Werte duerfen KEINEN Wert-Befund erzeugen."""
    for i, wert in enumerate(sorted(check.ENUM), start=200):
        _adr(tmp_path, str(i), "proposed", wert)
    befunde = [b for b in check.sammle(tmp_path) if b["art"] == "wert"]
    assert befunde == [], f"gueltige Werte faelschlich beanstandet: {befunde}"


def test_should_flag_accepted_none_without_a_visible_hint(tmp_path):
    _adr(tmp_path, "301", "accepted", "none")
    befunde = [b for b in check.sammle(tmp_path) if b["art"] == "hinweis"]
    assert len(befunde) == 1


def test_should_accept_a_visible_hint_in_the_body(tmp_path):
    """Gegenprobe zum Test darueber: mit Hinweis im Kopf des Textes kein Befund."""
    _adr(
        tmp_path,
        "302",
        "accepted",
        "none",
        body="> [!IMPORTANT]\n> Diese Regel ist beschlossen, aber NICHT IN KRAFT.",
    )
    assert [b for b in check.sammle(tmp_path) if b["art"] == "hinweis"] == []


def test_should_not_flag_partial_or_missing_field_as_hint_case(tmp_path):
    """`partial` heisst "etwas existiert", ein fehlendes Feld heisst "nicht erklaert".

    Beides waere hier Rauschen: gemessen am echten Bestand 92 Funde statt 14.
    """
    _adr(tmp_path, "401", "accepted", "partial")
    ohne_feld = tmp_path / "ADR-402-probe.md"
    ohne_feld.write_text(
        KOPF.format(nr="402", status="accepted", impl="none", body="Text.").replace(
            "implementation_status: none\n", ""
        ),
        encoding="utf-8",
    )
    assert [b for b in check.sammle(tmp_path) if b["art"] == "hinweis"] == []


def test_should_stay_silent_on_a_finished_adr(tmp_path):
    _adr(tmp_path, "501", "accepted", "implemented")
    assert check.sammle(tmp_path) == []


def test_should_default_to_suggest_and_gate_only_on_demand(tmp_path):
    """SUGGEST ist Vorgabe — neue Regeln starten im Repo advisory."""
    _adr(tmp_path, "601", "accepted", "not_started")
    assert check.main(["--adr-dir", str(tmp_path)]) == 0
    assert check.main(["--adr-dir", str(tmp_path), "--gate"]) == 1


def test_should_ignore_a_hint_that_appears_far_down_the_document(tmp_path):
    """Ein Hinweis nach 300 Zeilen hat den Leser laengst verfehlt."""
    tief = "\n".join(["Fuelltext."] * 80) + "\nDiese Regel ist NICHT IN KRAFT."
    _adr(tmp_path, "701", "accepted", "none", body=tief)
    assert len([b for b in check.sammle(tmp_path) if b["art"] == "hinweis"]) == 1
