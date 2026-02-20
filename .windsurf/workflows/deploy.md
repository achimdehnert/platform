---
description: Deploy any app to production server (88.198.191.108)
---

# Deploy Workflow

Deploys the specified app to production via SSH.

## Usage

`/deploy dev-hub` | `/deploy bfagent` | `/deploy weltenhub` | `/deploy travel-beat` | `/deploy risk-hub`

## Step 1: Setup (first time only)

Einmalig die Deploy-Scripts auf den Server kopieren:

```bash
ssh root@88.198.191.108 'cd /opt/dev-hub && git pull origin main && cp -r scripts /opt/scripts && chmod +x /opt/scripts/*.sh && echo SETUP OK'
```

## Step 2: Deploy

Ersetze `<app>` mit dem App-Namen:

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh dev-hub'`

**Andere Apps:**
```bash
# bfagent
ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh bfagent'

# weltenhub
ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh weltenhub'

# travel-beat
ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh travel-beat'

# risk-hub
ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh risk-hub'
```

## Erwartete Ausgabe

```
[dev-hub] git pull...
[dev-hub] docker cp...
[dev-hub] migrate...
[dev-hub] reload...
DEPLOY OK: dev-hub
```

## Troubleshooting

- **`No such file or directory`**: Setup (Step 1) noch nicht ausgeführt
- **Migration error**: Logs prüfen: `docker logs devhub_web --tail 30`
- **500 nach Deploy**: `docker logs devhub_web --tail 50`
