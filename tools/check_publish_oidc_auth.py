#!/usr/bin/env python3
"""Enforcement-Gate für ADR-278: PyPI-Publish muss OIDC Trusted Publishing sein.

Lehnt jede `*publish*.yml` ab, deren **PyPI**-Upload-Step (pypa/gh-action-pypi-publish)
einen `password:`-Input trägt — das deaktiviert Trusted Publishing (pypa-Action-Warnung
"disabling Trusted Publishing") und ist laut ADR-278 verboten. TestPyPI bleibt unberührt.

Der Check prüft den **Workflow-Input**, nicht die Existenz eines Secrets — ein Repo darf
seinen Token-Secret behalten, bis die Trusted-Publisher-Bindung bewiesen ist
(ADR-266: nie Token ohne Binding-Beweis raus), solange der Workflow-Input weg ist.

Nutzung:
  python3 tools/check_publish_oidc_auth.py                 # scannt .github/workflows/*publish*.yml (warn)
  python3 tools/check_publish_oidc_auth.py --block         # Exit 1 bei Fund
  python3 tools/check_publish_oidc_auth.py path/to/publish.yml [...]

Exit: 0 = sauber (oder warn-Modus), 1 = Fund im --block-Modus / Parse-Fehler im --block-Modus.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("check_publish_oidc_auth: PyYAML fehlt (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

PYPA_ACTION = "pypa/gh-action-pypi-publish"


def _is_testpypi(with_block: dict) -> bool:
    url = str(with_block.get("repository-url") or with_block.get("repository_url") or "")
    return "test.pypi.org" in url


def scan_file(path: Path) -> list[str]:
    """Return list of violation messages for one workflow file."""
    violations: list[str] = []
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - Parse-Fehler ist selbst ein Befund
        return [f"{path}: YAML nicht parsebar ({exc})"]
    if not isinstance(doc, dict):
        return violations
    for job_name, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            uses = str(step.get("uses") or "")
            if PYPA_ACTION not in uses:
                continue
            with_block = step.get("with") or {}
            if not isinstance(with_block, dict):
                continue
            if "password" in with_block and not _is_testpypi(with_block):
                step_name = step.get("name") or uses
                violations.append(
                    f"{path}: Job '{job_name}' Step '{step_name}' nutzt password-Input "
                    f"im PyPI-Upload → OIDC deaktiviert (ADR-278). password-Zeile entfernen."
                )
    return violations


def collect_targets(argv: list[str]) -> list[Path]:
    files = [a for a in argv if not a.startswith("-")]
    if files:
        return [Path(f) for f in files]
    return [Path(p) for p in glob.glob(".github/workflows/*publish*.yml")
            + glob.glob(".github/workflows/*publish*.yaml")]


def main(argv: list[str]) -> int:
    block = "--block" in argv
    targets = collect_targets(argv)
    if not targets:
        print("check_publish_oidc_auth: keine publish-Workflows gefunden (ok).")
        return 0
    all_violations: list[str] = []
    for path in targets:
        if path.exists():
            all_violations.extend(scan_file(path))
    if all_violations:
        header = "❌ ADR-278-Verstoß" if block else "⚠️  ADR-278-Warnung"
        print(f"{header}: token-basiertes PyPI-Publishing gefunden:")
        for v in all_violations:
            print(f"  - {v}")
        return 1 if block else 0
    print(f"✅ ADR-278: {len(targets)} publish-Workflow(s) sind OIDC-only (kein password-Input).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
