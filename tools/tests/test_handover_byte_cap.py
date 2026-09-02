"""Tests für scripts/checks/handover_byte_cap.py (platform#2606, Stufe 1).

Der Deckel ist ein Gate — ein Gate, das nur grün gesehen wurde, ist nicht als Gate
belegt (dieselbe Lehre wie im Golden-Test von handover_append_only). Deshalb prüft
dieser Test beide Richtungen einzeln und zusätzlich, dass der reale Bestand ihn hält.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "checks" / "handover_byte_cap.py"
HANDOVER = REPO_ROOT / "AGENT_HANDOVER.md"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_should_pass_when_file_is_below_limit(tmp_path: Path) -> None:
    datei = tmp_path / "AGENT_HANDOVER.md"
    datei.write_bytes(b"x" * 100)
    ergebnis = _run(str(datei), "--limit", "200")
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "100 B / 200 B" in ergebnis.stdout


def test_should_fail_when_file_exceeds_limit(tmp_path: Path) -> None:
    datei = tmp_path / "AGENT_HANDOVER.md"
    datei.write_bytes(b"x" * 201)
    ergebnis = _run(str(datei), "--limit", "200")
    assert ergebnis.returncode == 1
    assert "Arbeitsstand, nicht Archiv" in ergebnis.stdout + ergebnis.stderr


def test_should_pass_exactly_at_the_limit(tmp_path: Path) -> None:
    """Der Deckel ist inklusiv — genau `limit` Byte sind erlaubt, `limit + 1` nicht."""
    datei = tmp_path / "AGENT_HANDOVER.md"
    datei.write_bytes(b"x" * 200)
    assert _run(str(datei), "--limit", "200").returncode == 0


def test_should_error_when_file_is_missing(tmp_path: Path) -> None:
    """Fehlender Pfad darf nicht grün sein — sonst schaltet ein Rename das Gate ab."""
    ergebnis = _run(str(tmp_path / "gibt-es-nicht.md"))
    assert ergebnis.returncode == 2
    assert "nicht gefunden" in ergebnis.stderr


def test_should_hold_the_real_handover_under_the_default_limit() -> None:
    """Positivkontrolle am echten Bestand: der Deckel gilt für die Datei, die er meint."""
    ergebnis = _run()
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
    assert HANDOVER.stat().st_size <= 20_000
