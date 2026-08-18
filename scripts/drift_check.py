#!/usr/bin/env python3
"""drift_check.py — Cross-Repo Template Drift Detection

Erkennt, welche Repos vom Platform-Standard abgewichen sind:
  - Veraltete GitHub Actions Versionen (@v3 statt @v4)
  - Fehlende Pflicht-Dateien (Dockerfile, docker-compose.prod.yml, ...)
  - Veraltete iil-Packages (z.B. iil-testkit@0.3.x statt @0.4.x)
  - Fehlende Health-Endpoints (/livez/, /healthz/)
  - CI-Workflow nutzt alten Pattern (reusable workflow fehlt)
  - Python-Version veraltet (3.10 statt 3.12)
  - Fehlende Sicherheits-Patterns (GITHUB_TOKEN ohne least-privilege)

Verwendung:
    python3 scripts/drift_check.py                   # alle Django-Repos
    python3 scripts/drift_check.py coach-hub         # einzelnes Repo
    python3 scripts/drift_check.py --severity=error  # nur kritische Drifts
    python3 scripts/drift_check.py --format=json     # JSON-Output
    python3 scripts/drift_check.py --fix-hints       # Zeigt Fix-Befehle

SSoT: scripts/repo-registry.yaml + GitHub API + PyPI
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml fehlt — pip install pyyaml", file=sys.stderr)
    sys.exit(1)

PLATFORM_ROOT = Path(__file__).parent.parent
REGISTRY_FILE = PLATFORM_ROOT / "scripts" / "repo-registry.yaml"
GITHUB_ORG = "achimdehnert"  # Fallback-Default für Repos ohne canonical.yaml-Eintrag

# Owner-Auflösung aus der kanonischen Registry (ADR-234/255) statt Fleet-weitem
# Hardcode — iilgmbh-Repos (risk-hub, ausschreibungs-hub, ...) und meiki-lra/
# ttz-lif-Repos haben ein eigenes `github:`-Feld in registry/canonical.yaml,
# das bislang ignoriert wurde (FUNC-1, #1202).
sys.path.insert(0, str(PLATFORM_ROOT / "tools"))
import registry_api as reg  # noqa: E402


def _repo_owner(repo: str) -> str:
    """GitHub-Owner für EIN Fleet-Repo, mit Fallback auf GITHUB_ORG (F-5: owner()
    liefert None für unbekannte/nicht-registrierte Namen — kein harter Fail hier,
    da drift_check.py auch mit Repo-Namen außerhalb der Registry aufgerufen wird."""
    return reg.owner(repo) or GITHUB_ORG


# ── Drift-Regeln (erweiterbar ohne Code-Änderung) ─────────────────────────────

# Erstes Element ist entweder ein Pfad oder ein Tupel gleichwertiger Kandidaten —
# erfüllt ist die Regel, sobald EINER existiert. Beide Docker-Layouts sind im
# Fleet gelebte Praxis (Wurzel: dev-hub, weltenhub, trading-hub · docker/app:
# risk-hub, odoo-hub, pptx-hub), keines davon ist ein Ausreißer (#1469).
REQUIRED_FILES_DJANGO = [
    (("Dockerfile", "docker/app/Dockerfile"), "error", "Docker Build fehlt"),
    ("docker-compose.prod.yml", "error", "Prod-Compose fehlt"),
    (".env.example", "warn", ".env.example fehlt — neue Devs verloren"),
    ("pyproject.toml", "warn", "pyproject.toml fehlt — kein pytest-Config"),
    ("requirements.txt", "error", "requirements.txt fehlt"),
    ("requirements-test.txt", "warn", "requirements-test.txt fehlt"),
    ("tests/conftest.py", "warn", "Kein Test-Scaffold — run gen_test_scaffold.py"),
    (".github/workflows/ci.yml", "warn", "Kein CI-Workflow"),
]

REQUIRED_FILE_CONTENT_CHECKS = [
    # Das Muster ist owner-agnostisch und trifft weiterhin, seit platforms Kopie
    # retired ist (#1423) — die Fleet ruft iilgmbh/shared-ci/..._ci-python.yml.
    # Nur der Meldungstext nannte platform noch als Quelle.
    (
        ".github/workflows/ci.yml",
        r"_ci-python\.yml",
        "warn",
        "CI nutzt nicht shared-ci/_ci-python.yml (reusable workflow)",
    ),
    ("Dockerfile", r"python:3\.12", "warn", "Dockerfile nutzt nicht Python 3.12"),
    (
        "docker-compose.prod.yml",
        r"env_file",
        "error",
        "docker-compose.prod.yml ohne env_file (ADR-022 violation)",
    ),
    (
        "docker-compose.prod.yml",
        r"unless-stopped",
        "warn",
        "docker-compose.prod.yml ohne restart: unless-stopped",
    ),
    (
        "requirements.txt",
        r"(iil-|aifw|promptfw)",
        "info",
        "Kein iil-Package gefunden — ok wenn kein LLM/Test-Kit benötigt",
    ),
]

BANNED_PATTERNS = [
    (
        r"StrictHostKeyChecking=no",
        "error",
        "StrictHostKeyChecking=no gefunden (SD-001 CRITICAL)",
    ),
    (r"88\.198\.191\.108", "error", "Hardcoded Server-IP (SD-001 CRITICAL)"),
    (
        r"UUIDField\(primary_key=True\)",
        "error",
        "UUID als PK (DB-001 CRITICAL — nur BigAutoField erlaubt)",
    ),
    (
        r"environment:\s*\n(\s+\w+:\s*\$\{)",
        "warn",
        "docker-compose environment: mit ${VAR} (ADR-022 — env_file nutzen)",
    ),
    (r"sqlite", "warn", "SQLite-Referenz gefunden — PostgreSQL ist Pflicht (ADR-009)"),
]

# Banned-Patterns mit File-Scope: feuern NUR in der genannten Datei (nicht über
# alle gescannten Dateien wie BANNED_PATTERNS). Nötig z.B. für HEALTHCHECK, das
# im Dockerfile verboten (ADR-078), als compose `healthcheck:`-Key aber erlaubt
# ist — eine globale Regel würde sonst die Msg „…im Dockerfile … in
# docker-compose.prod.yml" produzieren. (file, pattern, severity, msg)
BANNED_FILE_PATTERNS = [
    (
        "Dockerfile",
        r"^HEALTHCHECK\b",
        "error",
        "HEALTHCHECK im Dockerfile (ADR-078 — Healthcheck gehört pro-Service in "
        "docker-compose.prod.yml, nicht ins image-globale Dockerfile)",
    ),
]

ACTIONS_VERSION_MAP = {
    "actions/checkout": "v4",
    "actions/setup-python": "v5",
    "actions/upload-artifact": "v4",
    "actions/download-artifact": "v4",
    "actions/cache": "v4",
    "docker/build-push-action": "v7",
    "docker/login-action": "v3",
}

IIL_PACKAGES_LATEST: dict[str, str] = {}  # befüllt via PyPI


# ── Datenmodell ──────────────────────────────────────────────────────────────


@dataclass
class DriftItem:
    rule: str
    severity: str  # error | warn | info
    file: str
    message: str
    fix_hint: str = ""

    @property
    def icon(self) -> str:
        return {"error": "🔴", "warn": "🟡", "info": "ℹ️"}.get(self.severity, "❓")


@dataclass
class RepoDrift:
    repo: str
    repo_type: str
    drifts: list[DriftItem] = field(default_factory=list)
    error: str = ""

    @property
    def errors(self) -> list[DriftItem]:
        return [d for d in self.drifts if d.severity == "error"]

    @property
    def warnings(self) -> list[DriftItem]:
        return [d for d in self.drifts if d.severity == "warn"]

    @property
    def status_icon(self) -> str:
        if self.error:
            return "⚠️"
        if self.errors:
            return "🔴"
        if self.warnings:
            return "🟡"
        return "✅"

    @property
    def drift_score(self) -> int:
        """0 = kein Drift. Je höher desto schlechter."""
        return len(self.errors) * 3 + len(self.warnings)


# ── GitHub API ────────────────────────────────────────────────────────────────


def _github_token() -> str:
    for env_var in ("GITHUB_TOKEN", "PROJECT_PAT"):
        if v := os.environ.get(env_var):
            return v
    path = Path.home() / ".secrets" / "github_PAT"
    return path.read_text().strip() if path.exists() else ""


def _api_get(path: str, token: str) -> dict | list | None:
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"token {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return None if e.code == 404 else None
    except Exception:
        return None


def _get_file_content(repo: str, path: str, token: str) -> str | None:
    data = _api_get(f"/repos/{_repo_owner(repo)}/{repo}/contents/{path}", token)
    if not isinstance(data, dict) or "content" not in data:
        return None
    try:
        return base64.b64decode(data["content"]).decode(errors="replace")
    except Exception:
        return None


def _get_dir_files(repo: str, path: str, token: str) -> list[str]:
    items = _api_get(f"/repos/{_repo_owner(repo)}/{repo}/contents/{path}", token)
    if not isinstance(items, list):
        return []
    return [i["name"] for i in items if isinstance(i, dict) and i.get("type") == "file"]


def _fetch_pypi_latest(package: str) -> str | None:
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/{package}/json", timeout=5
        ) as r:
            return json.loads(r.read())["info"]["version"]
    except Exception:
        return None


def _load_iil_latest() -> dict[str, str]:
    packages = [
        "iil-testkit",
        "aifw",
        "iil-promptfw",
        "iil-authoringfw",
        "iil-weltenfw",
        "iil-nl2cadfw",
    ]
    result = {}
    for pkg in packages:
        if v := _fetch_pypi_latest(pkg):
            result[pkg] = v
    return result


# ── Drift-Checks ──────────────────────────────────────────────────────────────


def _pyproject_declares_dependencies(content: str) -> bool:
    """Deklariert das pyproject im ``[project]``-Abschnitt einen ``dependencies``-Key?

    Bewusst nur ``[project]`` — ein ``dependencies`` unter ``[tool.poetry]`` oder in
    einer verschachtelten Tabelle beantwortet die Frage nicht, ob das Paket seine
    Laufzeit-Abhängigkeiten standardisiert trägt.
    """
    in_project = False
    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_project = line == "[project]"
            continue
        if in_project and re.match(r"dependencies\s*=", line):
            return True
    return False


def _requirements_covered_by_pyproject(repo: str, token: str) -> bool:
    """``requirements.txt`` ist entbehrlich, wenn das pyproject die Deps trägt.

    Nicht als Alternativpfad in REQUIRED_FILES_DJANGO gelöst: ``pyproject.toml``
    hat praktisch jedes Repo, ein reiner Existenz-Check machte die Regel vakuum.
    Geprüft wird deshalb der Inhalt (#1469).
    """
    content = _get_file_content(repo, "pyproject.toml", token)
    return content is not None and _pyproject_declares_dependencies(content)


# Regeln, die auch ohne die Datei erfüllt sein können. Schlüssel ist der
# kanonische (erste) Pfad des Eintrags.
ALTERNATIVE_SATISFIERS = {
    "requirements.txt": _requirements_covered_by_pyproject,
}


def check_required_files(repo: str, token: str) -> list[DriftItem]:
    drifts = []
    for entry, severity, msg in REQUIRED_FILES_DJANGO:
        candidates = (entry,) if isinstance(entry, str) else tuple(entry)
        canonical = candidates[0]

        # any() kurzschließt: liegt der erste Kandidat vor, entfällt der zweite
        # API-Call — und ein Repo mit BEIDEN Varianten erzeugt kein Doppel-Finding.
        if any(_get_file_content(repo, p, token) is not None for p in candidates):
            continue

        satisfier = ALTERNATIVE_SATISFIERS.get(canonical)
        if satisfier is not None and satisfier(repo, token):
            continue

        hint = f"Erstellen: touch {canonical}  (oder gen_test_scaffold.py nutzen)"
        if len(candidates) > 1:
            hint += f" — alternativ akzeptiert: {', '.join(candidates[1:])}"
        drifts.append(
            DriftItem(
                rule="required-file",
                severity=severity,
                file=canonical,
                message=msg,
                fix_hint=hint,
            )
        )
    return drifts


def check_file_contents(repo: str, token: str) -> list[DriftItem]:
    drifts = []
    for filepath, pattern, severity, msg in REQUIRED_FILE_CONTENT_CHECKS:
        content = _get_file_content(repo, filepath, token)
        if content is None:
            continue
        if not re.search(pattern, content):
            drifts.append(
                DriftItem(
                    rule="file-content",
                    severity=severity,
                    file=filepath,
                    message=msg,
                )
            )
    return drifts


def check_banned_patterns(repo: str, token: str) -> list[DriftItem]:
    """Scannt alle *.py, *.yml, Dockerfile auf verbotene Muster."""
    drifts = []
    files_to_check = []

    # Gezielte Dateien statt alle (API-effizient)
    for scan_path in [
        "Dockerfile",
        "docker-compose.prod.yml",
        ".github/workflows/ci.yml",
        ".env.example",
    ]:
        if (content := _get_file_content(repo, scan_path, token)) is not None:
            files_to_check.append((scan_path, content))

    for filepath, content in files_to_check:
        for pattern, severity, msg in BANNED_PATTERNS:
            if re.search(pattern, content, re.MULTILINE):
                drifts.append(
                    DriftItem(
                        rule="banned-pattern",
                        severity=severity,
                        file=filepath,
                        message=f"{msg} in {filepath}",
                    )
                )
        # File-scoped Patterns nur in der passenden Datei prüfen
        for scoped_file, pattern, severity, msg in BANNED_FILE_PATTERNS:
            if filepath == scoped_file and re.search(pattern, content, re.MULTILINE):
                drifts.append(
                    DriftItem(
                        rule="banned-file-pattern",
                        severity=severity,
                        file=filepath,
                        message=f"{msg} in {filepath}",
                    )
                )
    return drifts


def check_actions_versions(repo: str, token: str) -> list[DriftItem]:
    """Prüft ob GitHub Actions auf aktuellen Versionen (@v4 etc.) sind."""
    drifts = []
    workflow_files = _get_dir_files(repo, ".github/workflows", token)

    for wf_file in workflow_files:
        content = _get_file_content(repo, f".github/workflows/{wf_file}", token)
        if not content:
            continue
        for action, expected_version in ACTIONS_VERSION_MAP.items():
            pattern = rf"{re.escape(action)}@(v\d+)"
            for match in re.finditer(pattern, content):
                found_version = match.group(1)
                if found_version != expected_version:
                    drifts.append(
                        DriftItem(
                            rule="actions-version",
                            severity="warn",
                            file=f".github/workflows/{wf_file}",
                            message=f"{action}@{found_version} → sollte @{expected_version} sein",
                            fix_hint=f"sed -i 's/{action}@{found_version}/{action}@{expected_version}/g' .github/workflows/{wf_file}",
                        )
                    )
    return drifts


def check_iil_package_versions(
    repo: str, token: str, latest: dict[str, str]
) -> list[DriftItem]:
    """Prüft ob iil-Packages auf aktuellen Versionen pinned sind."""
    drifts = []
    for req_file in ["requirements.txt", "requirements-test.txt"]:
        content = _get_file_content(repo, req_file, token)
        if not content:
            continue
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkg_name = re.split(r"[>=<!;\[]", line)[0].strip()
            if pkg_name not in latest:
                continue
            match = re.search(r">=(\d+\.\d+\.\d+)", line)
            if match:
                pinned = match.group(1)
                current = latest[pkg_name]
                if pinned != current:
                    pinned_parts = tuple(int(x) for x in pinned.split("."))
                    current_parts = tuple(int(x) for x in current.split("."))
                    if current_parts > pinned_parts:
                        drifts.append(
                            DriftItem(
                                rule="iil-version",
                                severity="warn",
                                file=req_file,
                                message=f"{pkg_name}>={pinned} — neu: >={current}",
                                fix_hint=f"sed -i 's/{pkg_name}>={pinned}/{pkg_name}>={current}/' {req_file}",
                            )
                        )
    return drifts


def check_python_version(repo: str, token: str) -> list[DriftItem]:
    """Prüft ob Python 3.12 in CI und Dockerfile verwendet wird."""
    drifts = []
    for filepath in ["Dockerfile", ".github/workflows/ci.yml"]:
        content = _get_file_content(repo, filepath, token)
        if not content:
            continue
        version_match = re.search(r"python[:\s]+['\"]?3\.(\d+)", content, re.IGNORECASE)
        if version_match:
            minor = int(version_match.group(1))
            if minor < 12:
                drifts.append(
                    DriftItem(
                        rule="python-version",
                        severity="warn",
                        file=filepath,
                        message=f"Python 3.{minor} statt 3.12 — Update empfohlen",
                        fix_hint=f"python:3.{minor} → python:3.12 in {filepath}",
                    )
                )
    return drifts


# ── shared-ci Tag-Drift (🌀 Drift-Klasse „Tag ≠ main") ───────────────────────
#
# Dreimal passiert (zuletzt 2026-06-12, ADR-242 Phase 3): ein shared-ci-Tag
# wurde VOR einem Fix in der kanonischen platform-Quelle geschnitten bzw.
# Consumer pinnen veraltete Tags — Doku behauptet dann einen Stand, den die
# Flotte real nicht hat (deploy_runs_on-Regression #461; gate-Job fehlte in
# v1.0.2 trotz #548-Behauptung). Zwei Regeln:
#   shared-ci-tag-outdated (warn):  Consumer pinnt nicht-neuesten Tag
#   shared-ci-tag-stale    (error): neuester Tag ≠ platform-main-Kanon

SHARED_CI_REPO = "iilgmbh/shared-ci"
SHARED_CI_PIN_RE = re.compile(
    r"iilgmbh/shared-ci/\.github/workflows/([\w.-]+\.ya?ml)@([\w./-]+)"
)
_SHARED_CI_STATE: dict | None = None

# ── Kanon-Abgleich: strukturell, nicht per Text-Ersetzung ────────────────────
#
# Beim Portieren platform → shared-ci werden zwei Dinge umgeschrieben: der
# Repo-Pfad (`uses:`, `with.repository`) und das lokale Checkout-Verzeichnis
# (`with.path` plus jeder Aufruf darunter). Beides ist Mechanik, kein Drift.
#
# Naheliegend — und falsch — ist, das per `str.replace()` über den ganzen
# Dateiinhalt zurückzudrehen. Am realen Bestand (9 vergleichbare Dateien,
# gemessen 2026-08-04) erzeugt genau das drei Fehlalarme, die keine Token-Liste
# heilt, weil sie in die Sprache statt in die Struktur greift:
#
#   1. Kommentar-Prosa: `_ci-pypi.yml`/`validate-workflows.yml` unterscheiden
#      sich NUR in einem Kommentar, in dem "iilgmbh/shared-ci" der Gegenstand
#      des Satzes ist ("SSoT ist iilgmbh/shared-ci"). Die Ersetzung schreibt den
#      Satz um und erzeugt die Abweichung selbst.
#   2. Freitext mit Repo-Referenz: in `handoff-banner-gate.yml` steht die
#      Issue-Referenz "achimdehnert/platform#913" in einem Test-Fixture — auf
#      BEIDEN Seiten korrekt gleich, bis eine Ersetzung sie anfasst.
#   3. Verzeichnisname als gewöhnliches Wort: der Kanon von
#      `deploy-config-lint.yml` checkt nach `path: platform` aus und nennt den
#      Step "Checkout platform (Lint-Script)". Eine Token-Ersetzung trifft auch
#      den Step-Namen. Dazu kommen mindestens drei Kanon-Schreibweisen
#      (`_platform_checks`, `platform`, `_platform`) — eine gepflegte Liste
#      hinkt dieser Menge immer hinterher.
#
# Deshalb wird verglichen, was der Workflow TUT, nicht wie er formuliert ist:
# beide Seiten werden als YAML geladen (Kommentare fallen damit weg — sie laufen
# nicht) und nur an strukturell bedeutsamen Stellen normalisiert. Das
# Checkout-Verzeichnis wird nicht geraten, sondern aus dem `actions/checkout`-
# Step der jeweiligen Seite gelesen.
_SELF_REPO = "<SELF_REPO>"
_SELF_DIR = "<SELF_DIR>"

# ── Dritte Port-Mechanik: der Waechter-Aufruf ────────────────────────────────
#
# Es gibt eine Umschreibung, die beim Portieren zwangslaeufig entsteht und die
# obige Normalisierung nicht kennt. `shared-ci` besitzt weder
# `tools/check_silent_failures.py` noch `scripts/checks/publish_gate_invariant.sh`
# — die liegen in platform. Ein `run:` darauf lief dort ins Leere (exit 127,
# Gate dauerhaft rot und damit blind, platform#1844). Die Loesung war die
# Composite-Action `.github/actions/workflow-guards`: shared-ci ruft die Pruefer
# dort auf, wo sie leben, platform ruft sie direkt auf.
#
# Beides TUT dasselbe. Ohne diese Zuordnung meldet der Vergleich zwei Dateien
# dauerhaft als stale, ohne dass es etwas zu beheben gaebe — und ein Error, der
# sich nicht schliessen laesst, wird zu Hintergrundrauschen. Genau dann uebersieht
# man den naechsten, der echt ist (platform#2049).
#
# Quelle der Zuordnung ist die Action selbst; `test_should_match_the_guard_action`
# haelt diese Tabelle dagegen, damit sie nicht still auseinanderlaeuft.
_GUARD_ACTION_PFAD = ".github/actions/workflow-guards"
_GUARD_SKRIPTE = {
    "silent-failures": "tools/check_silent_failures.py",
    "publish-gate": "scripts/checks/publish_gate_invariant.sh",
}
# Die Action installiert PyYAML selbst. Der direkte Aufrufer braucht einen
# eigenen Schritt dafuer — auch der ist Port-Mechanik, kein Verhaltensunterschied.
_GUARD_VORBEREITUNG_RE = re.compile(
    r"^\s*(python3?\s+-m\s+)?pip\s+install\b.*\bpyyaml\b", re.I | re.M
)


def _guard_marker(namen: list[str]) -> dict[str, list[str]]:
    return {"<GUARD>": sorted(set(namen))}


def _guard_aus_uses(step: dict) -> dict | None:
    """Der Waechter als Composite-Action-Aufruf — oder None."""
    if _GUARD_ACTION_PFAD not in str(step.get("uses", "")):
        return None
    mit = step.get("with") or {}
    checks = str(mit.get("checks", "both")) if isinstance(mit, dict) else "both"
    return _guard_marker(list(_GUARD_SKRIPTE) if checks == "both" else [checks])


def _guard_aus_run(step: dict) -> dict | None:
    """Derselbe Waechter als direkter Skript-Aufruf — oder None."""
    run = step.get("run")
    if not isinstance(run, str):
        return None
    treffer = [name for name, skript in _GUARD_SKRIPTE.items() if skript in run]
    return _guard_marker(treffer) if treffer else None


def _ist_guard_vorbereitung(step: dict) -> bool:
    """Ein Schritt, der NUR PyYAML fuer den Waechter bereitstellt."""
    run = step.get("run")
    if not isinstance(run, str) or step.get("uses"):
        return False
    zeilen = [z for z in run.splitlines() if z.strip()]
    return len(zeilen) == 1 and bool(_GUARD_VORBEREITUNG_RE.search(run))


def _normalisiere_guards(tree: Any) -> Any:
    """Ersetzt beide Aufrufformen des Waechters durch denselben Marker.

    Zusaetzlich fallen weg: der reine PyYAML-Vorbereitungsschritt und
    Pfad-Trigger auf die Waechter-Skripte — beide existieren nur auf der Seite,
    die die Skripte selbst besitzt.
    """
    if not isinstance(tree, dict):
        return tree
    tree = copy.deepcopy(tree)

    # `on:` wird von YAML 1.1 als bool True gelesen — beide Schluessel pruefen.
    for schluessel in ("on", True):
        ausloeser = tree.get(schluessel)
        if not isinstance(ausloeser, dict):
            continue
        for bedingung in ausloeser.values():
            if not isinstance(bedingung, dict):
                continue
            pfade = bedingung.get("paths")
            if isinstance(pfade, list):
                bedingung["paths"] = [
                    p for p in pfade if str(p) not in _GUARD_SKRIPTE.values()
                ]

    for job in (tree.get("jobs") or {}).values():
        if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
            continue
        neu = []
        for step in job["steps"]:
            if not isinstance(step, dict):
                neu.append(step)
                continue
            if _ist_guard_vorbereitung(step):
                continue
            marker = _guard_aus_uses(step) or _guard_aus_run(step)
            neu.append(marker if marker is not None else step)
        job["steps"] = neu
    return tree


def _eigenes_checkout_verzeichnis(tree: Any, repo: str) -> str | None:
    """`with.path` des Steps, der `repo` selbst auscheckt (oder None)."""
    if not isinstance(tree, dict):
        return None
    for job in (tree.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            mit = step.get("with") or {}
            if (
                str(step.get("uses", "")).startswith("actions/checkout")
                and isinstance(mit, dict)
                and str(mit.get("repository", "")) == repo
                and mit.get("path")
            ):
                return str(mit["path"])
    return None


def normalisiere_port(node: Any, repo: str, verzeichnis: str | None) -> Any:
    """Ersetzt Port-Mechanik durch Platzhalter — nur strukturell.

    Angefasst werden ausschliesslich: `uses:`-Refs auf das eigene Repo,
    `with.repository`, `with.path` und Pfad-Praefixe in `run:`/`script:`.
    Alles andere (Step-Namen, Freitext, Issue-Referenzen) bleibt unberuehrt.
    """
    if isinstance(node, list):
        return [normalisiere_port(v, repo, verzeichnis) for v in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for key, value in node.items():
        key = str(key)
        if key == "uses" and isinstance(value, str) and value.startswith(repo + "/"):
            out[key] = _SELF_REPO + "/" + value[len(repo) + 1 :]
        elif key == "with" and isinstance(value, dict):
            mit = dict(value)
            if str(mit.get("repository", "")) == repo:
                mit["repository"] = _SELF_REPO
            if verzeichnis and str(mit.get("path", "")) == verzeichnis:
                mit["path"] = _SELF_DIR
            out[key] = normalisiere_port(mit, repo, verzeichnis)
        elif key in ("run", "script") and isinstance(value, str) and verzeichnis:
            # Nur als Pfad-Praefix ersetzen: `_shared_ci/tools/x.py` ja,
            # das blosse Wort im Fliesstext nein.
            out[key] = re.sub(
                rf"(?<![\w/]){re.escape(verzeichnis)}/", _SELF_DIR + "/", value
            )
        else:
            out[key] = normalisiere_port(value, repo, verzeichnis)
    return out


def shared_ci_deckt_kanon(tagged: str, canonical: str) -> bool:
    """True, wenn Tag-Inhalt und platform-Kanon dasselbe TUN.

    Faellt auf exakten Textvergleich zurueck, wenn eine Seite nicht als YAML
    ladbar ist — lieber ein Fehlalarm als ein stillschweigend uebersehener
    Drift.
    """
    try:
        tag_tree = yaml.safe_load(tagged)
        kanon_tree = yaml.safe_load(canonical)
    except yaml.YAMLError:
        return tagged == canonical
    return _kanon_normalform(tag_tree, SHARED_CI_REPO) == _kanon_normalform(
        kanon_tree, f"{GITHUB_ORG}/platform"
    )


def _kanon_normalform(tree: Any, repo: str) -> Any:
    """Beide Port-Mechaniken in einem Zug: Pfade und Waechter-Aufruf."""
    return normalisiere_port(
        _normalisiere_guards(tree), repo, _eigenes_checkout_verzeichnis(tree, repo)
    )


def kanon_richtung(tagged: str, canonical: str) -> tuple[int, int]:
    """(nur im Tag, nur im Kanon) — Zeilen der normalisierten Baeume.

    Der Fix-Hinweis der Regel behauptete jahrelang eine Richtung ("platform nach
    shared-ci portieren"), die nirgends gemessen wurde. Am 2026-08-17 lag
    shared-ci in drei von fuenf Dateien VORNE; ein Port in Hinweis-Richtung
    haette dort echte Fixes geloescht (Docker-Anmeldungs-Isolierung,
    CF-Access-Kopfzeilen, ein Gate, ein 16 Monate neuerer Action-Pin).
    Deshalb wird die Richtung jetzt genannt statt geraten.
    """
    import difflib

    def zeilen(text: str, repo: str) -> list[str]:
        return json.dumps(
            _kanon_normalform(yaml.safe_load(text), repo),
            indent=1,
            sort_keys=True,
            default=str,
        ).splitlines()

    try:
        a = zeilen(canonical, f"{GITHUB_ORG}/platform")
        b = zeilen(tagged, SHARED_CI_REPO)
    except yaml.YAMLError:
        return (0, 0)
    diff = [
        z
        for z in difflib.unified_diff(a, b, n=0)
        if z.startswith(("+", "-")) and not z.startswith(("+++", "---"))
    ]
    return (
        sum(1 for z in diff if z[0] == "+"),
        sum(1 for z in diff if z[0] == "-"),
    )


def parse_shared_ci_pins(content: str) -> list[tuple[str, str]]:
    """Extrahiert (workflow-datei, ref) aller shared-ci-Pins aus YAML-Text."""
    return [(m.group(1), m.group(2)) for m in SHARED_CI_PIN_RE.finditer(content)]


def _semver_key(tag: str) -> tuple[int, ...] | None:
    m = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    return tuple(int(x) for x in m.groups()) if m else None


def latest_shared_ci_tag(tags: list[str]) -> str | None:
    """Höchster vX.Y.Z-Tag nach Semver (API-Reihenfolge ist nicht verlässlich)."""
    versioned = [(k, t) for t in tags if (k := _semver_key(t)) is not None]
    return max(versioned)[1] if versioned else None


def _get_content_at(owner_repo: str, path: str, ref: str, token: str) -> str | None:
    data = _api_get(f"/repos/{owner_repo}/contents/{path}?ref={ref}", token)
    if not isinstance(data, dict) or "content" not in data:
        return None
    try:
        return base64.b64decode(data["content"]).decode(errors="replace")
    except Exception:
        return None


def _shared_ci_state(token: str) -> dict:
    """Einmal pro Lauf: neuester Tag + Abgleich Tag-Inhalt vs platform-Kanon."""
    global _SHARED_CI_STATE
    if _SHARED_CI_STATE is not None:
        return _SHARED_CI_STATE
    tags_data = _api_get(f"/repos/{SHARED_CI_REPO}/tags", token) or []
    tags = [t.get("name", "") for t in tags_data if isinstance(t, dict)]
    latest = latest_shared_ci_tag(tags)
    stale_files: list[str] = []
    richtungen: dict[str, tuple[int, int]] = {}
    if latest:
        listing = (
            _api_get(
                f"/repos/{SHARED_CI_REPO}/contents/.github/workflows?ref={latest}",
                token,
            )
            or []
        )
        for item in listing:
            if not isinstance(item, dict) or not item.get("name", "").endswith(
                (".yml", ".yaml")
            ):
                continue
            name = item["name"]
            canonical = _get_content_at(
                f"{GITHUB_ORG}/platform", f".github/workflows/{name}", "main", token
            )
            if canonical is None:
                continue  # existiert nur in shared-ci — kein Kanon-Abgleich
            tagged = _get_content_at(
                SHARED_CI_REPO, f".github/workflows/{name}", latest, token
            )
            # Strukturell vergleichen, nicht per Text-Ersetzung — Begruendung
            # und Messung siehe `shared_ci_deckt_kanon`.
            if tagged is not None and not shared_ci_deckt_kanon(tagged, canonical):
                stale_files.append(name)
                richtungen[name] = kanon_richtung(tagged, canonical)
    _SHARED_CI_STATE = {
        "latest_tag": latest,
        "stale_files": stale_files,
        "richtungen": richtungen,
    }
    return _SHARED_CI_STATE


def check_shared_ci_tag_drift(
    repo: str, token: str, state: dict | None = None
) -> list[DriftItem]:
    """Prüft shared-ci-Pins des Repos gegen neuesten Tag + platform-Kanon."""
    drifts = []
    pins: list[tuple[str, str, str]] = []  # (wf_file, pinned_file, ref)
    for wf_file in _get_dir_files(repo, ".github/workflows", token):
        content = _get_file_content(repo, f".github/workflows/{wf_file}", token)
        if not content:
            continue
        for pinned_file, ref in parse_shared_ci_pins(content):
            pins.append((wf_file, pinned_file, ref))
    if not pins:
        return drifts

    if state is None:
        state = _shared_ci_state(token)
    latest = state.get("latest_tag")
    stale_files = state.get("stale_files", [])

    for wf_file, pinned_file, ref in pins:
        if latest and ref != latest and _semver_key(ref) is not None:
            drifts.append(
                DriftItem(
                    rule="shared-ci-tag-outdated",
                    severity="warn",
                    file=f".github/workflows/{wf_file}",
                    message=f"shared-ci/{pinned_file}@{ref} — neuester Tag: {latest}",
                    fix_hint=f"sed -i 's#{pinned_file}@{ref}#{pinned_file}@{latest}#' .github/workflows/{wf_file}",
                )
            )
        if pinned_file in stale_files:
            nur_tag, nur_kanon = state.get("richtungen", {}).get(pinned_file, (0, 0))
            if nur_tag > nur_kanon:
                richtung = (
                    f"shared-ci ist VORAUS ({nur_tag} zu {nur_kanon} Zeilen) — "
                    "Kanon nachziehen, NICHT portieren"
                )
                hinweis = (
                    "shared-ci hat den neueren Stand: dessen Aenderungen nach "
                    "platform/.github/workflows uebernehmen"
                )
            elif nur_kanon > nur_tag:
                richtung = (
                    f"platform ist voraus ({nur_kanon} zu {nur_tag} Zeilen) — "
                    "shared-ci nachziehen + neuen Tag schneiden"
                )
                hinweis = "platform .github/workflows nach shared-ci portieren + neuen Tag schneiden"
            else:
                richtung = "beide Seiten haben Eigenes — Datei fuer Datei entscheiden"
                hinweis = "keine Seite ist Obermenge: zusammenfuehren, nicht portieren"
            drifts.append(
                DriftItem(
                    rule="shared-ci-tag-stale",
                    severity="error",
                    file=f".github/workflows/{wf_file}",
                    message=(
                        f"shared-ci@{latest}/{pinned_file} ≠ platform-main-Kanon — "
                        f"{richtung} (🌀 Tag≠main)"
                    ),
                    fix_hint=hinweis,
                )
            )
    return drifts


# ── Haupt-Scan ────────────────────────────────────────────────────────────────

SCAFFOLD_TYPES: frozenset[str] = frozenset({"django", "agent", "bot"})


def check_repo(
    repo: str, repo_type: str, token: str, iil_latest: dict[str, str]
) -> RepoDrift:
    drift = RepoDrift(repo=repo, repo_type=repo_type)

    # Repo erreichbar?
    if _api_get(f"/repos/{_repo_owner(repo)}/{repo}", token) is None:
        drift.error = "Repo nicht gefunden oder privat"
        return drift

    # Docker/requirements checks only apply to deployable scaffold repos
    if repo_type in SCAFFOLD_TYPES:
        drift.drifts.extend(check_required_files(repo, token))
        drift.drifts.extend(check_file_contents(repo, token))

    drift.drifts.extend(check_banned_patterns(repo, token))
    drift.drifts.extend(check_actions_versions(repo, token))
    drift.drifts.extend(check_iil_package_versions(repo, token, iil_latest))
    drift.drifts.extend(check_python_version(repo, token))
    drift.drifts.extend(check_shared_ci_tag_drift(repo, token))

    return drift


# ── Output ───────────────────────────────────────────────────────────────────


def print_report(
    drifts: list[RepoDrift], severity_filter: str, show_fix_hints: bool
) -> None:
    SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}
    min_level = SEVERITY_ORDER.get(severity_filter, 2)

    print(
        f"\n## Platform Drift Check — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
    )

    total_errors = sum(len(r.errors) for r in drifts)
    total_warns = sum(len(r.warnings) for r in drifts)
    clean = sum(1 for r in drifts if r.drift_score == 0 and not r.error)

    for repo_drift in sorted(drifts, key=lambda x: -x.drift_score):
        filtered = [
            d
            for d in repo_drift.drifts
            if SEVERITY_ORDER.get(d.severity, 2) <= min_level
        ]
        if not filtered and not repo_drift.error and severity_filter != "info":
            continue

        print(
            f"{repo_drift.status_icon}  **{repo_drift.repo}** ({repo_drift.repo_type})"
        )
        if repo_drift.error:
            print(f"    ⚠️  {repo_drift.error}")
        for d in sorted(filtered, key=lambda x: SEVERITY_ORDER.get(x.severity, 2)):
            print(f"    {d.icon} [{d.rule}] {d.file}: {d.message}")
            if show_fix_hints and d.fix_hint:
                print(f"       → {d.fix_hint}")
        print()

    print(f"{'=' * 70}")
    print(
        f"Repos: {len(drifts)}  |  ✅ Kein Drift: {clean}  |  🔴 Errors: {total_errors}  |  🟡 Warns: {total_warns}"
    )

    # Priorisierte Fix-Liste
    all_errors = [(r.repo, d) for r in drifts for d in r.errors]
    if all_errors:
        print(f"\n### 🔴 Priorität 1 — Sofort fixen ({len(all_errors)} errors):")
        for repo, d in sorted(all_errors, key=lambda x: x[0]):
            print(f"  {repo}: {d.file} — {d.message}")


def print_github_summary(drifts: list[RepoDrift]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a") as f:
        f.write("## Platform Drift Check\n\n")
        f.write("| Repo | Status | Errors | Warnings |\n")
        f.write("|------|--------|--------|----------|\n")
        for r in sorted(drifts, key=lambda x: -x.drift_score):
            f.write(
                f"| {r.status_icon} {r.repo} | {r.repo_type} | {len(r.errors)} | {len(r.warnings)} |\n"
            )


def print_json_output(drifts: list[RepoDrift]) -> None:
    out = []
    for r in drifts:
        out.append(
            {
                "repo": r.repo,
                "type": r.repo_type,
                "status": r.status_icon,
                "drift_score": r.drift_score,
                "errors": len(r.errors),
                "warnings": len(r.warnings),
                "drifts": [
                    {
                        "rule": d.rule,
                        "severity": d.severity,
                        "file": d.file,
                        "message": d.message,
                        "fix_hint": d.fix_hint,
                    }
                    for d in r.drifts
                ],
            }
        )
    print(json.dumps(out, indent=2))


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Platform Cross-Repo Drift Detection")
    parser.add_argument("repos", nargs="*", help="Repos (leer = alle Django)")
    parser.add_argument(
        "--severity",
        choices=["error", "warn", "info"],
        default="warn",
        help="Minimaler Report-Level",
    )
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--fix-hints", action="store_true", help="Fix-Befehle anzeigen")
    parser.add_argument(
        "--fail-on-error", action="store_true", help="Exit 1 wenn Error-Drifts gefunden"
    )
    parser.add_argument(
        "--skip-pypi",
        action="store_true",
        help="PyPI-Versionscheck überspringen (offline)",
    )
    args = parser.parse_args()

    registry = yaml.safe_load(REGISTRY_FILE.read_text()).get("repos", {})
    SCAFFOLD_TYPES = {"django", "agent", "bot"}

    targets = (
        {r: registry.get(r, {"type": "unknown"}) for r in args.repos}
        if args.repos
        else {
            n: p
            for n, p in registry.items()
            if isinstance(p, dict)
            and p.get("type") in SCAFFOLD_TYPES
            and n != "platform"
        }
    )

    token = _github_token()
    if not token:
        print(
            "WARN: Kein GitHub-Token — nur öffentliche Repos scanbar", file=sys.stderr
        )

    print(f"\n🔍  Drift Check — {len(targets)} Repos", flush=True)

    iil_latest: dict[str, str] = {}
    if not args.skip_pypi:
        print("   PyPI-Versionen laden...", end="", flush=True)
        iil_latest = _load_iil_latest()
        print(f" {len(iil_latest)} Packages geladen")

    results: list[RepoDrift] = []
    for repo, props in targets.items():
        repo_type = props.get("type", "?") if isinstance(props, dict) else "?"
        print(f"  {repo}...", end="", flush=True)
        result = check_repo(repo, repo_type, token, iil_latest)
        icon = result.status_icon
        print(f" {icon} ({len(result.errors)}E, {len(result.warnings)}W)")
        results.append(result)

    if args.format == "json":
        print_json_output(results)
    else:
        print_report(results, args.severity, args.fix_hints)

    print_github_summary(results)

    if args.fail_on_error:
        total_errors = sum(len(r.errors) for r in results)
        if total_errors:
            print(f"\nExit 1: {total_errors} kritische Drift-Errors", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
