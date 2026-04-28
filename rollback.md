---
description: Schneller Rollback eines fehlgeschlagenen Deployments auf Hetzner
---

# /rollback

> Einsatz: Deploy schlägt fehl, Health-Check rot, Prod broken.
> Ziel: Vorherige funktionierende Version in < 5 Minuten wieder online.
> Kein Full-Deploy-Prozess — minimale, sichere Schritte.

---

## Schritt 1: Lage klären (30 Sekunden)

```bash
REPO=REPO_NAME   # ← setzen
PORT=PORT        # ← setzen

# Prod-Status
curl -sf "https://${REPO}.iil.pet/livez/" && echo "✅ livez OK" || echo "❌ livez FAIL"
curl -sf "https://${REPO}.iil.pet/healthz/" && echo "✅ healthz OK" || echo "❌ healthz FAIL"

# Container-Status auf Server
ssh root@88.198.191.108 "docker ps --filter name=${REPO} --format '{{.Names}}\t{{.Status}}\t{{.Image}}'"
```

---

## Schritt 2: Letztes funktionierendes Image identifizieren

```bash
# Letzten 5 Images in GitHub Registry
TOKEN=$(cat ~/.secrets/github_PAT)
curl -s -H "Authorization: token ${TOKEN}" \
  "https://api.github.com/orgs/achimdehnert/packages/container/${REPO}-web/versions?per_page=5" \
  | python3 -c "
import json, sys
for v in json.load(sys.stdin):
    tags = v.get('metadata', {}).get('container', {}).get('tags', [])
    print(v['id'], v['updated_at'][:10], tags)
"
```

→ Letzten **vor** dem fehlgeschlagenen Commit wählen.

---

## Schritt 3: Rollback ausführen

### Option A — Image-Tag zurücksetzen (bevorzugt)

```bash
ROLLBACK_TAG=<SHA-aus-Schritt-2>

ssh root@88.198.191.108 << EOF
cd /opt/${REPO}

# Aktuellen Tag sichern
echo "Aktueller Tag: \$(grep 'IMAGE_TAG' .env.prod || echo 'latest')"

# Rollback-Tag setzen
sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=${ROLLBACK_TAG}/" .env.prod || \
  echo "IMAGE_TAG=${ROLLBACK_TAG}" >> .env.prod

# Container neu starten mit altem Image
docker compose -f docker-compose.prod.yml pull web
docker stop ${REPO}-web-1 && docker rm ${REPO}-web-1
docker compose -f docker-compose.prod.yml up -d web

# Health-Check
sleep 15
docker inspect ${REPO}-web-1 --format '{{.State.Health.Status}}'
EOF
```

### Option B — Letzten guten Git-Stand deployen (wenn kein altes Image verfügbar)

```bash
# Letzten guten Commit auf Main finden
git log --oneline -10 origin/main

# Auf letzten guten Commit zurücksetzen und pushen
git revert HEAD --no-edit
git push
# → CI baut + deployt automatisch
```

---

## Schritt 4: Verifikation

```bash
sleep 30
curl -sf "https://${REPO}.iil.pet/livez/" && echo "✅ ROLLBACK ERFOLGREICH" || echo "❌ NOCH KAPUTT"
curl -sf "https://${REPO}.iil.pet/healthz/" | python3 -m json.tool
```

---

## Schritt 5: Post-Mortem dokumentieren

```bash
# GitHub Issue erstellen
mcp0_create_issue(
  owner: "achimdehnert", repo: "${REPO}",
  title: "[incident] Rollback $(date +%Y-%m-%d) — <Grund>",
  body: "## Incident Report\n\n**Zeitpunkt:** $(date)\n**Dauer:** ?\n**Ursache:** \n**Fix:** Rollback auf <SHA>\n**Prävention:** ",
  labels: ["incident", "post-mortem"]
)
```

---

## Häufige Rollback-Ursachen

| Symptom | Wahrscheinliche Ursache | Schritt |
|---------|------------------------|---------|
| `livez` 200, `healthz` 500 | DB-Migration fehlgeschlagen | Option A + Migration manuell rückgängig |
| Container startet nicht | Fehlende Env-Variable | `.env.prod` prüfen |
| 502 Bad Gateway | Nginx-Config falsch | `nginx -t` auf Server |
| Import Error in Logs | Fehlendes Package in requirements.txt | Option B |

---

## Uptime-Monitoring (Einrichten — einmalig)

Externer Monitor für alle `/livez/` Endpoints — 0 Code nötig:

1. **Betterstack** (kostenlos bis 50 Monitore): https://betterstack.com/
2. Monitor pro Repo anlegen: `https://{repo}.iil.pet/livez/`
3. Alert: E-Mail/Slack bei Downtime > 2 Minuten
4. Status-Page: automatisch generiert

→ **Sinnvoll — 10 Minuten Setup, kein Code, sofortiger Mehrwert.**
