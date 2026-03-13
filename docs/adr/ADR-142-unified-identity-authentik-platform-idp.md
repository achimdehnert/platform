---
status: "draft"
date: 2026-03-13
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: ["ADR-118-platform-store-billing-hub-user-registration.md"]
related: ["ADR-118-platform-store-billing-hub-user-registration.md", "ADR-109-multi-tenancy-platform-standard.md", "ADR-114-discord-ide-like-communication-gateway.md", "ADR-045-secrets-management.md", "ADR-120-unified-deployment-pipeline.md"]
implementation_status: partial
implementation_evidence:
  - "Phase 1 Infrastructure deployed 2026-03-13: Docker Compose, DNS, Nginx"
  - "URL: https://id.iil.pet (HTTP 200)"
  - "Containers: iil_authentik_server, iil_authentik_worker, iil_authentik_db, iil_authentik_redis — all healthy"
  - "Port: 9000, DNS: CNAME id.iil.pet → Cloudflare Tunnel"
  - "Backup: /etc/cron.daily/authentik-backup"
---

# ADR-142: Unified Identity — authentik als Platform Identity Provider

---

## 1. Kontext & Problemstellung

### 1.1 Status Quo: N separate Auth-Systeme

Die IIL-Platform besteht aus 18+ Django-Hub-Repos, internen Tools und Infrastruktur-Services. Jedes System hat eine eigene Authentifizierung:

| Kategorie | Systeme | Auth heute |
|-----------|---------|-----------|
| **Kunden-Hubs** | risk-hub, ausschreibungs-hub, pptx-hub, weltenhub, coach-hub, travel-beat, trading-hub, wedding-hub, cad-hub, 137-hub | Jeder Hub: eigene Django-Auth-DB |
| **Interne Tools** | dev-hub, Grafana, Portainer, mcp-hub Dashboard | Separate Logins, teils Basic Auth |
| **Neue Services** | Outline (geplant), learn-hub | Noch kein Auth definiert |
| **Billing** | billing-hub | Eigene Auth-DB, kein User-Login (nur Admin) |

**Probleme:**

1. **Interne Tool-Fragmentierung**: 5+ separate Logins für Admin/Ops. Grafana hat eigene User, Portainer hat eigene User, dev-hub hat eigene User.
2. **Kein Cross-Hub-Login**: Ein Kunde, der risk-hub UND ausschreibungs-hub nutzt, braucht 2 Accounts mit 2 Passwörtern.
3. **ADR-118 hat SSO abgelehnt** — Begründung: "Hohe Komplexität, eigene Infrastruktur, Multi-Tenant-Isolation erschwert, gemeinsame Identität bringt keinen Mehrwert."
4. **Die Situation hat sich geändert**: billing-hub existiert als zentraler Store (ADR-118), Outline braucht Auth, und authentik (Python/Django) ist deutlich einfacher als Keycloak (Java).

### 1.2 Warum ADR-118 revidiert werden muss

| ADR-118 Argument (2026-03-10) | Heutige Realität |
|-------------------------------|------------------|
| "Hohe Komplexität, eigene Infrastruktur" | authentik: Docker Compose, ~1.5 GB RAM, Python/Django — identischer Stack |
| "Multi-Tenant-Isolation erschwert" | authentik: Tenants/Brands mit separaten Flows pro App, SCIM-Provisionierung |
| "Jede App hat andere Zielgruppe — gemeinsame Identität kein Mehrwert" | billing-hub IST bereits die gemeinsame Identität (E-Mail-basiert). Cross-Sell über Hubs ist strategisches Ziel. |
| "GDPR: getrennte User-Stores einfacher" | authentik unterstützt Data-Locality + Consent-Management. GDPR-Konformität ist einfacher mit einem zentralen IdP als mit N separaten. |

### 1.3 Warum authentik?

| Kriterium | Keycloak | Auth0/Clerk | authentik |
|-----------|----------|-------------|-----------|
| **Lizenz** | Apache 2.0 | SaaS ($$) | MIT |
| **Stack** | Java (Quarkus) | Cloud-hosted | **Python/Django + PostgreSQL** |
| **Self-hosted** | ✅ | ❌ | ✅ |
| **RAM** | ~2-4 GB | — | ~1.5 GB |
| **Protokolle** | OIDC, SAML, LDAP | OIDC | **OIDC, SAML, LDAP, RADIUS, Proxy** |
| **Multi-Tenant** | Realms | Orgs | **Tenants/Brands** |
| **Flow-Editor** | Theme-basiert | Dashboard | **Visueller Flow-Editor** |
| **SCIM** | Plugin | ✅ | ✅ |
| **Proxy-Auth** | Nein | Nein | **✅ (Outpost)** |
| **Fit für IIL-Stack** | ❌ Java-Fremdkörper | ❌ SaaS-Lock-in | **✅ Perfekter Fit** |

---

## 2. Entscheidungskriterien

- **Interne Effizienz**: Ein Login für alle internen Tools (Outline, Grafana, dev-hub, Portainer)
- **Kunden-Experience**: Ein Account für alle IIL-Produkte (Cross-Hub-Login)
- **Stack-Kompatibilität**: Python/Django, PostgreSQL, Docker — kein Fremdkörper
- **Kosten**: Self-hosted, Open Source, keine SaaS-Gebühren
- **Sicherheit**: MFA, Conditional Access, Audit-Log
- **Koexistenz**: billing-hub Flow (ADR-118) bleibt erhalten — authentik ergänzt, ersetzt nicht
- **Schrittweise Migration**: Kein Big-Bang — Hub für Hub migrierbar

---

## 3. Entscheidung

**authentik als zentraler Identity Provider** für die gesamte IIL-Platform — in zwei Phasen:

- **Phase 1**: Interne Tools (Outline, Grafana, dev-hub, Portainer, mcp-hub Dashboard)
- **Phase 2**: Kunden-Hubs (Cross-Hub-Login via OIDC, billing-hub-Integration)

### Amendment zu ADR-118

ADR-118 Section "Option A — SSO" wird hiermit **revidiert**. Die Entscheidung "SSO abgelehnt" wird durch ADR-142 ersetzt. Die billing-hub Store-Funktion (Registrierung, Stripe, Trial) bleibt bestehen — authentik übernimmt die **Authentifizierung**, billing-hub behält die **Autorisierung** (Subscription-Status, Plan-Gates).

---

## 4. Architektur

### 4.1 Komponenten-Übersicht

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IIL PLATFORM IDENTITY LAYER                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────┐     OIDC/OAuth2     ┌────────────────────┐ │
│  │  authentik           │ ◀───────────────── │  Django-Hubs       │ │
│  │  (id.iil.pet)        │                    │  (mozilla-django-  │ │
│  │                      │ ────────────────▶  │   oidc)            │ │
│  │  • OIDC Provider     │    ID-Token +      │                    │ │
│  │  • Flow-Editor       │    User-Info       │  risk-hub          │ │
│  │  • MFA (TOTP/WebA.)  │                    │  ausschreibungs-hub│ │
│  │  • Consent-Mgmt      │                    │  pptx-hub          │ │
│  │  • Audit-Log         │                    │  coach-hub         │ │
│  └──────────┬──────────┘                    │  ...               │ │
│             │                                └────────────────────┘ │
│             │ Proxy-Auth (Outpost)                                   │
│             ▼                                                        │
│  ┌─────────────────────┐                    ┌────────────────────┐  │
│  │  Interne Tools       │                    │  billing-hub       │  │
│  │  (Proxy-Auth)        │                    │  (Store)           │  │
│  │                      │                    │                    │  │
│  │  • Outline           │                    │  Registrierung →   │  │
│  │  • Grafana           │                    │  authentik User    │  │
│  │  • Portainer         │                    │  erstellen +       │  │
│  │  • dev-hub           │                    │  OIDC-fähig machen │  │
│  └─────────────────────┘                    └────────────────────┘  │
│                                                                      │
│  ┌─────────────────────┐                                            │
│  │  PostgreSQL           │  authentik_db (eigene Instanz)            │
│  │  + Redis              │  Keine Vermischung mit Hub-DBs            │
│  └─────────────────────┘                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Phase 1: Interne Tools (Proxy-Auth)

authentik Proxy-Outpost schützt Tools, die kein eigenes OIDC haben:

| Tool | Domain | Auth-Methode | Konfiguration |
|------|--------|-------------|---------------|
| **Outline** | knowledge.iil.pet | OIDC (nativ) | Outline hat OIDC-Support eingebaut |
| **Grafana** | grafana.iil.pet | OIDC (nativ) | `GF_AUTH_GENERIC_OAUTH_*` Env-Vars |
| **Portainer** | portainer.iil.pet | Proxy-Auth (Outpost) | authentik Outpost als Reverse Proxy |
| **dev-hub** | dev.iil.pet | OIDC (Django) | `mozilla-django-oidc` |
| **mcp-hub Dashboard** | mcp.iil.pet | Proxy-Auth (Outpost) | authentik Outpost |

**Zugriffskontrolle:**
- Gruppe `platform-admin`: Zugriff auf alle Tools
- Gruppe `developer`: Zugriff auf Outline, Grafana (read-only), dev-hub
- Gruppe `ops`: Zugriff auf Portainer, Grafana, mcp-hub Dashboard
- MFA (TOTP) pflicht für `platform-admin` und `ops`

### 4.3 Phase 2: Kunden-Hubs (OIDC-Login)

```
Kunde besucht risk-hub (schutztat.de)
  → "Einloggen" Button
  → Redirect zu id.iil.pet/application/risk-hub/authorize/
  → authentik Login-Flow (E-Mail + Passwort, optional MFA)
  → OIDC Callback → risk-hub erstellt/aktualisiert Django-User
  → Session aktiv

Kunde besucht danach ausschreibungs-hub (bieterpilot.de)
  → "Einloggen" Button
  → Redirect zu id.iil.pet/application/ausschreibungs-hub/authorize/
  → authentik: Session bereits aktiv → kein erneutes Login (SSO!)
  → OIDC Callback → ausschreibungs-hub erstellt/aktualisiert Django-User
  → Session aktiv
```

**Integration mit billing-hub (ADR-118):**

```
Neukunde: billing.iil.pet/checkout?product=risk-hub&plan=professional
  → E-Mail eingeben
  → billing-hub prüft: existiert authentik-User?
     → Nein: billing-hub erstellt authentik-User via API
       POST id.iil.pet/api/v3/core/users/
       {email, name, groups: ["customer"]}
     → Ja: bestehender User wird verknüpft
  → Stripe Checkout / Trial
  → Aktivierungs-Webhook an risk-hub (wie bisher, ADR-118)
  → risk-hub erstellt Tenant + verknüpft OIDC-User mit Tenant
```

**Wichtig:** billing-hub bleibt der Registrierungs- und Zahlungspunkt. authentik übernimmt nur die Authentifizierung. Die Autorisierung (welcher Plan, welche Module) bleibt in der jeweiligen App.

### 4.4 Django-Hub OIDC-Integration

Jeder Hub bekommt ~30 Zeilen Konfiguration via `mozilla-django-oidc`:

```python
# settings.py (jeder Hub)
# --- authentik OIDC (ADR-142) ---
from config.secrets import read_secret  # ADR-045

AUTHENTICATION_BACKENDS = [
    "core.auth.IILOIDCAuthenticationBackend",   # ADR-142 Custom Backend
    "django.contrib.auth.backends.ModelBackend",  # Fallback für Admin/Shell
]

# Credentials via read_secret() — ADR-045
OIDC_RP_CLIENT_ID     = read_secret("OIDC_RP_CLIENT_ID", required=True)
OIDC_RP_CLIENT_SECRET = read_secret("OIDC_RP_CLIENT_SECRET", required=True)

# App-spezifische OIDC-Endpoints — jeder Hub hat eigenen Application-Slug in authentik
_OIDC_APP_SLUG = read_secret("OIDC_APP_SLUG", required=True)
# z.B. "risk-hub", "outline", "dev-hub", "ausschreibungs-hub"

OIDC_OP_AUTHORIZATION_ENDPOINT = f"https://id.iil.pet/application/o/{_OIDC_APP_SLUG}/authorize/"
OIDC_OP_TOKEN_ENDPOINT         = f"https://id.iil.pet/application/o/{_OIDC_APP_SLUG}/token/"
OIDC_OP_USER_ENDPOINT          = f"https://id.iil.pet/application/o/{_OIDC_APP_SLUG}/userinfo/"
OIDC_OP_JWKS_ENDPOINT          = f"https://id.iil.pet/application/o/{_OIDC_APP_SLUG}/jwks/"
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES    = "openid email profile"

LOGIN_REDIRECT_URL  = read_secret("LOGIN_REDIRECT_URL", default="/dashboard/")
LOGOUT_REDIRECT_URL = "/"
```

```python
# core/auth.py (jeder Hub — Template für alle Hubs)
import logging

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)


class IILOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """Plattform-weites OIDC-Backend mit authentik (ADR-142 + ADR-109).

    - Soft-Delete-aware User-Lookup (is_active=True)
    - Tenant-Zuordnung über OIDC-Claims (Hub-spezifisch überschreibbar)
    - Konformes super() Chaining
    """

    def filter_users_by_claims(self, claims):
        """Sucht aktive (nicht deaktivierte) User per E-Mail."""
        email = claims.get("email")
        if not email:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(
            email__iexact=email,
            is_active=True,
        )

    def create_user(self, claims):
        """Erstellt neuen User bei erstem OIDC-Login (JIT-Provisioning)."""
        email = claims.get("email", "")
        if not email:
            logger.warning("OIDC create_user: no email in claims")
            return None

        user = super().create_user(claims)
        user.first_name = claims.get("given_name", "")[:150]
        user.last_name = claims.get("family_name", "")[:150]
        user.is_active = True
        user.save(update_fields=["first_name", "last_name", "is_active"])

        logger.info(
            "OIDC user created",
            extra={"email": email, "sub": claims.get("sub", "")},
        )
        return user

    def update_user(self, user, claims):
        """Aktualisiert bestehenden User bei jedem Login."""
        user = super().update_user(user, claims)
        updated = False
        new_first = claims.get("given_name", "")[:150]
        new_last = claims.get("family_name", "")[:150]

        if new_first and user.first_name != new_first:
            user.first_name = new_first
            updated = True
        if new_last and user.last_name != new_last:
            user.last_name = new_last
            updated = True

        if updated:
            user.save(update_fields=["first_name", "last_name"])
        return user

    def get_or_create_user(self, access_token, id_token, payload):
        """Hook: Tenant-Zuordnung nach User-Erstellung (ADR-109)."""
        user = super().get_or_create_user(access_token, id_token, payload)
        if user:
            self._assign_tenant(user, payload)
        return user

    @staticmethod
    def _assign_tenant(user, claims):
        """Ordnet User dem korrekten Tenant zu.

        Default: No-op. Jeder Hub überschreibt diese Methode wenn nötig.
        Claims können `tenant_id` Claim von authentik enthalten.
        """
        pass
```

### 4.5 Docker Deployment

```yaml
# docker-compose.authentik.yml — auf hetzner-prod (88.198.191.108)
name: authentik-stack

networks:
  authentik_net:
    name: iil_authentik_net
    driver: bridge

services:
  authentik_server:
    image: ghcr.io/goauthentik/server:2025.10.4
    container_name: iil_authentik_server
    command: server
    networks: [authentik_net]
    ports:
      - "127.0.0.1:9000:9000"
      - "127.0.0.1:9443:9443"
    environment:
      AUTHENTIK_SECRET_KEY: "${AUTHENTIK_SECRET_KEY}"
      AUTHENTIK_REDIS__HOST: iil_authentik_redis
      AUTHENTIK_REDIS__PASSWORD: "${AUTHENTIK_REDIS_PASSWORD}"
      AUTHENTIK_POSTGRESQL__HOST: iil_authentik_db
      AUTHENTIK_POSTGRESQL__USER: "${AUTHENTIK_DB_USER}"
      AUTHENTIK_POSTGRESQL__PASSWORD: "${AUTHENTIK_DB_PASS}"
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_ERROR_REPORTING__ENABLED: "false"
    env_file: [.env.authentik]
    volumes:
      - authentik_media:/media
      - authentik_templates:/templates
    depends_on:
      authentik_db:
        condition: service_healthy
      authentik_redis:
        condition: service_healthy
    mem_limit: 1g
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:9000/-/health/live/')\""]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

  authentik_worker:
    image: ghcr.io/goauthentik/server:2025.10.4
    container_name: iil_authentik_worker
    command: worker
    networks: [authentik_net]
    environment:
      AUTHENTIK_SECRET_KEY: "${AUTHENTIK_SECRET_KEY}"
      AUTHENTIK_REDIS__HOST: iil_authentik_redis
      AUTHENTIK_REDIS__PASSWORD: "${AUTHENTIK_REDIS_PASSWORD}"
      AUTHENTIK_POSTGRESQL__HOST: iil_authentik_db
      AUTHENTIK_POSTGRESQL__USER: "${AUTHENTIK_DB_USER}"
      AUTHENTIK_POSTGRESQL__PASSWORD: "${AUTHENTIK_DB_PASS}"
      AUTHENTIK_POSTGRESQL__NAME: authentik
    env_file: [.env.authentik]
    volumes:
      - authentik_media:/media
      - authentik_templates:/templates
    depends_on:
      authentik_db:
        condition: service_healthy
      authentik_redis:
        condition: service_healthy
    mem_limit: 512m
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:9000/-/health/live/')\""]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  authentik_db:
    image: postgres:16
    container_name: iil_authentik_db
    networks: [authentik_net]
    environment:
      POSTGRES_USER: "${AUTHENTIK_DB_USER}"
      POSTGRES_PASSWORD: "${AUTHENTIK_DB_PASS}"
      POSTGRES_DB: authentik
    volumes:
      - authentik_db_data:/var/lib/postgresql/data
    mem_limit: 512m
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${AUTHENTIK_DB_USER} -d authentik"]
      interval: 30s
      timeout: 5s
      retries: 3

  authentik_redis:
    image: redis:7-alpine
    container_name: iil_authentik_redis
    networks: [authentik_net]
    command: redis-server --requirepass "${AUTHENTIK_REDIS_PASSWORD}"
    mem_limit: 128m
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${AUTHENTIK_REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  authentik_media:
  authentik_templates:
  authentik_db_data:
```

**Nginx-Konfiguration** (in bestehende Nginx-Config integrieren):

```nginx
# /etc/nginx/conf.d/authentik.conf
limit_req_zone $binary_remote_addr zone=authentik_auth:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=authentik_api:10m rate=60r/m;

server {
    listen 80;
    server_name id.iil.pet;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name id.iil.pet;

    ssl_certificate     /etc/letsencrypt/live/id.iil.pet/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/id.iil.pet/privkey.pem;

    # Rate-Limiting auf Login-Flows
    location ~* ^/application/o/(authorize|token|introspect)/ {
        limit_req zone=authentik_auth burst=20 nodelay;
        limit_req_status 429;
        proxy_pass          http://127.0.0.1:9000;
        proxy_http_version  1.1;
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;
    }

    # Rate-Limiting auf API
    location /api/ {
        limit_req zone=authentik_api burst=100 nodelay;
        limit_req_status 429;
        proxy_pass          http://127.0.0.1:9000;
        proxy_http_version  1.1;
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;
    }

    # WebSocket-Upgrade fuer authentik Admin Live-Events
    location /ws/ {
        proxy_pass          http://127.0.0.1:9000;
        proxy_http_version  1.1;
        proxy_set_header    Upgrade    $http_upgrade;
        proxy_set_header    Connection "upgrade";
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass          http://127.0.0.1:9000;
        proxy_http_version  1.1;
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;
    }
}
```

### 4.6 Ressourcen-Bedarf

hetzner-prod aktuell: ~89 Container, ~10/22 GB RAM, 35 GB Disk frei.

| Container | RAM | CPU | Disk |
|-----------|-----|-----|------|
| authentik_server | 1 GB | 1 | ~500 MB (Image + Media) |
| authentik_worker | 512 MB | 0.5 | — |
| authentik_db | 512 MB | 0.5 | ~200 MB (initial) |
| authentik_redis | 128 MB | 0.25 | ~50 MB |
| **Gesamt** | **~2.15 GB** | **~2.25** | **~750 MB** |

**Machbar**: 10 + 2.15 = ~12.15 GB von 22 GB. Genug Headroom.

### 4.7 Sicherheit

| Aspekt | Maßnahme |
|--------|----------|
| **MFA** | TOTP pflicht für interne Gruppen (platform-admin, ops). Optional für Kunden. |
| **Brute-Force** | authentik hat eingebautes Rate-Limiting + IP-Reputation + Nginx Rate-Limiting (siehe 4.5) |
| **Secrets** | `AUTHENTIK_SECRET_KEY`, `AUTHENTIK_DB_PASS`, `AUTHENTIK_REDIS_PASSWORD` via `read_secret()` (ADR-045) |
| **OIDC Client Secrets** | Pro Hub ein Client-ID/Secret-Paar via `read_secret()` in `.env.prod` |
| **Redis-Auth** | `requirepass` auf authentik_redis — kein unauth. Zugriff aus Docker-Netzwerk |
| **Session-Dauer** | Interne Tools: 8h. Kunden-Hubs: 30 Tage (Remember Me). |
| **Consent** | Kunden-Hubs: Consent-Screen bei erstem Login. Interne: Implicit Consent. |
| **Audit** | authentik loggt alle Logins, Token-Grants, Fehler. Export nach Grafana möglich. |
| **Backup** | Täglicher `pg_dump` Cron auf `authentik_db` → `/opt/backups/authentik/`. Rotation: 7 Tage. |
| **Netzwerk-Isolation** | Eigenes Docker-Netzwerk `iil_authentik_net` — keine Erreichbarkeit aus fremden Stacks. |

### 4.8 billing-hub → authentik Integration (Fail-Safe)

Bei Registrierung über billing-hub wird ein authentik-User via API erstellt. **Fail-Safe-Strategie:**

- **authentik erreichbar**: User wird synchron erstellt, Registrierung normal.
- **authentik nicht erreichbar**: Registrierung wird **nicht blockiert**. Der Kunde bekommt eine E-Mail zur späteren Passwort-Aktivierung. Ein Celery-Retry-Task synchronisiert den User nachträglich.
- **Timeout**: 5 Sekunden. Bei Timeout: Registrierung fortsetzen, User-Sync asynchron nachholen.
- **Logging**: Alle Fehlerfälle werden geloggt (`logging.getLogger(__name__)`, kein `print()`).

---

## 5. Implementierungsplan

### Phase 1: Interne Tools (Woche 1-2)

| Step | Inhalt | Aufwand |
|------|--------|---------|
| 1.1 | authentik Docker Compose deployen auf hetzner-prod | 2h |
| 1.2 | DNS: `id.iil.pet` → Cloudflare A-Record + Nginx-Config + SSL | 1h |
| 1.3 | Admin-User anlegen, Gruppen erstellen (platform-admin, developer, ops) | 0.5h |
| 1.4 | Outline als OIDC-Application konfigurieren | 1h |
| 1.5 | Grafana OIDC-Integration | 1h |
| 1.6 | dev-hub: `mozilla-django-oidc` integrieren | 2h |
| 1.7 | Proxy-Outpost für Portainer + mcp-hub Dashboard | 2h |
| 1.8 | MFA-Policy für platform-admin + ops aktivieren | 0.5h |
| 1.9 | Smoke-Tests + Dokumentation | 1h |

**Phase 1 Gesamt: ~11h**

### Phase 2: Kunden-Hubs (Woche 3-6)

| Step | Inhalt | Aufwand |
|------|--------|---------|
| 2.1 | `core/auth.py` Template erstellen (OIDC-Backend mit Tenant-Zuordnung) | 2h |
| 2.2 | billing-hub: authentik User-Erstellung bei Registrierung (API-Integration) | 3h |
| 2.3 | **Pilot: risk-hub** — OIDC-Login + Tenant-Mapping | 3h |
| 2.4 | **Pilot: ausschreibungs-hub** — OIDC-Login | 2h |
| 2.5 | Consent-Flow + Branding anpassen (pro Hub eigenes Logo/Farben) | 2h |
| 2.6 | Rollout auf weitere Hubs (Template-basiert, ~1h pro Hub) | 8h |
| 2.7 | Legacy-Auth dekommissionieren (nach Migrations-Zeitraum) | 3h |
| 2.8 | Tests + E2E-Validierung | 3h |

**Phase 2 Gesamt: ~26h**

### Phase 3: Erweitert (Optional, nach Bedarf)

| Step | Inhalt | Aufwand |
|------|--------|---------|
| 3.1 | SCIM-Provisionierung: authentik → Hub-DBs (automatische User-Sync) | 4h |
| 3.2 | Social Login (Google, Microsoft) in authentik Flows | 2h |
| 3.3 | Passwordless (WebAuthn/Passkeys) | 2h |
| 3.4 | API-Token-Management via authentik (Service-Accounts) | 3h |

---

## 6. Offene Fragen

| Frage | Empfehlung | Status |
|-------|-----------|--------|
| Domain für authentik? | `id.iil.pet` — kurz, klar, unter Platform-Domain | Entschieden |
| MFA für Kunden pflicht? | Nein, optional. Pflicht nur für interne Gruppen. | Entschieden |
| Legacy-Login-Phase? | 3 Monate Dual-Login (OIDC + lokales Django-Auth), dann Sunset | Entschieden |
| Wie integriert authentik mit discord-bot? | authentik API-Token für Bot-User (Service-Account), keine OIDC-Session nötig (ADR-114) | Entschieden |
| SCIM oder manuelles User-Mapping? | Phase 1: manuell (OIDC Just-in-Time). Phase 3: SCIM | Entschieden |
| Branding pro Hub? | authentik Tenants/Brands — pro Hub eigenes Logo + Farben im Login-Flow | Entschieden |

---

## 7. Abgrenzung

- **Kein Ersatz für billing-hub** — authentik = Authentifizierung, billing-hub = Registrierung + Zahlung + Autorisierung
- **Kein Ersatz für django-tenancy** — Tenant-Isolation bleibt in der App (ADR-109). authentik liefert nur die User-Identität.
- **Kein erzwungenes SSO für alle Hubs** — Migration ist Hub-für-Hub, Opt-in. Legacy-Auth bleibt als Fallback.
- **Kein eigener User-Store in authentik für Businesslogik** — Apps haben weiterhin eigene Django-User-Tabelle. OIDC-Backend erstellt/aktualisiert diese automatisch.
- **Kein Social Login in Phase 1** — erst in Phase 3 (Google, Microsoft).

---

## 8. Konsequenzen

### Positiv

- **Ein Login für alle internen Tools** — sofort ab Phase 1
- **Ein Login für alle Kunden-Hubs** — ab Phase 2
- **MFA zentral konfigurierbar** — nicht pro App implementieren
- **Audit-Trail zentral** — alle Logins an einem Ort
- **Stack-Fit**: Python/Django/PostgreSQL — keine Java-Fremdkörper
- **Cross-Sell ermöglicht**: Kunde nutzt risk-hub → sieht auch ausschreibungs-hub (gleicher Login)
- **Outline/Knowledge-Hub kann sofort OIDC nutzen** (Phase 1, Step 1.4)

### Negativ / Risiken

- **Zusätzliche Infrastruktur**: ~2 GB RAM, 4 neue Container auf hetzner-prod
- **Single Point of Failure für Logins**: authentik-Ausfall → kein Login möglich. Mitigation: Health-Monitoring, `ModelBackend` als Django-Fallback für Admin-Zugang.
- **Migration pro Hub**: Jeder Hub braucht ~1-3h Anpassung. Bei 18 Hubs: signifikanter Rollout-Aufwand.
- **User-Daten-Split**: User-Identität in authentik, User-Daten in Hub-DB. Muss konsistent gehalten werden (OIDC JIT-Provisioning).
- **ADR-118 Flow wird komplexer**: billing-hub muss zusätzlich authentik-User erstellen bei Registrierung.

---

## 9. Review-Referenz

Dieses ADR revidiert die SSO-Entscheidung aus ADR-118 Section "Option A".
Vollständige Analyse: `docs/adr/inputs/dms/konzept-outline-research-hub.md` (Outline-Kontext).
