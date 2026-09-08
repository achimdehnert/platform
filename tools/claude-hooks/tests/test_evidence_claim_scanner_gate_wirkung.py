"""Rev 7 des Evidenz-Scanners — der fuenfte Rueckfall: Wirkung statt Vollzug.

platform#2954 schrieb in den PR-Body: „ein Gate erzwingt, dass sie stattgefunden
hat". Der Job war gebaut, er lief, und am Drill-PR #2955 wurde er auch wirklich
rot. Er stand nur nicht in ``required_status_checks`` des Rulesets — ein roter
Check, der nicht required ist, blockiert keinen Merge.

Das ist die Falle, gegen die Rev 7 gebaut ist: der Turn war voll von Belegen (ein
CI-Lauf, ein roter Check, gruene Tests), sie belegten nur alle dieselbe Sache —
dass der Check FEUERT. Dass er SPERRT, belegt allein das Ruleset. Deshalb hat
diese Art eine eigene, engere Korroboration und nicht ``BODY_EVIDENCE_TOKENS``.

Der erste Test haelt die Messung fest, aus der Rev 7 folgt: vor Rev 7 traf kein
vorhandenes Muster den Satz. Faellt er, deckt eine andere Art den Fall bereits
und Rev 7 gehoert geprueft statt verdoppelt.

Gegenprobe zu jedem Treffer: ein Satz derselben Bauart, der NICHT feuern darf.
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "evidence_claim_scanner.py"
_spec = importlib.util.spec_from_file_location("evidence_claim_scanner_r7", _QUELLE)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

REALFALL = (
    "Die Vergabe laeuft deshalb als letzter Schritt vor dem Merge, ausgeloest vom "
    "Autor, und ein Gate erzwingt, dass sie stattgefunden hat."
)


# --- Die Messung, aus der Rev 7 folgt --------------------------------------


def test_should_zeigen_dass_kein_altes_muster_den_realfall_traf() -> None:
    getroffen = [label for pat, label in scanner.CLAIM_PATTERNS if pat.search(REALFALL)]
    assert getroffen == [], f"unerwartet getroffen: {getroffen}"


def test_should_zeigen_dass_der_vollzugs_claim_den_realfall_nicht_traf() -> None:
    assert not scanner.VOLLZUG_CLAIM_RE.search(REALFALL)


# --- Das neue Muster: Treffer und Nicht-Treffer nebeneinander --------------


def test_should_erkennen_wirkungs_claim_im_realfall() -> None:
    assert scanner.GATE_WIRKUNG_CLAIM_RE.search(REALFALL)


def test_should_erkennen_wirkung_in_beiden_reihenfolgen() -> None:
    assert scanner.GATE_WIRKUNG_CLAIM_RE.search(
        "Der neue Check blockiert den Merge, solange die Nummer fehlt."
    )
    assert scanner.GATE_WIRKUNG_CLAIM_RE.search(
        "Gesperrt wird der Merge kuenftig von diesem Workflow."
    )


def test_should_reinen_laufstatus_ohne_wirkungsverb_in_ruhe_lassen() -> None:
    assert not scanner.GATE_WIRKUNG_CLAIM_RE.search(
        "Der Check ist gruen, der Lauf dauerte 40 Sekunden."
    )
    assert not scanner.GATE_WIRKUNG_CLAIM_RE.search(
        "| 3 | Gate gebaut | platform | #2954 | erledigt | mergen (du) |"
    )


def test_should_wirkungsverb_ohne_gate_subjekt_in_ruhe_lassen() -> None:
    assert not scanner.GATE_WIRKUNG_CLAIM_RE.search(
        "Der Konflikt blockiert den Merge, bis er aufgeloest ist."
    )


# --- Die Korroboration: nur die Regel-Ebene entwaffnet ---------------------


def test_should_von_einem_ruleset_lesen_entwaffnet_werden() -> None:
    for kommando in (
        "gh api repos/achimdehnert/platform/rules/branches/main",
        "gh api repos/o/r/rulesets --jq '.[].name'",
        "gh api repos/o/r/branches/main/protection",
    ):
        assert scanner.RULESET_READ_RE.search(kommando), kommando


def test_should_von_einem_bloßen_lauf_beleg_nicht_entwaffnet_werden() -> None:
    """Der Kern der Rev: genau diese Kommandos liefen im Realfall."""
    for kommando in (
        "gh pr checks 2955",
        "gh run list --branch main --limit 5",
        "make test",
        "gh run view 30712345678 --log-failed",
    ):
        assert not scanner.RULESET_READ_RE.search(kommando), kommando


# --- Ende zu Ende durch main(): Positivkontrolle und Entwaffnung -----------


def _transcript(tmp_path, body: str, belegkommando: str, ergebnis: str) -> Path:
    """Ein Zug, der den Body publiziert und daneben ein Belegkommando faehrt."""
    p = tmp_path / "transcript_gate_wirkung.jsonl"
    zeilen = [
        {"type": "user", "message": {"content": "bau das ADR-Gate"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": "b1",
                        "input": {"command": belegkommando},
                    },
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": "b2",
                        "input": {"command": f"gh pr create --title x --body '{body}'"},
                    },
                    {"type": "text", "text": "PR ist offen."},
                ]
            },
        },
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": ergebnis}]},
        },
    ]
    p.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


def _run(monkeypatch, capsys, tmp_path, pfad: Path):
    monkeypatch.setenv("EVIDENCE_SCANNER_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"transcript_path": str(pfad)}))
    )
    rc = scanner.main()
    out = capsys.readouterr()
    return rc, out.out + out.err


def test_should_wirkungs_claim_ohne_ruleset_lesen_melden(
    monkeypatch, capsys, tmp_path
) -> None:
    """POSITIVKONTROLLE: genau der Beleg aus dem Realfall — ein roter Check."""
    p = _transcript(
        tmp_path,
        REALFALL,
        "gh pr checks 2955",
        "ADR Schema Validation\tfail\t18s",
    )
    _, ausgabe = _run(monkeypatch, capsys, tmp_path, p)
    assert "gate-wirkungs-claim" in ausgabe, ausgabe


def test_should_wirkungs_claim_mit_ruleset_lesen_durchlassen(
    monkeypatch, capsys, tmp_path
) -> None:
    """Gegenprobe: derselbe Body, aber die Regel-Ebene wurde gelesen."""
    p = _transcript(
        tmp_path,
        REALFALL,
        "gh api repos/achimdehnert/platform/rules/branches/main",
        '[{"type":"required_status_checks","parameters":{"required_status_checks":[]}}]',
    )
    _, ausgabe = _run(monkeypatch, capsys, tmp_path, p)
    assert "gate-wirkungs-claim" not in ausgabe, ausgabe
