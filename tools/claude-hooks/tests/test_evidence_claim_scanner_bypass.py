"""Rev 4 des Evidenz-Scanners — der Fall, an dem er am 2026-08-28 versagte.

platform#2397, 06:56:41Z: `gh pr comment … "Admin-Merge (Ruleset-Bypass …)" && gh pr merge
--admin`. Der Merge antwortete "already merged" (wirdigital, regulaer), der Kommentar stand.
Der Scanner sah `state: MERGED` im Turn und hielt die Sache fuer belegt — MERGED sagt aber
nichts ueber den Merge-WEG. Zwei neue Treffer, beide mit Nicht-Treffer daneben, damit der
Waechter nicht bei jedem Merge anschlaegt.
"""

from __future__ import annotations

import importlib.util
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
