"""Drill fuer lint_blind_verification.

Ein Gate, das nur gruen kennt, belegt nichts — deshalb prueft der Drill beide
Richtungen: es MUSS die Falle finden UND die sichere Form in Ruhe lassen.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "lint_blind_verification", ROOT / "tools" / "lint_blind_verification.py"
)
lint = importlib.util.module_from_spec(_spec)
sys.modules["lint_blind_verification"] = lint
_spec.loader.exec_module(lint)

FALLE = '''#!/usr/bin/env bash
set -euo pipefail
git fetch --dry-run 2>&1 | grep -qi 'moved\\|redirect' && warnen
tar -tzf "$RAW" | grep -qx "$muss" || abbruch
'''

SICHER = '''#!/usr/bin/env bash
set -euo pipefail
LISTE="$(tar -tzf "$RAW")"
grep -qxF "$muss" <<<"$LISTE" || abbruch
git fetch --dry-run >/dev/null 2>&1 || abbruch
# git fetch | grep -q moved   <- nur ein Kommentar, kein Fund
'''


@pytest.mark.f1
def test_should_find_both_pipeline_greps(tmp_path):
    f = tmp_path / "falle.sh"
    f.write_text(FALLE, encoding="utf-8")
    assert len(lint.pruefe(f)) == 2


@pytest.mark.f1
def test_should_ignore_herestring_and_exit_code_form(tmp_path):
    f = tmp_path / "sicher.sh"
    f.write_text(SICHER, encoding="utf-8")
    assert lint.pruefe(f) == []


@pytest.mark.f3
def test_should_exit_nonzero_only_in_strict_mode(tmp_path, capsys):
    f = tmp_path / "falle.sh"
    f.write_text(FALLE, encoding="utf-8")
    assert lint.main([str(f)]) == 0
    assert lint.main([str(f), "--strict"]) == 1


@pytest.mark.f2
@pytest.mark.parametrize("zeile, erwartet", [
    ("cmd | grep -q x", 1),
    ("cmd | grep -qi x", 1),
    ("cmd | grep -c x", 0),
    ("grep -q x datei", 0),
])
def test_should_match_only_piped_quiet_greps(tmp_path, zeile, erwartet):
    f = tmp_path / "p.sh"
    f.write_text("#!/bin/bash\n" + zeile + "\n", encoding="utf-8")
    assert len(lint.pruefe(f)) == erwartet
