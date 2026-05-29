# Klausel-3-Migration Checkliste — Klickdummy-Host

**Voraussetzung:** ADR-212 (Traefik) + ADR-142 (Authentik) sind auf `staging-platform` deployed.
**Ziel-Zustand:** `staging-klickdummy.iil.pet` läuft über Traefik + Authentik-SSO (ADR-216 Klausel-3-Architektur, ADR-217 Owner-Auth via Authentik-Groups).
**Geschätzter Aufwand:** 30 Min (sofern Voraussetzungen erfüllt).

## Pre-Flight-Check

```bash
ssh root@staging-platform "
  docker network inspect traefik_public > /dev/null && echo '✓ traefik_public network'
  docker ps --format '{{.Names}}' | grep -q '^traefik$' && echo '✓ traefik container'
  docker ps --format '{{.Names}}' | grep -q 'authentik-outpost' && echo '✓ authentik-outpost container'
  curl -s -o /dev/null -w '✓ authentik web HTTP %{http_code}\n' http://localhost:9000/-/health/live/
"
```

Alle 4 Checks müssen ✓ zeigen. Wenn nicht: erst ADR-212 + ADR-142 deployen.

## Schritt 1 — Authentik-Setup für Klickdummy (~10 Min)

### 1a) OAuth-App + Provider anlegen

```bash
# Auf einem Rechner mit AK_TOKEN ENV (Authentik-API-Token)
cd ~/github/platform
./scripts/authentik-staging-oidc.sh \
  --app-slug klickdummy \
  --redirect-uri 'https://staging-klickdummy.iil.pet/outpost.goauthentik.io/callback?X-authentik-auth-callback=true' \
  --scopes 'openid profile email'
```

Output: Provider-ID, Client-Secret. Notieren für Outpost-Konfiguration.

### 1b) Authentik-Embedded-Outpost erweitern

Authentik-Admin-UI:
1. **Applications → Outposts → "embedded-outpost" → Edit**
2. Application `klickdummy` zur Liste hinzufügen
3. Save

Alternative via API:
```bash
curl -X PATCH "https://authentik.iil.pet/api/v3/outposts/instances/<embedded-uuid>/" \
  -H "Authorization: Bearer $AK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"providers": [<klickdummy-provider-id>, ...existing-ids]}'
```

### 1c) Gruppen anlegen + User zuweisen

Phase-1-Gruppe (alle Stakeholder zusammen):

```bash
ak group create klickdummy-viewers
ak user create raphael.bayer --email raphael.bayer@db.de --groups klickdummy-viewers
ak user create ilja.lerch --email ilja.lerch@bahn-sqf --groups klickdummy-viewers
ak user create grinninger --email grinninger@bahn-sqf --groups klickdummy-viewers
ak user create lra-meiki --email lra-meiki@meiki-lra --groups klickdummy-viewers
ak user create ttz-pilot --email ttz-pilot@ttz-lif --groups klickdummy-viewers
ak user create risk-pilot --email risk-pilot@achimdehnert --groups klickdummy-viewers
```

Phase-2-Gruppen (ADR-217 owner-spezifisch, später):

```bash
ak group create klickdummy-sqf-viewers
ak group create klickdummy-pg-viewers
ak group create klickdummy-meiki-viewers
ak group create klickdummy-ttz-viewers
ak group create klickdummy-risk-viewers
ak group create klickdummy-admin
```

### 1d) Application-Binding (Phase 1)

Authentik-Admin → Applications → klickdummy → Bindings → Create:
- Policy: User-in-Group → `klickdummy-viewers`
- Order: 10
- Enabled: true

## Schritt 2 — Klickdummy-Container migrieren (~5 Min)

```bash
ssh root@staging-platform '
  # Compose-File scp'd nach /opt/klickdummy/
  cp /tmp/klickdummy-host-bundle/docker-compose.klausel3.yml /opt/klickdummy/
  chown klickdummy-sync:klickdummy-sync /opt/klickdummy/docker-compose.klausel3.yml

  cd /opt/klickdummy
  # Klausel-2-Container stoppen
  docker compose -f docker-compose.klausel2.yml down

  # Symlink auf neue Compose-File
  ln -sf docker-compose.klausel3.yml docker-compose.yml

  # Hoch
  docker compose up -d
  docker ps --filter name=klickdummy --format "{{.Names}}|{{.Status}}"
'
```

## Schritt 3 — nginx-vhost entfernen (~2 Min)

```bash
ssh root@staging-platform '
  # vhost archivieren statt löschen
  mkdir -p /opt/klickdummy/archive
  mv /etc/nginx/sites-available/staging-klickdummy.iil.pet \
     /opt/klickdummy/archive/staging-klickdummy.iil.pet.$(date +%Y%m%d)
  rm /etc/nginx/sites-enabled/staging-klickdummy.iil.pet

  # htpasswd-Files archivieren
  mkdir -p /opt/klickdummy/archive/htpasswd
  mv /etc/nginx/htpasswd-{default,sqf,pg,meiki,ttz,risk} \
     /opt/klickdummy/archive/htpasswd/

  nginx -t && systemctl reload nginx
  echo "✓ nginx-vhost entfernt, Traefik übernimmt"
'
```

## Schritt 4 — Cloudflared-Tunnel-Config anpassen (~3 Min)

Aktuell: Tunnel routet alle staging.*-Hosts an `https://localhost:443` (nginx).
Mit Traefik: gleiche Route, aber Traefik (auf 443) macht das hostname-Routing.

**Kein Cloudflared-Change nötig** (gleicher Tunnel-Target). Aber: prüfen, ob Traefik wirklich auf 443 lauscht.

```bash
ssh root@staging-platform '
  ss -tlnp | grep -E ":(443|8080)"
  # Expected: traefik auf :443
'
```

Falls Traefik nicht auf 443 lauscht: Traefik-Compose anpassen (siehe `infra/traefik/docker-compose.yml`).

## Schritt 5 — End-to-End-Test (~5 Min)

```bash
# Ohne Auth — sollte zu Authentik-Login redirected
curl -s -o /dev/null -w "  / → HTTP %{http_code} (302 erwartet, Location: authentik)\n" \
  -L --max-redirs 0 \
  https://staging-klickdummy.iil.pet/

# Health (kein Auth)
curl -s -o /dev/null -w "  /healthz → HTTP %{http_code} (200 erwartet)\n" \
  https://staging-klickdummy.iil.pet/healthz

# Mit Browser: Login-Flow durchspielen
# → https://staging-klickdummy.iil.pet/
# → Authentik-Login-Screen
# → nach Login: Landing mit allen 11 Klickdummies
```

## Schritt 6 — Phase 2 (Owner-Auth via Authentik-Groups, ADR-217)

**Optional, später.** Pre-Pilot mit `klickdummy-viewers` reicht zunächst.

Wenn aktiviert: pro Org eine separate Authentik-Application + Binding, oder
nginx-Map mit `$remote_user`-Pfad-Filter (wenn nginx weiter im Stack ist — bei
Klausel 3 ist nginx aber raus, Traefik+Authentik macht Auth direkt).

Sauberster Pfad Phase 2:
- 5 Authentik-Applications (`klickdummy-sqf`, `klickdummy-pg`, …) je mit eigener Group-Policy
- 5 Traefik-Router-Rules mit `PathPrefix(/bahn-sqf/sqf-hub/)` etc.

Aufwand: ~30 Min nach Phase-1-Stabilität.

## Roll-Back zu Klausel 2

Falls Klausel 3 nicht funktioniert:

```bash
ssh root@staging-platform '
  cd /opt/klickdummy
  docker compose -f docker-compose.klausel3.yml down
  ln -sf docker-compose.klausel2.yml docker-compose.yml
  docker compose up -d

  # nginx-vhost wiederherstellen
  cp /opt/klickdummy/archive/staging-klickdummy.iil.pet.* \
     /etc/nginx/sites-available/staging-klickdummy.iil.pet
  ln -sf /etc/nginx/sites-available/staging-klickdummy.iil.pet \
     /etc/nginx/sites-enabled/

  # htpasswd wiederherstellen
  cp /opt/klickdummy/archive/htpasswd/* /etc/nginx/

  nginx -t && systemctl reload nginx
'
```

## Anti-Drift-Check (nach Migration)

```bash
ssh root@staging-platform '
  # Traefik routet klickdummy?
  curl -s http://localhost:8080/api/http/routers | jq ".[] | select(.name | contains(\"klickdummy\"))"

  # Container hat richtige Labels?
  docker inspect klickdummy --format "{{json .Config.Labels}}" | jq | grep traefik

  # SSO-Outpost reagiert?
  curl -s -o /dev/null -w "outpost-auth-endpoint → HTTP %{http_code}\n" \
    http://authentik-outpost:9000/outpost.goauthentik.io/auth/traefik
'
```

## Refs

- ADR-216 Hosting (Mutter)
- ADR-217 Owner-Auth Phase 2
- ADR-142 Authentik IdP
- ADR-212 Traefik-Ingress
- ADR-198 Cloudflared-Tunnel
- platform/scripts/authentik-staging-oidc.sh (Pattern aus risk-hub-Staging)
