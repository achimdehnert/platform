# ADR-162: REFLEX UI Testing & Authenticated Scraping

- **Status:** accepted
- **Date:** 2026-04-15
- **Decision-Makers:** Achim Dehnert
- **Scope:** platform (all hubs)
- **Related:** ADR-040, ADR-041, ADR-043, ADR-058

## Context and Problem Statement

UI-Qualität wird bisher nur durch manuelle Inspektion und Django unit tests (`test_frontend_views.py`) geprüft. Es fehlt:

1. **Systematische UI-Audits** — Heading-Hierarchie, ARIA-Labels, Tab-Order, HTMX-Verhalten
2. **Authentifiziertes Testen mit Playwright** — Cascade's Playwright MCP hat isolierte Browser-Sessions ohne Zugriff auf Credentials
3. **Daten-Extraktion aus login-geschützten Apps** — Odoo, Broker-Portale, interne Hubs

## Decision Drivers

- UI-Bugs fallen erst in Produktion auf (kein systematisches Gate)
- Playwright MCP (Cascade) kann keine Passwörter eingeben (keine .env Zugriff)
- Manuelle Logins in CI/CD sind fragil und nicht reproduzierbar
- Daten-Import aus Drittanbieter-Portalen ist bisher manuell

## Considered Options

1. **Selenium + pytest** — etabliert, aber langsam und wartungsintensiv
2. **Cypress** — JavaScript-only, kein Python-Ökosystem
3. **Playwright + REFLEX Methodik** — Python-native, Session Storage, MCP-integriert

## Decision Outcome

**Option 3: Playwright + REFLEX Methodik** mit drei komplementären Layern:

### Layer 1: Playwright MCP (Cascade interaktiv)

- Auth via `/dev-login/` signed token (SECRET_KEY, 5 min TTL)
- Kein Passwort in Tool-Output — Token wird on-the-fly generiert
- Für ad-hoc UI-Inspektion und REFLEX Audit-Läufe

### Layer 2: pytest-playwright (lokal / CI)

- Auth via Session Storage (`.auth/session.json`) aus `.env.test`
- REFLEX Zirkel 2: Audit-Tests gegen existierende UI
- Ergebnis: `feedback.json` pro Use Case / Version

### Layer 3: scraper_mcp (Batch-Extraktion)

- Neues MCP-Modul in `mcp-hub/scraper_mcp/`
- Auth via Session Storage + `.env.scraper`
- MCP-Tools: `scrape_table`, `download_report`, `screenshot_hub`
- Einsatz: Daten-Import aus Odoo, Trading-Portale, externe Compliance-DBs

### Shared Components

| Component | Layer 1 | Layer 2 | Layer 3 |
|-----------|---------|---------|---------|
| `/dev-login/` View | ✅ Primary | ✅ Alternative | ✅ Alternative |
| Session Storage | ❌ | ✅ Primary | ✅ Primary |
| `extractors.py` | ❌ | ✅ Assertions | ✅ Data Output |
| `feedback.json` | ❌ | ✅ Output | ❌ |

### REFLEX Methodik (v0.3)

Evidenzbasierter Qualitätszirkel:

1. **Zirkel 0** — Domain KB + Wireframe (kein Code)
2. **Zirkel 1** — Playwright ARIA-Snapshot → feedback.json → Iteration
3. **Zirkel 2** — pytest-playwright Audit gegen Live-UI
4. **Gate** — Alle Audit-Tests grün → erst dann Production-Code

### `/dev-login/` Pattern (alle Hubs)

```python
# apps/core/views_dev_login.py
class DevLoginView(View):
    def get(self, request):
        token = request.GET.get("token")
        data = signing.loads(token, max_age=300)  # 5 min
        user = User.objects.get(pk=data["uid"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect(data.get("next", "/"))
```

Generierung via Management Command:

```bash
python manage.py dev_login_url --next /projekte/
# → /dev-login/?token=<signed>
```

### Sicherheit

- Token ist SECRET_KEY-signiert, nicht erratbar
- TTL 5 Minuten — abgelaufene Tokens werden abgelehnt
- Kein Passwort wird gespeichert oder übertragen
- `.auth/`, `.env.test`, `.env.scraper` in `.gitignore`

## Consequences

### Positive

- Systematische UI-Qualität durch evidenzbasierte Audits
- Cascade kann authentifizierte Seiten testen (Layer 1)
- CI kann UI-Regression erkennen (Layer 2)
- Daten-Import aus Drittanbieter-Portalen automatisiert (Layer 3)

### Negative

- `/dev-login/` Endpoint muss in jedem Hub eingebaut werden
- Session Storage erfordert initiales Setup pro Umgebung
- scraper_mcp ist neues MCP-Modul mit Wartungsaufwand

### Risks

- `/dev-login/` in Production: Token-TTL von 5 Min und SECRET_KEY-Signatur sind ausreichend sicher für interne Apps
- Session Expiry: `check_session_valid()` + Auto-Renew löst das Problem

## Implementation Evidence

- writing-hub: `/dev-login/` + `dev_login_url` Command (Commit 5f5e8bd)
- writing-hub: `tests/ui/` Infrastruktur + 27 Audit-Tests (Commit 5f5e8bd)
- writing-hub: `feedback/writing-hub-audit.v1.feedback.json` — 27/27 PASS
