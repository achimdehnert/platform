# Klickdummy-Host (`klickdummy.iil.pet`)

Statisches Hosting der Cross-Repo-Klickdummies via nginx + Traefik mit SSO
(Authentik). Konkretisiert `platform:ADR-216`.

**Server:** `staging-platform` (`178.104.184.168`)
**Domain:** `klickdummy.iil.pet`
**Reverse-Proxy:** Traefik v3 (siehe `../traefik/`, ADR-212)
**SSO-Provider:** Authentik (ADR-142)

## Deployment

### 1. Files auf Server

```bash
ssh staging-platform "mkdir -p /opt/klickdummy /srv/klickdummy"
scp infra/klickdummy-host/* staging-platform:/opt/klickdummy/
ssh staging-platform "chmod +x /opt/klickdummy/sync.sh"
```

### 2. SSH-Deploy-Key für Repo-Sync

```bash
ssh staging-platform "ssh-keygen -t ed25519 -f /opt/klickdummy/.ssh/klickdummy-deploy_ed25519 -N '' -C 'klickdummy-host@staging-platform'"
ssh staging-platform "cat /opt/klickdummy/.ssh/klickdummy-deploy_ed25519.pub"
```

Den Public-Key als **Deploy-Key (read-only)** zu jedem der vier Klickdummy-Repos hinzufügen:
- `bahn-sqf/sqf-hub`
- `bahn-sqf/pg-hub`
- `meiki-lra/meiki-hub`
- `ttz-lif/ttz-hub`

### 3. Authentik OAuth-App + Outpost

```bash
# In platform-Repo:
scripts/authentik-staging-oidc.sh \
  --app-slug klickdummy \
  --redirect-uri 'https://klickdummy.iil.pet/outpost.goauthentik.io/callback?X-authentik-auth-callback=true' \
  --scopes openid,profile,email
```

Outpost-Container `authentik-outpost` muss im `traefik_public` Docker-Netzwerk laufen (Standard-Authentik-Embedded-Outpost-Setup).

### 4. Users + Gruppe `klickdummy-viewers` in Authentik

In Authentik-Admin (`https://authentik.iil.pet`):

1. Gruppe `klickdummy-viewers` anlegen
2. User anlegen (jeweils initial-Passwort + Reset-Link):
   - `raphael.bayer@db.de` (sqf-hub Stakeholder)
   - `ilja.lerch@bahn-sqf` (Citizen-Dev)
   - `grinninger@bahn-sqf` (pg-hub Stab)
   - `lra-meiki@meiki-lra` (LRA-Pilot)
   - `ttz-pilot@ttz-lif` (TTZ-Pilot)
3. Alle der Gruppe `klickdummy-viewers` zuweisen
4. App `klickdummy` an Gruppe binden (Bindings → Policy → Group: klickdummy-viewers)

### 5. DNS + Cloudflare-Tunnel

DNS-Record `klickdummy.iil.pet` → `bf-staging`-Tunnel (Cloudflare). Sollte über das Wildcard `*.iil.pet` schon abgedeckt sein; sonst expliziter CNAME.

### 6. Erste Container-Start + erste Sync

```bash
ssh staging-platform "cd /opt/klickdummy && docker compose up -d"
ssh staging-platform "/opt/klickdummy/sync.sh"
ssh staging-platform "curl -s https://klickdummy.iil.pet/healthz"   # ohne SSO
```

### 7. Cron für tägliche Sync

```bash
ssh staging-platform "echo '0 6 * * * /opt/klickdummy/sync.sh >> /var/log/klickdummy-sync.log 2>&1' | crontab -"
```

## Operations

### Manueller Sync

```bash
ssh staging-platform "/opt/klickdummy/sync.sh"
```

### Logs

- nginx: `docker logs klickdummy`
- Sync: `/var/log/klickdummy-sync.log`
- Traefik: `docker logs traefik` (siehe `../traefik/`)
- Authentik-Outpost: `docker logs authentik-outpost`

### Neuen Klickdummy hinzufügen

1. `repos.yaml` ergänzen (in diesem Repo, via PR)
2. Nach Merge: `ssh staging-platform "cd /opt/klickdummy && git pull && ./sync.sh"`
   (oder warten bis Cron läuft)

## Phase 2 (Owner-Login) — Backlog

Siehe ADR-216 § Authentifizierung Phase 2:

- Pro Org eine Authentik-Gruppe (`klickdummy-sqf-viewers`, …)
- Pro Org eine Traefik-Router-Rule mit Gruppen-Filter
- Separate ADR (geplant: `platform:ADR-217`)

## Refs

- `platform:ADR-216` — Klickdummy-Hosting (diese Konfiguration)
- `platform:ADR-215` — Klickdummy-Discovery (Stage 1.5)
- `platform:ADR-212` — Traefik-Ingress
- `platform:ADR-142` — Authentik als Plattform-IdP
- `platform:ADR-198` — Cloudflare-Tunnel `bf-staging`
- `platform:ADR-210` — 3-Stufen-Hosting-Modell
