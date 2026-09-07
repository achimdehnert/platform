"""Rev 6 des Evidenz-Scanners — Mail-Entwuerfe fallen durch jede Body-Extraktion.

Realfall 2026-09-07: ein Mail-Entwurf an einen Studierenden behauptete "At 22
pages and roughly 7,800 words"; `pdfinfo` sagte 23 Seiten. Der Entwurf wurde
abgelegt und vom Owner gesendet. Der Scanner sah die Zahl nie — seine
Body-Extraktion (`_published_bodies`) betrachtet nur Kommandos, die auf
`_GH_BODY_CARRIER_RE` passen (`gh pr|issue create|edit|comment|close|merge`).
Mail-Entwuerfe laufen ueber `tools/mail_agent/draft_mail.py --body-file <pfad>`
bzw. `tools/mail_agent/graph_mail.py --draft --body-file <pfad>` und fallen
deshalb durch.

Diese Datei haelt den neuen, eng begrenzten Carrier (`_MAIL_DRAFT_CARRIER_RE`),
die neue Messzahl-Erkennung (`_MESSZAHL_RE`/`_messzahl_ungehedgt_fires`) und den
Advisory-Sonderweg fest: die neue Trefferart `entwurf-messzahl` blockt NIE, auch
nicht im blocking-Mode (Owner-Vorgabe #2924 — "advisory: Warnzeile, Entwurf wird
trotzdem abgelegt").
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "evidence_claim_scanner.py"
_spec = importlib.util.spec_from_file_location("evidence_claim_scanner_r6", _QUELLE)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

REALFALL = "At 22 pages and roughly 7,800 words"


def _run(monkeypatch, capsys, tmp_path, event: dict):
    monkeypatch.setenv("EVIDENCE_SCANNER_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    rc = scanner.main()
    out = capsys.readouterr().out.strip()
    return rc, (json.loads(out) if out else {})


def _transcript(
    tmp_path, name: str, content_blocks: list, ergebnis: str = "ok"
) -> Path:
    p = tmp_path / f"transcript_{name}.jsonl"
    zeilen = [
        {"type": "user", "message": {"content": "schreib den Mail-Entwurf"}},
        {"type": "assistant", "message": {"content": content_blocks}},
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": ergebnis}]},
        },
    ]
    p.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


# --- 1: Positivkontrolle -----------------------------------------------------


def test_should_block_body_file_via_write_input_erkennen(
    monkeypatch, capsys, tmp_path
) -> None:
    """draft_mail.py --body-file mit Write-Input auf denselben Pfad — der Realfall."""
    body_pfad = str(tmp_path / "entwurf.txt")
    p = _transcript(
        tmp_path,
        "positiv",
        [
            {
                "type": "tool_use",
                "name": "Write",
                "input": {"file_path": body_pfad, "content": REALFALL},
            },
            {
                "type": "tool_use",
                "name": "Bash",
                "input": {
                    "command": (
                        "python3 tools/mail_agent/draft_mail.py --account hnu "
                        "--role hnu --to x@y.de --subject 'Re: Feedback' "
                        f"--body-file {body_pfad}"
                    )
                },
            },
            {"type": "text", "text": "Entwurf abgelegt."},
        ],
    )
    _, out = _run(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert "additionalContext" in out.get("hookSpecificOutput", {})
    assert "entwurf-messzahl" in out["hookSpecificOutput"]["additionalContext"]


# --- 2: zaehlendes Kommando im Turn entwaffnet --------------------------------


def test_should_mit_pdfinfo_im_turn_nicht_feuern(monkeypatch, capsys, tmp_path) -> None:
    body_pfad = str(tmp_path / "entwurf2.txt")
    p = _transcript(
        tmp_path,
        "mit_pdfinfo",
        [
            {
                "type": "tool_use",
                "name": "Bash",
                "input": {"command": 'pdfinfo "Chapter One.pdf"'},
            },
            {
                "type": "tool_use",
                "name": "Write",
                "input": {"file_path": body_pfad, "content": REALFALL},
            },
            {
                "type": "tool_use",
                "name": "Bash",
                "input": {
                    "command": (
                        "python3 tools/mail_agent/draft_mail.py --account hnu "
                        f"--role hnu --to x@y.de --subject 'Re: Feedback' "
                        f"--body-file {body_pfad}"
                    )
                },
            },
            {"type": "text", "text": "Entwurf abgelegt."},
        ],
        ergebnis="Pages: 23",
    )
    rc, out = _run(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert rc == 0
    assert out == {}, f"pdfinfo lief, Melder haette schweigen muessen: {out}"


# --- 3: gehedgter Satz --------------------------------------------------------


def test_should_gehedgten_satz_in_ruhe_lassen(monkeypatch, capsys, tmp_path) -> None:
    body_pfad = str(tmp_path / "entwurf3.txt")
    p = _transcript(
        tmp_path,
        "gehedgt",
        [
            {
                "type": "tool_use",
                "name": "Write",
                "input": {
                    "file_path": body_pfad,
                    "content": "The chapter is about 20 pages long.",
                },
            },
            {
                "type": "tool_use",
                "name": "Bash",
                "input": {
                    "command": (
                        "python3 tools/mail_agent/draft_mail.py --account hnu "
                        f"--role hnu --to x@y.de --subject 'Re: Feedback' "
                        f"--body-file {body_pfad}"
                    )
                },
            },
            {"type": "text", "text": "Entwurf abgelegt."},
        ],
    )
    rc, out = _run(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert rc == 0
    assert out == {}, f"Hedge haette den Treffer entwaffnen muessen: {out}"


# --- 4: kein Messwert im Body --------------------------------------------------


def test_should_entwurf_ohne_messzahl_in_ruhe_lassen(
    monkeypatch, capsys, tmp_path
) -> None:
    body_pfad = str(tmp_path / "entwurf4.txt")
    p = _transcript(
        tmp_path,
        "ohne_messzahl",
        [
            {
                "type": "tool_use",
                "name": "Write",
                "input": {
                    "file_path": body_pfad,
                    "content": "Danke fuer die Einreichung, ich melde mich naechste Woche.",
                },
            },
            {
                "type": "tool_use",
                "name": "Bash",
                "input": {
                    "command": (
                        "python3 tools/mail_agent/draft_mail.py --account hnu "
                        f"--role hnu --to x@y.de --subject 'Re: Feedback' "
                        f"--body-file {body_pfad}"
                    )
                },
            },
            {"type": "text", "text": "Entwurf abgelegt."},
        ],
    )
    rc, out = _run(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert rc == 0
    assert out == {}, f"kein Messwert im Body, Melder haette schweigen muessen: {out}"


# --- 5: graph_mail.py --draft, Body nur auf Platte (kein Write-Input) --------


def test_should_graph_mail_body_von_platte_lesen(monkeypatch, capsys, tmp_path) -> None:
    body_pfad = tmp_path / "entwurf5.txt"
    body_pfad.write_text(REALFALL, encoding="utf-8")
    p = _transcript(
        tmp_path,
        "graph_mail",
        [
            {
                "type": "tool_use",
                "name": "Bash",
                "input": {
                    "command": (
                        "python3 tools/mail_agent/graph_mail.py --draft --account hnu "
                        f"--to x@y.de --subject 'Re: Feedback' --body-file {body_pfad}"
                    )
                },
            },
            {"type": "text", "text": "Entwurf ueber Graph abgelegt."},
        ],
    )
    _, out = _run(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert "additionalContext" in out.get("hookSpecificOutput", {})
    assert "entwurf-messzahl" in out["hookSpecificOutput"]["additionalContext"]


# --- 6: Regressionsschutz — gh pr create --body-file bleibt unveraendert -----


def test_should_gh_pr_create_body_file_unveraendert_verhalten(
    monkeypatch, capsys, tmp_path
) -> None:
    """Der neue Carrier darf gh-Kommandos nicht miterfassen — Regressionsschutz."""
    body_pfad = tmp_path / "pr_body.md"
    body_pfad.write_text(REALFALL, encoding="utf-8")
    assert not scanner._MAIL_DRAFT_CARRIER_RE.search(
        f"gh pr create --title x --body-file {body_pfad}"
    )
    entwurf_bodies = scanner._entwurf_bodies(
        [("Bash", {"command": f"gh pr create --title x --body-file {body_pfad}"})]
    )
    assert entwurf_bodies == [], "gh-Kommando darf nicht als Mail-Entwurf gelten"


# --- 7: Routing — reiner Advisory-Fall blockt nicht, auch nicht im blocking-Mode


def test_should_reinen_advisory_fall_niemals_blocken(
    monkeypatch, capsys, tmp_path
) -> None:
    """Default-Modus ist blocking (kein evidence_scanner_mode-State-File) —
    trotzdem darf ein reiner entwurf-messzahl-Treffer nie `decision: block` sein."""
    body_pfad = str(tmp_path / "entwurf7.txt")
    p = _transcript(
        tmp_path,
        "routing",
        [
            {
                "type": "tool_use",
                "name": "Write",
                "input": {"file_path": body_pfad, "content": REALFALL},
            },
            {
                "type": "tool_use",
                "name": "Bash",
                "input": {
                    "command": (
                        "python3 tools/mail_agent/draft_mail.py --account hnu "
                        f"--role hnu --to x@y.de --subject 'Re: Feedback' "
                        f"--body-file {body_pfad}"
                    )
                },
            },
            {"type": "text", "text": "Entwurf abgelegt."},
        ],
    )
    rc, out = _run(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert rc == 0
    assert out.get("decision") != "block", f"Advisory-Sonderweg verletzt: {out}"
    assert "additionalContext" in out.get("hookSpecificOutput", {})
