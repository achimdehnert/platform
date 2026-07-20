"""Tests für tools/adr/adr_fm_migrate.py — derive_status() (F-11).

Repro (repo-optimize 2026-07-08-runB, Skeptiker-verifiziert): derive_status()
iterierte MAP in First-Match-Reihenfolge. Bei Status-Texten, die sowohl einen
Anfangs- als auch einen Endzustands-Marker enthalten (z.B. "Accepted
(superseded by ADR-99)"), gewann der zuerst in MAP gelistete Anfangszustand
("accepted") statt des fachlich korrekten Endzustands ("superseded").

Fix: MAP wurde umsortiert — Endzustände (superseded, deprecated, rejected)
werden jetzt VOR den Anfangszuständen (accepted, proposed, draft, ...)
geprüft. Alternative (Sammeln aller Treffer + feste Prioritätsliste) wurde
verworfen, weil eine reine Reihenfolge-Änderung ausreicht und alle
bestehenden MAP-Einträge auf Substring-Kollisionen mit den drei
vorgezogenen Endzustands-Keys geprüft wurden (keine gefunden).

adr_fm_migrate.py führt beim Import Top-Level-Code aus (liest sys.argv[1]
als Repo-Name, sys.argv[2] als findings.json und iteriert über
findings["phase1"][repo]["no_fm"]). Mit einer leeren no_fm-Liste bleibt die
Schleife ein no-op, sodass keine Dateien angefasst werden.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "adr" / "adr_fm_migrate.py"


def _load_module(tmp_path):
    findings = tmp_path / "findings.json"
    findings.write_text(
        json.dumps({"phase1": {"testrepo": {"no_fm": []}}}), encoding="utf-8"
    )
    old_argv = sys.argv
    sys.argv = ["adr_fm_migrate.py", "testrepo", str(findings)]
    try:
        spec = importlib.util.spec_from_file_location(
            "adr_fm_migrate_under_test", _SCRIPT
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["adr_fm_migrate_under_test"] = mod
        spec.loader.exec_module(mod)
    finally:
        sys.argv = old_argv
    return mod


def test_should_prefer_end_state_superseded_over_accepted(tmp_path):
    fm = _load_module(tmp_path)
    status, raw = fm.derive_status("**Status**: Accepted (superseded by ADR-99)")
    assert status == "superseded"


def test_should_prefer_end_state_rejected_over_proposed(tmp_path):
    fm = _load_module(tmp_path)
    status, raw = fm.derive_status("**Status**: Rejected (was Proposed)")
    assert status == "rejected"


def test_should_prefer_end_state_deprecated_over_draft(tmp_path):
    fm = _load_module(tmp_path)
    status, raw = fm.derive_status("**Status**: Draft (deprecated)")
    assert status == "deprecated"


def test_should_keep_simple_accepted_unchanged(tmp_path):
    fm = _load_module(tmp_path)
    status, raw = fm.derive_status("**Status**: Accepted")
    assert status == "accepted"


def test_should_keep_simple_proposed_unchanged(tmp_path):
    fm = _load_module(tmp_path)
    status, raw = fm.derive_status("**Status**: Proposed")
    assert status == "proposed"
