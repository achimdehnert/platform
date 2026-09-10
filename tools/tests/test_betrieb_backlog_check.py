"""K4 (#3015): Backlog-Vorschlag ohne Gegenrede und Alternative wird abgewiesen.

`test_should_keep_shipped_betriebsakten_clean` laeuft gegen die echten Akten
im Repo (Exit 0 erwartet) — der Test macht `pytest tools/tests/` zum
Required-Check-Gate fuer K4: eine neue Backlog-Zeile ohne Gegenrede faellt
sofort in CI durch, nicht erst beim naechsten Lesen.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "betrieb_backlog_check.py"
WURZEL = Path(__file__).resolve().parents[2]


def _run(*args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True,
        text=True,
        timeout=600,
    )


def _akte(
    tmp_path: Path,
    tabellenzeilen: str,
    ueberschrift: str = "## Verbesserungs-Backlog (K4)",
) -> Path:
    pfad = tmp_path / "akte.md"
    pfad.write_text(
        textwrap.dedent(
            f"""\
            # Testakte

            {ueberschrift}

            | # | Vorschlag | Advocatus Diaboli | Out of the Box | Anker |
            |---|---|---|---|---|
            {tabellenzeilen}
            """
        ),
        encoding="utf-8",
    )
    return pfad


# ── Der echte Stand: Gate fuer CI ───────────────────────────────────────────


def test_should_keep_shipped_betriebsakten_clean():
    r = _run(
        str(WURZEL / "docs/betrieb/mailcheck.md"),
        str(WURZEL / "docs/betrieb/todo-liste.md"),
        "--block",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert ", 0 Maengel" in r.stdout


# ── Gegenproben: wird er rot, wenn er rot werden muss? ──────────────────────


def test_should_flag_missing_advocatus_diaboli(tmp_path):
    zeile = "| 1 | Idee X | zu kurz | Eine ausreichend lange Alternative aus einer ganz anderen Richtung | offen |"
    akte = _akte(tmp_path, zeile)
    r = _run(str(akte), "--block")
    assert r.returncode == 1
    assert "Advocatus Diaboli" in r.stdout


def test_should_flag_too_short_out_of_the_box(tmp_path):
    zeile = "| 1 | Idee X | Eine ausreichend lange Gegenrede aus einer ganz anderen Richtung | zu kurz | offen |"
    akte = _akte(tmp_path, zeile)
    r = _run(str(akte), "--block")
    assert r.returncode == 1
    assert "Out of the Box" in r.stdout


def test_should_flag_table_without_required_columns(tmp_path):
    pfad = tmp_path / "akte.md"
    pfad.write_text(
        textwrap.dedent(
            """\
            # Testakte

            ## Verbesserungs-Backlog (K4)

            | # | Vorschlag | Kommentar |
            |---|---|---|
            | 1 | Idee X | irgendwas |
            """
        ),
        encoding="utf-8",
    )
    r = _run(str(pfad))
    assert "Backlog-Tabelle ohne Pflichtspalten" in r.stdout


def test_should_pass_complete_row_with_zero_findings(tmp_path):
    zeile = (
        "| 1 | Idee X | Eine ausreichend lange Gegenrede aus einer ganz anderen Richtung "
        "| Eine ausreichend lange Alternative aus einer ganz anderen Richtung | #123 |"
    )
    akte = _akte(tmp_path, zeile)
    r = _run(str(akte), "--block")
    assert r.returncode == 0
    assert "0 Maengel" in r.stdout


def test_should_report_counters_as_json(tmp_path):
    zeile = (
        "| 1 | Idee X | Eine ausreichend lange Gegenrede aus einer ganz anderen Richtung "
        "| Eine ausreichend lange Alternative aus einer ganz anderen Richtung | gebaut, PR #123 |"
    )
    akte = _akte(tmp_path, zeile)
    r = _run(str(akte), "--json")
    daten = json.loads(r.stdout)
    assert daten["vorschlaege"] == 1
    assert daten["maengel"] == 0
    assert daten["gebaut"] == 1
