# Review-Report: ADR-120 — Unified Multi-Repo Deployment Pipeline

**Reviewer:** Cascade (IT-Architekt · Senior Developer · Security-Experte)  
**Datum:** 2026-03-11  
**Dokument:** ADR-120-unified-deployment-pipeline.md v1.0  
**Scope:** ADR-Struktur · GitHub Actions Workflow · deploy.sh · Security · Platform-Invarianten

---

## 🔴 BLOCK — Muss vor Implementierung gefixt werden

---

### [BLOCK-1] Doppelter `push`-Key im Caller-Template — Staging-Deploy funktioniert NIE

**Datei:** Caller-Template (`.github/workflows/deploy.yml`), `on:`-Block  
**Problem:** YAML erlaubt keine doppelten Keys. Beide `push:`-Einträge sind ungültig — nur der **letzte** gewinnt (tags). Der `branches: ["main"]`-Trigger wird **stillschweigend ignoriert**. Staging wird nie automatisch deployt.

```yaml
# ❌ FALSCH — doppelter push-Key, branches wird ignoriert
on:
  push:
    branches: ["main"]
  push:                   # ← überschreibt das obige!
    tags: ["v*.*.*"]
```

```yaml
# ✅ KORREKT — beide Trigger in einem push-Block
on:
  push:
    branches: ["main"]
    tags: ["v*.*.*"]
  workflow_dispatch:
    inputs:
      image_tag_override:
        description: "Rollback auf Image-Tag (z.B. v1.2.1)"
        required: false
        default: ""
```

**Referenz:** YAML Spec 1.2 §3.2.1 — doppelte Mapping-Keys; GitHub Actions Doku  
**Auswirkung:** Staging-Gate funktioniert komplett nicht — Core-Feature der ADR.

---

### [BLOCK-2] `STAGING_*` Secrets als `required: true` — Production-only Deploys schlagen fehl

**Datei:** `_deploy-unified.yml`, `secrets:`-Block  
**Problem:** Alle drei Staging-Secrets sind `required: true`. Ein `git tag v1.2.3`-Deploy (pure Production) triggert den `deploy-staging`-Job nicht — aber GitHub Actions **validiert required secrets beim Workflow-Start**, nicht pro Job. Jedes Repo das keine Staging-Secrets hat, kann nie nach Production deployen.

```yaml
# ❌ FALSCH
secrets:
  STAGING_SSH_KEY:
    required: true   # ← Bricht alle Production-only Deploys
  STAGING_HOST:
    required: true
  STAGING_USER:
    required: true
```

```yaml
# ✅ KORREKT
secrets:
  STAGING_SSH_KEY:
    required: false  # Optional — nicht alle Repos brauchen Staging
  STAGING_HOST:
    required: false
  STAGING_USER:
    required: false
  PROD_SSH_KEY:
    required: true   # Production bleibt required
  PROD_HOST:
    required: true
  PROD_USER:
    required: true
```

**Referenz:** GitHub Actions Docs — Reusable Workflows, Required Secrets Validation  
**Auswirkung:** Alle 20+ Repos müssen Staging-Secrets haben, sonst kein Prod-Deploy möglich.

---

### [BLOCK-3] `appleboy/ssh-action` deaktiviert `StrictHostKeyChecking` — MITM-Angriffsfläche

**Datei:** `_deploy-unified.yml`, Jobs `deploy-staging` und `deploy-production`  
**Problem:** `appleboy/ssh-action@v1.0.3` setzt intern `StrictHostKeyChecking=no` als Default. Das ist im Reviewer-Prompt explizit als **verbotenes Pattern** gelistet. Ein Angreifer mit Kontrolle über DNS oder das Netzwerk zwischen GitHub Actions Runner und Hetzner-Server kann einen MITM-Angriff durchführen und beliebige Befehle auf dem Server ausführen.

```yaml
# ❌ UNSICHER — kein Host-Key-Fingerprint
- uses: appleboy/ssh-action@v1.0.3
  with:
    host: ${{ secrets.PROD_HOST }}
    username: ${{ secrets.PROD_USER }}
    key: ${{ secrets.PROD_SSH_KEY }}
    script: ...
```

```yaml
# ✅ SICHER — Host-Key-Fingerprint explizit setzen
- uses: appleboy/ssh-action@v1.0.3
  with:
    host: ${{ secrets.PROD_HOST }}
    username: ${{ secrets.PROD_USER }}
    key: ${{ secrets.PROD_SSH_KEY }}
    fingerprint: ${{ secrets.PROD_SSH_FINGERPRINT }}  # ← SHA256 Host-Key
    script: ...
```

**Host-Key-Fingerprint ermitteln:**
```bash
ssh-keyscan 88.198.191.108 | ssh-keygen -lf - -E sha256
# → SHA256:XXXX...  Fingerprint als Secret PROD_SSH_FINGERPRINT speichern
```

**Referenz:** Reviewer-Prompt: `StrictHostKeyChecking=no in SSH-Configs` → BLOCK  
**Auswirkung:** Kritische Security-Schwachstelle in der Deployment-Pipeline.

---

### [BLOCK-4] `COMPOSE_PROJECT_NAME` fehlt in `deploy.sh` — Container-Namenskonflikte auf dev-server

**Datei:** `deploy.sh`, Deploy-Abschnitt  
**Problem:** Das ADR beschreibt korrekt `COMPOSE_PROJECT_NAME=staging-<app>` als Notwendigkeit, aber das deploy.sh-Script setzt diese Variable nicht. Auf dem dev-server laufen DEV-Instanzen und Staging-Instanzen nebeneinander. Ohne `COMPOSE_PROJECT_NAME` überschreibt ein Staging-Deploy den laufenden DEV-Container.

```bash
# ❌ FEHLT — Docker Compose nutzt Directory-Namen als Projekt
cd "$APP_PATH"
docker compose pull
docker compose up -d --force-recreate --remove-orphans
```

```bash
# ✅ KORREKT
cd "$APP_PATH"

# Staging bekommt eigenes Compose-Projekt
if [[ "$ENVIRONMENT" == "staging" ]]; then
  export COMPOSE_PROJECT_NAME="staging-${APP_NAME}"
fi

docker compose pull
docker compose up -d --force-recreate --remove-orphans
```

**Referenz:** ADR-120 Decision — Staging-Port-Schema, `COMPOSE_PROJECT_NAME`-Anforderung  
**Auswirkung:** Staging-Deploy killt DEV-Container auf dev-server bei identischen App-Namen.

---

### [BLOCK-5] `docker compose` ohne `-f`-Flag — `docker-compose.prod.yml` wird ignoriert

**Datei:** `deploy.sh`, Deploy-Abschnitt  
**Problem:** Das deploy.sh ruft `docker compose pull/up` ohne explizites `-f`-Flag. Docker Compose sucht automatisch nach `docker-compose.yml`, **nicht** nach `docker-compose.prod.yml`. ADR-022 schreibt `docker-compose.prod.yml` für Production vor (mit Memory-Limits, JSON-Logging, separatem migrate-Service). Production deployt damit mit der falschen Compose-Config.

```bash
# ❌ FALSCH — nutzt docker-compose.yml, ignoriert docker-compose.prod.yml
docker compose pull
docker compose up -d --force-recreate --remove-orphans
```

```bash
# ✅ KORREKT — Compose-File nach Umgebung wählen
COMPOSE_FILE="docker-compose.yml"
if [[ "$ENVIRONMENT" == "production" && -f "$APP_PATH/docker-compose.prod.yml" ]]; then
  COMPOSE_FILE="docker-compose.prod.yml"
fi

docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans
```

**Referenz:** ADR-022 — `docker-compose.prod.yml` Pflicht für Production  
**Auswirkung:** Production läuft ohne Memory-Limits und JSON-Logging — ADR-022-Verletzung.

---

### [BLOCK-6] Kein CI-Gate vor Build/Deploy — Invariante 6 verletzt

**Datei:** `_deploy-unified.yml`, Jobs `build`, `deploy-staging`, `deploy-production`  
**Problem:** ADR-120 Invariante 6 lautet explizit: **"Kein Deploy ohne grüne CI (test + lint) — `_ci-python.yml` als Prerequisite"**. Weder der Caller-Template noch der Reusable Workflow enthält einen CI-Job oder ein `needs: [ci]`. Ein direkter Push auf `main` deployt sofort auf Staging — ohne Tests.

```yaml
# ❌ FEHLT — kein CI-Job im Caller-Template
jobs:
  deploy:
    uses: achimdehnert/platform/.github/workflows/_deploy-unified.yml@v1
    # ← Kein CI-Prerequisite
```

```yaml
# ✅ KORREKT — CI als Prerequisite im Caller
jobs:
  ci:
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
    # nur bei push auf main (nicht bei tags — dort wäre CI bereits gelaufen)
    if: github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'

  deploy:
    needs: [ci]   # ← Build nur nach grünem CI
    if: always() && (needs.ci.result == 'success' || needs.ci.result == 'skipped')
    uses: achimdehnert/platform/.github/workflows/_deploy-unified.yml@v1
    with:
      ...
```

**Referenz:** ADR-120 Invariante 6; ADR-009 (Reusable Workflows)  
**Auswirkung:** Defekter Code kann auf Staging landen ohne Test-Gate.

---

### [BLOCK-7] `docker login` Username hardcoded als `deploy` — GHCR-Auth schlägt fehl

**Datei:** `deploy.sh`, GHCR Login-Abschnitt  
**Problem:** GHCR erwartet den **GitHub-Username oder die GitHub-Organisation** als Login-User, nicht den Server-Username `deploy`. Mit `docker login ghcr.io -u deploy` wird die Authentifizierung fehlschlagen (401 Unauthorized), da kein GitHub-Account `deploy` existiert (oder der Token nicht zu diesem User gehört).

```bash
# ❌ FALSCH — Server-Username, nicht GitHub-Username
docker login ghcr.io -u deploy --password-stdin < /opt/scripts/.ghcr_token
```

```bash
# ✅ KORREKT — GitHub-Org/Username aus Token-File oder Konstante
GHCR_USER="achimdehnert"  # GitHub-Username/Org, nicht Server-User
docker login ghcr.io -u "$GHCR_USER" --password-stdin < /opt/scripts/.ghcr_token

# Oder flexibler: Username im Token-File mitspeichern
# /opt/scripts/.ghcr_credentials Format: "username:token"
IFS=: read -r GHCR_USER GHCR_TOKEN < /opt/scripts/.ghcr_credentials
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
```

**Referenz:** GHCR Authentication Docs — Container Registry  
**Auswirkung:** Image-Pull schlägt auf Server fehl → Deploy-Fehler bei allen neuen Tags.

---

## 🟡 SUGGEST — Empfehlung

---

### [SUGGEST-1] `concurrency` Group fehlt — parallele Deploys möglich

**Datei:** `_deploy-unified.yml`  
**Begründung:** Ohne Concurrency-Group können zwei gleichzeitige Pushes auf `main` (z.B. bei schnellen Commits) parallel auf denselben Server deployen. Der zweite Deploy kann den Rollback-State des ersten korrumpieren.

```yaml
# In _deploy-unified.yml auf Workflow-Ebene
concurrency:
  group: deploy-${{ inputs.app_name }}-${{ github.ref }}
  cancel-in-progress: false  # false = laufende Deploys NICHT abbrechen (Datenverlust-Risiko)
```

---

### [SUGGEST-2] `build` Job: explizite `platforms: linux/amd64` setzen

**Datei:** `_deploy-unified.yml`, build-Job  
**Begründung:** Ohne explizite Platform-Angabe baut Buildx für die Runner-Architektur. GitHub Actions nutzt standardmäßig AMD64-Runner, aber bei ARM-Runnern (z.B. self-hosted auf Apple M-Serie) entstehen inkompatible Images für Hetzner (AMD64).

```yaml
- name: Build and push
  uses: docker/build-push-action@v5
  with:
    platforms: linux/amd64   # ← explizit
    context: .
    push: true
    ...
```

---

### [SUGGEST-3] `docker image prune` zu aggressiv — entfernt potenziell Rollback-Images

**Datei:** `deploy.sh`, Cleanup-Abschnitt  
**Begründung:** `docker image prune -f --filter "until=24h"` löscht alle Images die älter als 24h sind — das kann das Rollback-Image (PREVIOUS_TAG) entfernen, wenn es in einer Folge-Deploy-Session benötigt wird. Sicherer: nur dangling (ungetaggte) Images entfernen.

```bash
# ❌ Zu aggressiv — kann Rollback-Images löschen
docker image prune -f --filter "until=24h"

# ✅ Nur dangling Images (keine Tags, nicht referenziert)
docker image prune -f
# Oder: behalte letzten N Images pro App mit custom-Script
```

---

### [SUGGEST-4] `notify` Job: fehlender `if: secrets.DISCORD_WEBHOOK != ''` auf Job-Ebene

**Datei:** `_deploy-unified.yml`, notify-Job  
**Begründung:** Der Job wird immer gestartet (verbraucht Runner-Minuten) und prüft das leere Webhook erst intern mit `exit 0`. Besser: Job direkt überspringen wenn kein Webhook konfiguriert.

```yaml
notify:
  needs: [resolve, deploy-staging, deploy-production]
  if: |
    always() &&
    inputs.notify_discord == true &&
    secrets.DISCORD_WEBHOOK != ''
```

> **Hinweis:** `secrets.DISCORD_WEBHOOK != ''` in `if:`-Expressions ist in Reusable Workflows nicht direkt verfügbar — Workaround über einen Output im `resolve`-Job der prüft ob der Secret gesetzt ist.

---

### [SUGGEST-5] `Review-History` Link ist broken

**Datei:** ADR-120, Abschnitt `Review-History`  
**Begründung:** Der Link `[Bewertung](../adr/reviews/ADR-120-input-bewertung.md)` referenziert eine nicht existierende Datei. Entweder den Link entfernen oder den korrekten Pfad setzen.

---

### [SUGGEST-6] ADR-Referenz-Inkonsistenz: ADR-101 vs. ADR-102 (Cloudflare DNS)

**Datei:** ADR-120, Frontmatter `related:`  
**Begründung:** Im Frontmatter steht `ADR-102 (Cloudflare DNS)`, aber in der Sitzung und in ADR-117 wurde konsequent `ADR-101` als Cloudflare-DNS-ADR referenziert. Eine der Referenzen ist falsch.

```yaml
# Prüfen und korrigieren:
related: ADR-009, ADR-022, ADR-101 (Cloudflare DNS), ADR-103 (bieterpilot)
```

---

## 🔵 QUESTION — Klärungsbedarf

---

### [QUESTION-1] ADR-Nummern-Gap: Was sind ADR-118 und ADR-119?

**Kontext:** Der ADR ist als ADR-120 nummeriert. Im ADR-117-Entwurf (dieser Session) wurde das gleiche Thema als ADR-117 behandelt. Der ADR referenziert `billing-hub` als ADR-118. Gibt es bereits ADR-118 und ADR-119 oder ist die Nummerierung ein Planungsstand?

---

### [QUESTION-2] Wie wird `_ci-python.yml` für Tag-Pushes gehandhabt?

**Kontext:** Bei `git tag v1.2.3` gibt es keinen Branch-Checkout — CI (lint, tests) wäre redundant weil der Code bereits auf `main` getestet wurde. Soll der CI-Job bei Tag-Pushes `if: github.ref_type == 'tag'` explizit geskippt werden, oder wird darauf vertraut dass der Tag nur von main aus erstellt wird?

---

### [QUESTION-3] Staging-Nginx und TLS — Wildcard-Cert oder separate Certs?

**Kontext:** Das ADR erwähnt `staging.<hub>.iil.pet` Domains, aber keine TLS-Strategie für den dev-server. Gibt es bereits ein Wildcard-Cert für `*.iil.pet` auf dem dev-server oder muss Certbot für jede Staging-Domain einzeln laufen?

---

## ⚪ NITS

---

- **[NITS-1]** `appleboy/ssh-action@v1.0.3` — Minor-Version-Pin ist fragil. Besser `@v1` (Major) oder SHA-Pin für maximale Reproduzierbarkeit.
- **[NITS-2]** `curl -sf` im Discord-Notify fehlt `--max-time 10` — Notify-Job kann bei Discord-Timeout hängen.
- **[NITS-3]** `LOG_FILE`-Naming mit `date +%Y%m%d_%H%M%S` — bei zwei simultanen Deploys in derselben Sekunde (unwahrscheinlich aber möglich) entstehen identische Filenames. `$$` (PID) anhängen: `${APP_NAME}_$(date +%Y%m%d_%H%M%S)_$$.log`
- **[NITS-4]** `exec > >(tee -a "$LOG_FILE") 2>&1` im deploy.sh — `tee`-Subshell wird bei `set -e` nicht korrekt terminiert. Besser explizites `tee`-Pipe-Handling oder `script`-Befehl.
- **[NITS-5]** `docker compose ps --format "{{.Status}}"` — das `--format`-Flag für `ps` ist in älteren Docker Compose V2-Versionen nicht verfügbar. Sicherer: `docker compose ps | grep -qi "unhealthy\|exit\|error"`.
- **[NITS-6]** Keine `timeout-minutes:` in Jobs — bei hängendem SSH-Connect kann ein Job unbegrenzt blockieren und Runner-Minuten verbrauchen. Empfohlen: `timeout-minutes: 15`.

---

## 📊 Zusammenfassung

| Kategorie | Anzahl |
|-----------|--------|
| 🔴 BLOCK | 7 |
| 🟡 SUGGEST | 6 |
| 🔵 QUESTION | 3 |
| ⚪ NITS | 6 |

**Gesamturteil:**

❌ **CHANGES REQUESTED** — 7 BLOCK-Items müssen vor Implementierung behoben werden.

### Kritischer Pfad (Prio-Reihenfolge)

| Prio | Block | Auswirkung ohne Fix |
|------|-------|---------------------|
| P0 | BLOCK-1 (doppelter push-Key) | Staging deployt **nie** automatisch |
| P0 | BLOCK-3 (StrictHostKeyChecking) | MITM-Angriffsfläche auf Deployment-Pipeline |
| P1 | BLOCK-2 (required Staging-Secrets) | Production-Deploy für alle Repos ohne Staging-Secrets unmöglich |
| P1 | BLOCK-7 (GHCR Username) | Image-Pull schlägt auf Server fehl |
| P2 | BLOCK-4 (COMPOSE_PROJECT_NAME) | DEV-Container werden auf dev-server überschrieben |
| P2 | BLOCK-5 (Compose-File) | Production ignoriert docker-compose.prod.yml — ADR-022-Verletzung |
| P3 | BLOCK-6 (CI-Gate) | Kein Test-Gate vor Staging — Invariante 6 verletzt |

### Positives

Das ADR ist **strukturell sehr solide**:
- MADR 4.0 Konformität ✅
- Trigger-Strategie (main=Staging, Tag=Prod) ist korrekt konzipiert ✅
- Auto-Rollback via `trap ERR` im deploy.sh ist elegant ✅
- Staging-Port-Schema ist durchdacht ✅
- Cloudflare-Access-Integration ist korrekt geplant ✅
- `set -euo pipefail` konsequent eingesetzt ✅

Die BLOCKs sind größtenteils **Implementierungsdetails** (falsches YAML, fehlende Flags), keine konzeptionellen Fehler. Nach Behebung ist das ADR produktionsreif.

---

*Review-Report ADR-120 v1.0 · IIL Platform · 2026-03-11*
