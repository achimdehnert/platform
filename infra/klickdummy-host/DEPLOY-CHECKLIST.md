# Deploy-Checkliste — `staging-klickdummy.iil.pet`

ADR-216 · One-Shot-Deploy + manuelle Schritte. Ziel: **~30 Min** end-to-end.

## Voraussetzungen (auf `staging-platform`)

- [ ] Sudo-Zugriff
- [ ] Docker + docker-compose v2 installiert
- [ ] Traefik läuft mit Network `traefik_public` (ADR-212)
- [ ] Authentik läuft, `authentik-outpost`-Container im `traefik_public`-Netz (ADR-142)
- [ ] DNS-Record für `staging-klickdummy.iil.pet` vorhanden ODER Wildcard `*.iil.pet` über `bf-staging`-Tunnel (ADR-198)

## Schritt 1 — Bundle auf Server kopieren (~ 2 Min)

Von einem Rechner mit Repo-Zugriff:

```bash
ssh staging-platform "mkdir -p /tmp/klickdummy-host-bundle"
scp infra/klickdummy-host/{deploy.sh,docker-compose.yml,nginx.conf,sync.sh,repos.yaml,generate_landing.py} \
    staging-platform:/tmp/klickdummy-host-bundle/
```

## Schritt 2 — One-Shot-Deploy ausführen (~ 3 Min)

```bash
ssh staging-platform "sudo bash /tmp/klickdummy-host-bundle/deploy.sh"
```

Skript ist idempotent. Ende der Ausgabe zeigt den **Public-Key** für die Deploy-Keys.

## Schritt 3 — Deploy-Key zu 4 Repos hinzufügen (~ 5 Min)

Public-Key aus Schritt 2 zu jedem Repo als **Deploy-Key (read-only!)**.

### Web-UI

- <https://github.com/bahn-sqf/sqf-hub/settings/keys/new>
- <https://github.com/bahn-sqf/pg-hub/settings/keys/new>
- <https://github.com/meiki-lra/meiki-hub/settings/keys/new>
- <https://github.com/ttz-lif/ttz-hub/settings/keys/new>

Titel jeweils: `klickdummy-sync staging-platform`. **"Allow write access" NICHT aktivieren.**

### Alternative: `gh`-CLI (lokal)

```bash
# Public-Key vom Server holen
PUBKEY=$(ssh staging-platform "sudo cat /var/lib/klickdummy-sync/.ssh/klickdummy-deploy_ed25519.pub")
echo "$PUBKEY" > /tmp/klickdummy-deploy.pub

for repo in bahn-sqf/sqf-hub bahn-sqf/pg-hub meiki-lra/meiki-hub ttz-lif/ttz-hub; do
  gh repo deploy-key add /tmp/klickdummy-deploy.pub \
    --repo "$repo" \
    --title "klickdummy-sync staging-platform"
done
```

## Schritt 4 — Sync nach Deploy-Key-Add erneut testen (~ 1 Min)

```bash
ssh staging-platform "sudo -u klickdummy-sync /opt/klickdummy/sync.sh"
```

Erfolgsbild: alle 4 Repos gepullt, Symlinks in `/srv/klickdummy/<owner>/<repo>`, `_index.json` generiert.

## Schritt 5 — Authentik OAuth-App (~ 5 Min)

### Via Skript (empfohlen)

```bash
# Auf einem Rechner mit Authentik-API-Zugriff + AK_TOKEN ENV
cd ~/github/platform
./scripts/authentik-staging-oidc.sh \
  --app-slug klickdummy \
  --redirect-uri 'https://staging-klickdummy.iil.pet/outpost.goauthentik.io/callback?X-authentik-auth-callback=true' \
  --scopes 'openid profile email'
```

### Via Web-UI (Fallback)

1. Authentik-Admin → **Applications → Create**
   - Name: `Klickdummy Demo`
   - Slug: `klickdummy`
   - Provider: → **Create Provider**
     - Type: OAuth2/OpenID Provider
     - Name: `klickdummy-oauth`
     - Client type: Confidential
     - Redirect URIs: `https://staging-klickdummy.iil.pet/outpost.goauthentik.io/callback?X-authentik-auth-callback=true`
     - Scopes: openid, profile, email
2. **Outpost → Edit "embedded-outpost"** → Application `klickdummy` hinzufügen

## Schritt 6 — Authentik-Gruppe + User (~ 5 Min)

Authentik-Admin → **Directory → Groups → Create**:

- Name: `klickdummy-viewers`
- Members: jeweils einen User pro Stakeholder anlegen + zuweisen:

| User | Stakeholder |
|---|---|
| `raphael.bayer@db.de` | sqf-hub (Lost Units) |
| `ilja.lerch@bahn-sqf` | pg-hub (Pocket Governance Citizen-Dev) |
| `grinninger@bahn-sqf` | pg-hub (Stab) |
| `lra-meiki@meiki-lra` | meiki-hub (LRA-Pilot) |
| `ttz-pilot@ttz-lif` | ttz-hub (TTZ-Pilot) |
| Dein eigener User | Admin/Test |

Bei User-Anlage: **Set initial password + Email send invitation link**.

### Application-Binding

**Applications → klickdummy → Bindings → Create**:
- Policy: User-in-Group → `klickdummy-viewers`
- Order: 10

## Schritt 7 — End-to-End-Test (~ 2 Min)

```bash
# Health (ohne SSO)
curl -s https://staging-klickdummy.iil.pet/healthz
# Expected: ok

# Discovery (ohne SSO via /api/list, da public — oder mit SSO falls protected)
curl -s https://staging-klickdummy.iil.pet/api/list | head -20

# Klickdummy via Browser (mit SSO-Login)
open https://staging-klickdummy.iil.pet/
```

Erfolgsbild: Authentik-Login-Screen → nach Login → Landing-Page mit 4 Klickdummies → Klick → AF1-Chat-Simulator läuft.

## Schritt 8 — Stakeholder-URLs versenden

| Stakeholder | URL |
|---|---|
| Raphael Bayer | https://staging-klickdummy.iil.pet/bahn-sqf/sqf-hub/af1-tages-zusammenfassung/chat-simulator.html |
| Ilja Lerch + Grinninger | https://staging-klickdummy.iil.pet/bahn-sqf/pg-hub/pocket-governance/shell.html |
| LRA-Meiki | https://staging-klickdummy.iil.pet/meiki-lra/meiki-hub/fristenmanagement-klickdummy/shell.html |
| TTZ-Pilot | https://staging-klickdummy.iil.pet/ttz-lif/ttz-hub/werkleiter-skizze/shell.html |

Alle URLs sind hinter SSO-Login geschützt. User bekommt Authentik-Login-Screen.

## Troubleshooting

### `traefik_public`-Network fehlt

```bash
docker network create traefik_public
# Dann Traefik-Compose mit traefik_public-Label neu starten
```

### Sync schlägt mit `Permission denied (publickey)` fehl

Deploy-Key noch nicht zu allen 4 Repos hinzugefügt → Schritt 3 wiederholen.

### `authentik-outpost`-Container fehlt

Authentik-Setup unvollständig — siehe ADR-142 + `platform/scripts/authentik-staging-oidc.sh`.

### `staging-klickdummy.iil.pet` resolved nicht

DNS-Record fehlt oder Cloudflare-Tunnel hat den Hostname noch nicht. Im `infra/cloudflared-tunnels.yaml` ergänzen oder Wildcard `*.iil.pet` aktivieren.

### `_index.json` ist leer

Sync-Job hat noch nicht gelaufen oder ist gescheitert:

```bash
ssh staging-platform "sudo -u klickdummy-sync /opt/klickdummy/sync.sh"
ssh staging-platform "sudo tail -50 /var/log/klickdummy-sync.log"
```

### Klickdummy zeigt nicht alle 4 Repos

`repos.yaml`-Eintrag fehlt — ergänzen, dann Sync.

## Roll-Back

```bash
ssh staging-platform "cd /opt/klickdummy && sudo docker compose down -v"
ssh staging-platform "sudo rm -f /etc/cron.d/klickdummy-sync /etc/logrotate.d/klickdummy-sync"
ssh staging-platform "sudo rm -rf /opt/klickdummy /srv/klickdummy /var/lib/klickdummy-sync"
ssh staging-platform "sudo userdel klickdummy-sync"
```

DNS-Record + Authentik-App bleiben — separat entfernen falls gewünscht.

## Refs

- ADR-216 (Hosting): `docs/adr/ADR-216-klickdummy-hosting-iil-pet.md`
- ADR-217 (Owner-Auth Phase 2): `docs/adr/ADR-217-klickdummy-owner-spezifische-auth.md`
- ADR-142 (Authentik IdP): `docs/adr/ADR-142-unified-identity-authentik-platform-idp.md`
- ADR-212 (Traefik): `docs/adr/ADR-212-traefik-ingress-staging-iil-pet.md`
- ADR-198 (Cloudflare-Tunnel): `docs/adr/ADR-198-...md`
