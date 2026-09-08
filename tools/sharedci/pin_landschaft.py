"""pin_landschaft.py — misst, welche shared-ci-Version jedes Repo gerade pinnt.

Siehe tools/sharedci/README.md. platform#2944: Anschluss an die gemeinsame
Melder-Huelle (`tools/melder_ergebnis.py`) ueber `--ergebnis-datei` — der
bisherige Aufruf ohne Flags bleibt unveraendert (gleiche Ausgabe, Exit 0).
"""

from __future__ import annotations

import argparse
import base64
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import melder_ergebnis  # noqa: E402

WERKZEUG_VERSION = "pin_landschaft/1"

REPOS = """achimdehnert/travel-beat achimdehnert/recruiting-hub achimdehnert/137-hub
achimdehnert/coach-hub achimdehnert/illustration-hub achimdehnert/pptx-hub
achimdehnert/weltenhub iilgmbh/ausschreibungs-hub iilgmbh/tax-hub achimdehnert/dev-hub
achimdehnert/apo-hub achimdehnert/onboarding-hub achimdehnert/trading-hub
achimdehnert/billing-hub achimdehnert/mcp-hub achimdehnert/dms-hub iilgmbh/risk-hub
meiki-lra/frist-hub achimdehnert/decks-hub meiki-lra/meiki-hub
iilgmbh/iil-voice-agent achimdehnert/bahn-hub achimdehnert/design-hub iilgmbh/desktop-setup iilgmbh/django-lms-lite iilgmbh/iil-fieldprefill iilgmbh/illustration-fw iilgmbh/nl2iot-hub achimdehnert/lastwar-bot achimdehnert/cad-hub achimdehnert/learn-hub achimdehnert/research-hub achimdehnert/dms-hub iilgmbh/iil-testkit""".split()


def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True)
    return r.stdout if not r.returncode else ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--ergebnis-datei",
        type=Path,
        help=(
            "Urteile zusaetzlich in der gemeinsamen Melder-Huelle ablegen "
            "(tools/melder_ergebnis.py, platform#2944). Ohne diese Datei meldet "
            "der Melder und verschwindet — der Future-Readiness-Erheber hat dann "
            "nichts zum Anschliessen."
        ),
    )
    a = p.parse_args(argv)

    gesamt: dict[str, dict[str, list[str]]] = {}
    # Zweite, parallele Buchfuehrung — nur fuer die Ergebnisdatei, aendert nichts
    # an `gesamt` oder den Print-Zeilen unten. Volle Repo-Kennung (mit Org), weil
    # Kurznamen ueber achimdehnert/iilgmbh/meiki-lra hinweg kollidieren koennen.
    je_repo: dict[str, list[dict]] = {}
    for repo in REPOS:
        dateien = gh(
            "api", f"repos/{repo}/contents/.github/workflows", "-q", ".[].name"
        ).split()
        for f in dateien:
            c = gh(
                "api", f"repos/{repo}/contents/.github/workflows/{f}", "-q", ".content"
            )
            if not c:
                continue
            try:
                t = base64.b64decode(c).decode()
            except Exception:
                continue
            for wf, ref in re.findall(
                r"shared-ci/\.github/workflows/([\w.-]+)@([\w.\-/]+)", t
            ):
                gesamt.setdefault(wf, {}).setdefault(ref, []).append(
                    f"{repo.split('/')[1]}:{f}"
                )
                je_repo.setdefault(repo, []).append(
                    {"workflow": wf, "version": ref, "datei": f}
                )
    for wf in sorted(gesamt):
        refs = gesamt[wf]
        print(f"\n=== {wf} — {len(refs)} verschiedene Pins")
        for ref in sorted(refs):
            print(
                f"  {ref:<12} {len(refs[ref])}x  {', '.join(sorted(refs[ref]))[:110]}"
            )

    if a.ergebnis_datei:
        # Nur Repo/Workflow-Dateiname/Version — alles bereits oeffentlich (REPOS
        # oben ist Klartext im selben Repo), keine Inhalte der Workflow-Dateien.
        melder_ergebnis.schreibe(
            a.ergebnis_datei,
            melder="pin_landschaft",
            ergebnis=[
                {"repo": repo, "pins": je_repo[repo]} for repo in sorted(je_repo)
            ],
            werkzeug_version=WERKZEUG_VERSION,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
