---
description: Vollständigkeits-Check für Repos und Packages — verbindliches Quality Gate vor Publish/Deploy
---

# Repo Health Check

**Trigger:** Vor jedem neuen Repo-Onboarding, Package-Publish oder wenn "unvollständige Angaben" gemeldet werden.

> Dieser Workflow ist **verbindlich**. Alle BLOCK-Items müssen grün sein bevor gepublisht oder deployed wird.
> Das maschinenausführbare Script `platform/tools/repo_health_check.py` prüft dieselben Regeln automatisch.

---

## Profil wählen

Zuerst bestimmen welches Profil zutrifft:

| Profil | Wann | Beispiele |
|--------|------|-----------|
| **python-package** | PyPI-publish, kein Django | authoringfw, aifw, nl2cad, riskfw, promptfw |
| **django-app** | Django + Docker + Hetzner | bfagent, travel-beat, weltenhub, risk-hub |

---

## PROFIL: python-package

### Step 1: pyproject.toml Vollständigkeit

// turbo
```bash
python3 -c "
import tomllib, sys
try:
    d = tomllib.load(open('pyproject.toml','rb'))['project']
    fields = ['name','version','description','readme','requires-python','license','authors','keywords','classifiers']
    missing = [f for f in fields if not d.get(f)]
    urls = d.get('urls', {})
    url_missing = [u for u in ['Homepage','Repository'] if u not in urls]
    print('MISSING fields:', missing or 'none')
    print('MISSING urls:', url_missing or 'none')
    print('description:', repr(d.get('description','')))
except Exception as e:
    print('ERROR:', e)
"
```

**BLOCK** — darf nicht fehlen:
- [ ] `name` — exakter PyPI-Package-Name
- [ ] `version` — SemVer (z.B. `0.1.0`)
- [ ] `description` — **nicht leer, nicht None** — max. 1 Satz, aussagekräftig
- [ ] `readme = "README.md"` — PyPI zeigt sonst keine Doku
- [ ] `requires-python` — z.B. `>=3.11`
- [ ] `license = {text = "MIT"}`
- [ ] `authors` — Name + E-Mail
- [ ] `keywords` — mind. 3 relevante Keywords
- [ ] `classifiers` — mind. Development Status, License, Python Version
- [ ] `[project.urls]` mit `Homepage` + `Repository`

**SUGGEST** — empfohlen:
- [ ] `[project.optional-dependencies]` mit `dev` Gruppe (pytest, ruff)
- [ ] `[tool.pytest.ini_options]` mit `testpaths` + `pythonpath`
- [ ] `[tool.ruff]` mit `line-length = 100`

---

### Step 2: Pflicht-Dateien

// turbo
```bash
for f in README.md CHANGELOG.md .gitignore pyproject.toml tests/__init__.py Makefile; do
  [ -e "$f" ] && echo "OK: $f" || echo "MISSING: $f"
done
```

**BLOCK:**
- [ ] `README.md` — mit Installations-Anleitung + Beispiel
- [ ] `.gitignore` — inkl. `dist/`, `*.egg-info/`, `__pycache__/`
- [ ] `pyproject.toml`
- [ ] `tests/` Verzeichnis

**SUGGEST:**
- [ ] `CHANGELOG.md`
- [ ] `Makefile` mit `make test` / `make clean`

---

### Step 3: GitHub Actions Workflows

// turbo
```bash
ls .github/workflows/ 2>/dev/null || echo "MISSING: .github/workflows/"
for f in test.yml publish.yml; do
  [ -e ".github/workflows/$f" ] && echo "OK: $f" || echo "MISSING: $f"
done
```

**BLOCK:**
- [ ] `.github/workflows/test.yml` — pytest auf push + PR
- [ ] `.github/workflows/publish.yml` — PyPI publish bei `v*` Tag

**BLOCK: Publish-Gate** — `publish.yml` muss `needs: test` haben:
```bash
grep -A2 'jobs:' .github/workflows/publish.yml | grep 'test\|needs'
grep 'needs:' .github/workflows/publish.yml
```
- [ ] `build` Job hat `needs: test` — **kein Publish ohne grüne Tests**

**BLOCK: Trigger** — `test.yml` muss auf push UND pull_request triggern:
```bash
grep -A5 '^on:' .github/workflows/test.yml
```
- [ ] `on: push: branches: [main]`
- [ ] `on: pull_request: branches: [main]`

---

### Step 4: GitHub Repository-Metadaten

Mit GitHub MCP prüfen:
```
<github-mcp>_get_file_contents *(Prefix aus mcp-tools.md)*(owner, repo, path="/") → prüfe response auf description != null
```

**BLOCK:**
- [ ] GitHub Repo `description` gesetzt (nicht `null`) — via GitHub UI: Repo → Zahnrad → About
- [ ] GitHub Repo hat mindestens 1 `topic`/Tag (optional aber empfohlen)

---

### Step 5: Tests laufen durch

```bash
make clean && make test
```

**BLOCK:**
- [ ] `pytest` läuft ohne Fehler
- [ ] Mind. 1 Test vorhanden (kein leeres `tests/`)

---

## PROFIL: django-app

### Step 1: Pflicht-Dateien

// turbo
```bash
for f in Makefile docker-compose.prod.yml Dockerfile .env.example requirements.txt requirements-test.txt; do
  [ -e "$f" ] && echo "OK: $f" || echo "MISSING: $f"
done
```

**BLOCK:**
- [ ] `Makefile` mit `make test` (DJANGO_SETTINGS_MODULE gesetzt)
- [ ] `docker-compose.prod.yml`
- [ ] `Dockerfile` (in Repo-Root oder `docker/app/Dockerfile`)
- [ ] `.env.example` — alle benötigten Keys dokumentiert, keine echten Werte
- [ ] `requirements.txt` + `requirements-test.txt`

**SUGGEST:**
- [ ] `CHANGELOG.md`
- [ ] `scripts/deploy.sh`

---

### Step 2: GitHub Actions Workflows

// turbo
```bash
ls .github/workflows/
```

**BLOCK:**
- [ ] `ci.yml` oder `_ci-python.yml` — Tests auf push + PR
- [ ] Build-Job hat `needs: [ci]` (kein Deploy ohne Tests)
- [ ] Deploy-Job hat `needs: [build]`

**SUGGEST:**
- [ ] `deploy-check.yml` oder `/deploy-check` Workflow bekannt

---

### Step 3: Django-Pflichten

```bash
grep -r 'tenant_id' src/ apps/ --include='*.py' -l | head -5
grep -r 'livez\|healthz' . --include='*.py' -l | head -3
```

**BLOCK:**
- [ ] Health-Endpoint `/livez/` existiert
- [ ] Alle user-data Models haben `tenant_id` (Multi-Tenant-Repos)
- [ ] `config/settings/test.py` existiert (für `DJANGO_SETTINGS_MODULE`)

---

### Step 4: Tests laufen durch

```bash
make clean && make test
```

**BLOCK:**
- [ ] `pytest` grün
- [ ] Mind. 10 Tests (Django-Apps haben mehr Oberfläche)

---

## Automatische Prüfung (maschinenausführbar)

Das Script `platform/tools/repo_health_check.py` prüft alle BLOCK-Items:

```bash
# Python Package
python3 ${GITHUB_DIR:-$HOME/github}/platform/tools/repo_health_check.py --profile python-package --path .

# Django App
python3 ${GITHUB_DIR:-$HOME/github}/platform/tools/repo_health_check.py --profile django-app --path .

# Mit GitHub-Check (braucht GITHUB_TOKEN)
python3 ${GITHUB_DIR:-$HOME/github}/platform/tools/repo_health_check.py --profile python-package --path . --owner achimdehnert --repo <name>
```

Exit-Code:
- `0` = alle BLOCK-Items OK
- `1` = ein oder mehr BLOCK-Items fehlgeschlagen

---

## Wann wird dieser Workflow ausgeführt?

| Situation | Wann | Wer |
|-----------|------|-----|
| Neues Repo anlegen | Pflicht vor erstem Commit | Agent + User |
| Neues PyPI-Package | Pflicht vor erstem `publish.yml` Tag | Agent |
| "unvollständige Angaben" gemeldet | Sofort | Agent |
| `/onboard-repo` Workflow | Eingebettet in Step 1 | Agent |
| Quarterly Review | Optional | Agent |

---

## Schnell-Fix wenn BLOCK-Items fehlen

| Fehlendes Item | Schnell-Fix |
|----------------|-------------|
| `description` leer | `pyproject.toml` editieren + `hatch build` + neu publishen |
| GitHub Repo `description: null` | GitHub UI: Repo → Zahnrad → About → Description eintragen |
| `publish.yml` ohne `needs: test` | Job `build:` → `needs: test` hinzufügen |
| `test.yml` fehlt | Template aus `authoringfw/.github/workflows/test.yml` kopieren |
| `Makefile` fehlt | Template aus `authoringfw/Makefile` kopieren |
| GitHub Repo description | Manuell: GitHub UI oder `gh repo edit --description "..."` |

---

## Server / Container Status

Laufzeit-Status der Platform-Server (Container up/down, Memory, Uptime) ist **getrennt** davon:

→ **[Operations Dashboard](https://devhub.iil.pet/operations/)** — Server-Status, Windsurf, Container-Logs
→ **[Health Dashboard](https://devhub.iil.pet/health/)** — Endpoint-Monitoring aller Hubs

Dieser Workflow prüft **Repo-Vollständigkeit** (CI, Tests, Dateien).
Das Operations Dashboard zeigt **Laufzeit-Status** (Server, Container).

---

*repo-health-check v1.1 | Platform Coding Agent System | 2026-03-05*
