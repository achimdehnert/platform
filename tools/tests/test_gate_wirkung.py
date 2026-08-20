"""Drill fuer tools/gate_wirkung.py — das Rueckfall-Mass des Session-Loops.

Der wichtigste Test hier ist NICHT die Rueckfall-Erkennung, sondern die
Ehrlichkeits-Sperre: ein frisch gebautes Gate darf nicht als "wirksam" gelten,
nur weil hinter seinem Bau-Datum noch kaum Retros liegen. Ohne diesen Test waere
die Kennzahl durch blosses Neubauen von Gates steigerbar (Goodhart) — und damit
genau das Gegenteil dessen, wofuer sie gebaut wurde.

Run: `python3 -m pytest tools/tests/test_gate_wirkung.py -q`
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "gate_wirkung.py"
_spec = importlib.util.spec_from_file_location("gate_wirkung", _QUELLE)
gw = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gw)


def _retro(
    verzeichnis: Path, datum: str, kuerzel: str, slugs: list[str], inline: bool = True
) -> None:
    """Legt ein Retro mit `recurring_findings` an — inline oder als YAML-Block."""
    if inline:
        block = "recurring_findings: [" + ", ".join(slugs) + "]"
    else:
        block = "recurring_findings:\n" + "".join(f"  - {s}\n" for s in slugs).rstrip()
    (verzeichnis / f"session-retro-{datum}-platform-{kuerzel}.md").write_text(
        f"---\nretro_schema: 1\ndate: {datum}\n{block}\n---\n\n# Retro\n",
        encoding="utf-8",
    )


def _urteile(verzeichnis: Path, gates: list[dict]) -> dict[str, dict]:
    retros = gw.lies_retros([str(verzeichnis)])
    return {e["slug"]: e for e in gw.bewerte(gates, retros)}


def test_should_mark_gate_rueckfaellig_when_finding_recurs_after_build(tmp_path):
    for i, tag in enumerate(["10", "11", "12"]):
        _retro(tmp_path, f"2026-07-{tag}", f"a{i}", ["schludrigkeit"])
    urteile = _urteile(
        tmp_path, [{"slug": "schludrigkeit", "mode": "blocking", "built": "2026-07-01"}]
    )

    assert urteile["schludrigkeit"]["urteil"] == "RUECKFAELLIG"
    assert urteile["schludrigkeit"]["nachher"] == 3
    assert urteile["schludrigkeit"]["letzter_rueckfall"] == "2026-07-12"


def test_should_not_call_fresh_gate_wirksam_before_min_fenster(tmp_path):
    """Die Ehrlichkeits-Sperre: zu wenig Retros seit Bau ⇒ 'zu-frueh', nie 'wirksam'."""
    _retro(tmp_path, "2026-07-01", "alt", ["schludrigkeit"])
    _retro(tmp_path, "2026-07-02", "alt2", ["schludrigkeit"])
    # genau EIN Retro nach dem Bau-Datum — unter MIN_FENSTER
    _retro(tmp_path, "2026-07-20", "neu", ["anderes"])
    urteile = _urteile(
        tmp_path, [{"slug": "schludrigkeit", "mode": "blocking", "built": "2026-07-10"}]
    )

    assert gw.MIN_FENSTER > 1, "Sperre ist wirkungslos, wenn ein einziges Retro genuegt"
    assert urteile["schludrigkeit"]["urteil"] == "zu-frueh"
    assert urteile["schludrigkeit"]["vorher"] == 2


def test_should_call_gate_wirksam_only_with_before_after_evidence(tmp_path):
    _retro(tmp_path, "2026-07-01", "a", ["schludrigkeit"])
    _retro(tmp_path, "2026-07-02", "b", ["schludrigkeit"])
    for i, tag in enumerate(["20", "21", "22"]):
        _retro(tmp_path, f"2026-07-{tag}", f"c{i}", ["anderes"])
    urteile = _urteile(
        tmp_path, [{"slug": "schludrigkeit", "mode": "blocking", "built": "2026-07-10"}]
    )

    assert urteile["schludrigkeit"]["urteil"] == "wirksam"
    assert urteile["schludrigkeit"]["vorher_messbar"] is True


def test_should_flag_missing_before_window_for_gate_older_than_data(tmp_path):
    """Gate aelter als das aelteste Retro ⇒ 'vorher' ist Datenfenster-Ende, kein Messwert."""
    for i, tag in enumerate(["10", "11", "12"]):
        _retro(tmp_path, f"2026-07-{tag}", f"a{i}", ["anderes"])
    urteile = _urteile(
        tmp_path, [{"slug": "uralt", "mode": "process", "built": "2026-01-01"}]
    )

    assert urteile["uralt"]["vorher_messbar"] is False
    assert urteile["uralt"]["urteil"] == "kein-vorher-fenster"


def test_should_read_recurring_findings_from_block_and_inline_form(tmp_path):
    _retro(tmp_path, "2026-07-10", "inline", ["a-slug", "b-slug"], inline=True)
    _retro(tmp_path, "2026-07-11", "block", ["a-slug"], inline=False)
    retros = gw.lies_retros([str(tmp_path)])

    assert sorted(slugs for _, slugs, _ in retros) == [["a-slug"], ["a-slug", "b-slug"]]


def test_should_ignore_extern_briefings(tmp_path):
    _retro(tmp_path, "2026-07-10", "echt", ["a-slug"])
    (tmp_path / "session-retro-2026-07-11-extern-platform-x.md").write_text(
        "---\nrecurring_findings: [a-slug]\n---\n", encoding="utf-8"
    )
    assert len(gw.lies_retros([str(tmp_path)])) == 1


def test_should_print_nothing_in_kurz_mode_without_rueckfall(tmp_path):
    """Der Runner darf keine Zeile bekommen, wenn es nichts zu melden gibt."""
    for i, tag in enumerate(["10", "11", "12"]):
        _retro(tmp_path, f"2026-07-{tag}", f"a{i}", ["anderes"])
    registry = tmp_path / "reg.json"
    registry.write_text(
        json.dumps(
            {"gates": [{"slug": "ruhig", "mode": "advisory", "built": "2026-07-01"}]}
        ),
        encoding="utf-8",
    )
    lauf = subprocess.run(
        [
            sys.executable,
            str(_QUELLE),
            "--kurz",
            "--registry",
            str(registry),
            "--dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert lauf.returncode == 0
    assert lauf.stdout.strip() == ""


def test_should_stay_exit_zero_on_unreadable_registry(tmp_path):
    """Fail-open: ein Melder, der den Sitzungsstart aufhaelt, wird abgeschaltet."""
    lauf = subprocess.run(
        [
            sys.executable,
            str(_QUELLE),
            "--kurz",
            "--registry",
            str(tmp_path / "gibtsnicht.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert lauf.returncode == 0
    assert lauf.stdout.strip() == ""
