"""Rev 5 des Evidenz-Scanners — der vierte Rueckfall, und warum er durchkam.

platform#2673 schrieb in den PR-Body: „Der Escrow ist **ausgefuehrt**". Gesichert
war eine Datei, die per ``RESTIC_PASSWORD_FILE`` nur einen ZEIGER enthaelt, nicht
den Schluessel; 40 Minuten spaeter belegte #2675 genau das.

Die Retro (a6368d, Korrektur zu §5a) erklaerte den Durchlaeufer damit, dass ein
Werkzeug lief, aber die falsche Ebene belegte. Die Gegenprobe hier zeigt etwas
Einfacheres: der Satz traf VOR Rev 5 kein einziges ``CLAIM_PATTERN``, der
Body-Zweig feuerte also nie — die Korroboration kam gar nicht zum Zug. Der erste
Test haelt diese Messung fest; faellt er, deckt ein anderes Muster den Fall
bereits und Rev 5 gehoert geprueft statt verdoppelt.

Gegenprobe zu jedem Treffer: ein Satz derselben Bauart, der NICHT feuern darf.
Der Melder soll den Vollzug eines Wirkungsschritts fangen, nicht jede Statuszeile
eines Action Boards — dort ist „✅ Erledigt" eine Bucket-Ueberschrift.
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "evidence_claim_scanner.py"
_spec = importlib.util.spec_from_file_location("evidence_claim_scanner_r5", _QUELLE)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

REALFALL = "Der Escrow ist **ausgefuehrt**: die Zugangsdatei liegt gesichert."


# --- Die Messung, aus der Rev 5 folgt --------------------------------------


def test_should_zeigen_dass_kein_altes_muster_den_realfall_traf() -> None:
    getroffen = [label for pat, label in scanner.CLAIM_PATTERNS if pat.search(REALFALL)]
    assert getroffen == [], f"unerwartet getroffen: {getroffen}"


# --- Das neue Muster: Treffer und Nicht-Treffer nebeneinander --------------


def test_should_erkennen_vollzugs_claim_im_realfall() -> None:
    assert scanner.VOLLZUG_CLAIM_RE.search(REALFALL)


def test_should_erkennen_vollzug_in_beiden_reihenfolgen() -> None:
    assert scanner.VOLLZUG_CLAIM_RE.search("Die Rotation der Tokens ist abgeschlossen.")
    assert scanner.VOLLZUG_CLAIM_RE.search("Eingerichtet ist das Backup auf hetzner.")


def test_should_pr_status_ohne_wirkungsgegenstand_in_ruhe_lassen() -> None:
    assert not scanner.VOLLZUG_CLAIM_RE.search("Der PR ist erledigt, Review offen.")
    assert not scanner.VOLLZUG_CLAIM_RE.search("| 3 | Doku | platform | ✅ Erledigt |")


def test_should_ankuendigung_ohne_vollzugsverb_in_ruhe_lassen() -> None:
    assert not scanner.VOLLZUG_CLAIM_RE.search(
        "Das Backup-Konzept ist im Anhang beschrieben."
    )


def test_should_satzgrenze_achten() -> None:
    # Gegenstand und Verb muessen im SELBEN Satz stehen; sonst traefe das Muster
    # jeden Body, in dem irgendwo „Backup" und irgendwo „erledigt" vorkommt.
    assert not scanner.VOLLZUG_CLAIM_RE.search(
        "Wir sprechen ueber das Backup. Der Review ist erledigt."
    )


# --- Ende zu Ende durch main(): Positivkontrolle und Entwaffnung -----------


def _transcript(tmp_path, body: str, belegkommando: str, ergebnis: str) -> Path:
    """Ein Zug, der den Body publiziert und daneben ein Belegkommando faehrt."""
    p = tmp_path / "transcript_vollzug.jsonl"
    zeilen = [
        {"type": "user", "message": {"content": "mach das Escrow"}},
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
                        "input": {
                            "command": f"gh pr comment 2673 --body '{body}'",
                        },
                    },
                    {"type": "text", "text": "Kommentar ist raus."},
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


def test_should_block_vollzugs_claim_ohne_lesen_am_ziel(
    monkeypatch, capsys, tmp_path
) -> None:
    # POSITIVKONTROLLE: das Belegkommando arbeitet an der QUELLE (Pruefsumme einer
    # lokalen Datei) — genau das lief im Realfall und belegte die falsche Ebene.
    p = _transcript(
        tmp_path,
        REALFALL,
        "sha256sum /tmp/ablage/zugang.cfg",
        "9f2c…  /tmp/ablage/zugang.cfg",
    )
    _, ausgabe = _run(monkeypatch, capsys, tmp_path, p)
    assert "vollzugs-claim" in ausgabe, ausgabe


def test_should_vollzugs_claim_mit_lesen_am_ziel_durchlassen(
    monkeypatch, capsys, tmp_path
) -> None:
    # Gegenprobe: derselbe Body, aber im Turn wurde am ZIEL gelesen.
    p = _transcript(
        tmp_path,
        REALFALL,
        "gh api repos/achimdehnert/platform/actions/runs/1 --jq .conclusion",
        "completed/success",
    )
    _, ausgabe = _run(monkeypatch, capsys, tmp_path, p)
    assert "vollzugs-claim" not in ausgabe, ausgabe
