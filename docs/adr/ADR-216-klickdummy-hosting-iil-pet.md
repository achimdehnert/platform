---
id: ADR-216
title: "Klickdummy-Hosting auf iil.pet (Self-Hosted Stakeholder-Demos)"
status: proposed
date: 2026-05-21
deciders: [Achim Dehnert]
consulted: []
informed: [meiki-lra, bahn-sqf, ttz-lif, iilgmbh]
domains: [infrastructure, deployment, klickdummy, hosting]
supersedes: []
amends: []
depends_on: [ADR-142, ADR-198, ADR-210, ADR-212, ADR-215]
related: [ADR-211, ADR-113]
tags: [klickdummy, hosting, traefik, staging, iil-pet, self-hosted]
scope:
  include_paths:
    - "infra/klickdummy-host/"
    - "docs/adr/ADR-216-*"
---

# ADR-216 — Klickdummy-Hosting auf `iil.pet` (Self-Hosted Stakeholder-Demos)

## Status

**proposed** — Konkretisiert Stage 2 aus der Klickdummy-Hosting-Frage
(meiki-hub-Session Iter. 24, User-Entscheidung Pfad D: „alles unter
meiner Kontrolle"). Tritt in Kraft mit erstem Container-Deployment.

## Kontext

### Stage 1.5 ist live (ADR-215)

`platform:ADR-215` (proposed, PR #283) etabliert pgvector-Discovery für
Cross-Repo-Klickdummies. Cross-Repo-Picker in den Klickdummies fetcht
beim Page-Load aus `orchestrator.iil.pet/api/discovery/klickdummy/list`,
mit Inline-Fallback. **Empirie #1 läuft in `meiki-hub` PR #38 (merged).**

### Pre-Pilot-Reviews brauchen URLs (Stage 2)

Stakeholder-Reviews mit Raphael Bayer (sqf), Ilja Lerch + Grinninger (pg),
TTZ-Pilot brauchen **klick-bare URLs**, nicht lokales `python3 -m http.server`.
Iter. 24 versuchte GitHub Pages für alle 4 Klickdummy-Repos — scheiterte am
Free-Plan-Limit für private Repos (siehe Drift-Memory
`github-pages-private-repo-plan`).

### User-Entscheidung 2026-05-21

> „D, da ich alles unter meiner Kontrolle will!"

Pfad D = self-hosted auf `iil.pet`-Infrastruktur, statt Plan-Upgrades bei
GitHub oder Drittanbietern wie Cloudflare Pages.

## Entscheidung

**Statisches Klickdummy-Hosting via Traefik-Reverse-Proxy auf
`klickdummy.iil.pet`.** Konkret:

1. **Hostname:** `klickdummy.iil.pet` (production, nicht `staging-*` — Stakeholder-Demos sind Pre-Pilot, aber Domain ist stabil)
2. **Reverse-Proxy:** existierender Traefik v3 (`platform:ADR-212` Klausel 3)
3. **Backend:** ein **nginx-Container** mit Volume-Mount auf `/srv/klickdummy/`
4. **URL-Schema:** `https://klickdummy.iil.pet/<org>/<repo>/<klickdummy>/`
5. **Content-Sync:** **Pull-Mode** via Cron — Server pullt alle Klickdummy-Repos täglich (`git pull --ff-only`) und kopiert `klickdummy/<name>/` und `docs/01-architektur/mockups/<name>/` ins nginx-DocRoot

## Warum Pull statt Push

| Push (CI) | Pull (Server) |
|---|---|
| Pro Repo eine GitHub Action mit `ssh staging-platform rsync ...` | Server-seitiger Cron-Job mit Deploy-Key pro Repo |
| Token auf jeder Org/Repo-Seite | Ein Deploy-Key zentral |
| Latenz: nahezu sofort nach Merge | Latenz: bis zu 24h (Cron-Intervall tunbar) |
| Sicherheits-Risiko: Token-Spread (vgl. Drift-Memory `pat-in-remote-url-leak`) | Sicherheits-Risiko: SSH-Key-Verwaltung server-seitig |
| 4× Workflow-Files in 4 Orgs | 1× Cron-Job + Repo-Liste |

**Pull-Mode passt zu „alles unter meiner Kontrolle":** keine Tokens in
GitHub, keine externen Push-Trigger, alles in einer Server-Verantwortung.

Latenz von 24h ist für Pre-Pilot-Demos ausreichend; bei Bedarf
`workflow_dispatch`-Trigger auf den Cron via SSH.

## Architektur-Skizze

```
                       Cloudflare Edge
                       (klickdummy.iil.pet)
                              │
                              ▼ Tunnel: bf-staging (ADR-198)
                              │
                       ┌──────┴───────────┐
                       │  178.104.184.168 │
                       │  staging-platform│
                       └──────┬───────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │   Traefik    │  ADR-212
                       │   :80/:443   │
                       └──────┬───────┘
              traefik_public  │
                              │
                       ┌──────▼──────────┐
                       │   nginx         │
                       │   (klickdummy)  │
                       └──────┬──────────┘
                              │ Volume-Mount
                       ┌──────▼──────────┐
                       │ /srv/klickdummy/│
                       │  meiki-lra/     │
                       │    meiki-hub/   │
                       │      fristen.../│
                       │      modul/     │
                       │  bahn-sqf/      │
                       │    sqf-hub/...  │
                       │    pg-hub/...   │
                       │  ttz-lif/       │
                       │    ttz-hub/...  │
                       └─────────────────┘
                              ▲
                              │ rsync von Git-Repos via Cron
                       ┌──────┴──────────┐
                       │ /opt/klickdummy/│
                       │    sync.sh      │   ← Pull-Job, deploy-key auth
                       │    repos.yaml   │   ← Repo-Liste
                       └─────────────────┘
```

## Konkret deploybar (Compose-Snippet)

`infra/klickdummy-host/docker-compose.yml`:

```yaml
services:
  klickdummy:
    image: nginx:alpine
    container_name: klickdummy
    restart: always
    volumes:
      - /srv/klickdummy:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - traefik_public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.klickdummy.rule=Host(`klickdummy.iil.pet`)"
      - "traefik.http.routers.klickdummy.entrypoints=websecure"
      - "traefik.http.routers.klickdummy.tls.certresolver=letsencrypt"
      - "traefik.http.services.klickdummy.loadbalancer.server.port=80"

networks:
  traefik_public:
    external: true
```

`infra/klickdummy-host/nginx.conf`:

```nginx
server {
  listen 80 default_server;
  server_name klickdummy.iil.pet;
  root /usr/share/nginx/html;
  index index.html;

  # CORS-Headers für Cross-Repo-Picker-Fetch zu orchestrator.iil.pet
  # (nicht zwingend, der Picker fetcht ja den orchestrator, nicht uns)
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-Frame-Options "SAMEORIGIN" always;

  # Auto-Index der org/repo/klickdummy-Verzeichnisse
  location / { autoindex on; autoindex_exact_size off; autoindex_localtime on; }
  location ~ \.(html|css|js|json|yaml|svg|png|jpg)$ { try_files $uri =404; }
}
```

`infra/klickdummy-host/sync.sh` (cron-job, `/opt/klickdummy/`):

```bash
#!/bin/bash
# Klickdummy-Pull-Job — täglich oder via systemd-timer
set -euo pipefail

WORK=/var/lib/klickdummy-sync
TARGET=/srv/klickdummy
REPOS=(
  "meiki-lra/meiki-hub:docs/01-architektur/mockups"
  "bahn-sqf/sqf-hub:klickdummy"
  "bahn-sqf/pg-hub:klickdummy"
  "ttz-lif/ttz-hub:klickdummy"
)

for entry in "${REPOS[@]}"; do
  repo="${entry%:*}"
  subdir="${entry#*:}"
  owner="${repo%/*}"
  name="${repo#*/}"

  clone_dir="$WORK/$owner/$name"
  if [ ! -d "$clone_dir" ]; then
    mkdir -p "$WORK/$owner"
    git clone --depth 1 "git@github.com:$repo.git" "$clone_dir"
  else
    git -C "$clone_dir" fetch --depth 1 origin main
    git -C "$clone_dir" reset --hard origin/main
  fi

  target_dir="$TARGET/$owner/$name"
  mkdir -p "$target_dir"
  rsync -av --delete "$clone_dir/$subdir/" "$target_dir/"
done

# Landing-Page generieren
python3 /opt/klickdummy/generate_landing.py > "$TARGET/index.html"
```

`infra/klickdummy-host/generate_landing.py` — generiert
`klickdummy.iil.pet/index.html` mit Auto-Discovery aller `<org>/<repo>/<kd>/shell.html`-
oder `chat-simulator.html`-Pfade. Verlinkt zu jedem direkt.

## I1–I4 Konsequenzen

### I2 Prod-Sicherheit — wichtig

Klickdummies bleiben `class: mock`. **Aber:** `klickdummy.iil.pet` ist eine
**öffentlich-erreichbare URL**. Das ist **kein I2-Verstoß**, weil:

- Klickdummies sind self-contained Mock-Renderer, kein Code-Pfad in eine
  Produktiv-App (siehe `class: mock` Definition: separater Wegwerf-Code-Pfad)
- `klickdummy_prod_guard.sh` (`platform:ADR-211` I2-Probe) prüft `mock`
  als **N/A** — Klickdummies dürfen public sein
- DSFA-Klärung 2026-05-21 (User): nicht kritisch (nur Funktionsrollen-Namen
  öffentlich, synthetische Operativ-Daten)

### I3 Off-Ramp — Phase A bleibt

Klickdummies sind weiterhin Phase A. Hosting auf `iil.pet` ändert nicht den
Phase-Status — es macht Phase A nur **demonstrationsfähig** für Stakeholder.

### I4 Namensraum — kein Eingriff

URL-Pattern `<org>/<repo>/<klickdummy>` ist mit `repo:ADR-NNN`-Konvention
konsistent (gleicher Diskriminator).

## DSGVO

DSFA-Klärung 2026-05-21 (User):

- Klickdummies enthalten ausschließlich Funktionsrollen-Bezeichnungen
  (Persona-Labels) und synthetische Operativ-Daten
- Echte Personendaten kommen erst in Phase B/C (in den jeweiligen Off-Ramp-
  Zielsystemen, nicht im Klickdummy selbst)
- **Klassifikation: nicht kritisch**

Public-Hosting auf `klickdummy.iil.pet` ist DSGVO-konform.

## Stakeholder-Compliance-Zustimmung (2026-05-21, Iter. 25)

User-Update: Konzern-Compliance-Klärung **erteilt** für alle relevanten
Klickdummy-Repos:

| Klickdummy | Stakeholder | Status |
|---|---|---|
| `bahn-sqf/sqf-hub` (AF1 Lost Units) | Raphael Bayer | ✅ zugestimmt |
| `bahn-sqf/pg-hub` (Pocket Governance) | Ilja Lerch + Grinninger (Stab) | ✅ zugestimmt |
| `meiki-lra/meiki-hub` (Fristen + Modul) | LRA | ✅ zugestimmt |
| `ttz-lif/ttz-hub` (Werkleitung + Schicht) | LRA-TTZ | ✅ zugestimmt |

## Authentifizierung (User-Anforderung Iter. 25)

User-Updates 2026-05-21:

> „Anforderung: https://klickdummy.iil.pet/<owner>/<repo>/ mit login
>  (1 login für alle repos für den anfang) später owner-login..?"
>
> ergänzt: „authenticate SSO?"

**Antwort: ja, SSO via Authentik** (`platform:ADR-142` etabliert
Authentik als Plattform-IdP). Sauberer als BasicAuth, skaliert direkt
zu Phase 2 (Owner-Login via Authentik-Gruppen-Mapping).

### Phase 1 (heute, deploy-fertig): Authentik-OIDC + Traefik forwardAuth

```
Browser → Cloudflare → Traefik → forwardAuth → Authentik (/application/o/...)
                                       ↓ (Session-OK)
                                     nginx
```

**Konkret:**

1. **Authentik OAuth2-Provider** anlegen (analog `risk-hub-staging`,
   siehe `platform/scripts/authentik-staging-oidc.sh` — Pattern aus
   ADR-142):
   ```bash
   scripts/authentik-staging-oidc.sh \
     --app-slug klickdummy \
     --redirect-uri https://klickdummy.iil.pet/outpost.goauthentik.io/callback?X-authentik-auth-callback=true \
     --scopes openid,profile,email
   ```

2. **Authentik-Outpost (forwardAuth-Endpoint)** deployen — eine
   leichtgewichtige Sidecar-Instanz, die `/outpost.goauthentik.io/auth/traefik`
   bereitstellt.

3. **Traefik-Middleware** `klickdummy-sso`:
   ```yaml
   labels:
     - "traefik.http.middlewares.klickdummy-sso.forwardauth.address=http://authentik-outpost:9000/outpost.goauthentik.io/auth/traefik"
     - "traefik.http.middlewares.klickdummy-sso.forwardauth.trustForwardHeader=true"
     - "traefik.http.middlewares.klickdummy-sso.forwardauth.authResponseHeaders=X-authentik-username,X-authentik-groups,X-authentik-email"
     - "traefik.http.routers.klickdummy.middlewares=klickdummy-sso,klickdummy-headers"
   ```

4. **User-Konten in Authentik** anlegen — Phase 1: alle Stakeholder in
   einer Gruppe `klickdummy-viewers` (kein Owner-Routing):
   - `raphael.bayer@db.de` → Gruppe `klickdummy-viewers`
   - `ilja.lerch@bahn-sqf` → `klickdummy-viewers`
   - `grinninger@bahn-sqf` → `klickdummy-viewers`
   - `lra-pilot@meiki-lra` → `klickdummy-viewers`
   - `ttz-pilot@ttz-lif` → `klickdummy-viewers`

### Phase 2 (Folge-Iteration): Owner-spezifischer Login via Authentik-Gruppen

Pro Org eine Gruppe; Traefik-Middleware-Chain hängt vom Pfad ab:

```yaml
# Pseudo: pro Owner eine eigene Router-Rule + Gruppen-Check
traefik.http.routers.klickdummy-sqf.rule=Host(`klickdummy.iil.pet`) && PathPrefix(`/bahn-sqf/`)
traefik.http.routers.klickdummy-sqf.middlewares=klickdummy-sso,klickdummy-sqf-group-check
# klickdummy-sqf-group-check: forwardAuth mit Gruppen-Filter ?required_group=sqf-viewers
```

**Authentik-Gruppen:**
- `klickdummy-sqf-viewers` → Zugriff auf `/bahn-sqf/*`
- `klickdummy-pg-viewers` → Zugriff auf `/bahn-sqf/pg-hub/` (Sperrvermerk-aware)
- `klickdummy-ttz-viewers` → `/ttz-lif/*`
- `klickdummy-meiki-viewers` → `/meiki-lra/*`
- `klickdummy-admin` → alle Pfade

Phase 2 ist eine separate ADR (ADR-217 oder Erweiterung dieser ADR) und
folgt nach Phase-1-Pilot.

### Warum SSO statt BasicAuth

| Punkt | BasicAuth | SSO (Authentik) |
|---|---|---|
| Setup | 10 Min (htpasswd) | 30–60 Min (OIDC-App + Outpost) |
| User-Mgmt | manuell pro Passwort | Web-UI in Authentik |
| Audit-Log | Traefik-Access-Log only | Authentik Event-Log + Traefik |
| Logout | nicht möglich (Browser-Cache) | Authentik /logout |
| Owner-spezifisch | nicht skalierbar | Phase-2-fähig via Gruppen |
| Bestehende Plattform | nein | ja (ADR-142 Authentik etabliert) |
| User-Erfahrung | unschön (Browser-Native-Dialog) | sauberer Login-Screen |

User-Erlaubnis „alles unter meiner Kontrolle" ist erfüllt — Authentik
ist self-hosted Teil der Plattform.

### Warum trotz Stakeholder-Compliance-Zustimmung

User-Compliance-Zustimmung erlaubt **Public-Hosting**. SSO ist
**zusätzlicher Schutz**:

- Verhindert Crawling / Indexing durch Suchmaschinen
- Verhindert versehentliches Teilen der URL
- Schafft Audit-Spur (welcher User wann auf welchen KD)
- Sauberer für künftig sensiblere Klickdummies in Phase B/C ohne
  Architektur-Wechsel
- Phase-2-Owner-Login ist direkter Folgeschritt — keine Re-Architektur

## Trotz Compliance-Zustimmung: warum Login

User-Compliance-Zustimmung der 4 Stakeholder (siehe oben) erlaubt
**Public-Hosting**. Login ist **zusätzlicher Schutz**:

- Verhindert Crawling / Indexing der Pre-Pilot-Demos durch Suchmaschinen
- Verhindert versehentliches Teilen der URL (jeder braucht das Passwort)
- Schafft Audit-Spur via Traefik Access-Log (welcher User wann auf welchen KD)
- Sauberer für künftig sensiblere Klickdummies in Phase B/C ohne Architektur-Wechsel

## Konsequenzen

### Positiv

- **Volle Kontrolle**: keine Drittanbieter-Pages, keine Plan-Upgrades, keine Tokens auf GitHub
- **Stabile URL-Pattern**: `klickdummy.iil.pet/<org>/<repo>/<kd>/` bleibt über Repo-Visibility-Änderungen stabil
- **Auth-fähig** in Phase 2 (Traefik forwardAuth)
- **Cross-Repo-Picker Discovery-Test-fertig**: CORS-Whitelist für `klickdummy.iil.pet` in Orchestrator-Issue #62 vorgesehen
- **Konsolidiert mit ADR-212**: dieselbe Traefik-Instanz, kein zusätzlicher Ingress

### Negativ

- **Server-Maintenance**: nginx + cron + sync-script-Pflege. Mitigation: simpel, standardisiert, kein zustandsbehaftetes Backend
- **Pull-Latenz** bis zu 24h (oder beliebig kürzer per cron-Frequenz)
- **SSH-Deploy-Key-Verwaltung**: pro Repo ein Deploy-Key oder ein globaler User-Key. Mitigation: read-only Keys, eine Cluster-Identität

### Neutral

- **klickdummy.iil.pet ist ein neuer Hostname** — separater Cloudflare-DNS-Record nötig (Wildcard `*.iil.pet` deckt das ggf. schon)

## Phase-Bauauftrag

### Phase 1 (heute, ADR-216 Initial)

1. ✅ ADR-216 schreiben (diese ADR)
2. ⏳ `infra/klickdummy-host/`-Verzeichnis mit Compose + nginx-conf + sync.sh + repos.yaml
3. ⏳ DNS-Record `klickdummy.iil.pet` → Cloudflare Tunnel `bf-staging`
4. ⏳ Deployment-Test: `docker compose up -d` + ersten Klickdummy-Aufruf
5. ⏳ Cross-Repo-Picker (meiki-hub PR #38) testet die URL als alternative `path_rel`-Quelle

### Phase 2 (optional, nach Stakeholder-Review)

6. Auth via Traefik forwardAuth (für pg-hub Sperrvermerk-Compliance)
7. Webhook-Trigger statt Cron (post-merge in jedem Klickdummy-Repo)
8. Sub-Domains pro Org (`sqf.klickdummy.iil.pet`, `meiki.klickdummy.iil.pet`)

## Alternativen

1. **GitHub Pages mit Plan-Upgrade** ($16+/Monat) — verworfen, nicht „unter eigener Kontrolle"
2. **Cloudflare Pages** — verworfen, externer Anbieter
3. **Repos public stellen** — verworfen, Compliance-Risiko pro Repo (Sperrvermerk pg-hub, Gov ttz/meiki)
4. **Push-Mode (CI rsync)** — verworfen, Token-Spread-Risiko (vgl. Drift-Memory)

## Provenance

- meiki-hub-Session 2026-05-21 Iter. 24: GitHub Pages für alle 4 Repos
  blockiert (Free-Plan + privat)
- User-Entscheidung Iter. 25: D — iil.pet self-hosted
- Drift-Memories: `pat-in-remote-url-leak`, `github-pages-private-repo-plan`
- Schwester-ADRs: 198 (Tunnel), 210 (3-Stufen), 212 (Traefik), 215 (Discovery)
