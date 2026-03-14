# OIDC Integration mit authentik — Pattern Guide

> **Gilt für**: Alle Hubs und Services, die OIDC/SSO über authentik (ADR-142) nutzen.
> **Lessons Learned** aus ADR-143 Outline-Integration (2026-03-14).

---

## Architektur

```
Browser                     Docker Host (hetzner-prod)
  │                         ┌─────────────────────────────────┐
  │  1. GET /               │  Nginx (443, self-signed cert)  │
  │ ──────────────────────► │  ├── id.iil.pet → :9000         │
  │  2. 302 → id.iil.pet   │  ├── knowledge.iil.pet → :3100  │
  │ ◄────────────────────── │  └── docs.iil.pet → :8102       │
  │  3. Login at authentik  │                                  │
  │ ──────────────────────► │  authentik (:9000)               │
  │  4. 302 → callback      │                                  │
  │ ◄────────────────────── │                                  │
  │  5. GET /auth/callback  │  App Container                   │
  │ ──────────────────────► │   ├── 6. POST /o/token/  ──────►│
  │                         │   └── 7. GET /o/userinfo/ ─────►│
  │  8. 302 → Dashboard     │        (via extra_hosts)         │
  │ ◄────────────────────── │                                  │
  └─────────────────────────┘─────────────────────────────────┘
```

**Kritisch**: Schritte 6+7 sind **Server-zu-Server** Calls vom App-Container zu authentik.
Der Browser ist nicht beteiligt. Deshalb gelten andere Netzwerk-Regeln.

---

## Checkliste: OIDC Provider in authentik erstellen

### 1. Provider erstellen (API oder Admin UI)

```python
# Via Django Shell (ak shell)
from authentik.providers.oauth2.models import OAuth2Provider, ScopeMapping
from authentik.flows.models import Flow

auth_flow = Flow.objects.get(slug="default-provider-authorization-implicit-consent")
inval_flow = Flow.objects.get(slug="default-provider-invalidation-flow")
signing_key = CertificateKeyPair.objects.first()  # Self-signed cert

provider = OAuth2Provider.objects.create(
    name="<app-name> OIDC Provider",
    authorization_flow=auth_flow,
    invalidation_flow=inval_flow,
    client_type="confidential",
    client_id="<app-slug>",
    signing_key=signing_key,  # ⚠️ PFLICHT — ohne Signing Key → 404 auf /authorize/
)
```

### 2. Scope Mappings zuweisen (⚠️ PFLICHT)

```python
# Ohne Scope Mappings → scope_allowed: set() → leere Userinfo-Response
openid = ScopeMapping.objects.get(scope_name="openid")
email = ScopeMapping.objects.get(scope_name="email")
profile = ScopeMapping.objects.get(scope_name="profile")

provider.property_mappings.add(openid, email, profile)
provider.save()
```

### 3. Application erstellen

```python
from authentik.core.models import Application

Application.objects.create(
    name="<App Display Name>",
    slug="<app-slug>",
    provider=provider,
    meta_launch_url="https://<domain>",
)
```

### 4. Redirect URI konfigurieren

```python
from authentik.providers.oauth2.models import RedirectURI, RedirectURIMatchingMode

RedirectURI.objects.create(
    provider=provider,
    matching_mode=RedirectURIMatchingMode.STRICT,
    url="https://<domain>/auth/callback",
)
```

---

## Bekannte Stolperfallen (Lessons Learned)

### 1. Signing Key fehlt → 404 auf /authorize/

**Symptom**: `Not Found` auf `https://id.iil.pet/application/o/authorize/`
**Ursache**: OAuth2Provider hat keinen `signing_key` zugewiesen.
**Fix**: `provider.signing_key = CertificateKeyPair.objects.first()` + `.save()`

### 2. Scope Mappings fehlen → leere Userinfo

**Symptom**: `auth-error` oder `internal-error` nach Login.
**Log**: `"scope_allowed": "set()"` in authentik Logs.
**Ursache**: Provider hat keine Property Mappings (Scope Mappings) zugewiesen.
**Fix**: `provider.property_mappings.add(openid, email, profile)` + `.save()`

### 3. OIDC URIs: KEIN Slug im Pfad

**Falsch**: `/application/o/<slug>/authorize/`
**Richtig**: `/application/o/authorize/`

Die slug-basierten Pfade sind **nur** für OIDC Discovery:
- ✅ Discovery: `/application/o/<slug>/.well-known/openid-configuration`
- ✅ Authorize: `/application/o/authorize/`
- ✅ Token: `/application/o/token/`
- ✅ Userinfo: `/application/o/userinfo/`

### 4. Self-signed Cert → Node.js/Python SSL-Fehler

**Symptom**: `self-signed certificate` Error bei Server-zu-Server Calls.
**Ursache**: Cloudflare Tunnel terminiert TLS. Origin nutzt self-signed Cert.
**Fix je nach Tech-Stack**:

| Stack | Lösung |
|-------|--------|
| **Node.js** (Outline) | `NODE_TLS_REJECT_UNAUTHORIZED: "0"` |
| **Python/Django** | `REQUESTS_CA_BUNDLE=""` oder `SSL_CERT_FILE` |
| **Go** | Custom TLS Config mit `InsecureSkipVerify` |

### 5. Container kann id.iil.pet nicht auflösen

**Symptom**: `ENOTFOUND id.iil.pet` oder `getaddrinfo failed`
**Ursache**: DNS löst auf Cloudflare IPs, die durch den Tunnel zurückrouten.
**Fix**: `extra_hosts: ["id.iil.pet:host-gateway"]` im docker-compose.yml.
Damit wird `id.iil.pet` auf die Docker-Host-IP aufgelöst → Nginx → authentik.

### 6. AUTHENTIK_HOST muss gesetzt sein

Ohne `AUTHENTIK_HOST=https://id.iil.pet` in der authentik-Config gibt
die OIDC Discovery falsche URLs zurück (z.B. `http://127.0.0.1:9000`).

---

## Template: docker-compose.yml OIDC-Block

```yaml
services:
  myapp:
    environment:
      # OIDC via authentik (ADR-142)
      OIDC_CLIENT_ID: "${OIDC_CLIENT_ID}"
      OIDC_CLIENT_SECRET: "${OIDC_CLIENT_SECRET}"
      # authorize = browser redirect (external URL, keine Änderung nötig)
      OIDC_AUTH_URI: "https://id.iil.pet/application/o/authorize/"
      # token + userinfo = server-to-server (via extra_hosts → host Nginx)
      OIDC_TOKEN_URI: "https://id.iil.pet/application/o/token/"
      OIDC_USERINFO_URI: "https://id.iil.pet/application/o/userinfo/"
      OIDC_SCOPES: "openid profile email"
      # Node.js: self-signed cert akzeptieren (intern, Tunnel terminiert TLS)
      NODE_TLS_REJECT_UNAUTHORIZED: "0"
    extra_hosts:
      - "id.iil.pet:host-gateway"
```

---

## Referenzen

- **ADR-142**: Unified Identity — authentik als Platform IdP
- **ADR-143**: Knowledge-Hub — Outline Integration (erste OIDC-Integration)
- **authentik Docs**: https://docs.goauthentik.io/docs/providers/oauth2/
