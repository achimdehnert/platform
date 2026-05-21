---
description: ADR-212 Klausel-3 Traefik-Rollout über Standard-Pattern-Repos (Sonnet-Tier-3). Arbeitet die Worklist ab — pro Repo ein PR-Pair.
---
# /adr-212-rollout — Klausel-3 Traefik-Migration

Arbeitet die Worklist `docs/runbooks/adr-212-rollout-worklist.md` ab. Pro Standard-Repo der Phase Sonnet-1: DNS-Check, Compose-Edit, PR pushen. Am Ende: Tracker-Batch-PR auf platform.

**Dieser Workflow ist explizit Tier-3.** Vor Start: `/model claude-sonnet-4-6`.

---

## Schritt 0 — Worklist laden

```bash
WORKLIST=~/github/platform/docs/runbooks/adr-212-rollout-worklist.md
ls -lh "$WORKLIST" || (echo "❌ Worklist nicht gefunden"; exit 1)
```

Lies die Tabelle „Standard-Repos für Sonnet (Phase Sonnet-1)". Jede `TODO`-Zeile ist ein zu verarbeitendes Repo.

## Schritt 1 — Pro Repo das 5-Schritt-Skript ausführen

Für jedes `TODO`-Repo aus der Worklist (in Tabellen-Reihenfolge):

**a) Pre-Check**
```bash
cd ~/github/<REPO>
git status --short || exit 1
[ -f docker-compose.staging.yml ] || (echo "STOP: kein staging.yml in <REPO>"; continue)
git fetch origin main
```

**b) DNS sicherstellen** (nur falls in der Worklist `MISSING` markiert)
```bash
CF_TOKEN=$(cat ~/shared/inbox/secrets/cloudflare_write_token)
ZONE_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones?name=iil.pet" \
  -H "Authorization: Bearer $CF_TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][0]['id'])")
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"type":"CNAME","name":"staging-<SLUG>","content":"2a517762-d011-4bf8-8405-9bd237b2c4f4.cfargotunnel.com","ttl":1,"proxied":true,"comment":"ADR-212 Klausel-3 — <REPO>"}'
```

**c) Branch + Compose-Edit**
```bash
git checkout -b feat/adr-212-traefik-migration origin/main
```

In `docker-compose.staging.yml`:
1. Header-Kommentar oben einfügen (Domain `staging-<SLUG>.iil.pet`)
2. Im `<SERVICE>:`-Block: `ports: 127.0.0.1:<HOST>:<INTERN>` → `expose: <INTERN>`
3. `traefik_public` ans Network anhängen
4. Labels-Block einfügen (siehe Runbook §Schritt 3)
5. `networks:`-Block am Ende: `traefik_public: external: true`

Exakte Block-Vorlagen: siehe `docs/runbooks/adr-212-rollout-worklist.md` §Schritt 3.

**d) Self-Check vor Commit**
```bash
docker compose -f docker-compose.staging.yml config 2>&1 | grep -v "env file" | head -5
# Bei Fehler: STOP, Repo überspringen
git diff docker-compose.staging.yml
# Erwartung: nur die Drei-Block-Änderung
```

**e) Commit + Push**
```bash
git add docker-compose.staging.yml
git commit -m "feat(staging): ADR-212 Klausel-3 migration to Traefik ingress

- Remove host port binding — Traefik routes now
- Add expose + traefik_public network + traefik.* labels
- Router: <SLUG>-staging, Host \`staging-<SLUG>.iil.pet\`, port <INTERN>

Refs: ADR-212, platform#246"
git push --set-upstream origin feat/adr-212-traefik-migration
```

PR-URL aus dem Output extrahieren (Format: `https://github.com/achimdehnert/<REPO>/pull/new/feat/adr-212-traefik-migration`).

## Schritt 2 — Tracker-Batch-PR auf platform (am Ende)

Nach allen Compose-PRs:

```bash
WT=/tmp/platform-adr212-tracker-batch
git -C ~/github/platform worktree add "$WT" origin/main -b chore/adr-212-tracker-batch
cd "$WT"
```

In `docs/staging-ingress-migration.md` pro erledigtem Repo:
```diff
- | <repo> | `staging-<slug>.iil.pet` | 🔴 todo | — |
+ | <repo> | `staging-<slug>.iil.pet` | 🟡 in-progress | <PR-URL> |
```

```bash
git add docs/staging-ingress-migration.md
git commit -m "chore(adr-212): tracker — phase-1 repos in-progress

PRs gepusht: <repo-1>, <repo-2>, ..."
git push --set-upstream origin chore/adr-212-tracker-batch
git -C ~/github/platform worktree remove "$WT"
```

## Schritt 3 — Output

Pro Repo eine Zeile:
```
✅ <repo>  PR=<URL>  DNS=<status>  Service=<name>  Port=<intern>
⚠️ <repo>  SKIPPED: <grund>
❌ <repo>  ERROR: <details>
```

Plus am Ende der Tracker-PR-URL.

## Stop-Bedingungen

- Pre-Check fehlt (kein `docker-compose.staging.yml`) → STOP für dieses Repo, in Phase 2 vermerken
- Service-Name unklar (mehrere `ports:`-Mappings, kein eindeutiger Web-Container) → STOP
- `docker compose config` failed → STOP, Repo manuell prüfen
- Push failed (Berechtigung, Konflikt) → STOP, Mensch fragen
- Worklist-Repo nicht in `~/github/<repo>/` vorhanden → STOP, klären

Bei STOP für ein Repo: zum nächsten weitergehen, am Ende die Liste der gestoppten Repos ausgeben.

## Nicht in diesem Workflow

- Phase 2 (Repos OHNE `docker-compose.staging.yml`) → eigener Pass nötig
- Phase 3 (Sonderfälle bfagent / travel-beat / mcp-hub / odoo-hub / ttz-hub / risk-hub) → Opus oder Mensch
- Deploy auf staging-platform (`ssh staging-platform && docker compose up -d`) → manueller Cutover nach Merge
- nginx-vhost-Cleanup auf staging-platform → manueller Schritt nach Smoke-Test

## Referenz

- Runbook: `docs/runbooks/adr-212-rollout-worklist.md` (Worklist + Faktentabelle)
- ADR: `docs/adr/ADR-212-traefik-ingress-staging-iil-pet.md`
- Tracker: `docs/staging-ingress-migration.md`
- Pilot-Vorlagen: `cad-hub#feat/adr-212-traefik-migration`, `writing-hub#feat/adr-212-traefik-migration`
