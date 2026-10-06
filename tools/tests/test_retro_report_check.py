"""Tests für tools/retro_report_check.py.

Traegt zugleich den Pruefer in die CI: `--alle` laeuft ueber jeden Report ab
`GILT_AB`, und `tools/tests/` ist ein Required Check. Ein Retro-Report, der die
Eiserne Regel 5 verletzt, faellt damit im PR auf statt erst in der naechsten
Laengsschnitt-Auswertung.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from retro_report_check import GILT_AB, SPALTEN, datum_aus_name, pruefe  # noqa: E402

SAUBER = f"""---
findings_total: 3
refuted_rate: 0.1
pre_refuted: 0
over_ask_klassen: []
over_act_klassen: []
gate_candidates: [foo]
streichkandidaten: [bar]
---

# Retro

## 2. Befund-Tabelle
{SPALTEN}
|---|---|---|---|---|---|---|

## 8. Nicht verifiziert

**Getan:** x. **Angenommen:** y. **Nicht verifizierbar:** z. **Offen geblieben:** w.
"""


def test_should_pass_a_conforming_report():
    assert pruefe(SAUBER) == []


def test_should_flag_missing_coverage_statement():
    """Eiserne Regel 5 — der Realfall aus 5 von 16 Reports seit 2026-09-02."""
    ohne = SAUBER.replace(
        "**Getan:** x. **Angenommen:** y. **Nicht verifizierbar:** z. "
        "**Offen geblieben:** w.",
        "Ein paar Restluecken in Prosa.",
    )
    befunde = pruefe(ohne)
    assert any("Eiserne Regel 5" in b for b in befunde)


def test_should_flag_missing_section_eight():
    befunde = pruefe(SAUBER.replace("## 8. Nicht verifiziert", "## Restliches"))
    assert any("## 8" in b for b in befunde)


def test_should_flag_broken_frozen_columns():
    befunde = pruefe(SAUBER.replace(SPALTEN, "| Befund | Beleg |"))
    assert any("eingefrorenen Spalten" in b for b in befunde)


def test_should_flag_missing_frontmatter_field():
    befunde = pruefe(SAUBER.replace("refuted_rate: 0.1\n", ""))
    assert any("refuted_rate" in b for b in befunde)


def test_should_flag_empty_streichkandidaten_without_reason():
    """Phase 7: 'keiner' braucht den Grund-Satz, nicht nur das Wort."""
    befunde = pruefe(
        SAUBER.replace("streichkandidaten: [bar]", "streichkandidaten: []")
    )
    assert any("streich_begruendung" in b for b in befunde)


def test_should_allow_empty_streichkandidaten_with_reason():
    """Gegenprobe — mit Grund ist leer ausdruecklich erlaubt."""
    mit = SAUBER.replace(
        "streichkandidaten: [bar]",
        "streichkandidaten: []\nstreich_begruendung: keiner, weil nichts ohne Leser lief",
    )
    assert pruefe(mit) == []


def test_should_read_date_from_filename():
    assert (
        datum_aus_name(Path("session-retro-2026-09-16-platform-abc123.md"))
        == "2026-09-16"
    )
    assert datum_aus_name(Path("irgendwas.md")) is None


def test_should_be_green_on_every_report_in_scope():
    """Der eigentliche Traeger: laeuft in CI ueber alle Reports ab GILT_AB.

    Die fuenf gemessenen Altluecken (vor {gilt}) sind bewusst ausserhalb —
    ein Pruefer, der beim ersten Lauf Altlasten meldet, wird abgeschaltet
    statt befolgt.
    """
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "retro_report_check.py"), "--alle"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_baseline_is_documented_not_silently_skipped():
    """Die Grenze steht als Konstante da, nicht als stille Annahme."""
    assert GILT_AB == "2026-09-16"
