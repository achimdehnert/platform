"""Rev 9 des Evidenz-Scanners (Retro 7d2e16 §5a, platform#3283).

Zwei Arten, beide advisory bis zum Ende des Kalibrierfensters:

(1) UNPRUEFBAR-CLAIM — der Scanner sah nur Erfolgs-Behauptungen. Realfall
    writing-hub PR #1201: „Rasterbilder, nicht pruefbar" ohne gescheiterten Versuch
    im Turn. Der ehrliche Satz nennt den billigsten Check und bleibt still.
(2) FREMDPRUEFUNGS-CLAIM — deckt `self-review-presented-as-review`. Realfall
    writing-hub#1181 K4: „gegengeprueft", 44 von 51 vom Erzeuger selbst. Ein zweiter
    Kontext (Agent/Task/Workflow, claude -p, headless_run) im Turn entwaffnet.

Der erste Test haelt die Messung fest, aus der Rev 9 folgt: kein CLAIM_PATTERN traf
den #1201-Satz — der Hook feuerte an jenem Tag auf einen anderen Satz.
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "evidence_claim_scanner.py"
_spec = importlib.util.spec_from_file_location("evidence_claim_scanner_r9", _QUELLE)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

#: PR-Body writing-hub#1201 (2026-09-16), auf den Satz gekuerzt.
REALFALL_1201 = (
    "Zum „Bild mit Rechtschreibfehlern (S1)“: alle 261 Wörter der 23 gezeichneten "
    "Diagramme geprüft — keiner. Vermutlich eine der fünf Buchabbildungen aus Termin 1 "
    "(Rasterbilder, nicht prüfbar) — bitte Vorlesung und Folie nennen."
)
EHRLICHE_FORM = (
    "K5 von außen nicht verifiziert — billigster Check ist ein Login-Abruf der "
    "Modulseite; ohne Zugang lässt sich der Prod-Stand nicht prüfen."
)
FREMDPRUEFUNG_BODY = (
    "Wie geprüft: jede Seitenangabe wurde am Chunk gegengeprüft (fremder Blick), "
    "51 von 51 halten."
)
OFFENGELEGT_BODY = (
    "Lücke: dass die Aussage auf der zitierten Seite steht, ist für 44 von 51 "
    "Vorschlägen nur von den Agenten selbst geprüft."
)


# --- Die Messung, aus der Rev 9 folgt --------------------------------------


def test_should_zeigen_dass_kein_altes_muster_den_1201_satz_traf() -> None:
    getroffen = [
        lab
        for pat, lab in scanner.CLAIM_PATTERNS
        if pat.search("(Rasterbilder, nicht prüfbar)")
    ]
    assert getroffen == [], getroffen


# --- Reine Funktionen ------------------------------------------------------


def test_should_unpruefbar_satz_ohne_check_finden() -> None:
    """POSITIVKONTROLLE am Realfall."""
    satz = scanner._unpruefbar_ungehedgt(REALFALL_1201)
    assert "nicht prüfbar" in satz, satz


def test_should_satz_mit_benanntem_check_durchlassen() -> None:
    """NEGATIVKONTROLLE: die ehrliche Form nennt den billigsten Check."""
    assert scanner._unpruefbar_ungehedgt(EHRLICHE_FORM) == ""


def test_should_fehlversuch_im_turn_erkennen() -> None:
    assert scanner.FEHLVERSUCH_RE.search("HTTP 302 → Login")
    assert scanner.FEHLVERSUCH_RE.search("curl: (7) Connection refused")
    assert not scanner.FEHLVERSUCH_RE.search("29 passed in 72.44s")


def test_should_fremdpruefung_nur_bei_behauptung_treffen() -> None:
    assert scanner.FREMDPRUEFUNG_CLAIM_RE.search(FREMDPRUEFUNG_BODY)
    assert not scanner.FREMDPRUEFUNG_CLAIM_RE.search(OFFENGELEGT_BODY), (
        "Offenlegung ist keine Behauptung"
    )


def test_should_zweiten_kontext_an_agent_oder_headless_erkennen() -> None:
    assert scanner._zweiter_kontext_lief([("Agent", {"prompt": "prüfe"})], "")
    assert scanner._zweiter_kontext_lief([], "claude -p 'prüfe Seite 141'")
    assert not scanner._zweiter_kontext_lief(
        [("Bash", {"command": "gh pr view 1187"})], "gh pr view"
    )


# --- Ende zu Ende durch main() ---------------------------------------------


def _transcript(
    tmp_path,
    *,
    body: str = "",
    text: str = "",
    tool_result: str = "",
    agent: bool = False,
) -> Path:
    p = tmp_path / "transcript_r9.jsonl"
    content = [
        {
            "type": "tool_use",
            "name": "Bash",
            "id": "b1",
            "input": {"command": "gh pr view 1201"},
        }
    ]
    if agent:
        content.append(
            {
                "type": "tool_use",
                "name": "Agent",
                "id": "a1",
                "input": {"prompt": "prüfe Seite 141 im Chunk"},
            }
        )
    if body:
        content.append(
            {
                "type": "tool_use",
                "name": "Bash",
                "id": "b2",
                "input": {"command": f"gh pr comment 1201 --body '{body}'"},
            }
        )
    content.append({"type": "text", "text": text or "Erledigt."})
    zeilen = [
        {"type": "user", "message": {"content": "prüfe das Bild"}},
        {"type": "assistant", "message": {"content": content}},
        {
            "type": "user",
            "message": {
                "content": [{"type": "tool_result", "content": tool_result or "ok"}]
            },
        },
    ]
    p.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


def _run(monkeypatch, capsys, tmp_path, pfad: Path) -> str:
    monkeypatch.setenv("EVIDENCE_SCANNER_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"transcript_path": str(pfad)}))
    )
    scanner.main()
    out = capsys.readouterr()
    return out.out + out.err


def test_should_unpruefbar_claim_im_body_ohne_fehlversuch_melden(
    monkeypatch, capsys, tmp_path
) -> None:
    """POSITIVKONTROLLE Ende zu Ende am Realfall #1201."""
    ausgabe = _run(
        monkeypatch, capsys, tmp_path, _transcript(tmp_path, body=REALFALL_1201)
    )
    assert "unpruefbar-claim" in ausgabe, ausgabe


def test_should_unpruefbar_claim_bei_fehlversuch_im_turn_schweigen(
    monkeypatch, capsys, tmp_path
) -> None:
    ausgabe = _run(
        monkeypatch,
        capsys,
        tmp_path,
        _transcript(tmp_path, body=REALFALL_1201, tool_result="HTTP 302 → /login/"),
    )
    assert "unpruefbar-claim" not in ausgabe, ausgabe


def test_should_unpruefbar_claim_im_chat_mit_benanntem_check_schweigen(
    monkeypatch, capsys, tmp_path
) -> None:
    ausgabe = _run(
        monkeypatch, capsys, tmp_path, _transcript(tmp_path, text=EHRLICHE_FORM)
    )
    assert "unpruefbar-claim" not in ausgabe, ausgabe


def test_should_unpruefbar_claim_nie_blocken(monkeypatch, capsys, tmp_path) -> None:
    """Advisory-Sonderweg: Warnzeile, kein Block — auch im blocking-Mode."""
    monkeypatch.setenv("EVIDENCE_SCANNER_MODE", "blocking")
    ausgabe = _run(
        monkeypatch, capsys, tmp_path, _transcript(tmp_path, body=REALFALL_1201)
    )
    assert "unpruefbar-claim" in ausgabe and '"decision": "block"' not in ausgabe, (
        ausgabe
    )


def test_should_fremdpruefung_ohne_zweiten_kontext_melden(
    monkeypatch, capsys, tmp_path
) -> None:
    ausgabe = _run(
        monkeypatch, capsys, tmp_path, _transcript(tmp_path, body=FREMDPRUEFUNG_BODY)
    )
    assert "fremdpruefungs-claim" in ausgabe, ausgabe


def test_should_fremdpruefung_mit_agent_im_turn_durchlassen(
    monkeypatch, capsys, tmp_path
) -> None:
    ausgabe = _run(
        monkeypatch,
        capsys,
        tmp_path,
        _transcript(tmp_path, body=FREMDPRUEFUNG_BODY, agent=True),
    )
    assert "fremdpruefungs-claim" not in ausgabe, ausgabe


def test_should_offengelegte_selbstpruefung_durchlassen(
    monkeypatch, capsys, tmp_path
) -> None:
    ausgabe = _run(
        monkeypatch, capsys, tmp_path, _transcript(tmp_path, body=OFFENGELEGT_BODY)
    )
    assert "fremdpruefungs-claim" not in ausgabe, ausgabe
