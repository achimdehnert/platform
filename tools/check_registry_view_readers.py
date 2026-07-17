#!/usr/bin/env python3
"""check_registry_view_readers — Guard gegen NEUE Direct-Reads der generierten Registry-Views.

ADR-234 §11.1 REC-4. Nach dem P0-Flip sind `scripts/repo-registry.yaml` (flat) und
`registry/repos.yaml` (rich) GENERIERTE Views von `registry/canonical.yaml`. Bestehende
Konsumenten dürfen sie weiter lesen (akzeptierter End-Zustand, ADR-234 Changelog 2026-06-01);
NEUER Code soll die Read-API `tools/registry_api.py` nutzen, damit die Views nicht wieder zu
faktischen SSoTs werden.

Mechanik: deterministischer Text-Scan über `git ls-files`. Wer einen View-Pfad referenziert
und NICHT in der eingefrorenen Baseline (`registry_view_readers.txt`) steht, lässt den Check
fehlschlagen. Migration eines Konsumenten auf die API → Baseline schrumpft (informational, kein Fail).

Pfad-präzise (REC-4): `registry/repos.yaml` (NICHT bare `repos.yaml` — kollidiert mit dem
separaten `infra/klickdummy-host` `/opt/klickdummy/repos.yaml`, anderes File) +
`repo-registry.yaml` (eindeutiger Basename der flat-View).

Run:    python3 tools/check_registry_view_readers.py
Update: python3 tools/check_registry_view_readers.py --update   # nur nach echter Konsumenten-Migration
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = Path(__file__).resolve().parent / "registry_view_readers.txt"

# Pfad-präzise Marker der generierten Views. Bare `repos.yaml` BEWUSST nicht.
VIEW_MARKERS = ("repo-registry.yaml", "registry/repos.yaml")

# Nur Code/Config scannen — REC-4 zielt auf *Code*, das die Views liest. Doku (.md/.rst)
# erwähnt die Pfade in Prosa und ist kein SSoT-Drift-Risiko (sonst False-Positive bei jedem
# neuen ADR, der den Pfad nennt).
CODE_SUFFIXES = (".py", ".sh", ".yml", ".yaml", ".toml", ".cfg", ".ini")

# Registry-Maschinerie selbst — kein "Konsument": Generator, Read-API, Drift-Gate, die
# Views + canonical, dieser Guard + seine Baseline.
ALLOWED = {
    "tools/registry_api.py",
    "tools/registry-canonical.py",
    "tools/registry-consistency-check.py",
    "tools/check_registry_view_readers.py",
    "tools/tests/test_check_registry_view_readers.py",  # enthält View-Pfade als Test-Fixtures, kein Reader
    "tools/registry_view_readers.txt",
    "registry/canonical.yaml",
    "registry/repos.yaml",
    "scripts/repo-registry.yaml",
    "registry/sync_registry.py",
    ".github/workflows/registry-consistency.yml",
    ".github/workflows/registry-lint.yml",
}


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def find_readers(root: Path, files: list[str]) -> set[str]:
    """Dateien, die einen View-Pfad referenzieren — ohne Maschinerie/Archiv."""
    readers = set()
    for rel in files:
        # Archivierte Dateien sind Historie, kein aktiver Reader — in JEDEM
        # _ARCHIVED/ überspringen (root wie verschachtelt, z.B. ADR-275 P5:
        # registry/_ARCHIVED/github_repos.yaml, dessen RETIRED-Banner die
        # View-Pfade nennt).
        if (
            rel in ALLOWED
            or rel.startswith("_ARCHIVED/")
            or "/_ARCHIVED/" in rel
        ):
            continue
        if not rel.endswith(CODE_SUFFIXES):
            continue
        try:
            text = (root / rel).read_text(errors="ignore")
        except (OSError, UnicodeError):
            continue
        if any(m in text for m in VIEW_MARKERS):
            readers.add(rel)
    return readers


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {
        ln.strip()
        for ln in BASELINE.read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    }


def write_baseline(readers: set[str]) -> None:
    header = (
        "# Eingefrorene Baseline der LEGITIMEN Direct-Reader der generierten Registry-Views\n"
        "# (ADR-234 §11.1 REC-4). NEUE Reader hier NICHT eintragen — stattdessen\n"
        "# tools/registry_api.py (flat/rich/repos/repo) nutzen. Regenerieren NUR nach echter\n"
        "# Migration eines Konsumenten auf die API:\n"
        "#   python3 tools/check_registry_view_readers.py --update\n"
    )
    BASELINE.write_text(header + "\n".join(sorted(readers)) + "\n")


def main(argv: list[str]) -> int:
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    readers = find_readers(ROOT, _tracked_files())
    if "--update" in argv:
        write_baseline(readers)
        print(f"✅ Baseline aktualisiert: {len(readers)} Reader → {BASELINE.relative_to(ROOT)}")
        return 0

    baseline = load_baseline()
    if not baseline:
        print("FEHLER: Baseline fehlt — erst `--update` (committed) laufen lassen.", file=sys.stderr)
        return 2

    new = readers - baseline
    gone = baseline - readers
    if gone:
        print(
            f"ℹ {len(gone)} Baseline-Reader lesen die Views nicht mehr (Migration?) — "
            f"optional `--update`: {', '.join(sorted(gone))}"
        )
    if new:
        print("🔴 NEUE Direct-Reads der generierten Registry-Views (ADR-234 §11.1 REC-4):")
        for r in sorted(new):
            print(f"   - {r}")
        print("\n   Die Views (scripts/repo-registry.yaml, registry/repos.yaml) sind GENERIERT.")
        print("   Neuer Code liest die Registry über tools/registry_api.py")
        print("   (flat()/rich()/repos()/repo()). Falls dieser Reader bewusst legitim ist,")
        print("   begründe ihn und nimm ihn per `--update` in die Baseline auf.")
        return 1

    print(f"✅ Keine neuen View-Direct-Reads ({len(readers)} bekannte Reader, Baseline eingehalten).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
