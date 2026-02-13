# Infrastruktur

## Server

Alle Apps auf einem Hetzner Cloud VM: `88.198.191.108`

## Docker-Architektur

```text
┌─────────────────────────────────────────────────────────┐
│                    Hetzner VM                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Nginx   │  │ bfagent_db   │  │ bfagent_redis     │  │
│  │ (Proxy)  │  │ (Postgres16) │  │ (Redis 7)         │  │
│  └────┬─────┘  └──────────────┘  └───────────────────┘  │
│       │                                                  │
│  ┌────┴──────────────────────────────────────────────┐   │
│  │            bf_platform_prod (Docker Network)       │   │
│  ├────────────┬──────────────┬──────────────────────┤   │
│  │ bfagent    │ travel-beat  │ weltenhub            │   │
│  │ :8000      │ :8002        │ :8081                │   │
│  ├────────────┼──────────────┼──────────────────────┤   │
│  │ mcp-hub    │ cad-hub      │ risk-hub             │   │
│  │ :8003      │ :8094        │ :8091                │   │
│  └────────────┴──────────────┴──────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## TLS / Domains

| Domain | App | Zertifikat |
|--------|-----|-----------|
| bfagent.iil.pet | bfagent | Let's Encrypt |
| drifttales.com | travel-beat | Let's Encrypt |
| weltenforger.com | weltenhub | Let's Encrypt |
| mcp-hub.iil.pet | mcp-hub | Let's Encrypt |
| nl2cad.de | cad-hub | Let's Encrypt |
| schutztat.de | risk-hub | Let's Encrypt |

## Deploy-Prozess

Jede App hat ein eigenes `docker-compose.prod.yml` in `/opt/<app>/`.

```bash
# Typischer Deploy
ssh root@88.198.191.108
cd /opt/<app>
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --force-recreate <service>
```
