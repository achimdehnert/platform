---
id: ADR-099
title: "dev-hub Release Management UI — PyPI Publishing & GitHub Tag Workflow via devhub.iil.pet"
status: accepted
date: 2026-03-04
author: Achim Dehnert
owner: Achim Dehnert
scope: dev-hub, platform, nl2cad, all Python package repos
tags: [dev-hub, release-management, pypi, github-actions, ui, management-console]
related: [ADR-050, ADR-077, ADR-086, ADR-090, ADR-100]
last_verified: 2026-03-08
---

# ADR-099: dev-hub Release Management UI

## 1. Context

### 1.1 Problem

Aktuell erfordert das Publizieren eines Python-Packages auf PyPI mehrere manuelle
CLI-Schritte die fehleranfällig sind und Kontextwissen über Git-Tag-Formate,
`pyproject.toml`-Versionierung und PyPI Trusted Publisher-Konfiguration erfordern:

```bash
# Aktuell: fehleranfällig, kein UI, kein Überblick
git tag nl2cad-core@0.2.0
git push origin nl2cad-core@0.2.0
# → Muss Version vorher in pyproject.toml manuell angepasst haben
# → Muss wissen welche Packages in welchem Repo existieren
# → Muss GitHub Actions Status separat prüfen
# → Muss PyPI Trusted Publisher per Package konfiguriert haben
```

**Konkrete Probleme die aufgetreten sind:**

| Problem | Ursache | Aufwand zur Behebung |
|---------|---------|---------------------|
| Tag auf falschem Commit gesetzt | `pyproject.toml` Version nicht gebumpt | Tag löschen + neu setzen |
| `iil-nl2cadfw` Trusted Publisher falsch konfiguriert | Falsches Repository (iil-nl2cadfw statt nl2cad) | Manuell in PyPI UI korrigieren |
| Tag-Pattern in `publish.yml` fehlte für Meta-Package | Nur `nl2cad-*@*`, nicht `iil-nl2cadfw@*` | Workflow-Datei editieren |
| Version in `pyproject.toml` nicht mit Tag synchron | Manuelle Schritte vergessen | Workflow-Run schlug fehl |

### 1.2 Bestehende Infrastruktur (aus ADR-050 + ADR-077)

- **dev-hub** existiert als Central Developer Portal (`devhub.iil.pet`)
- **Catalog DB** führt alle Repos, Komponenten, Services als `catalog-info.yaml` → DB
- **GitHub Actions Workflows** sind bereits als Templates in `platform/templates/workflows/` verfügbar
- **OIDC Trusted Publishing** ist per Package auf PyPI konfiguriert
- **`uv version --package`** löst das Versions-Sync-Problem automatisch (seit ADR-099)

### 1.3 Vision

`devhub.iil.pet/releases/` wird zur **Management Console** für alle Package-Releases:
Ein Formular, ein Klick → GitHub Tag wird gesetzt → Actions baut und publiziert.

---

## 2. Decision

### 2.1 Neue dev-hub App: `releases`

Eine neue Django-App `releases` in dev-hub mit folgender Verantwortung:

- **Package Registry**: Welche PyPI-Packages existieren in welchem Repo?
- **Release Trigger**: UI-Formular → GitHub Tag via GitHub API setzen
- **Status-Tracking**: GitHub Actions Workflow-Status per Package anzeigen
- **Trusted Publisher Checker**: Prüft ob PyPI Trusted Publisher korrekt konfiguriert ist
- **Release History**: Welche Versionen wurden wann veröffentlicht?

### 2.2 Architektur

```
devhub.iil.pet/releases/
│
├── /                          # Package-Übersicht (alle registrierten Packages)
├── <package-name>/            # Package-Detail: Versionen, Workflow-Status
├── <package-name>/release/    # Release-Formular: Version eingeben → Tag setzen
└── <package-name>/status/     # HTMX-Polling: GitHub Actions Run-Status
```

```
┌─────────────────────────────────────────────────────────────┐
│  devhub.iil.pet/releases/                                    │
│                                                              │
│  Package         Repo           PyPI     Last Release        │
│  ─────────────────────────────────────────────────────────  │
│  nl2cad-core     nl2cad         ✅ 0.1.0  [Release →]        │
│  nl2cad-areas    nl2cad         ✅ 0.1.0  [Release →]        │
│  iil-nl2cadfw    nl2cad         ✅ 0.1.2  [Release →]        │
│  ...                                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Release: nl2cad-core                                        │
│                                                              │
│  Aktuelle Version (PyPI): 0.1.0                             │
│  Neue Version:  [ 0.2.0    ]  (Semantic Version)            │
│                                                              │
│  Was passiert:                                               │
│  1. GitHub Tag nl2cad-core@0.2.0 wird gesetzt               │
│  2. publish.yml triggert via OIDC                            │
│  3. uv version setzt Version automatisch                     │
│  4. PyPI erhält nl2cad-core 0.2.0                           │
│                                                              │
│  Trusted Publisher: ✅ konfiguriert                          │
│  Workflow: publish.yml  Environment: pypi                    │
│                                                              │
│  [ Release starten ]                                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Datenmodell

```python
# releases/models.py

@dataclass
class PyPIPackage:
    """Registriertes PyPI-Package in der Catalog DB."""
    name: str                    # z.B. "nl2cad-core"
    pypi_name: str               # PyPI-Projektname (kann abweichen)
    repo: str                    # GitHub Repo, z.B. "nl2cad"
    tag_prefix: str              # Tag-Format, z.B. "nl2cad-core@"
    root_package: bool           # True wenn pyproject.toml im Repo-Root
    trusted_publisher_ok: bool   # Wird via PyPI API geprüft
    current_pypi_version: str    # Aktuelle Version auf PyPI
```

```python
# Django Model in catalog DB
class PyPIPackage(models.Model):
    name = models.CharField(max_length=100, unique=True)
    pypi_name = models.CharField(max_length=100)
    repo = models.CharField(max_length=100)           # GitHub Repo-Name
    tag_prefix = models.CharField(max_length=100)     # z.B. "nl2cad-core@"
    root_package = models.BooleanField(default=False)
    workflow_file = models.CharField(max_length=50, default="publish.yml")
    environment_name = models.CharField(max_length=50, default="pypi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ReleaseRun(models.Model):
    package = models.ForeignKey(PyPIPackage, on_delete=models.CASCADE)
    version = models.CharField(max_length=50)
    tag = models.CharField(max_length=100)            # z.B. "nl2cad-core@0.2.0"
    github_run_id = models.BigIntegerField(null=True)
    status = models.CharField(max_length=20)          # pending/running/success/failed
    triggered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
```

### 2.4 Service Layer

```python
# releases/services.py

class ReleaseService:
    """Triggert GitHub Tags via GitHub API und trackt Workflow-Status."""

    def trigger_release(self, package: PyPIPackage, version: str) -> ReleaseRun:
        """
        1. Validiert Version (SemVer)
        2. Prüft ob Version auf PyPI bereits existiert
        3. Setzt GitHub Tag via GitHub API (POST /repos/.../git/refs)
        4. Erstellt ReleaseRun in DB
        5. Startet HTMX-Polling für Status-Updates
        """

    def check_trusted_publisher(self, package: PyPIPackage) -> bool:
        """Prüft via PyPI API ob Trusted Publisher korrekt konfiguriert ist."""

    def get_workflow_status(self, run: ReleaseRun) -> str:
        """Fragt GitHub Actions API nach aktuellem Run-Status."""

    def get_pypi_version(self, pypi_name: str) -> str:
        """Fragt PyPI JSON API nach aktueller Version."""
```

### 2.5 Views (HTMX-Pattern gemäß ADR-048)

```python
# releases/views.py

class PackageListView(ListView):
    """GET /releases/ — Alle registrierten Packages mit PyPI-Status."""

class PackageDetailView(DetailView):
    """GET /releases/<name>/ — Package-Detail + Release-Formular."""

class TriggerReleaseView(View):
    """POST /releases/<name>/release/ — Tag setzen, ReleaseRun anlegen."""
    # HTMX: gibt Status-Widget zurück das polling startet

class ReleaseStatusView(View):
    """GET /releases/<name>/status/<run_id>/ — HTMX-Polling Endpoint."""
    # Gibt aktualisierten Status-Badge zurück
    # HX-Trigger: stopPolling wenn completed
```

### 2.6 GitHub Tag via API (kein CLI)

```python
# releases/github_client.py

import httpx

class GitHubClient:
    """Setzt Git-Tags via GitHub REST API — kein CLI, kein SSH-Key nötig."""

    BASE = "https://api.github.com"

    def __init__(self, token: str):
        self._token = token

    def get_default_branch_sha(self, owner: str, repo: str) -> str:
        """HEAD-Commit SHA des Default-Branches."""
        ...

    def create_tag(self, owner: str, repo: str, tag: str, sha: str) -> dict:
        """POST /repos/{owner}/{repo}/git/refs — erstellt leichtgewichtigen Tag."""
        ...
```

---

## 3. Integration in bestehende dev-hub Infrastruktur

### 3.1 catalog-info.yaml Erweiterung

Jeder Repo mit PyPI-Packages bekommt einen `x-pypi-packages` Block:

```yaml
# nl2cad/catalog-info.yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: nl2cad
  annotations:
    github.com/project-slug: achimdehnert/nl2cad
spec:
  type: library
  lifecycle: production
  owner: achim-dehnert
  x-pypi-packages:
    - name: nl2cad-core
      tag_prefix: "nl2cad-core@"
      root_package: false
    - name: nl2cad-areas
      tag_prefix: "nl2cad-areas@"
      root_package: false
    - name: nl2cad-brandschutz
      tag_prefix: "nl2cad-brandschutz@"
      root_package: false
    - name: nl2cad-gaeb
      tag_prefix: "nl2cad-gaeb@"
      root_package: false
    - name: nl2cad-nlp
      tag_prefix: "nl2cad-nlp@"
      root_package: false
    - name: iil-nl2cadfw
      pypi_name: iil-nl2cadfw
      tag_prefix: "iil-nl2cadfw@"
      root_package: true
```

Der bestehende `populate_catalog` Management Command wird erweitert um
`x-pypi-packages` in `PyPIPackage` Modelle zu importieren.

### 3.2 GitHub Token

Ein GitHub PAT (Personal Access Token) mit `contents: write` Scope wird als
`GITHUB_PAT` in den dev-hub Secrets gespeichert. Nur zum Tag-Setzen verwendet —
das eigentliche Publizieren läuft weiterhin via OIDC in GitHub Actions.

---

## 4. Implementierungsplan

| Phase | Feature | Aufwand | Status |
|-------|---------|---------|--------|
| **P1** | `PyPIPackage` + `ReleaseRun` Models + Migrations | 2h | ✅ done |
| **P1** | `catalog-info.yaml` Import für `x-pypi-packages` | 1h | pending |
| **P2** | `GitHubClient.create_tag()` + `ReleaseService.trigger_release()` | 2h | ✅ done |
| **P2** | `PackageListView` + `PackageDetailView` + Templates | 2h | ✅ done |
| **P3** | `TriggerReleaseView` + HTMX-Polling Status-Widget | 2h | ✅ done |
| **P3** | PyPI API Integration (aktuelle Version abrufen) | 1h | ✅ done |
| **P4** | Trusted Publisher Checker (PyPI API) | 1h | pending |
| **P4** | `outlinefw/catalog-info.yaml` mit `x-pypi-packages` | 30min | ✅ done |

**Gesamtaufwand**: ~11h | **Target**: devhub.iil.pet/releases/

---

## 4b. Implementation — Live-Stand (2026-03-08)

### dev-hub `releases` App

- `apps/releases/models.py`: `PyPIPackage` + `ReleaseRun` — Migration `0001_initial` applied
- `apps/releases/services.py`: `ReleaseService` mit `trigger_release()`, `get_pypi_version()`, `refresh_run_status()`
- `apps/releases/views.py`: `PackageListView`, `PackageDetailView`, `TriggerReleaseView`, `RunStatusView` (HTMX-Polling)
- `apps/releases/urls.py`: Namespace `releases:*` unter `/releases/`
- Registriert in `INSTALLED_APPS` + `config/urls.py` — Live: `devhub.iil.pet/releases/`

### Erstes Live-Package: `iil-outlinefw`

| Feld | Wert |
|------|------|
| `PyPIPackage.repo` | `outlinefw` |
| `PyPIPackage.tag_prefix` | `v` |
| `PyPIPackage.workflow_file` | `publish.yml` |
| PyPI Trusted Publisher | ✅ konfiguriert (GitHub OIDC, env `pypi`) |
| Erste Version | `0.1.0` — 2026-03-08 |
| PyPI URL | https://pypi.org/project/iil-outlinefw/ |

### Validierter Release-Flow

```
POST /releases/iil-outlinefw/release/  version="0.1.0"
  → ReleaseService.trigger_release()
  → GitHub Tag v0.1.0 @ HEAD-SHA (via GitHub REST API)
  → publish.yml: Tests ✅ → hatch build ✅ → pypa/gh-action-pypi-publish ✅
  → iil-outlinefw 0.1.0 live auf PyPI
  → writing-hub: iil-outlinefw>=0.1.0,<1 in requirements.txt
```

### Abweichungen vom Design

| Punkt | Design | Ist |
|-------|--------|-----|
| Tag-Format | `package@0.2.0` | `v0.1.0` (SemVer-Standard) |
| Catalog-Import | `populate_catalog` Erweiterung | `catalog-info.yaml` vorhanden, Import pending |

---

## 5. Consequences

### 5.1 Positiv

- **Zero-CLI Releases**: Tag setzen + Publizieren komplett via UI
- **Überblick**: Alle Packages, Versionen, Workflow-Status auf einen Blick
- **Fehlerprävention**: UI validiert Version, prüft Trusted Publisher, zeigt SHA
- **Audit Trail**: Jeder Release-Trigger wird in `ReleaseRun` geloggt
- **Erweiterbar**: Gleiches Pattern für alle zukünftigen PyPI-Packages

### 5.2 Negativ / Risiken

| Risiko | Mitigation |
|--------|-----------|
| GitHub PAT muss rotiert werden | Secret in dev-hub `.env.prod`, Reminder im Calendar |
| PyPI API ohne Auth → Rate-Limit | Cache PyPI-Version für 5 Min (Redis) |
| GitHub Actions Status-Polling → viele API-Calls | HTMX-Polling nur wenn Run aktiv, max 60s |
| Tag auf falschem Commit | UI zeigt immer HEAD-SHA des Main-Branches an |

---

## 6. Abgrenzung zu bestehenden ADRs

| ADR | Bezug |
|-----|-------|
| **ADR-050** | dev-hub als Management Console — dieser ADR implementiert Release-Management als neue App darin |
| **ADR-077** | catalog-info.yaml als Import-Format — wird um `x-pypi-packages` erweitert |
| **ADR-086** | Agent Team Workflow — Release-Trigger kann zukünftig auch durch Agent ausgelöst werden |
| **ADR-090** | CI/CD Pipeline Pattern — publish.yml bleibt unverändert, UI ist nur Trigger |
