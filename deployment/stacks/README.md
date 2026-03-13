# Deployment Stacks — Third-Party Services

Produktionsreife Docker Compose Stacks für Third-Party-Services auf hetzner-prod.

## Stacks

| Stack | ADR | Domain | Port | Status |
|-------|-----|--------|------|--------|
| **authentik** | ADR-142 | id.iil.pet | 9000 | Bereit |
| **outline** | ADR-143 | knowledge.iil.pet | 3000 | Bereit |
| **doc-hub** | ADR-144 | docs.iil.pet | 8102 | Deployed |

## Deployment

```bash
# 1. Auf hetzner-prod: Verzeichnis erstellen
ssh hetzner-prod "mkdir -p /opt/<stack>"

# 2. Dateien kopieren
scp deployment/stacks/<stack>/docker-compose.yml hetzner-prod:/opt/<stack>/
scp deployment/stacks/<stack>/.env.template hetzner-prod:/opt/<stack>/.env

# 3. Secrets ausfüllen
ssh hetzner-prod "vi /opt/<stack>/.env"

# 4. Starten
ssh hetzner-prod "cd /opt/<stack> && docker compose up -d"

# 5. Nginx-Config kopieren + aktivieren
scp deployment/nginx/prod/<domain>.conf hetzner-prod:/etc/nginx/sites-available/
ssh hetzner-prod "ln -sf /etc/nginx/sites-available/<domain>.conf /etc/nginx/sites-enabled/"
ssh hetzner-prod "nginx -t && systemctl reload nginx"

# 6. SSL (wenn kein Cloudflare Tunnel)
ssh hetzner-prod "certbot --nginx -d <domain>"

# 7. Backup-Cron
scp deployment/stacks/<stack>/backup.sh hetzner-prod:/etc/cron.daily/<stack>-backup
ssh hetzner-prod "chmod +x /etc/cron.daily/<stack>-backup"
```

## Dateistruktur

```
deployment/stacks/
├── authentik/           # ADR-142: Identity Provider
│   ├── docker-compose.yml
│   ├── .env.template
│   ├── backup.sh
│   └── templates/       # OIDC-Integration Templates für Django-Hubs
│       ├── core_auth.py
│       └── settings_oidc.py
├── outline/             # ADR-143: Knowledge-Hub Wiki
│   ├── docker-compose.yml
│   ├── .env.template
│   └── backup.sh
└── doc-hub/             # ADR-144: Paperless-ngx DMS
    ├── docker-compose.yml
    ├── .env.template
    └── backup.sh
```

## Platform-Standards (alle Stacks)

- `name:` im Compose (COMPOSE_PROJECT_NAME)
- Dediziertes Docker-Netzwerk (`iil_<stack>_*`)
- Container-Prefix `iil_`
- Redis mit `requirepass`
- Healthchecks auf allen Services
- `depends_on: condition: service_healthy`
- Version-Pinning (kein `:latest`)
- Secrets via `.env` (nie committed)
- Backup-Script mit `set -euo pipefail`
