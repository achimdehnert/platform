---
description: Onboard a new third-party stack (Outline, Authentik, Paperless, etc.) into the platform infrastructure
---

# /onboard-stack

Neuen Third-Party-Stack in die Platform-Infrastruktur aufnehmen (nicht Django-Hubs — dafür `/onboard-repo`).

## Wann verwenden?
- Neue Third-Party-Software deployen (z.B. Outline, Authentik, Paperless, Uptime Kuma)
- Bestehenden Stack auf neuen Server migrieren

## Schritte

1. **Port reservieren**
   - `platform/infra/ports.yaml` lesen
   - Nächsten freien Port vergeben (aktuell: 8108+)
   - Eintrag hinzufügen mit prod/staging/domain

2. **Verzeichnis auf Server anlegen**
```
mcp0_ssh_manage(action="exec", host="88.198.191.108", command="mkdir -p /opt/<stack-name>")
```

3. **docker-compose.prod.yml erstellen** (ADR-021 compliant)
   Pflicht-Elemente:
   - `ports: "127.0.0.1:<PORT>:<INTERNAL_PORT>"`
   - `mem_limit` auf allen Services
   - `healthcheck` auf Haupt-Service
   - `logging: driver: json-file` mit `max-size: 10m`, `max-file: 3`
   - `restart: unless-stopped`
   - `env_file: .env.prod` (keine `${VAR}` interpolation)

4. **.env.prod erstellen**
   - Secrets generieren (min. 32 Zeichen)
   - NIEMALS Klartext-Passwörter im Compose-File

5. **Nginx-Config erstellen**
   Pflicht:
   ```nginx
   listen 443 ssl http2;
   listen [::]:443 ssl http2;  # IPv6 PFLICHT!
   server_name <domain>;
   proxy_pass http://127.0.0.1:<PORT>;
   ```

6. **Cloudflare DNS**
```
mcp0_cloudflare_manage(action="cf_dns_upsert", domain="iil.pet", name="<subdomain>", record_type="CNAME", content="<tunnel-id>.cfargotunnel.com")
```

7. **SSL-Zertifikat**
```
mcp0_network_manage(action="ssl_obtain", domains="<domain>", email="admin@iil.gmbh", standalone=true, host="88.198.191.108")
```

8. **Stack starten**
```
mcp0_docker_manage(action="compose_up", host="88.198.191.108", project_path="/opt/<stack-name>")
```

9. **Nginx reload**
```
mcp0_system_manage(action="nginx_reload", host="88.198.191.108")
```

10. **Health-Check**
```
mcp0_ssh_manage(action="http_check", host="88.198.191.108", url="https://<domain>/")
```

11. **Knowledge Graph updaten**
    - `repos.json` — neuen Eintrag mit `settings_module: null` für non-Django
    - `edges.json` — mindestens COMPOSE-001 und NGINX-001 Edges

12. **Outline dokumentieren**
    - Repo-Steckbrief erstellen oder vorhandenen updaten

## Referenzen
- ADR-021: Unified Deployment Pattern
- ADR-056: Docker Security
- Lesson Learned (IPv6): `88e79861-a37f-43a7-9086-25335281176f`
- `/stack-upgrade` — für Updates bestehender Stacks
