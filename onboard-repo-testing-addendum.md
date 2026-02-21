---
description: Testing-Addendum für onboard-repo — wird in Step 1.6 und Checkliste referenziert
---

# Onboard-Repo: Testing-Addendum (ADR-058)

Dieses Dokument ergänzt `.windsurf/workflows/onboard-repo.md` um den verpflichtenden
Testing-Abschnitt. Die vollständige Anleitung steht in `testing-setup.md`.

## Step 1.6: Test-Infrastruktur (PFLICHT, nach Step 1.5)

**Vollständige Anleitung:** `.windsurf/workflows/testing-setup.md`

Kurzfassung für neue Django-Repos:

1. `requirements-test.txt` mit `platform-context[testing]>=0.3.0` erstellen
2. `tests/conftest.py` mit Imports aus `platform_context.testing.fixtures`
3. `tests/factories.py` mit `UserFactory` (+ domain-spezifische Factories)
4. `tests/test_auth.py` mit `assert_login_required` für alle geschützten URLs
5. `pyproject.toml` mit `[tool.pytest.ini_options]`

Für Nicht-Django-Repos (MCP-Server, Libraries): nur Assertion-Helpers einbinden.

## Checkliste-Ergänzung für Step 7

Diese Punkte gehören in die Verifikations-Checkliste von `onboard-repo.md`:

```text
Testing (ADR-058):
  [ ] requirements-test.txt mit platform-context[testing]>=0.3.0
  [ ] tests/__init__.py existiert
  [ ] tests/conftest.py importiert platform_context.testing.fixtures
  [ ] tests/factories.py mit UserFactory
  [ ] tests/test_auth.py mit assert_login_required für alle geschützten URLs
  [ ] pyproject.toml mit [tool.pytest.ini_options]
  [ ] CI/CD: pytest läuft in Stage 1 (vor Build + Deploy)
  [ ] pytest läuft lokal ohne Fehler: pytest tests/ -v
```

## CI/CD: Tests automatisch im Deployment

Tests laufen **immer vor dem Deploy** — garantiert durch `needs: [ci]` in der Pipeline.

```
push to main
    │
    ▼
[Stage 1: CI]  ← pytest läuft hier (platform_context.testing)
    ├── ruff lint
    ├── pytest tests/
    └── security scan
    │
    ▼ (nur wenn CI grün)
[Stage 2: Build]  ← kein Deploy ohne grüne Tests
    └── docker build + push to GHCR
    │
    ▼
[Stage 3: Deploy]
    ├── docker compose pull + up --force-recreate
    └── health check /livez/ → Rollback wenn 503
```

### Post-Deploy Tests im Container (für DB-abhängige Tests)

```bash
# Via deployment-mcp:
mcp5_docker_manage(action="container_exec",
    container_id="<REPO_UNDERSCORE>_web",
    command="python manage.py test apps/ --verbosity=2")
```

**Empfehlung:**
- Unit/Integration-Tests → im CI (vor Deploy, schnell, kein Server nötig)
- DB-Migrations-Tests → im Container nach Deploy (echte DB)
- Smoke-Tests → HTTP-Check auf `/livez/` + `/healthz/` nach Deploy
