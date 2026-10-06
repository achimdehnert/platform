"""Tests fuer tools/blindstellen.py (Melder ueber PASS-Zellen ohne Pruefung).

Positivkontrolle in beide Richtungen (#2623): ein Runner mit bekannter Blindstelle
liefert genau diese, ein sauberer Runner liefert keine. Dazu die Selbstvalidierung:
null geparste record-Aufrufe sind ein Fehler, nie „alles sauber".
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import blindstellen  # noqa: E402


def _runner(tmp_path: Path, *zeilen: str) -> Path:
    datei = tmp_path / "session_start_checks.sh"
    datei.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return datei


def test_should_find_a_pass_whose_note_describes_a_skipped_check(tmp_path: Path):
    datei = _runner(
        tmp_path,
        'record "0.7.4 prio-referenzen" "PASS" "keine Prio-Liste im Handover — nichts zu pruefen"',
        'record "0.2 platform-sync" "PASS" "origin/main aktuell"',
    )
    treffer, gesamt = blindstellen.scan(datei)
    assert gesamt == 2
    assert [(t["zeile"], t["phase"]) for t in treffer] == [(1, "0.7.4 prio-referenzen")]


def test_should_report_nothing_for_a_runner_whose_passes_all_checked(tmp_path: Path):
    datei = _runner(
        tmp_path,
        'record "0.2 platform-sync" "PASS" "origin/main aktuell"',
        'record "0.7.11 erreichbarkeit" "PASS" "12 Hosts geprueft, alle 2xx/401"',
    )
    assert blindstellen.scan(datei) == ([], 2)


def test_should_ignore_skip_notes_that_are_not_labelled_pass(tmp_path: Path):
    """Ein ehrliches SKIP/WARN ist die Fix-Richtung, keine Blindstelle."""
    datei = _runner(
        tmp_path,
        'record "0.7.4 prio-referenzen" "SKIP" "keine Prio-Liste — nichts zu pruefen"',
        'record "0.7.9 gate-deckung" "WARN" "uebersprungen: Registry fehlt"',
    )
    assert blindstellen.scan(datei) == ([], 2)


def test_should_fail_loudly_when_no_record_call_parses(tmp_path: Path, capsys):
    datei = _runner(tmp_path, "#!/usr/bin/env bash", 'echo "kein record hier"')
    assert blindstellen.main(["--datei", str(datei)]) == 2
    assert "der Melder ist blind" in capsys.readouterr().err


def test_should_exit_zero_and_name_the_blind_spot_on_the_real_runner_shape(
    tmp_path: Path, capsys
):
    datei = _runner(
        tmp_path,
        'record "0.5.1 secret-zone" "PASS" "Drop-Zone leer"',
        'record "0.7.17 backup-deckung" "PASS" "ohne backup.yaml — by design"',
    )
    assert blindstellen.main(["--datei", str(datei)]) == 0
    out = capsys.readouterr().out
    assert "RESULT: BLINDSTELLEN — 1 von 2" in out
    assert "0.7.17 backup-deckung" in out
