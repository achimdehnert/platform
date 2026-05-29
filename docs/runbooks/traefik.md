# Runbook: Traefik Ingress — Staging-Platform

**Server:** 178.104.184.168 (staging-platform)
**Stack:** `/opt/traefik/docker-compose.yml`
**ADR:** ADR-212 (Klausel-3-Routing für `staging-*.iil.pet`)

---

## Traefik ist down — sofortige Diagnose

```bash
# 1. Ist der Container überhaupt da?
ssh staging-platform "docker ps -a --filter name=traefik --format '{{.Names}} {{.Status}}'"

# 2. Logs der letzten 50 Zeilen
ssh staging-platform "docker logs --tail 50 traefik"

# 3. Health-Check direkt abfragen
ssh staging-platform "curl -sf http://127.0.0.1:8080/ping && echo OK"
```

### Traefik crasht in Loop (`Restarting`)

```bash
# Logs zeigen Startup-Fehler:
ssh staging-platform "docker logs traefik 2>&1 | tail -20"

# Häufigste Ursache: CF_DNS_API_TOKEN fehlt oder leer
ssh staging-platform "grep CF_DNS_API_TOKEN /opt/traefik/.env"

# Fix: .env korrigieren, dann
ssh staging-platform "cd /opt/traefik && docker compose up -d"
```

### Traefik läuft, aber Routing funktioniert nicht

```bash
# Sind die Apps im richtigen Docker-Network?
ssh staging-platform "docker network inspect traefik_public --format '{{range .Containers}}{{.Name}} {{end}}'"

# Labels eines Containers prüfen (Beispiel dev-hub):
ssh staging-platform "docker inspect dev_hub_staging_web | python3 -m json.tool | grep -A1 'traefik'"

# Traefik-Dashboard zeigt alle Routes — via SSH-Tunnel:
ssh -L 8080:127.0.0.1:8080 staging-platform
# Dann: http://localhost:8080/dashboard/
```

---

## Neu-Start nach Crash

```bash
ssh staging-platform "cd /opt/traefik && docker compose restart traefik"
```

Falls Container nicht mehr existiert:

```bash
ssh staging-platform "cd /opt/traefik && docker compose up -d"
```

---

## Wildcard-Cert erneuern / debuggen

```bash
# Cert-Status im ACME-Storage prüfen
ssh staging-platform "docker exec traefik cat /letsencrypt/acme.json | python3 -m json.tool | grep -A5 'iil.pet'"

# Manuelles ACME-Renewal triggern:
# Traefik erneuert automatisch 30 Tage vor Ablauf.
# Falls klemmt: Container neustarten (ACME-Client läuft beim Start durch)
ssh staging-platform "cd /opt/traefik && docker compose restart traefik"

# CF-Token verifizieren
ssh staging-platform "source /opt/traefik/.env && curl -sf -H 'Authorization: Bearer \$CF_DNS_API_TOKEN' https://api.cloudflare.com/client/v4/user/tokens/verify | python3 -m json.tool"
```

---

## Neuen Klausel-3-Hub hinzufügen

1. In `<repo>/docker-compose.staging.yml`:
   ```yaml
   services:
     web:
       networks:
         - traefik_public
         - default
       labels:
         traefik.enable: "true"
         traefik.http.routers.<slug>-staging.rule: "Host(`staging-<slug>.iil.pet`)"
         traefik.http.routers.<slug>-staging.entrypoints: "websecure"
         traefik.http.routers.<slug>-staging.tls: "true"
         traefik.http.routers.<slug>-staging.tls.certresolver: "letsencrypt"
         traefik.http.services.<slug>-staging.loadbalancer.server.port: "<intern-port>"
   
   networks:
     traefik_public:
       external: true
   ```

2. `docker compose -f docker-compose.staging.yml up -d` auf staging-platform.
3. Traefik erkennt die Labels automatisch — kein reload nötig.
4. Smoke-Test: `curl -sI https://staging-<slug>.iil.pet/livez/`
5. Nginx-vhost für diesen Hub aus `/etc/nginx/sites-available/` entfernen (Klausel-2-Config).
6. `docs/staging-ingress-migration.md` auf ✅ setzen.

---

## Klausel-3-Hub entfernen

```bash
# Container stoppen/entfernen — Traefik entfernt Route automatisch
ssh staging-platform "cd /opt/<repo> && docker compose -f docker-compose.staging.yml down"
```

---

## Update auf neue Traefik-Version

```bash
# 1. Neue Image-Version in docker-compose.yml (infra/traefik/docker-compose.yml)
# 2. Auf staging-platform deployen:
ssh staging-platform "cd /opt/traefik && docker compose pull && docker compose up -d"
# 3. Smoke-Test:
curl -sI https://staging-traefiktest.iil.pet
```

---

## Monitoring

- **Uptime-Kuma:** Monitor auf `https://staging-traefiktest.iil.pet` (HTTP 200).
  Wenn dieser Monitor anschlägt → Traefik oder whoami-Container down.
- **Dashboard:** SSH-Tunnel → `http://localhost:8080/dashboard/` (BasicAuth).

---

## Vollständiger Reset (Notfall)

```bash
ssh staging-platform "cd /opt/traefik && docker compose down -v && docker compose up -d"
```

**ACHTUNG:** `-v` löscht das ACME-Storage-Volume. Das LE-Cert wird neu angefordert
(DNS-01 Propagation ~60s, dann Cert ausgestellt). Kurze Downtime für alle
Klausel-3-Hubs während ACME läuft.
