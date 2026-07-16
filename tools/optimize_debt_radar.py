#!/usr/bin/env python3
"""optimize_debt_radar.py — KONZ-platform-019 (read-only, wöchentlicher Fleet-Radar).

Zählt die in /platform-audit Phase 1.2/2.1 definierten Debt-Signale je lokalem Repo-
Klon und meldet, welche Repos gegenüber der letzten Baseline am stärksten zugelegt
haben (Delta-ggü.-Vorwoche, nicht absolut — KONZ-019 R-thresh, User-Entscheidung
2026-07-16: alarm-müdigkeits-ärmer). SSoT der Signal-Menge (KONZ-019 L7): `/platform-
audit` soll künftig dieses Modul referenzieren statt eigener Inline-Greps zu pflegen.

Bewusst AUSSER Scope (keine Duplikation, KONZ-019 L4): Git-Hygiene/Branch-Status/
Staleness gehört `fleet-drift-report`; rote Deploys gehört `deploy-health-triage`.
Dieser Radar misst reinen Code-Optimierungs-Debt.

Normalisierung ggü. dem Original-Grep (bewusste Abweichung, keine Neuerfindung):
platform-audit.md mischt Einheiten — manche Signale zählen Dateien (`grep -l`),
andere rohe Trefferzeilen (`grep -n`). Für einen über Wochen vergleichbaren Delta-
Wert zählt dieses Modul für ALLE Muster-Signale einheitlich "Anzahl Dateien mit
≥1 Treffer" — eine Datei mit 12 print()-Aufrufen soll nicht 12 Repos mit je einem
Treffer im Delta überstrahlen.

Repo-Quelle = `registry/canonical.yaml` (SSoT) statt eines hardcodierten ALL_REPOS-
Strings wie in platform-audit.md — vermeidet eine dritte Kopie derselben Fleet-Liste.

Reiner Kern (`scan_repo`, `compute_deltas`) ist dateisystem-lokal bzw. rein
funktional, fault-injectable via tmp_path in Tests (Analogie zu
registry_coverage_drift.py::compute_drift).
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

CANONICAL = Path(__file__).resolve().parents[1] / "registry" / "canonical.yaml"
REQUIRED_FILES = ["README.md", ".gitignore", "Makefile", "pyproject.toml", "CHANGELOG.md"]

PATTERNS = {
    "uuid_pk": re.compile(r"UUIDField\(primary_key=True\)"),
    "os_environ": re.compile(r"os\.environ"),
    "print_calls": re.compile(r"print\("),
    "direct_llm_imports": re.compile(r"^\s*(import anthropic|import openai|from groq)", re.MULTILINE),
}
HEALTH_ENDPOINT_PATTERN = re.compile(r"livez|healthz|health/")
EXCLUDE_DIR_PARTS = {".venv", "node_modules", "__pycache__"}


def _iter_py_files(repo_path: Path, exclude_tests: bool = True):
    for p in repo_path.rglob("*.py"):
        parts = set(p.parts)
        if parts & EXCLUDE_DIR_PARTS:
            continue
        if exclude_tests and (p.name.startswith("test_") or p.name.endswith("_test.py")
                               or p.name == "conftest.py" or "tests" in parts):
            continue
        yield p


def _files_matching(repo_path: Path, pattern: re.Pattern, exclude_tests: bool = True) -> int:
    """Anzahl Dateien mit >=1 Treffer (Datei-Einheit, s. Modul-Docstring)."""
    n = 0
    for p in _iter_py_files(repo_path, exclude_tests=exclude_tests):
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if pattern.search(text):
            n += 1
    return n


def missing_required_files(repo_path: Path) -> list:
    return [f for f in REQUIRED_FILES if not (repo_path / f).exists()]


def is_django(repo_path: Path) -> bool:
    return (repo_path / "manage.py").exists()


def has_default_auto_field(repo_path: Path) -> bool:
    for p in repo_path.rglob("settings*.py"):
        if set(p.parts) & EXCLUDE_DIR_PARTS:
            continue
        try:
            if "DEFAULT_AUTO_FIELD" in p.read_text(errors="ignore"):
                return True
        except OSError:
            continue
    return False


def has_health_endpoint(repo_path: Path) -> bool:
    for p in _iter_py_files(repo_path, exclude_tests=True):
        try:
            if HEALTH_ENDPOINT_PATTERN.search(p.read_text(errors="ignore")):
                return True
        except OSError:
            continue
    return False


def test_file_count(repo_path: Path) -> int:
    n = 0
    for p in repo_path.rglob("*.py"):
        if set(p.parts) & EXCLUDE_DIR_PARTS:
            continue
        if p.name.startswith("test_") or p.name.endswith("_test.py"):
            n += 1
    return n


def scan_repo(repo_path: Path) -> dict:
    """Reiner Dateisystem-Scan eines lokalen Klons — keine Netzwerk-Calls."""
    django = is_django(repo_path)
    missing_files = missing_required_files(repo_path)
    tests = test_file_count(repo_path)
    signals = {key: _files_matching(repo_path, pat) for key, pat in PATTERNS.items()}
    signals["missing_required_files"] = len(missing_files)
    signals["default_auto_field_missing"] = int(django and not has_default_auto_field(repo_path))
    signals["health_endpoint_missing"] = int(django and not has_health_endpoint(repo_path))
    signals["zero_tests"] = int(tests == 0)
    return {
        "signals": signals,
        "debt_total": sum(signals.values()),
        "missing_files": missing_files,
        "is_django": django,
        "test_file_count": tests,
    }


def _repo_excluded(entry: dict) -> bool:
    rich = (entry or {}).get("rich") or {}
    flat = (entry or {}).get("flat") or {}
    return (rich.get("lifecycle") == "archived"
            or rich.get("archived") is True
            or flat.get("archived") is True)


def discover_repos(github_dir: Path, canonical_path: Path):
    """Repo-Quelle = registry/canonical.yaml (SSoT, KONZ-019 L7) statt hardcodierter
    ALL_REPOS-Liste. Gibt (name->local_path, skipped_no_clone, skipped_archived)
    zurück — keine stillen Lücken (Org-Konvention "no silent caps")."""
    d = yaml.safe_load(canonical_path.read_text())
    repos, skipped_no_clone, skipped_archived = {}, [], []
    for name, entry in (d.get("repos") or {}).items():
        if _repo_excluded(entry):
            skipped_archived.append(name)
            continue
        local = github_dir / name
        if not (local / ".git").exists():
            skipped_no_clone.append(name)
            continue
        repos[name] = local
    return repos, skipped_no_clone, skipped_archived


def compute_deltas(current: dict, baseline: dict) -> dict:
    """Pure: delta je Repo = current_total - baseline_total (kein Baseline-Eintrag
    => delta = current_total, d.h. neu hinzugekommenes Repo zählt komplett als Delta)."""
    return {name: current[name] - baseline.get(name, 0) for name in current}


def render_text(current_totals: dict, deltas: dict, skipped_no_clone: list,
                 skipped_archived: list, top_n: int) -> str:
    flagged = sorted((n for n, d in deltas.items() if d > 0),
                      key=lambda n: deltas[n], reverse=True)[:top_n]
    lines = [
        "=== optimize-debt-radar (KONZ-platform-019) ===",
        f"  Repos gescannt: {len(current_totals)} · archiviert übersprungen: {len(skipped_archived)}",
    ]
    if skipped_no_clone:
        lines.append(
            f"  ⚠ ATTESTATION: {len(skipped_no_clone)} Repo(s) ohne lokalen Klon, "
            f"NICHT geprüft ({', '.join(sorted(skipped_no_clone))})"
        )
    lines.append(f"  TOP-{top_n} Delta ggü. Baseline (Kandidaten für /repo-optimize):")
    for name in flagged:
        lines.append(f"    + {name}: Δ{deltas[name]:+d} (debt_total={current_totals[name]})")
    if not flagged:
        lines.append("    — keine Zuwächse ggü. Baseline")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--github-dir", default=str(Path.home() / "github"))
    ap.add_argument("--canonical", default=str(CANONICAL))
    ap.add_argument("--repos", default=None,
                     help="Komma-Liste; überschreibt Registry-Discovery (für Tests/Teilscans)")
    ap.add_argument("--baseline", default=None,
                     help="Pfad zur vorherigen debt_total-JSON (Delta-Basis)")
    ap.add_argument("--out", default=None,
                     help="Pfad zum Schreiben der neuen Ergebnis-JSON (zusätzlich zu stdout)")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    a = ap.parse_args()

    github_dir = Path(a.github_dir)
    if a.repos:
        names = [r.strip() for r in a.repos.split(",") if r.strip()]
        repos = {n: github_dir / n for n in names if (github_dir / n / ".git").exists()}
        skipped_no_clone = [n for n in names if not (github_dir / n / ".git").exists()]
        skipped_archived = []
    else:
        repos, skipped_no_clone, skipped_archived = discover_repos(github_dir, Path(a.canonical))

    results = {name: scan_repo(path) for name, path in repos.items()}
    current_totals = {name: r["debt_total"] for name, r in results.items()}

    baseline = {}
    if a.baseline and Path(a.baseline).exists():
        baseline = json.loads(Path(a.baseline).read_text()).get("debt_total", {})
    deltas = compute_deltas(current_totals, baseline)

    out = {
        "debt_total": current_totals,
        "signals": {name: r["signals"] for name, r in results.items()},
        "delta_vs_baseline": deltas,
        "skipped_no_local_clone": sorted(skipped_no_clone),
        "skipped_archived": sorted(skipped_archived),
    }
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))

    if a.format == "json":
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(render_text(current_totals, deltas, skipped_no_clone, skipped_archived, a.top))

    sys.exit(0)  # advisory, kein Gate — der Radar flaggt nur (KONZ-019 L5, kein Coding-Agent)


if __name__ == "__main__":
    main()
