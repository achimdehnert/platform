---
description: Deploy any app to production server (88.198.191.108)
---

# Deploy Workflow

## Einmalig: Setup (nur beim ersten Mal)

// turbo
Run: `ssh root@88.198.191.108 'cd /opt/dev-hub && git pull origin main && cp -r scripts /opt/scripts && chmod +x /opt/scripts/*.sh && echo SETUP OK'`

## dev-hub (https://devhub.iil.pet)

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh dev-hub'`

## bfagent (https://bfagent.iil.pet)

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh bfagent'`

## weltenhub (https://weltenforger.com)

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh weltenhub'`

## travel-beat (https://drifttales.app)

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh travel-beat'`

## risk-hub (Schutztat)

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh risk-hub'`

## Erwartete Ausgabe

```
[dev-hub] git pull...
[dev-hub] docker cp...
[dev-hub] migrate...
[dev-hub] reload...
DEPLOY OK: dev-hub
```

## Troubleshooting

- **`No such file or directory`**: Setup oben ausführen
- **500 nach Deploy**: `ssh root@88.198.191.108 'docker logs devhub_web --tail 50'`
