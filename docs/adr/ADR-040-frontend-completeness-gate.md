---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-040: Frontend Completeness Gate

| Metadata | Value |
|----------|-------|
| **Status** | Accepted |
| **Date** | 2026-02-16 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-009 (Deployment Architecture), PLATFORM_ARCHITECTURE_MASTER.md |

---

## 1. Context

### 1.1 Problem Statement

AI-gestützte Codegenerierung (Windsurf, Cursor, Claude Code) liefert bei Frontend-Aufgaben systematisch unvollständige Ergebnisse. Die KI meldet "Fertig", obwohl wesentliche UI-Elemente fehlen — Buttons, Formulare, Navigations-Komponenten, HTMX-Attribute oder ganze Template-Partials werden ausgelassen. Dieses Problem ist plattformübergreifend dokumentiert und betrifft alle BF Agent Platform Applikationen.

### 1.2 Business Impact

| Auswirkung | Schweregrad | Beschreibung |
|------------|-------------|--------------|
| Zeitverlust durch Nacharbeit | **HOCH** | Jede KI-Session erfordert manuelles Audit fehlender Elemente |
| Deployment defekter UIs | **KRITISCH** | Fehlende Elemente in Produktion ohne automatisierte Prüfung |
| Vertrauensverlust in KI-Tooling | **MITTEL** | Entwickler verlieren Vertrauen, nutzen KI-Tools weniger effektiv |
| Inkonsistente UI-Qualität | **HOCH** | Unterschiedliche Vollständigkeit je nach KI-Session |
| Regressionsgefahr | **MITTEL** | Bestehende Elemente werden bei Änderungen unbemerkt entfernt |

### 1.3 Betroffene Applikationen

| Application | Frontend-Stack | Template-Count (geschätzt) | HTMX-Nutzung |
|-------------|---------------|---------------------------|---------------|
| BF Agent | Django + HTMX + Alpine.js | ~80 Templates | Intensiv |
| Travel-Beat | Django + HTMX | ~120 Templates | Intensiv |
| Risk-Hub | Django + HTMX | ~40 Templates | Moderat |
| CAD-Hub | Django + HTMX | ~30 Templates | Moderat |
| MCP-Hub | Django + HTMX | ~25 Templates | Leicht |

### 1.4 Root Cause Analysis

Die Ursachen für unvollständige KI-generierte Frontends lassen sich in vier Kategorien einteilen:

**1. Context-Window-Limitierung:** Die KI verliert bei komplexen UIs den Überblick über bereits definierte Anforderungen, besonders wenn viele Komponenten gleichzeitig generiert werden sollen.

**2. Fehlende Verifikationsschleife:** Es existiert kein automatisierter Feedback-Mechanismus, der der KI mitteilt, welche Elemente noch fehlen — die KI "halluziniert" Vollständigkeit.

**3. Keine maschinenlesbare Spezifikation:** Anforderungen werden als Freitext formuliert, nicht als prüfbare Kontrakte. Die KI kann nicht gegen eine formale Spec validieren.

**4. Keine Test-First-Disziplin:** Ohne vorab definierte Tests existiert kein objektives Kriterium für "fertig".

### 1.5 Requirements

| Requirement | Priorität | Begründung |
|-------------|-----------|------------|
| Maschinenlesbares UI-Manifest | **HOCH** | Single Source of Truth für alle erwarteten Elemente |
| Automatisierter Completeness-Check | **HOCH** | Sofortige Erkennung fehlender Elemente nach Generierung |
| Playwright E2E-Tests als Gate | **HOCH** | Browser-basierte Verifikation inkl. HTMX-Interaktionen |
| CI/CD-Integration | **HOCH** | Kein Deployment ohne grüne Completeness-Tests |
| Pre-Commit Hook | **MITTEL** | Lokale Prüfung vor jedem Commit |
| KI-Prompt-Strategie | **MITTEL** | Strukturierte Prompts mit Manifest-Referenz |
| Django/HTMX-spezifische Prüfungen | **HOCH** | hx-get, hx-post, hx-target, hx-swap Attribute |
| Inkrementelle Adoption | **MITTEL** | Schrittweise Einführung pro App, kein Big-Bang |

---

## 2. Decision

### 2.1 Architecture Choice

**Wir implementieren ein zweistufiges Frontend Completeness Gate**, das zwei komplementäre Strategien kombiniert:

**Stufe 1 — UI-Manifest + Static Completeness Checker (Option A):**
Maschinenlesbares YAML-Manifest definiert alle erwarteten Seiten, Komponenten und Elemente. Ein Python-basierter Checker prüft den generierten Code statisch gegen das Manifest. Schnell, ohne Browser, ideal als erster Filter.

**Stufe 2 — Playwright E2E Tests als Acceptance Gate (Option C):**
Test-First-Ansatz mit `pytest-playwright` und `pytest-django`. Tests werden *vor* der Codegenerierung geschrieben und prüfen die tatsächliche Sichtbarkeit und Interaktivität aller Elemente im Browser — inklusive HTMX-Swaps und dynamischer Inhalte.
```
+---------------------------------------------------------------------+
|                    FRONTEND COMPLETENESS GATE                       |
|                                                                     |
|  +---------------------------------------------------------------+  |
|  |  STUFE 1: Static Manifest Check (< 5 Sekunden)               |  |
|  |                                                               |  |
|  |  ui-manifest.yaml --> check_frontend.py --> Report            |  |
|  |                                                               |  |
|  |  Prüft: data-testid, Komponenten-Namen, URL-Routes,          |  |
|  |         HTMX-Attribute, Template-Existenz                     |  |
|  +--------------------------+------------------------------------+  |
|                             |                                       |
|                    Pass?    | Fail -> Report + KI-Feedback-Loop     |
|                             |                                       |
|  +--------------------------v------------------------------------+  |
|  |  STUFE 2: Playwright E2E Tests (< 60 Sekunden)               |  |
|  |                                                               |  |
|  |  pytest --playwright --> Browser-basierte Verifikation        |  |
|  |                                                               |  |
|  |  Prüft: Sichtbarkeit, Interaktivität, HTMX-Swaps,           |  |
|  |         Formular-Validierung, Navigation, Responsive          |  |
|  +--------------------------+------------------------------------+  |
|                             |                                       |
|                    Pass?    | Fail -> Screenshot + Trace            |
|                             |                                       |
|  +--------------------------v------------------------------------+  |
|  |  GATE PASSED -> Commit / Deploy erlaubt                       |  |
|  +---------------------------------------------------------------+  |
+---------------------------------------------------------------------+
```

### 2.2 Rejected Alternatives

#### Option B: Screenshot-basierter Vergleich (Visual Regression)

Abgelehnt weil: Zu ungenau für Element-Vollständigkeit (erkennt fehlende Buttons nicht zuverlässig), hoher Wartungsaufwand für Baseline-Screenshots, erkennt fehlende HTMX-Funktionalität nicht (nur visuell, nicht funktional), erfordert zusätzliche Infrastruktur (Percy, Chromatic), und produziert False Positives bei Styling-Änderungen.

#### Option D: Rein manuelle Checklisten

Abgelehnt weil: Nicht automatisierbar, menschliches Versagen bei langen Listen, nicht in CI/CD integrierbar, skaliert nicht über mehrere Applikationen.

---

## 3. Implementation

### 3.1 Komponente 1: UI-Manifest Schema

Das UI-Manifest definiert den Vertrag zwischen Anforderung und Implementierung. Es wird pro Feature/Page gepflegt und ist die Single Source of Truth für erwartete Frontend-Elemente.

**Dateistruktur im Repository:**
```
<app>/
├── ui-manifests/
│   ├── _schema.yaml              # JSON-Schema für Manifest-Validierung
│   ├── dashboard.yaml            # Manifest für /dashboard
│   ├── settings.yaml             # Manifest für /settings
│   └── ...
├── tests/
│   ├── e2e/
│   │   ├── conftest.py           # Playwright-Fixtures + HTMX-Helpers
│   │   ├── test_dashboard.py     # E2E-Tests für /dashboard
│   │   └── test_settings.py      # E2E-Tests für /settings
│   └── completeness/
│       └── test_manifest.py      # Statische Manifest-Checks
└── templates/
    └── ...
```

**Manifest-Format (YAML):**
```yaml
# ui-manifests/dashboard.yaml
# =============================================================================
# UI-Manifest: Dashboard
# Definiert alle erwarteten Frontend-Elemente für die Dashboard-Seite.
# Jedes Element MUSS als data-testid im HTML existieren.
# =============================================================================

manifest_version: "1.0"
page:
  route: /dashboard/
  title: "Dashboard"
  django_view: "apps.core.views.DashboardView"
  django_url_name: "dashboard"

components:
  # ---------------------------------------------------------------------------
  # Navigation / Layout
  # ---------------------------------------------------------------------------
  - id: main-navigation
    type: navigation
    description: "Hauptnavigation mit Links zu allen Bereichen"
    required_elements:
      - element_id: nav-logo
        type: image
        description: "Platform-Logo im Header"

      - element_id: nav-link-dashboard
        type: link
        htmx: false
        description: "Link zur Dashboard-Seite"

      - element_id: nav-link-settings
        type: link
        htmx: false
        description: "Link zu den Einstellungen"

      - element_id: nav-user-menu
        type: dropdown
        description: "User-Dropdown mit Profil und Logout"

      - element_id: nav-logout-btn
        type: button
        description: "Logout-Button im User-Dropdown"

  # ---------------------------------------------------------------------------
  # Content Area
  # ---------------------------------------------------------------------------
  - id: stats-overview
    type: data-display
    description: "Übersichtskarten mit Key Metrics"
    htmx_source: true
    htmx_endpoint: /api/dashboard/stats/
    required_elements:
      - element_id: stat-card-revenue
        type: card
        description: "Umsatz-Karte"

      - element_id: stat-card-users
        type: card
        description: "Aktive-Nutzer-Karte"

      - element_id: stat-card-conversion
        type: card
        description: "Conversion-Rate-Karte"

  - id: activity-table
    type: table
    description: "Letzte Aktivitäten als Tabelle"
    required_elements:
      - element_id: activity-table-header
        type: table-header
        description: "Tabellenkopf mit Spaltenüberschriften"

      - element_id: activity-table-body
        type: table-body
        description: "Tabellenkörper mit Datenzeilen"

      - element_id: activity-pagination
        type: pagination
        htmx: true
        htmx_attributes:
          - hx-get
          - hx-target
          - hx-swap
        description: "Seitennavigation mit HTMX-Nachladen"

# ---------------------------------------------------------------------------
# HTMX-Contracts: Erwartete HTMX-Interaktionen auf dieser Seite
# ---------------------------------------------------------------------------
htmx_contracts:
  - trigger_element: activity-pagination
    method: GET
    endpoint_pattern: "/dashboard/activities/?page=*"
    target_element: activity-table-body
    swap_strategy: innerHTML

  - trigger_element: stat-card-revenue
    method: GET
    endpoint_pattern: "/api/dashboard/stats/"
    target_element: stats-overview
    swap_strategy: outerHTML
```

### 3.2 Komponente 2: Static Completeness Checker

Python-basierter Checker, der den generierten Code statisch gegen das Manifest prüft. Läuft ohne Browser in unter 5 Sekunden.
```python
#!/usr/bin/env python3
"""
Frontend Completeness Checker.

Prüft ob alle im UI-Manifest definierten Elemente
tatsächlich im generierten Code vorhanden sind.

Designed für Django + HTMX + Alpine.js Stack.
Erkennt: data-testid, Komponenten, Routes, HTMX-Attribute.

Usage:
    python -m tools.check_frontend
    python -m tools.check_frontend --manifest ui-manifests/dashboard.yaml
    python -m tools.check_frontend --format json --ci

Exit Codes:
    0 = Alle Elemente vorhanden
    1 = Fehlende Elemente gefunden
    2 = Manifest-Fehler (ungültiges YAML, Schema-Verletzung)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


# =============================================================================
# Data Models
# =============================================================================

class CheckStatus(Enum):
    """Status eines einzelnen Element-Checks."""
    FOUND = "found"
    MISSING = "missing"
    PARTIAL = "partial"


@dataclass
class ElementCheck:
    """Ergebnis einer Einzelprüfung."""
    element_id: str
    status: CheckStatus
    found_in: str | None = None
    details: str = ""
    missing_htmx_attrs: list[str] = field(default_factory=list)


@dataclass
class ComponentCheck:
    """Ergebnis einer Komponentenprüfung."""
    component_id: str
    page_route: str
    element_checks: list[ElementCheck] = field(default_factory=list)

    @property
    def missing_count(self) -> int:
        return sum(
            1 for e in self.element_checks
            if e.status in (CheckStatus.MISSING, CheckStatus.PARTIAL)
        )

    @property
    def is_complete(self) -> bool:
        return self.missing_count == 0


# =============================================================================
# Completeness Checker
# =============================================================================

class FrontendCompletenessChecker:
    """
    Prüft generierten Frontend-Code gegen ein UI-Manifest.

    Such-Strategien (in Prioritätsreihenfolge):
    1. data-testid Attribute (bevorzugt, explizit)
    2. id-Attribute (Fallback)
    3. CSS-Klassen (Fallback)
    4. Django Template Tags
    5. HTMX-Attribute (hx-get, hx-post, hx-target, hx-swap)
    """

    ELEMENT_PATTERNS: list[str] = [
        r'data-testid=["\']({eid})["\']',
        r'id=["\']({eid})["\']',
        r'class(?:Name)?=["\'][^"\']*\b({eid})\b',
        r'<({eid_pascal})\b',
        r'def\s+({eid_snake})\b',
        r"path\([\"'].*({eid})",
        r'{{% include ["\'][^"\']*({eid})',
    ]

    HTMX_PATTERNS: dict[str, str] = {
        "hx-get": r'hx-get=["\']([^"\']+)["\']',
        "hx-post": r'hx-post=["\']([^"\']+)["\']',
        "hx-put": r'hx-put=["\']([^"\']+)["\']',
        "hx-delete": r'hx-delete=["\']([^"\']+)["\']',
        "hx-target": r'hx-target=["\']([^"\']+)["\']',
        "hx-swap": r'hx-swap=["\']([^"\']+)["\']',
        "hx-trigger": r'hx-trigger=["\']([^"\']+)["\']',
        "hx-indicator": r'hx-indicator=["\']([^"\']+)["\']',
    }

    EXTENSIONS: set[str] = {
        ".html", ".htm", ".txt", ".py", ".js", ".ts", ".jsx", ".tsx",
    }

    def __init__(
        self,
        manifest_path: str | Path,
        source_dirs: list[str | Path],
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.source_dirs = [Path(d) for d in source_dirs]
        self._file_cache: dict[Path, str] = {}
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, Any]:
        """Lädt und validiert das UI-Manifest."""
        if not self.manifest_path.exists():
            print(
                f"ERROR: Manifest nicht gefunden: {self.manifest_path}",
                file=sys.stderr,
            )
            sys.exit(2)
        try:
            with open(self.manifest_path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(f"ERROR: Ungültiges YAML: {exc}", file=sys.stderr)
            sys.exit(2)
        if not isinstance(data, dict) or "components" not in data:
            print(
                "ERROR: Manifest muss 'components' enthalten.",
                file=sys.stderr,
            )
            sys.exit(2)
        return data

    def _read_source_files(self) -> dict[Path, str]:
        """Liest alle relevanten Quelldateien ein und cached sie."""
        if self._file_cache:
            return self._file_cache
        for src_dir in self.source_dirs:
            if not src_dir.exists():
                continue
            for file_path in src_dir.rglob("*"):
                if file_path.suffix in self.EXTENSIONS and file_path.is_file():
                    try:
                        self._file_cache[file_path] = file_path.read_text(
                            encoding="utf-8",
                        )
                    except (UnicodeDecodeError, PermissionError):
                        continue
        return self._file_cache

    @staticmethod
    def _to_variants(element_id: str) -> dict[str, str]:
        """Erzeugt Naming-Varianten eines Element-IDs."""
        words = element_id.replace("-", " ").replace("_", " ").split()
        return {
            "eid": element_id,
            "eid_snake": element_id.replace("-", "_"),
            "eid_pascal": "".join(w.capitalize() for w in words),
        }

    def _search_element_in_sources(
        self, element_id: str,
    ) -> tuple[bool, str | None]:
        """Sucht ein Element in allen Quelldateien."""
        variants = self._to_variants(element_id)
        sources = self._read_source_files()
        for file_path, content in sources.items():
            for pattern_template in self.ELEMENT_PATTERNS:
                pattern = pattern_template.format(**variants)
                if re.search(pattern, content, re.IGNORECASE):
                    return True, str(file_path)
        return False, None

    def _check_htmx_attributes(
        self,
        element_id: str,
        required_attrs: list[str],
    ) -> list[str]:
        """Prüft ob ein Element die erwarteten HTMX-Attribute hat."""
        sources = self._read_source_files()
        missing: list[str] = []
        for attr_name in required_attrs:
            pattern = self.HTMX_PATTERNS.get(attr_name)
            if not pattern:
                continue
            found = False
            for content in sources.values():
                eid_pattern = (
                    rf'data-testid=["\']({re.escape(element_id)})["\']'
                )
                for match in re.finditer(eid_pattern, content):
                    start = max(0, match.start() - 200)
                    end = min(len(content), match.end() + 500)
                    context = content[start:end]
                    if re.search(pattern, context):
                        found = True
                        break
                if found:
                    break
            if not found:
                missing.append(attr_name)
        return missing

    def _check_element(self, element_spec: dict[str, Any]) -> ElementCheck:
        """Prüft ein einzelnes Element gegen den Quellcode."""
        element_id = element_spec["element_id"]
        found, found_in = self._search_element_in_sources(element_id)
        if not found:
            return ElementCheck(
                element_id=element_id,
                status=CheckStatus.MISSING,
                details=(
                    f"Nicht gefunden in"
                    f" {len(self._read_source_files())} Dateien"
                ),
            )
        htmx_attrs = element_spec.get("htmx_attributes", [])
        if htmx_attrs:
            missing_attrs = self._check_htmx_attributes(
                element_id, htmx_attrs,
            )
            if missing_attrs:
                return ElementCheck(
                    element_id=element_id,
                    status=CheckStatus.PARTIAL,
                    found_in=found_in,
                    details="Element gefunden, HTMX-Attribute fehlen",
                    missing_htmx_attrs=missing_attrs,
                )
        return ElementCheck(
            element_id=element_id,
            status=CheckStatus.FOUND,
            found_in=found_in,
        )

    def run_check(self) -> list[ComponentCheck]:
        """Führt die vollständige Prüfung durch."""
        results: list[ComponentCheck] = []
        page_route = self.manifest.get("page", {}).get("route", "/unknown/")
        for component in self.manifest.get("components", []):
            comp_check = ComponentCheck(
                component_id=component["id"],
                page_route=page_route,
            )
            for element_spec in component.get("required_elements", []):
                check = self._check_element(element_spec)
                comp_check.element_checks.append(check)
            results.append(comp_check)
        return results

    def print_report(self, results: list[ComponentCheck]) -> int:
        """Gibt Report aus. Gibt die Anzahl fehlender Elemente zurück."""
        total_missing = 0
        total_partial = 0
        total_found = 0
        for comp in results:
            icon = "PASS" if comp.is_complete else "FAIL"
            print(f"\n[{icon}] {comp.page_route} -> {comp.component_id}")
            for elem in comp.element_checks:
                if elem.status == CheckStatus.FOUND:
                    print(f"   [OK]   {elem.element_id}")
                    total_found += 1
                elif elem.status == CheckStatus.PARTIAL:
                    attrs = ", ".join(elem.missing_htmx_attrs)
                    print(
                        f"   [WARN] {elem.element_id}"
                        f"  <- HTMX fehlt: {attrs}",
                    )
                    total_partial += 1
                else:
                    print(f"   [MISS] {elem.element_id}  <- FEHLT!")
                    total_missing += 1
        total = total_found + total_partial + total_missing
        print(f"\n{'='*60}")
        print(
            f"Ergebnis: {total_found}/{total} gefunden, "
            f"{total_partial} unvollständig, "
            f"{total_missing} fehlend",
        )
        return total_missing + total_partial

    def generate_ai_feedback(
        self, results: list[ComponentCheck],
    ) -> str:
        """
        Erzeugt strukturierten Feedback-Text für die KI.
        Kann direkt als Follow-up-Prompt an Windsurf/Cursor/Claude
        übergeben werden.
        """
        missing_elements: list[dict[str, Any]] = []
        for comp in results:
            for elem in comp.element_checks:
                if elem.status == CheckStatus.MISSING:
                    missing_elements.append({
                        "component": comp.component_id,
                        "element_id": elem.element_id,
                        "action": "CREATE",
                    })
                elif elem.status == CheckStatus.PARTIAL:
                    missing_elements.append({
                        "component": comp.component_id,
                        "element_id": elem.element_id,
                        "action": "ADD_HTMX_ATTRS",
                        "missing_attrs": elem.missing_htmx_attrs,
                    })
        if not missing_elements:
            return "Alle Frontend-Elemente sind vollständig implementiert."
        feedback = (
            "## FEHLENDE FRONTEND-ELEMENTE\n\n"
            "Die folgenden Elemente fehlen oder sind unvollständig.\n"
            "Jedes Element MUSS ein data-testid Attribut haben.\n\n"
        )
        for item in missing_elements:
            if item["action"] == "CREATE":
                feedback += (
                    f"- ERSTELLEN: data-testid=\"{item['element_id']}\""
                    f" in Komponente {item['component']}\n"
                )
            else:
                attrs = ", ".join(item.get("missing_attrs", []))
                feedback += (
                    f"- HTMX ERGÄNZEN: {item['element_id']}"
                    f" braucht: {attrs}\n"
                )
        feedback += (
            "\n## AKZEPTANZKRITERIUM\n"
            "`python -m tools.check_frontend` gibt Exit-Code 0 zurück.\n"
        )
        return feedback


def main() -> None:
    """CLI Entry Point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Frontend Completeness Checker",
    )
    parser.add_argument(
        "--manifest", "-m", default="ui-manifests/",
    )
    parser.add_argument(
        "--source", "-s", nargs="+",
        default=["templates/", "apps/", "static/"],
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json", "ai-feedback"],
        default="text",
    )
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    total_missing = 0

    if manifest_path.is_dir():
        manifests = sorted(
            m for m in manifest_path.glob("*.yaml")
            if not m.name.startswith("_")
        )
    else:
        manifests = [manifest_path]

    if not manifests:
        print(
            f"ERROR: Keine Manifeste gefunden in: {manifest_path}",
            file=sys.stderr,
        )
        sys.exit(2)

    for mf in manifests:
        print(f"\n{'='*60}")
        print(f"Manifest: {mf.name}")
        print(f"{'='*60}")
        checker = FrontendCompletenessChecker(
            manifest_path=mf, source_dirs=args.source,
        )
        results = checker.run_check()
        if args.format == "json":
            output = []
            for comp in results:
                for elem in comp.element_checks:
                    output.append({
                        "manifest": mf.name,
                        "component": comp.component_id,
                        "element_id": elem.element_id,
                        "status": elem.status.value,
                        "found_in": elem.found_in,
                        "missing_htmx": elem.missing_htmx_attrs,
                    })
            print(json.dumps(output, indent=2, ensure_ascii=False))
        elif args.format == "ai-feedback":
            print(checker.generate_ai_feedback(results))
        else:
            total_missing += checker.print_report(results)

    sys.exit(1 if total_missing > 0 else 0)


if __name__ == "__main__":
    main()
```

### 3.3 Komponente 3: Playwright E2E Tests

Playwright-Tests als zweite Stufe, die im echten Browser gegen einen laufenden Django-Server testen. Diese Tests werden **vor** der Codegenerierung geschrieben (Test-First).

**conftest.py — Shared Fixtures + HTMX-Helpers:**
```python
"""
Playwright E2E Test Configuration.

Provides:
- Django live_server integration via pytest-django
- HTMX-aware waiting helpers
- Authentication fixtures
- Screenshot-on-failure für Debugging

Requirements:
    pip install pytest-playwright pytest-django
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

User = get_user_model()


# =============================================================================
# HTMX Helpers
# =============================================================================

def wait_for_htmx_settled(page: Page, timeout: int = 5000) -> None:
    """
    Wartet bis alle laufenden HTMX-Requests abgeschlossen sind.

    HTMX setzt die CSS-Klasse 'htmx-request' auf Elemente die
    gerade einen Request ausführen. Diese Funktion wartet bis
    keine solchen Elemente mehr existieren.
    """
    page.wait_for_function(
        """
        () => {
            if (typeof htmx === 'undefined') return true;
            return document.querySelectorAll('.htmx-request').length === 0;
        }
        """,
        timeout=timeout,
    )


def wait_for_htmx_applied(
    page: Page, selector: str, timeout: int = 5000,
) -> None:
    """
    Wartet bis HTMX auf ein bestimmtes DOM-Element angewendet wurde.

    HTMX-Elemente erhalten die Property 'htmx-internal-data' erst
    nachdem htmx.process() sie verarbeitet hat.
    """
    page.wait_for_function(
        """
        selector => {
            const el = document.querySelector(selector);
            return el && el['htmx-internal-data'] !== undefined;
        }
        """,
        arg=selector,
        timeout=timeout,
    )


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture()
def test_user(db):
    """Erzeugt einen Test-User für authentifizierte Tests."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123!",
    )


@pytest.fixture()
def authenticated_page(page: Page, live_server, test_user) -> Page:
    """Page die bereits eingeloggt ist."""
    page.goto(f"{live_server.url}/accounts/login/")
    page.get_by_label("Username").fill("testuser")
    page.get_by_label("Password").fill("testpass123!")
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(f"{live_server.url}/**")
    return page


@pytest.fixture(autouse=True)
def _screenshot_on_failure(request, page: Page) -> None:
    """Erstellt automatisch einen Screenshot bei Test-Failure."""
    yield
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        screenshot_dir = Path("test-results/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(
            path=str(screenshot_dir / f"{request.node.name}.png"),
            full_page=True,
        )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook um Test-Ergebnis an Fixture weiterzugeben."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
```

**Beispiel E2E-Test — Dashboard Completeness:**
```python
"""
E2E Tests: Dashboard UI Completeness.

Diese Tests werden VOR der Codegenerierung geschrieben.
Sie definieren das Akzeptanzkriterium für "Dashboard ist fertig".
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import wait_for_htmx_settled


class TestDashboardNavigation:
    """Verifiziert alle Navigations-Elemente aus dem UI-Manifest."""

    @pytest.mark.django_db(transaction=True)
    def test_logo_visible(
        self, authenticated_page: Page, live_server,
    ) -> None:
        authenticated_page.goto(f"{live_server.url}/dashboard/")
        logo = authenticated_page.locator('[data-testid="nav-logo"]')
        expect(logo).to_be_visible()

    @pytest.mark.django_db(transaction=True)
    def test_navigation_links(
        self, authenticated_page: Page, live_server,
    ) -> None:
        authenticated_page.goto(f"{live_server.url}/dashboard/")
        for testid in ["nav-link-dashboard", "nav-link-settings"]:
            expect(
                authenticated_page.locator(f'[data-testid="{testid}"]')
            ).to_be_visible()

    @pytest.mark.django_db(transaction=True)
    def test_user_menu_and_logout(
        self, authenticated_page: Page, live_server,
    ) -> None:
        authenticated_page.goto(f"{live_server.url}/dashboard/")
        user_menu = authenticated_page.locator(
            '[data-testid="nav-user-menu"]',
        )
        expect(user_menu).to_be_visible()
        user_menu.click()
        logout_btn = authenticated_page.locator(
            '[data-testid="nav-logout-btn"]',
        )
        expect(logout_btn).to_be_visible()


class TestDashboardStats:
    """Verifiziert die Stats-Karten inklusive HTMX-Nachladen."""

    @pytest.mark.django_db(transaction=True)
    def test_stat_cards_visible(
        self, authenticated_page: Page, live_server,
    ) -> None:
        authenticated_page.goto(f"{live_server.url}/dashboard/")
        wait_for_htmx_settled(authenticated_page)
        for card_id in [
            "stat-card-revenue",
            "stat-card-users",
            "stat-card-conversion",
        ]:
            expect(
                authenticated_page.locator(
                    f'[data-testid="{card_id}"]',
                )
            ).to_be_visible()

    @pytest.mark.django_db(transaction=True)
    def test_stats_htmx_endpoint(
        self, authenticated_page: Page, live_server,
    ) -> None:
        with authenticated_page.expect_response(
            lambda resp: (
                "/api/dashboard/stats/" in resp.url
                and resp.status == 200
            ),
        ):
            authenticated_page.goto(f"{live_server.url}/dashboard/")


class TestDashboardActivityTable:
    """Verifiziert Aktivitätstabelle inklusive HTMX-Pagination."""

    @pytest.mark.django_db(transaction=True)
    def test_table_structure(
        self, authenticated_page: Page, live_server,
    ) -> None:
        authenticated_page.goto(f"{live_server.url}/dashboard/")
        wait_for_htmx_settled(authenticated_page)
        for testid in [
            "activity-table-header",
            "activity-table-body",
            "activity-pagination",
        ]:
            expect(
                authenticated_page.locator(
                    f'[data-testid="{testid}"]',
                )
            ).to_be_visible()

    @pytest.mark.django_db(transaction=True)
    def test_pagination_htmx_swap(
        self, authenticated_page: Page, live_server,
    ) -> None:
        authenticated_page.goto(f"{live_server.url}/dashboard/")
        wait_for_htmx_settled(authenticated_page)
        pagination = authenticated_page.locator(
            '[data-testid="activity-pagination"]',
        )
        expect(
            pagination.locator("[hx-get]"),
        ).to_have_count(1, timeout=3000)

        with authenticated_page.expect_response(
            lambda resp: (
                "page=2" in resp.url and resp.status == 200
            ),
        ):
            pagination.locator("a", has_text="2").click()

        wait_for_htmx_settled(authenticated_page)
        expect(
            authenticated_page.locator(
                '[data-testid="activity-table-body"]',
            )
        ).to_be_visible()
```

### 3.4 Komponente 4: CI/CD Integration

**GitHub Actions Workflow:**
```yaml
# .github/workflows/frontend-completeness.yml
name: Frontend Completeness Gate

on:
  pull_request:
    paths:
      - 'templates/**'
      - 'apps/**/templates/**'
      - 'static/**'
      - 'ui-manifests/**'
      - 'tests/e2e/**'

jobs:
  manifest-check:
    name: "Stufe 1: Manifest Check"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pyyaml
      - run: python -m tools.check_frontend --format json --ci

  playwright-e2e:
    name: "Stufe 2: Playwright E2E"
    runs-on: ubuntu-latest
    needs: manifest-check
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-playwright pytest-django
          playwright install chromium --with-deps
      - name: Run E2E Completeness Tests
        env:
          DATABASE_URL: postgres://test_user:test_pass@localhost:5432/test_db
          DJANGO_SETTINGS_MODULE: config.settings.test
        run: |
          python manage.py migrate --run-syncdb
          pytest tests/e2e/ -v --tracing on --output test-results/
      - name: Upload Traces on Failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-traces
          path: test-results/
          retention-days: 7
```

**Pre-Commit Hook:**
```bash
#!/usr/bin/env bash
# .git/hooks/pre-commit
set -euo pipefail

CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if echo "$CHANGED_FILES" | grep -qE '(templates/|static/|\.html$)'; then
    echo "Frontend Completeness Check (Stufe 1: Manifest)..."
    python -m tools.check_frontend --ci 2>&1
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        echo ""
        echo "Frontend-Elemente fehlen! Commit abgelehnt."
        echo "Führe 'python -m tools.check_frontend --format ai-feedback'"
        echo "aus und übergib die Ausgabe an dein KI-Tool."
        exit 1
    fi
    echo "Alle Manifest-Elemente vorhanden."
fi
```

### 3.5 Komponente 5: KI-Prompt-Strategie

Strukturierte Prompts, die der KI das Manifest als Kontrakt mitgeben:
```text
## Aufgabe
Implementiere die Dashboard-Seite gemäß dem angehängten UI-Manifest
(ui-manifests/dashboard.yaml).

## Regeln
1. Jedes Element unter 'required_elements' MUSS als data-testid
   im HTML existieren: <div data-testid="element-id">
2. HTMX-Attribute (hx-get, hx-target, hx-swap) gemäß 'htmx_contracts'.
3. Nach JEDER Komponente: Selbst-Check gegen das Manifest.
4. Am Ende: Liste ALLER implementierten data-testid Attribute mit
   Bestätigung der Vollständigkeit.

## Akzeptanzkriterium
1. `python -m tools.check_frontend -m ui-manifests/dashboard.yaml`
   gibt Exit-Code 0 zurück.
2. `pytest tests/e2e/test_dashboard.py` ist grün.

## Manifest (siehe Anhang)
<Inhalt von ui-manifests/dashboard.yaml hier einfügen>
```

---

## 4. Adoption Strategy

### 4.1 Phasenplan

| Phase | Zeitraum | Scope | Deliverables |
|-------|----------|-------|--------------|
| **Phase 1: Pilot** | Woche 1-2 | Travel-Beat Dashboard | Manifest + Checker + 5 E2E Tests |
| **Phase 2: Rollout** | Woche 3-4 | Travel-Beat (alle Seiten) | Vollständige Manifest-Coverage |
| **Phase 3: Platform** | Woche 5-8 | BFAgent, Risk-Hub | Manifeste für alle kritischen Seiten |
| **Phase 4: Enforcement** | Woche 9+ | Alle Apps | CI/CD Gate, Pre-Commit Hooks |

### 4.2 Metriken

| Metrik | Baseline (aktuell) | Ziel (nach Phase 4) |
|--------|-------------------|---------------------|
| Fehlende Elemente nach KI-Generierung | ~40-60% | < 5% |
| Manuelle Nacharbeit pro Feature | ~2-4 Stunden | < 15 Minuten |
| UI-Regressions in Produktion | ~3-5 pro Monat | 0 |
| E2E-Test-Coverage (kritische Seiten) | 0% | > 80% |
| Zeit bis "grünes Gate" | N/A | < 3 Minuten |

### 4.3 KI-Feedback-Loop (Self-Healing)

Der Check erzeugt strukturiertes Feedback, das direkt als Prompt an die KI zurückgegeben werden kann:
```
  1. KI generiert Code
         |
         v
  2. Checker läuft (Stufe 1 + 2)
         |
    Pass? | Fail?
         |
         v
  3. AI-Feedback wird generiert (--format ai-feedback)
         |
         v
  4. Feedback als Prompt an KI zurückgeben
         |
         v
  5. KI ergänzt fehlende Elemente -> zurück zu 2.
```

---

## 5. Dependencies

### 5.1 Python-Packages

| Package | Version | Zweck |
|---------|---------|-------|
| `pyyaml` | >=6.0 | Manifest-Parsing |
| `pytest-playwright` | >=0.5.0 | Playwright-pytest Integration |
| `pytest-django` | >=4.8 | Django live_server Fixture |
| `playwright` | >=1.48 | Browser-Automation |

### 5.2 Infrastruktur

Keine zusätzliche Infrastruktur erforderlich. Playwright läuft headless in GitHub Actions.

### 5.3 Kompatibilität

| Komponente | Kompatibel? | Anmerkung |
|------------|-------------|-----------|
| Django 5.x | Ja | live_server Fixture nativ unterstützt |
| HTMX 2.x | Ja | htmx-internal-data Property für wait_for_htmx_applied |
| PostgreSQL 16 | Ja | transaction=True für Test-Isolation |
| GitHub Actions | Ja | playwright install --with-deps in CI |
| Alpine.js | Ja | Playwright wartet auf DOM via x-data |

---

## 6. Risks and Mitigations

| Risiko | Schweregrad | Wahrscheinlichkeit | Mitigation |
|--------|-------------|---------------------|------------|
| Manifest-Pflege wird vernachlässigt | HOCH | MITTEL | CI blockiert Deployment ohne Manifest |
| Playwright-Tests sind fragil/flaky | MITTEL | MITTEL | HTMX-Wait-Helpers, Auto-Retry, Traces bei Failures |
| False Positives bei Naming-Varianten | NIEDRIG | NIEDRIG | Multi-Pattern-Suche (data-testid, id, class, Komponente) |
| Performance-Impact in CI | NIEDRIG | NIEDRIG | Stufe 1 < 5s, Stufe 2 < 60s, nur bei Frontend-Änderungen |
| HTMX-Attribute-Check zu strikt | MITTEL | MITTEL | Kontext-basierte Suche (500 Zeichen Umkreis) |

---

## 7. References

- [Playwright Best Practices](https://playwright.dev/docs/best-practices) — Offizielle Playwright-Empfehlungen
- [pytest-playwright Django Integration](https://github.com/mxschmitt/python-django-playwright) — Referenzimplementierung
- [HTMX Wait Pattern](https://www.djangotricks.com/tricks/5BvmFsgsehWg/) — wait_for_htmx_applied Pattern
- [DjangoCon Europe 2025: E2E Testing with Playwright](https://pretalx.evolutio.pt/djangocon-europe-2025/talk/ETFCCS/) — Template-Partials Testing
- [adacs-django-playwright](https://pypi.org/project/adacs-django-playwright/) — Django+HTMX Playwright Package mit htmx_settle
- [Platform Architecture Master](../PLATFORM_ARCHITECTURE_MASTER.md)
- [ADR-009: Deployment Architecture](./ADR-009-deployment-architecture.md)

---

## 8. Amendment: Anti-Pattern Enforcement + Token Compliance (2026-02-18)

### 8.1 Motivation

The original ADR-040 defines **what** must be present (UI manifest + Playwright
E2E). Two new ADRs extend the platform's frontend quality system:

- **ADR-048** (HTMX Playbook) defines canonical patterns and banned anti-patterns
- **ADR-049** (Design Token System) defines semantic CSS tokens

This amendment integrates their enforcement rules into ADR-040's existing
completeness checker and CI pipeline.

### 8.2 Extended Manifest Format (v2.0)

The manifest gains two new sections: `forbidden_patterns` and `token_rules`.

```yaml
# ui-manifests/dashboard.yaml (additions to v1.0 format)
manifest_version: "2.0"

# ... existing components and htmx_contracts sections ...

# NEW: Anti-pattern checks (from ADR-048)
forbidden_patterns:
  - pattern: 'style="'
    severity: ERROR
    message: "Inline styles banned (AP-004) -- use Tailwind + design tokens"
  - pattern: 'onclick="'
    severity: ERROR
    message: "onclick banned with HTMX (AP-003) -- use hx-* attributes"
  - pattern: 'hx-boost="true"'
    context: form
    severity: ERROR
    message: "hx-boost on forms banned (AP-002) -- causes double-submit"

# NEW: Token compliance (from ADR-049)
token_rules:
  ban_direct_colors: true       # Flag bg-blue-500, text-red-600 etc.
  ban_hardcoded_hex: true       # Flag #2563eb in CSS/style attributes
  require_semantic_classes: true # Require bg-primary, text-danger etc.
```

### 8.3 Checker Extensions

The existing `check_frontend.py` gains two new check methods:

```python
# tools/check_frontend.py -- Extensions for v2.0

class FrontendCompletenessChecker:
    """Extended with anti-pattern and token compliance checks."""

    def check_anti_patterns(
        self, html_content: str, manifest: dict,
    ) -> list[CheckResult]:
        """Check against ADR-048 banned patterns (AP-001..007)."""
        results: list[CheckResult] = []
        for rule in manifest.get("forbidden_patterns", []):
            if rule["pattern"] in html_content:
                results.append(CheckResult(
                    status=Status.FAIL,
                    rule=rule.get("id", "AP-xxx"),
                    message=rule["message"],
                    severity=rule.get("severity", "ERROR"),
                ))
        return results

    def check_token_compliance(
        self, html_content: str, manifest: dict,
    ) -> list[CheckResult]:
        """Check against ADR-049 design token rules."""
        import re

        rules = manifest.get("token_rules", {})
        results: list[CheckResult] = []

        if rules.get("ban_direct_colors"):
            pattern = re.compile(
                r"\b(?:bg|text|border)"
                r"-(?:blue|red|green|gray|amber|sky|purple)"
                r"-\d{2,3}\b"
            )
            for match in pattern.finditer(html_content):
                results.append(CheckResult(
                    status=Status.WARNING,
                    rule="TOKEN-001",
                    message=(
                        f"Direct color '{match.group()}'"
                        f" -- use semantic class (bg-primary, text-danger)"
                    ),
                ))

        if rules.get("ban_hardcoded_hex"):
            hex_pattern = re.compile(
                r"(?:color|background|border-color)"
                r"\s*:\s*#[0-9a-fA-F]{3,8}"
            )
            for match in hex_pattern.finditer(html_content):
                results.append(CheckResult(
                    status=Status.FAIL,
                    rule="TOKEN-002",
                    message=(
                        f"Hardcoded color '{match.group()}'"
                        f" -- use --pui-* CSS variable"
                    ),
                ))

        return results
```

### 8.4 CI Pipeline Extension

The existing `frontend-quality.yml` workflow adds token and pattern checks:

```yaml
# .github/workflows/frontend-quality.yml (addition to static-analysis job)
      - name: Run Frontend Checks (v2.0)
        run: |
          set -euo pipefail
          python -m tools.check_frontend \
            --ci \
            --check-anti-patterns \
            --check-token-compliance \
            --format json \
            > frontend-report.json
```

### 8.5 Pre-Commit Integration

Two new hooks complement the existing manifest check:

```yaml
# .pre-commit-config.yaml (additions)
      - id: htmx-anti-patterns
        name: "HTMX Anti-Pattern Check (ADR-048)"
        entry: python -m tools.check_htmx_patterns
        language: python
        files: '\.html$'
        pass_filenames: true

      - id: design-token-check
        name: "Design Token Compliance (ADR-049)"
        entry: python -m tools.check_design_tokens
        language: python
        files: '\.(html|css)$'
        pass_filenames: true
```

### 8.6 Enforcement Summary

| Check | Layer | Speed | Source ADR |
| ----- | ----- | ----- | ---------- |
| `data-testid` on interactive elements | Pre-commit | ~1s | ADR-040 |
| Anti-patterns AP-001..004 (regex) | Pre-commit | ~1s | ADR-048 |
| Token compliance (direct colors) | Pre-commit | ~1s | ADR-049 |
| Full manifest check (components, HTMX contracts) | CI | ~5s | ADR-040 |
| Anti-patterns AP-005..007 (manifest-aware) | CI | ~5s | ADR-048 |
| Token compliance (hardcoded hex in CSS) | CI | ~5s | ADR-049 |
| Playwright E2E (browser-based) | CI | ~60s | ADR-040 |

---

## 9. Migration Tracking

| Service | UI-Manifests | Static Checker | Playwright E2E | data-testid | Status |
|---------|-------------|----------------|----------------|-------------|--------|
| `travel-beat` | ✅ dashboard.yaml, trip_list.yaml, trip_detail.yaml | ✅ check_frontend.py + test_manifest_completeness.py | ✅ test_dashboard.py, test_trip_list.py, test_trip_detail.py | ✅ dashboard + trip_list + trip_detail | Phase 2 done |
| `cad-hub` | ✅ avb_project_list.yaml, avb_tender_list.yaml | ✅ test_manifest_completeness.py | ⬜ | ✅ project_list + tender_list | Phase 1 done |
| `risk-hub` | ✅ dsb_dashboard.yaml, dsb_vvt_list.yaml | ✅ test_manifest_completeness.py | ⬜ | ✅ dashboard + vvt_list | Phase 1 done |
| `bfagent` | ⬜ | ⬜ | ⬜ | ⬜ | Ausstehend |

**Nächste Schritte:**
- CI-Integration: `pytest tests/completeness/ -m "not e2e"` als Gate vor Deploy
- Weitere Manifeste: world_detail, story_list (travel-beat)
- bfagent UI-Manifeste + data-testid ergänzen

---

## 10. Changelog

| Datum      | Autor          | Änderung                                                                    |
|------------|----------------|-----------------------------------------------------------------------------|
| 2026-02-24 | Achim Dehnert | travel-beat: UI-Manifeste + Playwright E2E + Static Checker implementiert |
| 2026-02-16 | Achim Dehnert | Initial Draft -- kombiniert Option A (Manifest) + Option C (Playwright)      |
| 2026-02-18 | Achim Dehnert | Amendment: Anti-Pattern Enforcement (ADR-048) + Token Compliance (ADR-049)   |