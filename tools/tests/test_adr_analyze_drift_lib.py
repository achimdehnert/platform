"""Tests für tools/adr/adr_analyze.py — Delegation an iil_adrfw.rules.drift (platform#3457 Schritt 3).

Zwei Fragen:
1. Ruft adr_analyze.py wirklich die Bibliotheksfunktion `pruefe_adr` auf,
   statt sie nur zu importieren und weiter lokal zu rechnen?
   (test_should_use_library_rules — Monkeypatch beweist echte Delegation.)
2. Klassifiziert das Werkzeug dieselben drei Fixture-ADRs (stale, superseded
   ohne superseded_by, sauber) weiterhin wie vor dem Umbau — als Positivkontrolle
   gegen einen stillen Bedeutungswechsel?
   (test_should_classify_fixture_adrs_consistently)

adr_analyze.py führt beim Import Top-Level-Code aus (liest sys.argv[1]/[2]),
daher wird sys.argv vor dem Import auf ein Inventory-JSON umgebogen, wie in
test_adr_analyze_pdate.py.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import sys
from pathlib import Path

import iil_adrfw.rules.drift as real_drift

_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "adr" / "adr_analyze.py"


def _run(tmp_path, rows):
    inventory = tmp_path / "inventory.json"
    findings = tmp_path / "findings.json"
    inventory.write_text(json.dumps(rows), encoding="utf-8")
    old_argv = sys.argv
    sys.argv = ["adr_analyze.py", str(inventory), str(findings)]
    try:
        spec = importlib.util.spec_from_file_location("adr_analyze_under_test", _SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["adr_analyze_under_test"] = mod
        spec.loader.exec_module(mod)
    finally:
        sys.argv = old_argv
    return json.loads(findings.read_text(encoding="utf-8"))


def _row(**overrides):
    base = {
        "repo": "demo-repo",
        "file": "ADR-001-x.md",
        "num": 1,
        "title": "X",
        "status": "",
        "date": "",
        "supersedes": "",
        "superseded_by": "",
        "impl": "",
        "has_fm": True,
        "bytes": 1000,
        "madr": True,
        "template_rest": False,
    }
    base.update(overrides)
    return base


def test_should_use_library_rules(tmp_path, monkeypatch):
    """Ein junges (nicht-veraltetes) proposed-ADR muss trotzdem als stale_proposed
    auftauchen, wenn `pruefe_adr` das per Stub behauptet — nur so ist bewiesen,
    dass adr_analyze.py das Ergebnis der Bibliothek uebernimmt statt selbst
    (weiterhin lokal) zu rechnen."""
    calls = []

    def fake_pruefe_adr(**kwargs):
        calls.append(kwargs)
        klassen = real_drift.leere_klassen()
        klassen["wirkung"].append(real_drift.DriftReason.STALE_NO_UPDATE)
        return klassen

    monkeypatch.setattr(real_drift, "pruefe_adr", fake_pruefe_adr)

    heute = datetime.date.today()
    rows = [
        _row(
            status="proposed",
            date=heute.isoformat(),  # heute -> unter der echten Regel NICHT stale
        )
    ]
    rep = _run(tmp_path, rows)

    assert calls, "adr_analyze.py hat iil_adrfw.rules.drift.pruefe_adr nicht aufgerufen"
    assert rep["phase1"]["demo-repo"].get("stale_proposed"), (
        "Stub-Klassifikation (STALE_NO_UPDATE) wurde nicht in stale_proposed uebernommen "
        "-> adr_analyze.py rechnet noch lokal statt zu delegieren"
    )


def test_should_classify_fixture_adrs_consistently(tmp_path):
    """Positivkontrolle mit der echten (nicht gemockten) Bibliothek: drei
    Fixture-ADRs (stale proposed, superseded ohne superseded_by, sauber)
    liefern dieselbe Klassifikation wie vor dem Umbau auf iil_adrfw.rules.drift."""
    heute = datetime.date.today()
    stale_date = heute - datetime.timedelta(days=200)
    fresh_date = heute - datetime.timedelta(days=5)

    rows = [
        _row(
            num=1,
            file="ADR-001-stale.md",
            status="proposed",
            date=stale_date.isoformat(),
        ),
        _row(
            num=2,
            file="ADR-002-superseded-ohne-by.md",
            status="superseded",
            date=fresh_date.isoformat(),
            superseded_by="",
        ),
        _row(
            num=3,
            file="ADR-003-sauber.md",
            status="accepted",
            date=fresh_date.isoformat(),
        ),
    ]
    rep = _run(tmp_path, rows)

    stale_proposed = rep["phase1"]["demo-repo"].get("stale_proposed", [])
    assert any("ADR-001-stale.md" in x for x in stale_proposed)
    assert not any("ADR-002" in x or "ADR-003" in x for x in stale_proposed)

    broken = rep["phase2"]["supersession_broken"]
    assert any(
        "ADR-002-superseded-ohne-by.md: status=superseded ohne superseded_by" in x
        for x in broken
    )
    assert not any("ADR-001" in x or "ADR-003" in x for x in broken)
