# Authentik Staging OIDC — Credentials Reference (ADR-142)

> **WICHTIG**: Dieses Dokument enthält KEINE Secrets. Die Client Secrets
> liegen ausschließlich auf dem Staging-Server unter `/opt/<hub>/.env.staging`.

## Architektur

```
┌─────────────────────┐
│  Authentik (Prod)    │  id.iil.pet
│  88.198.191.108:9000 │
├─────────────────────┤
│ Production Apps (20) │  billing-hub, coach-hub, ...
│ Staging Apps (4)     │  billing-hub-staging, coach-hub-staging, ...
└─────────┬───────────┘
          │ OIDC
    ┌─────┴─────┐
    ▼           ▼
┌────────┐ ┌─────────┐
│ PROD   │ │ STAGING │
│ Server │ │ Server  │
│ .108   │ │ .75     │
└────────┘ └─────────┘
```

**Entscheidung**: Single Authentik, Dual Applications (Option A+C).
Staging-Apps nutzen dieselbe Authentik-Instanz mit eigenen Client-Credentials.

## Staging Applications

| Hub | Authentik Slug | Redirect URI | Staging Domain |
|-----|---------------|--------------|----------------|
| billing-hub | `billing-hub-staging` | `https://billing-staging.iil.pet/oidc/callback/` | billing-staging.iil.pet |
| coach-hub | `coach-hub-staging` | `https://learn-staging.iil.pet/oidc/callback/` | learn-staging.iil.pet |
| wedding-hub | `wedding-hub-staging` | `https://wedding-staging.iil.pet/oidc/callback/` | wedding-staging.iil.pet |
| weltenhub | `weltenhub-staging` | `https://welten-staging.iil.pet/oidc/callback/` | welten-staging.iil.pet |

## ENV-Variablen (Staging .env)

```bash
# Pflicht
OIDC_ENABLED=true
OIDC_APP_SLUG=<hub>-staging          # z.B. billing-hub-staging
OIDC_RP_CLIENT_ID=<from-authentik>
OIDC_RP_CLIENT_SECRET=<from-authentik>

# Optional (Default: https://id.iil.pet)
OIDC_IDP_BASE_URL=https://id.iil.pet
```

## Credentials-Speicherorte

| Server | Pfad | Permissions |
|--------|------|-------------|
| Staging (88.99.38.75) | `/opt/<hub>/.env.staging` | `600 root` |
| Prod (88.198.191.108) | `/opt/<hub>/.env.prod` | `600 root` |

## OIDC deaktivieren (lokal)

```bash
# In .env oder als ENV-Variable
OIDC_ENABLED=false
```

## Neue Staging-App hinzufuegen

1. Authentik Admin UI: https://id.iil.pet/if/admin/
2. Providers > Create > OAuth2/OpenID
3. Authorization Flow: `default-provider-authorization-implicit-consent`
4. Invalidation Flow: `default-invalidation-flow`
5. Signing Key: `authentik Self-signed Certificate`
6. Application erstellen mit Slug `<hub>-staging`, Group `staging`
7. `.env.staging` auf Staging-Server anlegen

Oder via API (siehe `create_staging_app.sh` Pattern oben).

## Erstellt

- **Datum**: 2026-04-04
- **Erstellt durch**: Cascade (automated)
- **ADR**: ADR-142 (authentik OIDC Integration)
