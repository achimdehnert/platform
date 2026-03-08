# ADR-090 — Private Package Distribution via GitHub Organization & GitHub Packages

| | |
|---|---|

| **Datum** | 2026-03-08 |
| **Autor** | Achim Dehnert / AI Engineering Squad |
| **Organisation** | iilgmbh (github.com/iilgmbh) |
| **Betrifft** | Alle Repos unter iilgmbh — platform, risk-hub, coach-hub, research-hub, mcp-hub, … |
| **Ersetzt** | Einzelne PROJECT_PAT Secrets pro Repo (achimdehnert/*) |
| **Basis-ADRs** | ADR-059, ADR-080, ADR-081 |

---

## 1. Kontext und Problemstellung

Das iilgmbh-Ökosystem besteht aus mehreren privaten Python-Projekten, die gemeinsame
Bibliotheken aus einem zentralen `platform`-Repository nutzen. Bisher wurden diese
als Git-Dependencies referenziert:

```
git+https://github.com/achimdehnert/platform.git@main#egg=django-tenancy
```

Sobald alle Repos auf **privat** gestellt werden, schlägt dieser Ansatz in CI/CD fehl —
GitHub Actions hat keinen anonymen Lesezugriff auf private Repos anderer Besitzer.

Der bisherige Workaround (PROJECT_PAT pro Repo manuell setzen) skaliert nicht:

- N Repos × manuelles Secret-Setting = hoher Verwaltungsaufwand
- PAT-Rotation muss in jedem Repo einzeln aktualisiert werden
- `git+https`-Dependencies sind kein echter Package-Manager — keine Versionierung,
  kein `pip freeze`, kein Dependency-Resolution

---

## 2. Entscheidungskriterien (Decision Drivers)

- **Zero-Maintenance** — kein manuelles Secret-Management pro Repo
- **Skalierbarkeit** — funktioniert automatisch für alle jetzigen und zukünftigen iilgmbh-Repos
- **Kosten** — keine zusätzliche Infrastruktur oder externe Dienste
- **Sicherheit** — private Packages bleiben privat
- **Developer Experience** — `pip install` funktioniert nativ, kein `git+https`-Hack
- **Versionierung** — Semantic Versioning, pinnable Versions in `requirements.txt`
- **Kompatibilität** — GitHub Actions, lokale Entwicklung, Windsurf/Cascade

---

## 3. Betrachtete Optionen — Vollständiger Vergleich

| Option | Aufwand (einmalig) | Laufend | Skaliert | Kosten | Empfehlung |
|---|---|---|---|---|---|
| **A: Org Secret + PAT** | Repos transferieren, 1× Secret | PAT 1×/Jahr rotieren | ✅ alle iilgmbh-Repos | $0 | ✅ Gut / sofort |
| **B: GitHub Packages** | publish-Workflow + pyproject.toml | Nichts (automatisch) | ✅ versioniert, pip-nativ | $0 | ⭐ **Beste Lösung** |
| **C: platform repo public** | 1 Klick | Nichts | ✅ einfachste | $0 | ⚠️ Kein IP-Schutz |
| **D: Gitea/Cloudsmith** | Infra aufbauen (~2 Tage) | Pakete bei Release pushen | ✅ professionell | $20–50/Mo | ❌ Over-Engineering |
| **E: Dateien kopieren** | Copy-Paste | Manuell sync bei Updates | ❌ nicht skalierbar | $0 | ❌ Tech Debt |

### 3.1 Option A — Organization Secret + Fine-Grained PAT

Ein Fine-Grained PAT mit `Contents:Read` auf `iilgmbh/platform` wird einmalig als
**Organization Secret** `PROJECT_PAT` gesetzt. Alle Workflows verwenden
`${{ secrets.PROJECT_PAT }}` für den pip-Install.

- ✅ Sofort einsetzbar, null Infrastruktur, Industry-Standard
- ✅ Organization Secrets sind automatisch in **allen** iilgmbh-Repos verfügbar
- ❌ `git+https` ist kein echter Package-Manager — keine Versionierung
- ❌ PAT muss jährlich rotiert werden (1 Org-Secret-Update)

### 3.2 Option B — GitHub Packages als privater PyPI ⭐

GitHub bietet für Organisationen einen privaten Package-Registry der vollständig
pip-kompatibel ist. Packages werden bei jedem Release-Tag automatisch publiziert.

- ✅ Echter Package-Manager mit Semantic Versioning
- ✅ Kostenlos für private Org-Repos
- ✅ `GITHUB_TOKEN` reicht für Publish — kein PAT nötig
- ✅ `pip install iilgmbh-django-tenancy==0.2.1` funktioniert nativ
- ❌ Einmaliger Setup-Aufwand (~1 Stunde)
- ❌ Consumer-Repos brauchen `pip.conf`-Anpassung

### 3.3 Option C — platform repo public

Das platform-Repo bleibt öffentlich. Kein Token-Handling nötig.

- ✅ Null Aufwand, sofort
- ❌ Kein IP-Schutz — Geschäftslogik öffentlich sichtbar

### 3.4 Option D — Gitea/Cloudsmith

Externe PyPI-Infrastruktur für professionelle Package-Distribution.

- ❌ Over-Engineering für 1 Person / kleines Team
- ❌ Zusätzliche Infrastruktur und Kosten (~$30/Mo)

---

## 4. Entscheidung

**Zweistufiger Ansatz:**

1. **Sofort: Option A** (Organization Secret + Fine-Grained PAT) —
   ermöglicht den Repo-Transfer und das Auf-Privat-Stellen ohne Downtime.

2. **Mittelfristig (innerhalb 1 Woche): Option B** (GitHub Packages) —
   vollständige Umstellung auf privaten PyPI für professionelle Package-Distribution.

**Begründung:** Option A ist der sichere Schritt 1, der nichts bricht.
Option B ist die nachhaltige Lösung die Developer Experience und Wartbarkeit
massiv verbessert. Beide schließen sich nicht aus — A ist die Brücke zu B.

---

## 5. Implementierungsplan

| # | Aktion | Wie | Aufwand | Status |
|---|---|---|---|---|
| 1 | Repos von `achimdehnert` zu `iilgmbh` transferieren | GitHub Settings → Transfer (pro Repo) | 5 min/Repo | ⏸ TODO |
| 2 | Fine-Grained PAT erstellen | Settings → Developer → Fine-grained PATs | 5 min | ⏸ TODO |
| 3 | `PROJECT_PAT` als Org Secret setzen | github.com/organizations/iilgmbh → Settings → Secrets | 2 min | ⏸ TODO |
| 4 | `pyproject.toml` für alle Packages anlegen | Für jedes Package in `iilgmbh/platform` | 30 min | ⏸ TODO |
| 5 | `publish.yml` Workflow in platform anlegen | Gemäß Abschnitt 5.1 | 15 min | ⏸ TODO |
| 6 | Ersten Release-Tag pushen und testen | `git tag v0.1.0 && git push --tags` | 10 min | ⏸ TODO |
| 7 | Consumer-Repos auf GitHub Packages umstellen | `requirements.txt` + `pip.conf` gemäß 5.3 | 15 min/Repo | ⏸ TODO |
| 8 | E2E-Test: CI in risk-hub grün | GitHub Actions Run beobachten | 15 min | ⏸ TODO |
| 9 | Alle Repos auf privat setzen | `gh repo edit --visibility private` (5.4) | 5 min | ⏸ TODO |

---

### 5.1 `publish.yml` — GitHub Packages (in `iilgmbh/platform`)

```yaml
# .github/workflows/publish.yml
name: Publish Packages to GitHub Packages

on:
  push:
    tags: ['v*.*.*']
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write          # GITHUB_TOKEN bekommt Write-Zugriff auf Packages
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install build tools
        run: pip install build twine

      - name: Build all packages
        run: |
          for pkg in packages/*/; do
            echo "Building $pkg"
            python -m build "$pkg" --outdir dist/
          done

      - name: Publish to GitHub Packages
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.GITHUB_TOKEN }}
        run: |
          twine upload \
            --repository-url https://upload.pkg.github.com/iilgmbh \
            dist/*.whl dist/*.tar.gz
```

---

### 5.2 `pyproject.toml` Template (pro Package in `iilgmbh/platform`)

```toml
# packages/django-tenancy/pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "iilgmbh-django-tenancy"
version = "0.1.0"
description = "Multi-Tenancy für iilgmbh Django-Projekte"
requires-python = ">=3.11"
dependencies = [
  "django>=4.2",
  "psycopg2-binary>=2.9",
]

[tool.setuptools.packages.find]
where = ["src"]
```

**Naming-Konvention:** Alle internen Packages erhalten den Prefix `iilgmbh-`
um Konflikte mit öffentlichen PyPI-Packages zu vermeiden.

---

### 5.3 Consumer-Repo: `pip.conf` + `requirements.txt`

```yaml
# In jedem Consumer-Repo CI-Workflow (oder als reusable workflow)
- name: Configure GitHub Packages
  run: |
    mkdir -p ~/.config/pip
    cat > ~/.config/pip/pip.conf << 'EOF'
    [global]
    extra-index-url = https://${{ secrets.PROJECT_PAT }}@pip.pkg.github.com/iilgmbh/simple/
    EOF

- name: Install dependencies
  run: pip install -r requirements.txt
```

```txt
# requirements.txt (Consumer-Repo — nach Umstellung)

# Interne Packages (von GitHub Packages)
iilgmbh-django-tenancy==0.1.0
iilgmbh-platform-context==0.1.0

# Externe Packages (von PyPI wie gewohnt)
django>=4.2
celery>=5.3
```

---

### 5.4 Alle Repos auf privat setzen (gh CLI)

```bash
# Alle iilgmbh-Repos auflisten und auf privat setzen
gh repo list iilgmbh --limit 100 --json name -q '.[].name' | \
  while read repo; do
    echo "Setting $repo to private..."
    gh repo edit "iilgmbh/$repo" --visibility private
  done
```

> **Hinweis:** Benötigt einen PAT mit `admin:org` + `repo` Scope.
> Nach vollständigem Transfer ist `GITHUB_TOKEN` in Actions ausreichend.

---

## 6. Ziel-Architektur

```
iilgmbh/platform  (privat)
├── packages/
│   ├── django-tenancy/       → iilgmbh-django-tenancy==0.x.x
│   ├── platform-context/     → iilgmbh-platform-context==0.x.x
│   └── django-module-shop/   → iilgmbh-django-module-shop==0.x.x
└── .github/workflows/
    └── publish.yml           → publiziert bei v*.*.*-Tag

GitHub Packages Registry (pip.pkg.github.com/iilgmbh/)
    ↑ GITHUB_TOKEN (publish)        ↓ PROJECT_PAT Org Secret (install)

iilgmbh/risk-hub    → pip install iilgmbh-django-tenancy==0.1.0
iilgmbh/coach-hub   → pip install iilgmbh-platform-context==0.1.0
iilgmbh/mcp-hub     → pip install iilgmbh-django-tenancy==0.1.0
iilgmbh/research-hub → pip install iilgmbh-platform-context==0.1.0
```

### Datenfluss: Von Commit zu `pip install`

```
Developer pusht Tag v0.2.0 in iilgmbh/platform
   │
   ▼
publish.yml startet (GITHUB_TOKEN mit packages:write)
   │
   ▼
python -m build → dist/*.whl erzeugt
   │
   ▼
twine upload → GitHub Packages Registry
   │           https://pip.pkg.github.com/iilgmbh/
   ▼
Consumer-Repo CI: pip install iilgmbh-django-tenancy==0.2.0
   │              (pip.conf + PROJECT_PAT Org Secret)
   ▼
Package installiert — CI grün ✅
```

---

## 7. Risiken und Mitigationen

| # | Risiko | Schwere | Mitigation |
|---|---|---|---|
| R1 | PAT verliert Scope oder läuft ab | Mittel | Org Secret: 1× jährlich rotieren. GitHub benachrichtigt 60 Tage vorher. |
| R2 | GitHub Packages Registry nicht erreichbar | Niedrig | `pip.conf` nutzt `extra-index-url` — PyPI-Packages bleiben erreichbar. |
| R3 | Repo-Transfer bricht bestehende Workflows | **Hoch** | Alle `git remote` URLs auf `iilgmbh/*` umstellen. GitHub leitet 301 weiter (temporär). |
| R4 | `GITHUB_TOKEN` hat keine Rechte auf andere Repos | Mittel | Für Cross-Repo-Zugriff `PROJECT_PAT` nutzen. `GITHUB_TOKEN` ist repo-scoped. |
| R5 | Package-Version Konflikt zwischen Repos | Niedrig | Semantic Versioning + pinned Dependencies (`==Version` statt `>=`). |
| R6 | Lokale Entwicklung ohne pip.conf | Niedrig | `make dev-setup` Target das `pip.conf` lokal schreibt (Token aus `.env`). |

---

## 8. Fine-Grained PAT — Minimaler Scope

```
Token Name:     iilgmbh-platform-read
Expiration:     1 Jahr (mit Kalender-Reminder für Rotation)
Repository:     iilgmbh/platform (nur dieses Repo)

Permissions:
  Contents:     Read-only   ← einzige benötigte Permission
  Metadata:     Read-only   ← automatisch gesetzt

NICHT benötigt:
  Actions, Secrets, Pull Requests, Issues, Workflows, ...
```

---

## 9. Consequences

### Positiv
- Alle iilgmbh-Repos funktionieren sofort nach Transfer mit Organization Secret
- `pip install iilgmbh-*` funktioniert nativ — kein `git+https`-Hack mehr
- Semantic Versioning: Consumer-Repos können auf spezifische Versionen pinnen
- Zero-Maintenance nach Setup: PAT 1×/Jahr, Packages automatisch bei Release
- Lokale Entwicklung und CI nutzen dieselbe `pip.conf` — keine Umgebungs-Unterschiede

### Negativ / Akzeptierte Trade-offs
- `pip.conf` muss in allen Consumer-Repos eingerichtet werden (einmaliger Aufwand)
- GitHub Packages hat kein Web-UI für Browse wie PyPI — nur API/CLI-Zugriff
- Bei GitHub-Outage sind interne Packages nicht installierbar (acceptable für internes Tool)

---

## 10. Offene Punkte

| # | Frage | Entscheider | Deadline |
|---|---|---|---|
| O1 | Welche Packages sollen initial publiziert werden? | Achim | Vor Schritt 4 |
| O2 | Soll `make dev-setup` die lokale `pip.conf` automatisch schreiben? | Achim | Vor Schritt 7 |
| O3 | Reusable Workflow in `platform` für Consumer-Repos? | AI Squad | Phase 7 |

---

*Erstellt: 2026-03-08 | Autor: Cascade (Claude Sonnet 4.6) | Status: ACCEPTED*
