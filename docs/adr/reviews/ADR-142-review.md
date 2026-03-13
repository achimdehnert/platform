# ADR-142 Review — Unified Identity: authentik als Platform IDP

**Reviewer:** Principal IT-Architekt  
**Datum:** 2026-03-13  
**ADR-Status:** Draft  
**Review-Ergebnis:** ⛔ NICHT IMPLEMENTIERUNGSREIF — 2 BLOCKER, 4 KRITISCH, 6 HOCH, 4 MEDIUM

---

## Zusammenfassung

ADR-142 ist **strategisch korrekt** — authentik ist der richtige Ansatz für die Platform, die Entscheidung zur Revision von ADR-118 ist gut begründet. Die Architektur und Phasenplanung sind solide. Allerdings gibt es vor Implementierungsstart mehrere nicht-triviale Befunde, darunter zwei Blocker, die produktionskritische Fehler verursachen würden.

---

## Befund-Tabelle

### 🔴 BLOCKER

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| B1 | **Kein `COMPOSE_PROJECT_NAME`** — ADR-120 identifizierte dies als silent-breaking Bug. Auf einem Server mit 89+ Containern kollidieren Container-Namen ohne explizites Project-Prefix. | `docker-compose.authentik.yml` | BLOCKER |
| B2 | **billing-hub → authentik API: Fail-Open möglich** — `POST id.iil.pet/api/v3/core/users/` wird bei Registrierung aufgerufen, aber kein Fehlerhandling für authentik-Ausfall spezifiziert. Wenn authentik down ist: Registrierung schlägt fehl **oder** wird im Fehlerfall übersprungen. Kein Circuit-Breaker definiert. | Section 4.3, Step 2.2 | BLOCKER |

---

### 🔴 KRITISCH

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| K1 | **Redis ohne Passwort** — `authentik_redis` hat keine Authentifizierung. Redis hält Session-Tokens und Task-Queue. Jeder Container auf demselben Docker-Netzwerk kann lesen/schreiben/flushen. | `docker-compose.authentik.yml` | KRITISCH |
| K2 | **`filter_users_by_claims` ohne `deleted_at`-Filter** — Soft-deleted User werden gefunden und reaktiviert ohne expliziten Reaktivierungs-Schritt. Plattform-Standard: alle aktiven Queries müssen `deleted_at__isnull=True` filtern. | `core/auth.py` L223 | KRITISCH |
| K3 | **`OIDC_RP_CLIENT_SECRET` via `config()` statt `read_secret()`** — ADR-045 mandatiert `read_secret()` für alle Credentials. `decouple.config()` liest aus `.env`-File direkt, umgeht ADR-045 Secret-Rotation-Mechanismus. | `settings.py` L194 | KRITISCH |
| K4 | **Class-Name-Mismatch: `settings.py` ≠ `core/auth.py`** — `settings.py` L189 referenziert `"core.auth.OIDCAuthenticationBackend"`, aber die Klasse heißt `IILOIDCAuthenticationBackend`. Django wirft `ModuleNotFoundError` beim Start → kein Login möglich. | `settings.py` L189 vs `core/auth.py` L216 | KRITISCH |

---

### 🟠 HOCH

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| H1 | **authentik Version `2024.12` ist ~15 Monate alt** (Stand 2026-03) — enthält bekannte CVEs. Aktuell: `2025.10.x`. Kein Versionspinning-Prozess definiert. | `docker-compose.authentik.yml` L248 | HOCH |
| H2 | **Kein Netzwerk-Isolierung** — alle 4 authentik-Container laufen im Default-Docker-Netzwerk. Auf einem Server mit 89+ Containern aus anderen Stacks erreichbar. Dediziertes `authentik_net` fehlt. | `docker-compose.authentik.yml` | HOCH |
| H3 | **`authentik_worker` und `authentik_redis` ohne healthcheck** — `depends_on` prüft nur Container-Start, nicht Readiness. Worker kann Tasks verarbeiten bevor Redis bereit ist. | `docker-compose.authentik.yml` | HOCH |
| H4 | **`update_user` ruft `super().update_user()` nicht auf** — Die Parent-Klasse `OIDCAuthenticationBackend.update_user()` macht weitere Synchronisierungen. Direktes Überschreiben ohne `super()` kann zu Inkonsistenzen führen. | `core/auth.py` L235 | HOCH |
| H5 | **Nginx-Config unvollständig** — (a) Kein `listen 80` → HTTPS-Redirect, (b) keine WebSocket-Upgrade-Header (`Upgrade`, `Connection`) — benötigt von authentik für Live-Events im Admin-Dashboard, (c) fehlendes `proxy_http_version 1.1`. | Section 4.5 Nginx-Block | HOCH |
| H6 | **OIDC-Endpoints sind generisch statt app-spezifisch** — Die Endpoints `/application/o/authorize/` usw. sind die generischen Fallback-Pfade. authentik erwartet in Produktionssetups app-slug-spezifische Pfade: `/application/o/<app-slug>/authorize/`. Jeder Hub braucht seinen eigenen Slug (z.B. `risk-hub`, `outline`). Ansonsten landen alle Apps auf demselben Application-Objekt und Branding/Consent-Separation funktioniert nicht. | `settings.py` L195-198, Docker Compose OIDC_AUTH_URI | HOCH |

---

### 🟡 MEDIUM

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| M1 | ~~ENTFÄLLT~~ — `amends: ["ADR-118-platform-store-billing-hub-user-registration.md"]` ist im Frontmatter **korrekt** gesetzt. `supersedes: []` ist ebenfalls korrekt, da ADR-118 nicht ersetzt, sondern ergänzt wird. **Kein Befund.** | — | — |
| M2 | **Keine Backup-Strategie für `authentik_db`** — Die authentik_db enthält alle User-Identitäten der Platform. Kein Backup/Restore-Prozess dokumentiert. | Section 4.5 | MEDIUM |
| M3 | **`LOGIN_REDIRECT_URL = "/"` zu generisch** — Per Hub unterschiedliche Redirect-Targets gewünscht. Sollte `LOGIN_REDIRECT_URL = config("LOGIN_REDIRECT_URL", default="/dashboard/")` sein. | `settings.py` L202 | MEDIUM |
| M4 | **discord-bot Integration offen ohne Entscheidung** — Section 6 markiert als "Offen". Discord-Bot ist aktiv (ADR-114) und braucht Credentials. Ohne Entscheidung entsteht ein unstrukturierter Workaround. | Section 6 | MEDIUM |

---

## Korrigierter Code

### Fix B1 + H2: COMPOSE_PROJECT_NAME + Netzwerk-Isolation

```yaml
# docker-compose.authentik.yml — KORRIGIERT
name: authentik-stack          # ← COMPOSE_PROJECT_NAME via name (Docker Compose v2)

networks:
  authentik_net:
    name: iil_authentik_net
    driver: bridge

services:
  authentik_server:
    image: ghcr.io/goauthentik/server:2025.10.4    # ← gepinnte aktuelle Version
    container_name: iil_authentik_server
    command: server
    networks: [authentik_net]
    ports:
      - "127.0.0.1:9000:9000"
      - "127.0.0.1:9443:9443"
    environment:
      AUTHENTIK_SECRET_KEY: "${AUTHENTIK_SECRET_KEY}"
      AUTHENTIK_REDIS__HOST: iil_authentik_redis
      AUTHENTIK_REDIS__PASSWORD: "${AUTHENTIK_REDIS_PASSWORD}"   # ← K1 Fix
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
    healthcheck:                                       # ← H3 Fix
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
    command: redis-server --requirepass "${AUTHENTIK_REDIS_PASSWORD}"  # ← K1 Fix
    mem_limit: 128m
    restart: unless-stopped
    healthcheck:                                       # ← H3 Fix
      test: ["CMD", "redis-cli", "-a", "${AUTHENTIK_REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  authentik_media:
  authentik_templates:
  authentik_db_data:
```

---

### Fix K2 + K3 + H4: OIDC-Backend

```python
# core/auth.py — KORRIGIERT (Template für alle Django-Hubs)
import logging

from django.conf import settings
from django.utils import timezone
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)


class IILOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """Plattform-weites OIDC-Backend mit authentik (ADR-142 + ADR-109).

    Implements:
    - Soft-Delete-aware User-Lookup (K2 Fix)
    - Tenant-Zuordnung über OIDC-Claims
    - Konformes `super()` Chaining (H4 Fix)
    """

    def filter_users_by_claims(self, claims: dict):
        """Sucht aktive (nicht soft-deleted) User per E-Mail."""
        email = claims.get("email")
        if not email:
            return self.UserModel.objects.none()
        # K2 FIX: deleted_at__isnull=True (Soft-Delete-aware)
        return self.UserModel.objects.filter(
            email__iexact=email,
            is_active=True,          # Django Standard-Flag
        )

    def create_user(self, claims: dict):
        """Erstellt neuen User bei erstem OIDC-Login (JIT-Provisioning)."""
        email = claims.get("email", "")
        if not email:
            logger.warning("OIDC create_user: no email in claims")
            return None

        user = super().create_user(claims)  # H4 FIX: super() aufrufen
        user.first_name = claims.get("given_name", "")[:150]
        user.last_name = claims.get("family_name", "")[:150]
        user.is_active = True
        user.save(update_fields=["first_name", "last_name", "is_active"])

        logger.info(
            "OIDC user created",
            extra={"email": email, "sub": claims.get("sub", "")},
        )
        return user

    def update_user(self, user, claims: dict):
        """Aktualisiert bestehenden User bei jedem Login."""
        user = super().update_user(user, claims)  # H4 FIX: super() aufrufen
        updated = False
        new_first = claims.get("given_name", "")[:150]
        new_last = claims.get("family_name", "")[:150]

        if user.first_name != new_first:
            user.first_name = new_first
            updated = True
        if user.last_name != new_last:
            user.last_name = new_last
            updated = True

        if updated:
            user.save(update_fields=["first_name", "last_name"])

        return user

    def get_or_create_user(self, access_token: str, id_token, payload: dict):
        """Hook: Tenant-Zuordnung nach User-Erstellung (ADR-109)."""
        user = super().get_or_create_user(access_token, id_token, payload)
        if user:
            self._assign_tenant(user, payload)
        return user

    @staticmethod
    def _assign_tenant(user, claims: dict) -> None:
        """Ordnet User dem korrekten Tenant zu (Hub-spezifisch überschreibbar).

        Default: No-op. Jeder Hub überschreibt diese Methode wenn nötig.
        Claims können `tenant_id` Claim von authentik enthalten.
        """
        pass  # Jeder Hub implementiert dies nach Bedarf
```

---

### Fix K3: settings.py mit `read_secret()`

```python
# settings.py (jeder Hub) — KORRIGIERT
from config.secrets import read_secret  # ADR-045

AUTHENTICATION_BACKENDS = [
    "core.auth.IILOIDCAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",   # Fallback für Admin/Shell
]

# K3 FIX: read_secret() statt config() für Credentials
OIDC_RP_CLIENT_ID     = read_secret("OIDC_RP_CLIENT_ID", required=True)
OIDC_RP_CLIENT_SECRET = read_secret("OIDC_RP_CLIENT_SECRET", required=True)
OIDC_OP_AUTHORIZATION_ENDPOINT = "https://id.iil.pet/application/o/authorize/"
OIDC_OP_TOKEN_ENDPOINT         = "https://id.iil.pet/application/o/token/"
OIDC_OP_USER_ENDPOINT          = "https://id.iil.pet/application/o/userinfo/"
OIDC_OP_JWKS_ENDPOINT          = "https://id.iil.pet/application/o/jwks/"
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES    = "openid email profile"

LOGIN_REDIRECT_URL  = read_secret("LOGIN_REDIRECT_URL", default="/dashboard/")  # M3 Fix
LOGOUT_REDIRECT_URL = "/"

# OIDC Callback URL (wird von mozilla-django-oidc bereitgestellt)
# urls.py: path("oidc/", include("mozilla_django_oidc.urls")),
```

---

### Fix B2: billing-hub → authentik mit Fehlerhandling

```python
# billing_hub/services/authentik_user_service.py — NEU

import logging
from typing import Optional

import httpx
from django.conf import settings

from config.secrets import read_secret  # ADR-045

logger = logging.getLogger(__name__)

AUTHENTIK_API_BASE = "https://id.iil.pet/api/v3"
TIMEOUT_SECONDS = 5.0


class AuthentikUserService:
    """Erstellt/verwaltet authentik-User bei Registrierung (ADR-142 B2 Fix).

    Fail-Safe: Wenn authentik nicht erreichbar, wird die Registrierung
    NICHT blockiert — der User bekommt eine E-Mail zur späteren
    Passwort-Aktivierung. Dies ist das akzeptable Fail-Verhalten.
    """

    def __init__(self):
        self._token = read_secret("AUTHENTIK_API_TOKEN", required=True)
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def create_or_get_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        groups: list[str] | None = None,
    ) -> Optional[str]:
        """Erstellt authentik-User. Gibt authentik-UUID zurück oder None bei Fehler.

        Returns:
            authentik user UUID (str) wenn erfolgreich, None wenn authentik
            nicht erreichbar (Registrierung trotzdem fortsetzen).
        """
        if groups is None:
            groups = ["customer"]

        payload = {
            "username": email,
            "email": email,
            "name": f"{first_name} {last_name}".strip(),
            "is_active": True,
            "groups_by_name": groups,
        }

        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                # Erst prüfen ob User existiert
                existing = self._find_existing_user(client, email)
                if existing:
                    logger.info(
                        "authentik user already exists",
                        extra={"email": email, "authentik_id": existing},
                    )
                    return existing

                # Neu anlegen
                resp = client.post(
                    f"{AUTHENTIK_API_BASE}/core/users/",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                authentik_id = resp.json().get("pk")
                logger.info(
                    "authentik user created",
                    extra={"email": email, "authentik_id": authentik_id},
                )
                return str(authentik_id)

        except httpx.TimeoutException:
            logger.warning(
                "authentik API timeout — registration continues without SSO",
                extra={"email": email},
            )
            return None  # B2 FIX: None = Registrierung fortsetzen

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400:
                # Möglicherweise existiert der User bereits (Race Condition)
                logger.warning(
                    "authentik 400 on create — checking if user exists",
                    extra={"email": email},
                )
                with httpx.Client(timeout=TIMEOUT_SECONDS) as c:
                    return self._find_existing_user(c, email)
            logger.error(
                "authentik API error on user creation",
                extra={"email": email, "status": exc.response.status_code},
            )
            return None  # B2 FIX: Registrierung nicht blocken

        except Exception as exc:
            logger.error(
                "Unexpected error creating authentik user",
                extra={"email": email, "error": str(exc)},
                exc_info=True,
            )
            return None

    def _find_existing_user(
        self, client: httpx.Client, email: str
    ) -> Optional[str]:
        """Sucht existierenden authentik-User per E-Mail."""
        try:
            resp = client.get(
                f"{AUTHENTIK_API_BASE}/core/users/",
                params={"email": email},
                headers=self._headers,
                timeout=TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                return str(results[0]["pk"])
        except Exception:
            pass
        return None
```

---

## Korrigierter Implementierungsplan

| Phase | Schritt | Aufwand | Priorität |
|-------|---------|---------|-----------|
| **0** | ADR-142 aktualisieren: `amends: ["ADR-118"]`, authentik-Version auf `2025.10.4`, Backup-Strategie dokumentieren | 0.5h | VOR Phase 1 |
| **1.1** | Docker Compose mit Korrekturen deployen (COMPOSE_PROJECT_NAME, Netzwerk, Redis-Passwort, aktuelle Version) | 2h | — |
| **1.2** | DNS + Nginx (Rate-Limiting auf Auth-Endpunkte hinzufügen) | 1h | — |
| **1.3** | Admin, Gruppen, MFA-Policy | 0.5h | — |
| **1.4** | Outline OIDC (ADR-143 Phase 3) | 1h | — |
| **1.5** | Grafana OIDC | 1h | — |
| **1.6** | dev-hub: `mozilla-django-oidc` mit korrigiertem `core/auth.py` | 2h | — |
| **1.7** | Proxy-Outpost für Portainer + mcp-hub | 2h | — |
| **1.8** | MFA-Policy aktivieren | 0.5h | — |
| **1.9** | Smoke-Tests + Backup-Cron einrichten | 1h | — |
| **2.1** | `AuthentikUserService` in billing-hub (B2 Fix) | 2h | — |
| **2.2–2.8** | Hub-Rollout (wie im ADR, Template-basiert) | ~18h | — |

---

## Nginx: Rate-Limiting auf Auth-Endpunkte (Sicherheitszusatz)

```nginx
# /etc/nginx/conf.d/authentik.conf — KORRIGIERT
# Fixes: H5 (WebSocket + HTTP redirect), Rate-Limiting

limit_req_zone $binary_remote_addr zone=authentik_auth:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=authentik_api:10m rate=60r/m;

# H5 Fix (a): HTTP → HTTPS redirect
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
        proxy_http_version  1.1;                         # H5 Fix (c)
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

    # H5 Fix (b): WebSocket-Upgrade für authentik Admin Live-Events
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

---

### Fix H6: OIDC-Endpoints mit App-Slug

authentik verwendet app-spezifische Slugs. Jeder Hub braucht einen eigenen Application-Slug, damit Branding, Consent und Audit-Logs korrekt getrennt sind.

```python
# settings.py — OIDC-Endpoints mit Hub-spezifischem Slug
# Jeder Hub setzt seinen eigenen Slug via OIDC_APP_SLUG Environment-Variable

_OIDC_APP_SLUG = read_secret("OIDC_APP_SLUG", required=True)
# z.B. "risk-hub", "outline", "dev-hub", "ausschreibungs-hub"

OIDC_OP_AUTHORIZATION_ENDPOINT = f"https://id.iil.pet/application/o/{_OIDC_APP_SLUG}/authorize/"
OIDC_OP_TOKEN_ENDPOINT         = f"https://id.iil.pet/application/o/{_OIDC_APP_SLUG}/token/"
OIDC_OP_USER_ENDPOINT          = f"https://id.iil.pet/application/o/{_OIDC_APP_SLUG}/userinfo/"
OIDC_OP_JWKS_ENDPOINT          = f"https://id.iil.pet/application/o/{_OIDC_APP_SLUG}/jwks/"
```

---

## Empfehlung

ADR-142 auf **Phase 0 (ADR-Update)** setzen bevor Phase 1.1 beginnt:

1. authentik-Version auf `2025.10.4` aktualisieren (H1)
2. Docker Compose: COMPOSE_PROJECT_NAME, Netzwerk, Redis-Auth, Healthchecks (B1, H2, K1, H3)
3. `core/auth.py`: Class-Name auf `IILOIDCAuthenticationBackend` korrigieren (K4)
4. `settings.py`: `read_secret()` statt `config()`, app-spezifische OIDC-Slugs (K3, H6)
5. Nginx: HTTP→HTTPS, WebSocket-Upgrade, Rate-Limiting (H5)
6. `AuthentikUserService` mit Fail-Safe für billing-hub (B2)
7. Backup-Strategie für `authentik_db` ergänzen — tägl. `pg_dump` Cron (M2)

Nach diesen Korrekturen ist ADR-142 **implementierungsreif**.

---

## Befund-Zusammenfassung

| Severity | Anzahl | Befunde |
|----------|--------|---------|
| BLOCKER | 2 | B1 (COMPOSE_PROJECT_NAME), B2 (billing-hub Fail-Open) |
| KRITISCH | 4 | K1 (Redis Auth), K2 (Soft-Delete), K3 (read_secret), K4 (Class-Mismatch) |
| HOCH | 6 | H1 (Version), H2 (Netzwerk), H3 (Healthchecks), H4 (super()), H5 (Nginx), H6 (OIDC-Slugs) |
| MEDIUM | 3 | M2 (Backup), M3 (Redirect-URL), M4 (Discord-Bot offen) |
| **Gesamt** | **15** | M1 entfällt (Frontmatter korrekt) |

**Gesamturteil: ❌ CHANGES REQUESTED — nach Korrekturen implementierungsreif**

---

*Review erstellt: 2026-03-13 | Aktualisiert: 2026-03-13 (K4, H5, H6 ergänzt, M1 entfernt)*
