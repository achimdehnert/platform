# Klickdummy-Host (`staging-klickdummy.iil.pet`)

Statisches Hosting der Cross-Repo-Klickdummies via nginx + Traefik mit SSO
(Authentik). Konkretisiert `platform:ADR-216`.

**Server:** `staging-platform` (`178.104.184.168`)
**Domain:** `staging-klickdummy.iil.pet`
**Reverse-Proxy:** Traefik v3 (siehe `../traefik/`, ADR-212)
**SSO-Provider:** Authentik (ADR-142)

## Deployment

### 0. Dedizierten Sync-User anlegen (Review-Pass 2: NICHT root)

```bash
ssh staging-platform "sudo useradd -r -m -d /var/lib/klickdummy-sync -s /bin/bash klickdummy-sync"
ssh staging-platform "sudo mkdir -p /opt/klickdummy /srv/klickdummy /var/lib/klickdummy-sync"
ssh staging-platform "sudo chown -R klickdummy-sync:klickdummy-sync /opt/klickdummy /srv/klickdummy /var/lib/klickdummy-sync"
```

### 1. Files auf Server

```bash
scp infra/klickdummy-host/* staging-platform:/tmp/klickdummy/
ssh staging-platform "sudo mv /tmp/klickdummy/* /opt/klickdummy/ && sudo chown -R klickdummy-sync:klickdummy-sync /opt/klickdummy && sudo chmod +x /opt/klickdummy/sync.sh /opt/klickdummy/generate_landing.py"
```

### 2. SSH-Deploy-Key für Repo-Sync (User-skopiert, nicht root)

```bash
ssh staging-platform "sudo -u klickdummy-sync ssh-keygen -t ed25519 -f /var/lib/klickdummy-sync/.ssh/klickdummy-deploy_ed25519 -N '' -C 'klickdummy-sync@staging-platform'"
ssh staging-platform "sudo cat /var/lib/klickdummy-sync/.ssh/klickdummy-deploy_ed25519.pub"
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
  --redirect-uri 'https://staging-klickdummy.iil.pet/outpost.goauthentik.io/callback?X-authentik-auth-callback=true' \
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

DNS-Record `staging-klickdummy.iil.pet` → `bf-staging`-Tunnel (Cloudflare). Sollte über das Wildcard `*.iil.pet` schon abgedeckt sein; sonst expliziter CNAME.

### 6. Erste Container-Start + erste Sync

```bash
ssh staging-platform "cd /opt/klickdummy && docker compose up -d"
ssh staging-platform "/opt/klickdummy/sync.sh"
ssh staging-platform "curl -s https://staging-klickdummy.iil.pet/healthz"   # ohne SSO
```

### 7. Cron — 15-Min-Intervall (Review-Pass: schnellere Iteration als 24h)

Als User `klickdummy-sync`:

```bash
ssh staging-platform "sudo -u klickdummy-sync crontab -l 2>/dev/null; echo '*/15 * * * * /opt/klickdummy/sync.sh >> /var/log/klickdummy-sync.log 2>&1' | sudo -u klickdummy-sync crontab -"
```

Log-Rotation (logrotate-Snippet):

```bash
cat | sudo tee /etc/logrotate.d/klickdummy-sync <<EOF
/var/log/klickdummy-sync.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
EOF
```

## Discovery-API (Review-Pass 4 Idee 1)

`staging-klickdummy.iil.pet/api/list` ist ein **same-origin Discovery-Endpoint**.
Vom Sync-Job als `/srv/klickdummy/_index.json` generiert. Cross-Repo-Picker
in einem Klickdummy kann same-origin fetchen statt orchestrator.iil.pet
(spart CORS-Setup):

```javascript
const resp = await fetch('/api/list', { credentials: 'include' });
const data = await resp.json();
CROSS_REPO_INDEX = data.entries;
```

Beide Discovery-Quellen sind verfügbar — Picker kann frei wählen:

| Endpoint | Quelle | Vorteile |
|---|---|---|
| `orchestrator.iil.pet/api/discovery/klickdummy/list` | pgvector (ADR-215) | semantische Search, MCP-Tool |
| `/api/list` (same-origin) | Filesystem-Index | kein CORS, low-latency, no-SPOF auf Orchestrator |

## Sicherheits-Anmerkungen (Review-Pass 3)

- `sync.sh` läuft als `klickdummy-sync`, nicht root — verhindert lateral movement bei sync-Script-Kompromittierung
- SSH-Deploy-Key ist **read-only pro Repo** — single key compromise ⇒ nur 4 Klickdummy-Repos read-leak (statt Schreibzugriff)
- nginx-Container mountet `/srv/klickdummy` **read-only** — kann Quelle nicht überschreiben
- `/healthz` ohne Auth (Trade-off für Monitoring); minimal Info-Leak ist akzeptabel
- Authentik-Outpost trägt Session-Cookie pro User — Audit-Log via Authentik-Event-Log

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
