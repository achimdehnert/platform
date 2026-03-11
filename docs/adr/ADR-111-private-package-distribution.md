---
status: superseded
date: 2026-03-08
amended: 2026-03-11
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
related: [ADR-022-platform-consistency-standard.md]
---

# ADR-111 — Private Package Distribution via GitHub Packages

> **⚠️ Status: Superseded (2026-03-11)**
> Die Package-Repos (`aifw`, `authoringfw`, `promptfw`, `weltenfw`, `illustration-fw`,
> `testkit`, `researchfw`) wurden als **eigenständige Repos** unter `achimdehnert/`
> aufgesetzt und publizieren direkt auf **PyPI** (öffentlich).
> `iil-testkit==0.1.0` ist seit 2026-03-06 auf PyPI.
> GitHub Packages bleibt als Fallback relevant falls Repos privat werden.
> Die `platform/packages/` Subdirectory-Strategie ist deprecated.

| | |
|---|---|
| **Status** | ~~Accepted~~ → **Superseded** |
| **Datum** | 2026-03-08 |
| **Autor** | Achim Dehnert / AI Engineering Squad |
| **Organisation** | achimdehnert (github.com/achimdehnert) |
| **Betrifft** | Alle Repos unter achimdehnert — platform, risk-hub, coach-hub, research-hub, mcp-hub, … |
| **Ersetzt** | Einzelne PROJECT_PAT Secrets pro Repo (manuell) |
| **Basis-ADRs** | ADR-059, ADR-080, ADR-081, ADR-022 |

---

## 1. Kontext und Problemstellung

Das Ökosystem besteht aus mehreren privaten Python-Projekten, die gemeinsame
Bibliotheken aus `achimdehnert/platform` nutzen. Bisher wurden diese
als Git-Dependencies referenziert:

```
git+https://github.com/achimdehnert/platform.git@main#subdirectory=packages/django-tenancy
```

Sobald Repos auf **privat** gestellt werden, schlägt dieser Ansatz in CI/CD fehl —
GitHub Actions hat keinen anonymen Lesezugriff auf private Repos.

Der bisherige Workaround (PROJECT_PAT pro Repo manuell setzen) skaliert nicht:

- N Repos × manuelles Secret-Setting = hoher Verwaltungsaufwand
- PAT-Rotation muss in jedem Repo einzeln aktualisiert werden
- `git+https`-Dependencies sind kein echter Package-Manager — keine Versionierung,
  kein `pip freeze`, kein Dependency-Resolution

---

## 2. Entscheidungskriterien

- **Zero-Maintenance** — kein manuelles Secret-Management pro Repo
- **Skalierbarkeit** — funktioniert automatisch für alle jetzigen und zukünftigen Repos
- **Kosten** — keine zusätzliche Infrastruktur oder externe Dienste
- **Sicherheit** — private Packages bleiben privat
- **Developer Experience** — `pip install` funktioniert nativ, kein `git+https`-Hack
- **Versionierung** — Semantic Versioning, pinnable Versions
- **Kompatibilität** — GitHub Actions, lokale Entwicklung, Windsurf/Cascade
- **Konsistenz** — `hatchling` Build-Backend (Platform-Standard, ADR-022)

---

## 3. Optionen

| Option | Aufwand (einmalig) | Laufend | Skaliert | Kosten | Empfehlung |
|---|---|---|---|---|---|
| **A: Org Secret + PAT** | 1× Secret setzen | PAT 1×/Jahr rotieren | ✅ alle Repos | $0 | ✅ Brücke zu B |
| **B: GitHub Packages** | publish-Workflow + pyproject.toml | Nichts (automatisch) | ✅ versioniert | $0 | ⭐ **Ziel** |
| **C: platform repo public** | 1 Klick | Nichts | ✅ einfachste | $0 | ⚠️ Kein IP-Schutz |
| **D: Gitea/Cloudsmith** | ~2 Tage | Pakete pushen | ✅ professionell | $20–50/Mo | ❌ Over-Engineering |
| **E: Dateien kopieren** | Copy-Paste | Manuell bei Updates | ❌ | $0 | ❌ Tech Debt |

### 3.1 Option A — Fine-Grained PAT als Repository Secret

Ein Fine-Grained PAT mit `Contents:Read` auf `achimdehnert/platform` wird als
**Repository Secret** `PROJECT_PAT` in jedem Consumer-Repo gesetzt — oder als
**Org Secret** wenn eine GitHub Organization vorhanden ist.

- ✅ Sofort einsetzbar, null Infrastruktur, Industry-Standard
- ❌ `git+https` ist kein echter Package-Manager
- ❌ PAT muss jährlich rotiert werden

### 3.2 Option B — GitHub Packages als privater PyPI ⭐

GitHub bietet für Repositories einen privaten Package-Registry der vollständig
pip-kompatibel ist. Packages werden bei jedem Release-Tag automatisch publiziert.

- ✅ Echter Package-Manager mit Semantic Versioning
- ✅ Kostenlos für private Repos
- ✅ `GITHUB_TOKEN` reicht für Publish — kein PAT nötig
- ✅ `pip install iil-django-tenancy==0.2.1` funktioniert nativ
- ❌ Einmaliger Setup-Aufwand (~1 Stunde)
- ❌ Consumer-Repos brauchen `pip.conf`-Anpassung oder `--extra-index-url`

---

## 4. Entscheidung

**Zweistufiger Ansatz:**

1. **Sofort: Option A** — PAT als Repository Secret ermöglicht `pip install` aus
   privaten Repos ohne Downtime.

2. **Mittelfristig (innerhalb 1 Woche): Option B** — GitHub Packages als privater PyPI
   für professionelle Package-Distribution mit Semantic Versioning.

**Begründung:** Option A ist der sichere Schritt 1 — nichts bricht.
Option B ist die nachhaltige Lösung. Beide schließen sich nicht aus.

### Naming-Konvention

Alle internen Packages verwenden den Prefix **`iil-`** (konsistent mit
bestehenden PyPI-Packages: `iil-aifw`, `iil-testkit`, `iil-django-tenancy`).
**Nicht** `iilgmbh-` — Konflikte mit bestehenden Packages vermeiden.

---

## 5. Implementierungsplan

| # | Aktion | Wie | Aufwand | Status |
|---|---|---|---|---|
| 1 | Fine-Grained PAT erstellen | Settings → Developer → Fine-grained PATs | 5 min | ⏸ TODO |
| 2 | `PROJECT_PAT` als Repository Secret (oder Org Secret) setzen | Repo/Org → Settings → Secrets | 2 min/Repo | ⏸ TODO |
| 3 | `pyproject.toml` für alle Packages prüfen | `packages/*/pyproject.toml` — Standard bereits gesetzt | ✅ erledigt | ✅ |
| 4 | `publish-packages.yml` Workflow anlegen | Gemäß Abschnitt 5.1 | 15 min | ⏸ TODO |
| 5 | Ersten Release-Tag pushen und testen | `git tag packages/v0.1.0 && git push --tags` | 10 min | ⏸ TODO |
| 6 | Consumer-Repos auf GitHub Packages umstellen | `requirements.txt` + Workflow gemäß 5.3 | 15 min/Repo | ⏸ TODO |
| 7 | E2E-Test: CI in einem Consumer-Repo grün | GitHub Actions Run beobachten | 15 min | ⏸ TODO |
| 8 | Repos auf privat setzen (optional) | `gh repo edit --visibility private` (5.4) | 5 min | ⏸ TODO |

---

### 5.1 `publish-packages.yml` — GitHub Packages (in `achimdehnert/platform`)

```yaml
# .github/workflows/publish-packages.yml
name: Publish Packages to GitHub Packages

on:
  push:
    tags:
      - 'packages/v*.*.*'
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install build tools
        run: |
          set -euo pipefail
          pip install build twine

      - name: Build all packages
        run: |
          set -euo pipefail
          for pkg in packages/*/; do
            if [ -f "$pkg/pyproject.toml" ]; then
              echo "Building $pkg"
              python -m build "$pkg" --outdir dist/
            fi
          done

      - name: Publish to GitHub Packages
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          twine upload \
            --repository-url https://upload.pkg.github.com/achimdehnert \
            dist/*.whl dist/*.tar.gz
```

---

### 5.2 `pyproject.toml` Standard (bereits implementiert)

```toml
# packages/django-tenancy/pyproject.toml — Referenz-Implementation
[build-system]
requires = ["hatchling"]          # Platform-Standard (ADR-022) — NICHT setuptools legacy
build-backend = "hatchling.build"

[project]
name = "iil-django-tenancy"       # Prefix iil- (konsistent mit iil-aifw, iil-testkit)
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "Django>=4.2",
]

[tool.hatch.build.targets.wheel]
packages = ["django_tenancy"]
```

**Naming-Regel:** Alle internen Packages → `iil-<name>` (nicht `iilgmbh-`).

---

### 5.3 Consumer-Repo: CI-Workflow + `requirements.txt`

```yaml
# In jedem Consumer-Repo CI-Workflow
- name: Configure GitHub Packages
  run: |
    set -euo pipefail
    pip install \
      --extra-index-url https://${{ secrets.PROJECT_PAT }}@pip.pkg.github.com/achimdehnert/simple/ \
      -r requirements.txt
```

Alternativ via `pip.conf` (für lokale Entwicklung):

```ini
# ~/.config/pip/pip.conf  (lokal — via make dev-setup generiert)
[global]
extra-index-url = https://<PAT>@pip.pkg.github.com/achimdehnert/simple/
```

```txt
# requirements.txt (Consumer-Repo — nach Umstellung)

# Interne Packages (von GitHub Packages)
iil-django-tenancy==0.1.0

# Externe Packages (von PyPI wie gewohnt)
django>=4.2
celery>=5.3
```

---

### 5.4 `make dev-setup` Target (Makefile in Consumer-Repos)

```makefile
# Makefile
dev-setup:
	@echo "Configuring GitHub Packages access..."
	@if [ -z "$$PROJECT_PAT" ]; then \
	  echo "ERROR: PROJECT_PAT env var required. Set in .env"; exit 1; \
	fi
	@mkdir -p ~/.config/pip
	@echo "[global]\nextra-index-url = https://$$PROJECT_PAT@pip.pkg.github.com/achimdehnert/simple/" \
	  > ~/.config/pip/pip.conf
	@echo "pip.conf written. Run: pip install -r requirements.txt"
```

---

### 5.5 Alle Repos auf privat setzen (gh CLI, optional)

```bash
# Einzelnes Repo:
gh repo edit achimdehnert/platform --visibility private

# Alle Repos (benötigt PAT mit admin:repo Scope):
gh repo list achimdehnert --limit 100 --json name -q '.[].name' | \
  while read repo; do
    echo "Setting $repo to private..."
    gh repo edit "achimdehnert/$repo" --visibility private
  done
```

---

## 6. Ziel-Architektur

```
achimdehnert/platform  (privat)
├── packages/
│   ├── django-tenancy/       → iil-django-tenancy==0.x.x
│   └── (weitere packages/)
└── .github/workflows/
    └── publish-packages.yml  → publiziert bei packages/v*.*.*-Tag

GitHub Packages Registry (pip.pkg.github.com/achimdehnert/)
    ↑ GITHUB_TOKEN (publish)        ↓ PROJECT_PAT Secret (install)

achimdehnert/risk-hub    → pip install iil-django-tenancy==0.1.0
achimdehnert/weltenhub   → pip install iil-django-tenancy==0.1.0
achimdehnert/mcp-hub     → pip install iil-django-tenancy==0.1.0
```

### Datenfluss

```
Developer pusht Tag packages/v0.2.0 in achimdehnert/platform
   │
   ▼
publish-packages.yml startet (GITHUB_TOKEN mit packages:write)
   │
   ▼
python -m build → dist/*.whl erzeugt (hatchling)
   │
   ▼
twine upload → GitHub Packages Registry
   │           https://pip.pkg.github.com/achimdehnert/
   ▼
Consumer-Repo CI: pip install iil-django-tenancy==0.2.0
   │              (--extra-index-url + PROJECT_PAT Secret)
   ▼
Package installiert — CI grün ✅
```

---

## 7. Risiken und Mitigationen

| # | Risiko | Schwere | Mitigation |
|---|---|---|---|
| R1 | PAT verliert Scope oder läuft ab | Mittel | Repository Secret: 1× jährlich rotieren. GitHub benachrichtigt 60 Tage vorher. |
| R2 | GitHub Packages Registry nicht erreichbar | Niedrig | `extra-index-url` — PyPI-Packages bleiben erreichbar. |
| R3 | `GITHUB_TOKEN` hat keine Rechte auf andere Repos | Mittel | Für Cross-Repo-Zugriff `PROJECT_PAT` nutzen. `GITHUB_TOKEN` ist repo-scoped. |
| R4 | Package-Version Konflikt zwischen Repos | Niedrig | Semantic Versioning + pinned Dependencies (`==Version`). |
| R5 | Lokale Entwicklung ohne pip.conf | Niedrig | `make dev-setup` schreibt `pip.conf` lokal (Token aus `.env`). |
| R6 | Tag-Konflikt mit normalen Release-Tags | Niedrig | Package-Tags `packages/v*.*.*` sind von App-Tags getrennt. |

---

## 8. Fine-Grained PAT — Minimaler Scope

```
Token Name:     platform-packages-read
Expiration:     1 Jahr (mit Kalender-Reminder für Rotation)
Repository:     achimdehnert/platform (nur dieses Repo)

Permissions:
  Contents:     Read-only   ← einzige benötigte Permission
  Packages:     Read-only   ← für pip install aus GitHub Packages
  Metadata:     Read-only   ← automatisch gesetzt

NICHT benötigt:
  Actions, Secrets, Pull Requests, Issues, Workflows, ...
```

---

## 9. Consequences

### Positiv
- `pip install iil-*` funktioniert nativ — kein `git+https`-Hack mehr
- Semantic Versioning: Consumer-Repos können auf spezifische Versionen pinnen
- Zero-Maintenance nach Setup: PAT 1×/Jahr, Packages automatisch bei Release-Tag
- Lokale Entwicklung und CI nutzen dieselbe Methode — keine Umgebungs-Unterschiede
- `hatchling` Build-Backend konsistent mit Platform-Standard

### Negativ / Akzeptierte Trade-offs
- `PROJECT_PAT` Secret muss in allen Consumer-Repos eingerichtet werden (einmaliger Aufwand)
- GitHub Packages hat kein Web-UI wie PyPI — nur API/CLI-Zugriff
- Bei GitHub-Outage sind interne Packages nicht installierbar (acceptable für internes Tool)

---

## 10. Offene Punkte

| # | Frage | Entscheider | Deadline |
|---|---|---|---|
| O1 | Welche Packages sollen initial publiziert werden? (`iil-django-tenancy` allein, oder auch `platform-context`?) | Achim | Vor Schritt 4 |
| O2 | `make dev-setup` Target in alle Consumer-Repos Makefile aufnehmen? | Achim | Vor Schritt 6 |
| O3 | Reusable Workflow in `platform` für Consumer-Repos (ADR-080)? | AI Squad | Phase 6 |

---

*ADR-111 | Platform Architecture | 2026-03-08 | Erstellt aus Input ADR-XXX (korrigiert: Org achimdehnert, hatchling, iil- Prefix)*
