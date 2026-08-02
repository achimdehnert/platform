"""Mutationstest fuer den Baseline-Modus von scripts/checks/run_all.sh (ADR-210).

Warum dieser Test existiert
---------------------------
Am 2026-08-01 fielen auf dem Prod-Runner **7 von 8** Staging-Checks; die
Gesamt-Conclusion war `success`, weil jeder Job `continue-on-error: true` trug.
Das war eine bewusste Wahl (Header des Workflows: "sichtbar, nicht blockierend"),
hatte aber eine Luecke: **bei sieben dauerhaft roten Jobs ist ein achter, NEUER
Fehlschlag nicht unterscheidbar.**

Der Baseline-Modus schliesst genau das. Er ist damit selbst ein Gate — und nach
ADR-291 gilt: kein Gate ohne bewiesene Rot-Faehigkeit. Die Faelle unten decken
beide Richtungen ab (duldet Bekanntes / faellt bei Neuem), weil ein Gate, das nur
duldet, dasselbe Nichts aussagt wie `continue-on-error`.

Gearbeitet wird auf Mini-Checks in tmp_path, nicht auf den echten acht: die
brauchen SSH zu dev-desktop/staging-platform/prod und waeren weder schnell noch
deterministisch.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ECHT = REPO / "scripts" / "checks" / "run_all.sh"

EXIT_OK = 0
EXIT_REGRESSION = 1
EXIT_BEDIENFEHLER = 2

NAMEN = ("staging_a.sh", "staging_b.sh", "staging_c.sh")


@pytest.fixture
def umgebung(tmp_path: Path) -> Path:
    """run_all.sh mit auf drei Mini-Checks umgestellter CHECKS-Liste."""
    checks = tmp_path / "checks"
    checks.mkdir()
    for n in NAMEN:
        _setze(checks, n, erfolg=True)

    quelle = ECHT.read_text(encoding="utf-8")
    start = quelle.index("CHECKS=(")
    ende = quelle.index(")", start) + 1
    ersatz = "CHECKS=(\n  " + "\n  ".join(NAMEN) + "\n)"
    (checks / "run_all.sh").write_text(quelle[:start] + ersatz + quelle[ende:])
    return checks


def _setze(checks: Path, name: str, *, erfolg: bool) -> None:
    (checks / name).write_text(f"#!/bin/bash\nexit {0 if erfolg else 1}\n")


def _fahre(
    checks: Path, baseline: Path | str | None
) -> subprocess.CompletedProcess[str]:
    cmd = ["bash", str(checks / "run_all.sh")]
    if baseline is not None:
        cmd += ["--baseline", str(baseline)]
    return subprocess.run(cmd, cwd=checks, capture_output=True, text=True)


def _baseline(tmp_path: Path, *namen: str) -> Path:
    p = tmp_path / "baseline.txt"
    p.write_text("# Testfixture\n" + "".join(f"{n}\n" for n in namen))
    return p


def test_should_pass_when_all_green(umgebung: Path, tmp_path: Path) -> None:
    """Kontrollgruppe — ohne sie sagt kein einziger Rot-Fall etwas aus."""
    e = _fahre(umgebung, _baseline(tmp_path))
    assert e.returncode == EXIT_OK, e.stdout


def test_should_tolerate_failure_listed_in_baseline(
    umgebung: Path, tmp_path: Path
) -> None:
    _setze(umgebung, "staging_b.sh", erfolg=False)
    e = _fahre(umgebung, _baseline(tmp_path, "staging_b.sh"))
    assert e.returncode == EXIT_OK, e.stdout
    assert "keine Regression" in e.stdout


def test_should_fail_on_regression_outside_baseline(
    umgebung: Path, tmp_path: Path
) -> None:
    """DER Zielfall: ein Check faellt, der in der Baseline gruen war."""
    _setze(umgebung, "staging_c.sh", erfolg=False)
    e = _fahre(umgebung, _baseline(tmp_path, "staging_b.sh"))
    assert e.returncode == EXIT_REGRESSION, e.stdout
    assert "staging_c.sh" in e.stdout
    assert "REGRESSION" in e.stdout


def test_should_report_regression_even_when_baseline_entry_also_fails(
    umgebung: Path, tmp_path: Path
) -> None:
    """Ein neuer Fehlschlag darf nicht im Rauschen der geduldeten untergehen —
    das ist der Ausgangsbefund (7 rote Jobs, achter unsichtbar)."""
    _setze(umgebung, "staging_b.sh", erfolg=False)
    _setze(umgebung, "staging_c.sh", erfolg=False)
    e = _fahre(umgebung, _baseline(tmp_path, "staging_b.sh"))
    assert e.returncode == EXIT_REGRESSION, e.stdout
    assert "staging_c.sh" in e.stdout


def test_should_report_recovered_entries_so_baseline_can_shrink(
    umgebung: Path, tmp_path: Path
) -> None:
    """Ohne diese Meldung veraltet die Baseline still und wird zum Freibrief."""
    e = _fahre(umgebung, _baseline(tmp_path, "staging_b.sh"))
    assert "behoben" in e.stdout
    assert "staging_b.sh" in e.stdout


def test_should_report_operator_error_for_missing_baseline(umgebung: Path) -> None:
    """Bedienfehler bekommt einen EIGENEN Wert — nie als Regression getarnt."""
    e = _fahre(umgebung, "/gibt/es/nicht")
    assert e.returncode == EXIT_BEDIENFEHLER, e.stdout + e.stderr


def test_should_keep_old_behaviour_without_baseline(
    umgebung: Path, tmp_path: Path
) -> None:
    """Ohne --baseline bleibt jeder Fehlschlag hartes Rot (Rueckwaertskompatibel)."""
    _setze(umgebung, "staging_a.sh", erfolg=False)
    e = _fahre(umgebung, None)
    assert e.returncode == EXIT_REGRESSION, e.stdout
