#!/usr/bin/env python3
"""workflow_tool_ref_check.py — CI-Gate für die verify-adr156 Workflow-Tool-Referenz-Invariant
(Issue #1310, Retro session-retro-2026-07-21-platform-8d663b Befund B2).

Problem: der estimate_job-Falsch-grün-Bug (mcp-hub#180) überlebte ~3 Monate, weil
`scripts/verify-adr156.sh` (mcp-hub) nur lokal beim Session-Start läuft und bei
Nicht-Grün lediglich WARN (nicht blockierend) ist. Das Skript selbst ist CI-untauglich
(SSH auf den Prod-Host + cross-repo lokale Pfade unter ~/github) — dieses Gate zieht
NICHT das Skript in CI, sondern verankert die eine CI-fähige Teil-Invariante direkt
als platform-Check: `.windsurf/workflows/ship.md` und `backup.md` müssen den echten
Tool-Aufruf in Aufruf-Form tragen, nicht nur den String irgendwo erwähnen.

Die Aufruf-Form ist eine Zeile, die (ggf. mit YAML-Einrückung) mit
`mcp__orchestrator__estimate_job:` beginnt — genau das Muster, das ship.md/backup.md
tatsächlich verwenden. Ein Satz wie "estimate_job existiert nicht mehr" oder "kein
estimate_job mehr nötig" enthält den nackten String, aber NICHT die Aufruf-Form, und
darf das Gate nicht grün machen (das war der Kern des ~3-Monate-Bugs: ein naiver
`grep -q estimate_job` hätte auch die Verneinung als Treffer gezählt).

Aufruf:  workflow_tool_ref_check.py <datei> [<datei> ...]
Exit 0 = alle geprüften Dateien tragen die Aufruf-Form · Exit 1 = mindestens eine ohne
Exit 2 = Usage-Fehler (keine Argumente). Nur stdlib, kein Netz.
Verdrahtet in .github/workflows/workflow-tool-ref-gate.yml;
Tests: tools/tests/test_workflow_tool_ref_check.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Aufruf-Form: Zeilenanfang (ggf. Whitespace für YAML-Einrückung), dann der Tool-Name
# gefolgt von einem Doppelpunkt — genau das Muster von "mcp__orchestrator__estimate_job:"
# in ship.md/backup.md. Eine Prosa-Erwähnung ("... estimate_job existiert nicht mehr")
# hat keinen Doppelpunkt direkt nach dem Namen am Zeilenanfang und matcht daher NICHT.
TOOL_CALL_RE = re.compile(r"^\s*mcp__orchestrator__estimate_job:", re.MULTILINE)

FAIL_HINT = (
    "die Aufruf-Form 'mcp__orchestrator__estimate_job:' fehlt — eine bloße Prosa-\n"
    "  Erwähnung des Strings genügt NICHT (das war der ~3-Monate-Bug, mcp-hub#180).\n"
    "  Fix: sicherstellen, dass der Workflow den echten Tool-Aufruf\n"
    "  'mcp__orchestrator__estimate_job:' als eigene (ggf. eingerückte) Zeile enthält."
)


def has_tool_call(path: Path) -> bool:
    """True, wenn die Datei die Aufruf-Form des estimate_job-Tool-Aufrufs enthält."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return bool(TOOL_CALL_RE.search(text))


def main(argv: list[str]) -> int:
    if not argv:
        print(
            "usage: workflow_tool_ref_check.py <ship.md|backup.md> [...]",
            file=sys.stderr,
        )
        return 2
    failed: list[str] = []
    for name in argv:
        path = Path(name)
        if not path.is_file():
            # Gelöschte/umbenannte Dateien sind kein Gate-Fall (Caller filtert i.d.R.
            # per --diff-filter=ACMR; hier defensiv doppelt abgesichert).
            print(f"SKIP  {name} (existiert nicht — vermutlich gelöscht)")
            continue
        if has_tool_call(path):
            print(f"PASS  {name} (Aufruf-Form mcp__orchestrator__estimate_job: vorhanden)")
        else:
            print(f"FAIL  {name} — Aufruf-Form mcp__orchestrator__estimate_job: fehlt")
            failed.append(name)
    if failed:
        print(f"\n⛔ Gate workflow-tool-ref: {len(failed)} Datei(en) ohne Aufruf-Form —")
        print(FAIL_HINT)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
