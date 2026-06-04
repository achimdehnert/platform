#!/usr/bin/env python3
"""Test-Claim-Check — Warn-only CI gate (session-retro Gate 1).

Befund 6 des Session-Retros (2026-06-04): ein PR-Body behauptet "unit-getestet",
aber der Diff enthält keine geänderte Testdatei — eine prüfbare Behauptung ohne
committeten Beleg (Wiederholung von House-Rule "Evidenz vor Behauptung" +
Drift-Memory claim-confidence-vs-cheapest-check). Memo-Ebene hielt nicht → Gate.

Mechanik (rein deterministisch, KEIN LLM — feedback_repo_health_rule_discipline):
  1. PR-Body + Commit-Messages nach *Test*-Claim-Wörtern scannen.
  2. Geänderte Dateien nach Testdateien scannen.
  3. Claim ohne Test-Diff -> WARN (Kommentar). Sonst -> still.

Phase SUGGEST: Das Gate WARNT nur (Exit immer 0 für das Verdikt), bis es gegen
echte PRs FP-frei validiert ist. Erst danach ggf. auf Fail hochziehen.

CLI:
  python tools/test_claim_check.py \
    --body-file pr_body.txt [--commits-file commits.txt] \
    --changed-files-file changed.txt [--format markdown|json]

Run-Tests: python3 -m pytest tools/tests/test_test_claim_check.py -q
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# --- Claim-Erkennung -------------------------------------------------------
# Bewusst auf *starke* Test-Behauptungen zentriert (Precision > Recall — ein
# warn-only Gate, das Wolf schreit, wird ignoriert). Empirisch getunt gegen die
# letzten 30 merged platform-PRs (2026-06-04): diese Liste -> 1 WARN (#453, der
# kanonische Befund-6-Fall), 0 FP. BEWUSST AUSGESCHLOSSEN, weil FP-Magneten:
#   - das blosse "verifiziert"/"verified" (meist manuelle/inhaltliche Verifikation,
#     z.B. "Portabilitaet verifiziert");
#   - das blosse "getestet"/"tested" als Einzelwort (kam in Docs-Prosa wie
#     '"Rueckgabefaehig" = getestet, nicht behauptet' vor -> #437 war damit FP).
# Die starken Marker (unit-getestet, unittests, test coverage, "tests added/pass")
# tragen den Befund-6-Kern ohne das Rauschen.
_CLAIM_PATTERNS = [
    r"\bunit[\s-]?(?:getestet|tested|tests?)\b",
    r"\bunittests?\b",
    r"\btest[\s-]?coverage\b",
    r"\btests?\s+(?:added|pass(?:ed|ing)?|hinzugef[uü]gt|erg[aä]nzt|gr[uü]n)\b",
]
_CLAIM_RE = re.compile("|".join(f"(?:{p})" for p in _CLAIM_PATTERNS), re.IGNORECASE)

# Negation/Abschwaechung im Fenster VOR dem Treffer -> kein Claim.
# Faengt "nicht getestet", "noch nicht getestet", "manuell getestet",
# "kein Unit-Test", "not tested", "without tests".
_NEG_RE = re.compile(
    r"(nicht|noch\s+nicht|kein[e]?|ohne|manuell|manual|\bnot\b|\bno\b|without)",
    re.IGNORECASE,
)
_NEG_WINDOW = 30  # Zeichen vor dem Treffer

# --- Testdatei-Erkennung ---------------------------------------------------
_TEST_FILE_PATTERNS = [
    r"(^|/)tests?/",
    r"(^|/)test_[^/]+\.py$",
    r"_test\.(?:py|js|ts|tsx|jsx|go|rb)$",
    r"\.test\.(?:js|ts|jsx|tsx)$",
    r"\.spec\.(?:js|ts|jsx|tsx)$",
    r"(^|/)conftest\.py$",
]
_TEST_FILE_RE = re.compile("|".join(_TEST_FILE_PATTERNS))


def find_test_claims(text: str) -> list[str]:
    """Liefert die gefundenen Claim-Phrasen (Negationen herausgefiltert)."""
    if not text:
        return []
    claims: list[str] = []
    for m in _CLAIM_RE.finditer(text):
        window = text[max(0, m.start() - _NEG_WINDOW): m.start()]
        if _NEG_RE.search(window):
            continue  # abgeschwaecht/negiert -> kein Test-Claim
        claims.append(m.group(0).strip())
    return claims


def changed_test_files(paths: list[str]) -> list[str]:
    """Filtert die Liste geaenderter Pfade auf Testdateien."""
    return [p for p in paths if p and _TEST_FILE_RE.search(p)]


def analyze(body: str, commits: str, changed_files: list[str]) -> dict:
    """Kern-Verdikt. Pure function — vollstaendig unit-testbar."""
    claims = find_test_claims(body) + find_test_claims(commits)
    test_files = changed_test_files(changed_files)
    verdict = "warn" if claims and not test_files else "ok"
    return {
        "verdict": verdict,
        "should_comment": verdict == "warn",
        "claims": sorted(set(claims), key=str.lower),
        "test_files": test_files,
    }


def render_markdown(result: dict) -> str:
    claims = ", ".join(f"`{c}`" for c in result["claims"])
    return (
        "### 🧪 Test-Claim-Check — Hinweis (warn-only)\n\n"
        f"Dieser PR enthält Test-Behauptung(en) ({claims}), aber der Diff ändert "
        "**keine Testdatei**.\n\n"
        "Bitte eines von beidem:\n"
        "- den behaupteten Test als Datei committen (`tests/`, `test_*.py`, "
        "`*_test.*`, `*.spec.*`), **oder**\n"
        "- die Behauptung im PR-Body präzisieren (z. B. „manuell verifiziert“, "
        "„kein Unit-Test nötig“).\n\n"
        "> Hintergrund: Session-Retro 2026-06-04, Befund 6 — „Evidenz vor "
        "Behauptung“. Dieser Check ist **informativ, nie blockierend**."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Test-Claim-Check (warn-only)")
    ap.add_argument("--body-file")
    ap.add_argument("--commits-file")
    ap.add_argument("--changed-files-file")
    ap.add_argument("--format", choices=["markdown", "json"], default="json")
    args = ap.parse_args(argv)

    def _read(p: str | None) -> str:
        if not p:
            return ""
        try:
            with open(p, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return ""

    body = _read(args.body_file)
    commits = _read(args.commits_file)
    changed = [ln.strip() for ln in _read(args.changed_files_file).splitlines() if ln.strip()]

    result = analyze(body, commits, changed)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False))
    elif result["should_comment"]:
        print(render_markdown(result))

    return 0  # warn-only: Verdikt blockiert nie


if __name__ == "__main__":
    sys.exit(main())
