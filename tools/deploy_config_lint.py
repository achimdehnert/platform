#!/usr/bin/env python3
"""deploy_config_lint.py — Org-Gate gegen Auto-Prod-Deploy-Drift.

Prueft die Deploy-Workflows eines Repos darauf, dass push->main NICHT auf
'production' defaultet. Org-Standard (platform/_deploy-unified.yml):
push->main = staging; Prod nur via Tag v* oder bewusster workflow_dispatch-Wahl.

Hintergrund: risk-hub deployte ~20 Tage unbemerkt push->main direkt auf Prod,
weil deploy.yml `target_environment` auf 'production' defaultete (session-retro
2026-06-04, run wf_313a3b58). Dieses Lint faengt die Drift-Klasse org-weit am
PR-Gate — statt N-ter Memory-Eintrag.

Usage:
    python3 deploy_config_lint.py [<workflows-dir>]   # default .github/workflows
Exit 1 wenn ein Auto-Prod-Default-Anti-Pattern gefunden wird, sonst 0.
"""

from __future__ import annotations

import pathlib
import re
import sys

# Anti-Pattern 1 (Haupt-Drift-Ursache): push-Fallback auf production, z.B.
#   target_environment: ${{ inputs.target_environment || 'production' }}
_FALLBACK = re.compile(r"""target_environment\s*:.*\|\|\s*['"]production['"]""")

# Anti-Pattern 2: workflow_dispatch-Input-Default 'production' im
# target_environment-Block (Mehrzeilen-Block bis zum naechsten default:).
_INPUT_DEFAULT = re.compile(
    r"""target_environment\s*:\s*\n(?:[ \t]+\S.*\n)*?[ \t]+default\s*:\s*['"]production['"]""",
)


def lint_text(name: str, text: str) -> list[str]:
    """Findet Auto-Prod-Default-Anti-Pattern in einem Workflow-Text."""
    out: list[str] = []
    for m in _FALLBACK.finditer(text):
        out.append(
            f"{name}: push->branch faellt auf production zurueck (Default sollte 'staging'): {m.group(0).strip()}"
        )
    if _INPUT_DEFAULT.search(text):
        out.append(
            f"{name}: workflow_dispatch target_environment-Default = 'production' (sollte 'staging')"
        )
    return out


def lint_dir(d: pathlib.Path) -> list[str]:
    out: list[str] = []
    for f in sorted([*d.glob("*.yml"), *d.glob("*.yaml")]):
        out.extend(lint_text(str(f), f.read_text(encoding="utf-8", errors="ignore")))
    return out


def main(argv: list[str]) -> int:
    d = pathlib.Path(argv[1] if len(argv) > 1 else ".github/workflows")
    if not d.is_dir():
        print(f"✅ Deploy-Config-Lint: kein Verzeichnis {d} — nichts zu pruefen.")
        return 0
    offenders = lint_dir(d)
    if offenders:
        print("❌ Deploy-Config-Lint: Auto-Prod-Default-Anti-Pattern gefunden:")
        for o in offenders:
            print("  -", o)
        print(
            "\nFix: target_environment-Default auf 'staging'. Prod nur via Tag v* "
            "oder bewusster workflow_dispatch-Wahl (Org-Standard _deploy-unified.yml)."
        )
        return 1
    print("✅ Deploy-Config-Lint: kein Auto-Prod-Default.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
