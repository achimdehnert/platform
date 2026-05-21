# ADR-212 Rollout — Sonnet-Worklist (Phase Sonnet-1)

**Stand:** 2026-05-21
**Modell:** Sonnet 4.6 (Tier 3)
**Vorlage:** `cad-hub` PR-Pair (`feat/adr-212-traefik-migration` + `chore/adr-212-tracker-cadhub`)
**Voraussetzung:** Traefik-Stack auf `staging-platform` läuft (platform#246 ✅)

---

## Was Sonnet pro Repo zu tun hat (5-Schritt-Skript)

Für jedes Repo in der **Standard-Liste** unten:

### Schritt 0 — Pre-Check

```bash
cd ~/github/<REPO>
git status --short        # Workdir clean?
git fetch origin main
ls docker-compose.staging.yml    # muss existieren — Phase-1-Filter
```

Wenn `docker-compose.staging.yml` fehlt → **STOP**, in Phase 2 verschieben.

### Schritt 1 — DNS sicherstellen

```bash
CF_TOKEN=$(cat ~/shared/inbox/secrets/cloudflare_write_token)
ZONE_ID=94737a5d3a1a9075a6e3f37b0f48a4c4   # iil.pet zone id (cacheable)

# Prüfen ob CNAME existiert
EXISTS=$(curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?name=staging-<SLUG>.iil.pet" \
  -H "Authorization: Bearer $CF_TOKEN" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('result',[])))")

# Wenn 0 → anlegen
if [ "$EXISTS" = "0" ]; then
  curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" \
    --data '{"type":"CNAME","name":"staging-<SLUG>","content":"2a517762-d011-4bf8-8405-9bd237b2c4f4.cfargotunnel.com","ttl":1,"proxied":true,"comment":"ADR-212 Klausel-3 — <REPO>"}'
fi
```

### Schritt 2 — Feature-Branch im Repo

```bash
git checkout -b feat/adr-212-traefik-migration origin/main
```

### Schritt 3 — `docker-compose.staging.yml` editieren

**Substitutionen pro Repo:**
- `<REPO>` = Repo-Name (z. B. `billing-hub`)
- `<SLUG>` = Traefik-Slug aus Worklist-Tabelle (z. B. `billing`)
- `<SERVICE>` = Web-Container-Service-Name aus Worklist (z. B. `web` oder `billing-hub-staging-web`)
- `<INTERN_PORT>` = Container-interner Port aus Worklist (meist `8000`)

**Drei Block-Edits:**

**(a) Header-Kommentar oben einfügen (vor `services:`):**
```yaml
# <REPO> — Staging Docker Compose
# Domain: staging-<SLUG>.iil.pet (ADR-212 Klausel 3, Traefik-Ingress)
# Routing: Cloudflare bf-staging Tunnel → Traefik (178.104.184.168) → container:<INTERN_PORT>
```

**(b) Im `<SERVICE>:`-Block: `ports:`-Zeile durch `expose:` ersetzen, `traefik_public` ans Network anhängen, Labels-Block hinzufügen:**

```yaml
# ALT:
    ports:
      - "127.0.0.1:<HOST_PORT>:<INTERN_PORT>"
    networks:
      - <repo>_staging_net

# NEU:
    expose:
      - "<INTERN_PORT>"
    networks:
      - <repo>_staging_net
      - traefik_public
    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=traefik_public"
      - "traefik.http.routers.<SLUG>-staging.rule=Host(`staging-<SLUG>.iil.pet`)"
      - "traefik.http.routers.<SLUG>-staging.entrypoints=websecure"
      - "traefik.http.routers.<SLUG>-staging.tls.certresolver=letsencrypt"
      - "traefik.http.services.<SLUG>-staging.loadbalancer.server.port=<INTERN_PORT>"
```

**(c) Unten im `networks:`-Block `traefik_public` als external hinzufügen:**
```yaml
networks:
  <repo>_staging_net:
    driver: bridge
  traefik_public:
    external: true
```

### Schritt 4 — Commit + Push

```bash
git add docker-compose.staging.yml
git commit -m "feat(staging): ADR-212 Klausel-3 migration to Traefik ingress

- Remove host port binding (127.0.0.1:<HOST_PORT>:<INTERN_PORT>) — Traefik routes now
- Add expose: <INTERN_PORT>
- Attach traefik_public external network
- Add traefik.* labels (router=<SLUG>-staging, websecure, letsencrypt)

Refs: ADR-212, platform#246, cad-hub pilot PR"

git push --set-upstream origin feat/adr-212-traefik-migration
```

PR-URL aus dem `git push`-Output extrahieren und in der Worklist-Tabelle notieren.

### Schritt 5 — Self-Check vor Merge

```bash
# Syntax-Check (env-file darf fehlen — ignoriere "env file ... not found")
docker compose -f docker-compose.staging.yml config 2>&1 | grep -v "env file" | head -5

# Diff zur Vorversion zeigen
git diff origin/main..feat/adr-212-traefik-migration -- docker-compose.staging.yml
```

Erwartung: Diff zeigt die Drei-Block-Änderung sauber. Kein anderer Code geändert.

---

## Standard-Repos für Sonnet (Phase Sonnet-1)

| # | Repo | Slug | Service-Name | Port intern | Port Host (alt) | DNS-CNAME | Status |
|---|---|---|---|---|---|---|---|
| 0 | **cad-hub** | cadhub | web | 8000 | 8194 | exists | ✅ PR gepusht (Pilot) |
| 0 | **writing-hub** | writing | writing_hub_staging_web | 8000 | 8098 | exists | ✅ PR gepusht (Pilot 2) |
| 1 | **dev-hub** | devhub | dev-hub-staging-web | 8000 | 19002 | exists | TODO |
| 2 | **billing-hub** | billing | web | 8000 | 8192 | exists | TODO |
| 3 | **coach-hub** | coachhub | coach-hub-staging-web | 8000 | 8017 | **MISSING — anlegen!** | TODO |
| 4 | **pptx-hub** | pptxhub | web | 8000 | 8120 | **MISSING — anlegen!** | TODO |
| 5 | **trading-hub** | tradinghub | trading-hub-staging-web | 8000 | 8188 | **MISSING — anlegen!** | TODO |

**Volumen:** 5 Repos × ~3 min Sonnet-Time = ~15 min für Phase Sonnet-1.

---

## Tracker-Update auf platform (1 PR sammelt alle)

Nach allen 5 Compose-PRs: **ein** platform-PR, der den Migration-Tracker für alle in-progress-Repos aktualisiert.

```bash
cd /tmp && git worktree add platform-tracker-batch ~/github/platform origin/main -b chore/adr-212-tracker-batch
cd platform-tracker-batch
```

Edit `docs/staging-ingress-migration.md` — pro Repo aus Worklist:
```
| <repo> | `staging-<slug>.iil.pet` | 🔴 todo  →  🟡 in-progress | <PR-URL> |
```

```bash
git commit -m "chore(adr-212): tracker — phase-1 repos in-progress (dev-hub, billing-hub, coach-hub, pptx-hub, trading-hub)"
git push --set-upstream origin chore/adr-212-tracker-batch
```

---

## Phase 2 — Repos OHNE `docker-compose.staging.yml`

Diese 7 Repos brauchen **zuerst** ein staging.yml (das ist mehr als ein Compose-Edit, eher ein Setup):

- `research-hub`, `sqf-hub`, `tax-hub`, `137-hub`, `wedding-hub`, `recruiting-hub`, `dms-hub`

Pro Repo: docker-compose.prod.yml als Vorlage kopieren → staging-Werte anpassen (DB, env-file, Container-Namen, Ressourcen) → DANN ADR-212-Labels einbauen. Eigener Pass, Opus-tauglich oder genau dokumentierter Sonnet-Pass mit Repo-spezifischem Briefing.

## Phase 3 — Sonderfälle (Opus / Mensch)

- `bfagent` — Multi-Endpoint (caddy + mcp-api + llm-gateway), mehrere Router-Labels
- `travel-beat` — Caddy als Reverse-Proxy davor, muss entfernt oder umgelabelt werden
- `mcp-hub` — MCP-SSE Streaming, Traefik-Sticky-Sessions/Keepalive prüfen
- `odoo-hub` — schon Traefik, aber **eigener** Traefik (`odoo_hub_proxy`); konvergieren auf zentralen Traefik
- `ttz-hub` — Third-Party-Stack
- `risk-hub` — Klausel 1 (eigene Domain `staging-demo.schutztat.de`), bleibt nginx

## Skipped

- `bahn-hub` — kein Staging-Container im Repo (läuft nativ uvicorn lokal); Klärung mit Stakeholder, ob Staging überhaupt benötigt
- `learn-hub` — nur prod.yml; Klärung Staging-Ambition
- `recruiting-hub` — nur prod.yml (in Phase 2 verschoben, weil staging-Cnam existiert evtl. nicht; prüfen)

---

## Start-Befehl für Sonnet-Session

```
/model claude-sonnet-4-6

# Prompt:
Bearbeite die Repos in ~/github/platform/docs/runbooks/adr-212-rollout-worklist.md, Phase Sonnet-1.
Pro Repo: das 5-Schritt-Skript ausführen, PR pushen.
Nach allen 5 Repos: den Tracker-Batch-PR auf platform erstellen.
Stop nach Fehler. Stop wenn ein Repo nicht Standard-Pattern matched.
Output: pro Repo eine Zeile mit PR-URL + Status.
```

## Stop-Bedingungen (Sonnet)

- **Pre-Check fehlt:** kein `docker-compose.staging.yml` → STOP, Repo in Phase 2
- **Service-Name unklar:** ports:-Binding ist nicht eindeutig einem Service zuordbar → STOP
- **Compose-Syntax-Fehler nach Edit:** `docker compose config` failed → STOP, Repo manuell prüfen
- **Push failed:** Konflikt oder Berechtigung → STOP, Mensch fragen

Bei STOP: aktuelles Repo überspringen, mit nächstem fortfahren, Liste der gestoppten Repos am Ende ausgeben.
