"""Rev 4 des Evidenz-Scanners — der Fall, an dem er am 2026-08-28 versagte.

platform#2397, 06:56:41Z: `gh pr comment … "Admin-Merge (Ruleset-Bypass …)" && gh pr merge
--admin`. Der Merge antwortete "already merged" (wirdigital, regulaer), der Kommentar stand.
Der Scanner sah `state: MERGED` im Turn und hielt die Sache fuer belegt — MERGED sagt aber
nichts ueber den Merge-WEG. Zwei neue Treffer, beide mit Nicht-Treffer daneben, damit der
Waechter nicht bei jedem Merge anschlaegt.
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "evidence_claim_scanner.py"
_spec = importlib.util.spec_from_file_location("evidence_claim_scanner_r4", _QUELLE)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

REALFALL = (
    'gh pr comment 2397 -R achimdehnert/platform --body "Admin-Merge (Ruleset-Bypass, '
    'durables Artefakt): CI 11/11 gruen …" >/dev/null && '
    "gh pr merge 2397 -R achimdehnert/platform --squash --delete-branch --admin 2>&1 | tail -1"
)


def test_should_erkennen_kommentar_vor_merge_im_realfall() -> None:
    assert scanner._kommentar_vor_merge([("Bash", {"command": REALFALL})])


def test_should_kommentar_nach_merge_in_ruhe_lassen() -> None:
    cmd = (
        "gh pr merge 234 -R achimdehnert/mcp-hub --squash --admin && "
        'gh pr comment 234 -R achimdehnert/mcp-hub --body "Admin-Merge, Owner-Freigabe …"'
    )
    assert not scanner._kommentar_vor_merge([("Bash", {"command": cmd})])


def test_should_kommentar_ohne_statuswort_vor_merge_in_ruhe_lassen() -> None:
    cmd = (
        'gh pr comment 5 --body "Danke fuer den Review, Frage zu Zeile 12?" && '
        "gh pr merge 5 --squash"
    )
    assert not scanner._kommentar_vor_merge([("Bash", {"command": cmd})])


def test_should_bypass_claim_erkennen_und_mergedby_als_beleg_akzeptieren() -> None:
    body = "Admin-Merge (Ruleset-Bypass): Owner-Freigabe im Kapitaens-Kanal."
    assert scanner.BYPASS_CLAIM_RE.search(body)
    assert not scanner.MERGEDBY_EVIDENCE_RE.search(
        "state: MERGED"
    )  # der Irrtum von #2397
    assert scanner.MERGEDBY_EVIDENCE_RE.search(
        'gh pr view 2397 --json state,mergedBy → {"mergedBy":{"login":"wirdigital"}}'
    )


def test_should_normalen_merge_kommentar_nicht_als_bypass_werten() -> None:
    assert not scanner.BYPASS_CLAIM_RE.search("Gemergt nach gruener CI, Tag folgt.")


# --- Ende zu Ende durch main() ----------------------------------------------
#
# Die beiden Treffer-Etiketten `bypass-claim` und `comment-before-merge` stehen
# nur als Volltext im zusammengesetzten `fired`-Text von main() (Regex-Objekte
# und Funktionsnamen oben tragen sie nicht woertlich). `gate_namensdeckung.py`
# misst genau diesen Volltext — ohne einen echten Lauf durch main() bleibt der
# Fall in der Registry unberuehrt, unabhaengig davon, wie gut die reinen
# Funktionstests oben sind.


def _transcript(tmp_path: Path, command: str, tool_result: str) -> Path:
    p = tmp_path / "transcript_bypass.jsonl"
    zeilen = [
        {"type": "user", "message": {"content": "mach den Merge"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": "b1",
                        "input": {"command": command},
                    },
                    {"type": "text", "text": "Gemergt."},
                ]
            },
        },
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": tool_result}]},
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


def test_should_bypass_claim_und_comment_before_merge_im_realfall_ueber_main_melden(
    monkeypatch, capsys, tmp_path
) -> None:
    """POSITIVKONTROLLE Ende zu Ende, Realfall platform#2397: derselbe Befehl
    loest beide neuen Trefferarten aus — die Bypass-Behauptung im Kommentar UND
    der Statuswort-Kommentar VOR dem Merge in derselben Kette."""
    pfad = _transcript(tmp_path, REALFALL, "already merged (state: MERGED)")
    ausgabe = _run(monkeypatch, capsys, tmp_path, pfad)
    assert "bypass-claim" in ausgabe, ausgabe
    assert "comment-before-merge" in ausgabe, ausgabe


def test_should_normalen_merge_mit_mergedby_beleg_in_main_in_ruhe_lassen(
    monkeypatch, capsys, tmp_path
) -> None:
    """Gegenprobe: Merge zuerst, Kommentar danach, UND ein echter mergedBy-Beleg
    im Turn — keine der beiden neuen Trefferarten darf hier feuern."""
    cmd = (
        "gh pr merge 234 -R achimdehnert/mcp-hub --squash --admin && "
        'gh pr comment 234 -R achimdehnert/mcp-hub --body "Admin-Merge, Owner-Freigabe …"'
    )
    tool_result = (
        'gh pr view 234 --json mergedBy → {"mergedBy":{"login":"achimdehnert"}}'
    )
    ausgabe = _run(
        monkeypatch, capsys, tmp_path, _transcript(tmp_path, cmd, tool_result)
    )
    assert "bypass-claim" not in ausgabe, ausgabe
    assert "comment-before-merge" not in ausgabe, ausgabe
