# ADR-098 — Production Infrastructure Tuning Standard
## Platform Architecture Review

| Attribut | Wert |
|----------|------|
| **Reviewer** | Platform Architecture Review |
| **Datum** | 2026-03-04 |
| **Basis** | ADR-022, ADR-021, ADR-046, adr-review-checklist.md v2.0 |
| **Severity** | 🔴 Critical \| 🟠 High \| 🟡 Medium \| 🔵 Low \| ✅ OK |

---

## Executive Summary

ADR-098 löst ein reales und wichtiges Problem — fehlende Ressourcen-Limits und Kernel-Defaults
sind ein messbares Stabilitätsrisiko auf einer 7-App-Single-Server-Topologie. Der technische
Inhalt der Spezifikation (Layer 0–2) ist überwiegend korrekt und gut begründet.

**Jedoch**: Das ADR hat **3 kritische Fehler** die vor Annahme behoben werden müssen:

1. **RAM-Budget ist arithmetisch falsch** — db-Container werden aus der Tabelle ausgeblendet,
   tatsächlicher Bedarf ist ~11 GB > 8 GB verfügbar
2. **MADR 4.0 Non-Compliance** — keine Considered Options, kein Confirmation-Block
3. **Compose-Template-Regression** — `healthcheck` und `depends_on` fehlen im §3.2-Template

**Verdict**: ❌ **Reject — rework required** (Korrekturen sind eindeutig spezifizierbar,
kein konzeptioneller Neustart notwendig)

---

## 1. MADR 4.0 Compliance

### F-1.1 🔴 CRITICAL — Kein `## Considered Options` / `## Pros and Cons`

**Befund**: Das ADR springt direkt von Kontext zu Entscheidung ohne die Platform-Pflichtstruktur:
`Decision Drivers` → `Considered Options (≥3)` → `Pros and Cons` fehlen vollständig.

**Risiko**: ADR ist laut Platform-Template non-compliant. Das Risiko-/Abwägungs-Reasoning
ist nicht nachvollziehbar (z.B.: Warum kein `cgroupv2`-basiertes Memory-Management?
Warum kein pgBouncer statt `max_connections=50`? Warum kein separater DB-Server?).

**Empfehlung**: Ergänze mindestens diese 3 Options:

| Option | Kern-Idee |
|--------|-----------|
| A (gewählt) | 3-Layer in-place tuning (daemon.json + sysctl + compose) |
| B | PgBouncer + shared PostgreSQL Instanz (ein DB-Prozess für alle Apps) |
| C | Upgrade PROD auf CPX42 (8 vCPU, 16 GB RAM) — mehr Headroom statt Tuning |

---

### F-1.2 🟠 HIGH — Kein `### Confirmation` Subsection

**Befund**: ADR-022 Review-Checklist §1.9 erfordert einen `### Confirmation` Block,
der beschreibt wie die Compliance verifiziert wird.

**Risiko**: Das Audit-Script existiert und wäre der perfekte Confirmation-Mechanismus —
aber der ADR-eigene Nachweis fehlt.

**Empfehlung**: Füge nach `## Consequences` hinzu:

```markdown
### Confirmation

Compliance wird durch `scripts/server/bf-tuning-audit.sh` verifiziert.
Das Script MUSS mit 0 FAIL enden bevor ein neues App-Repo ongeboardet wird
(Gate in `docs/guides/onboard-repo.md` §7 Compliance Checklist).

CI-Integration (nach ADR-078):
```yaml
- name: Infrastructure tuning audit
  run: |
    ssh -o BatchMode=yes \
        -o StrictHostKeyChecking=accept-new \
        root@${DEPLOY_HOST} \
        'bash /opt/scripts/bf-tuning-audit.sh --json' \
    | jq -e '.totals.fail == 0'
```

Drift-Detector:
- `staleness_months: 6`
- `drift_check_paths: [scripts/server/bf-tuning-audit.sh, docker-compose.prod.yml]`
```

---

### F-1.3 🟡 MEDIUM — Frontmatter nicht MADR-4.0-konform

**Befund**: Das Frontmatter verwendet `author:` (ADR-098) statt `decision-makers:`
(MADR 4.0 Standard). Felder `consulted`, `informed` fehlen. Titel ist kein aktiver Satz.

**Empfehlung**:
```yaml
---
id: ADR-098
title: "Adopt 3-Layer Tuning Standard for PROD/DEV Hetzner Infrastructure"
status: Accepted
date: 2026-03-04
decision-makers: Achim Dehnert
consulted: –
informed: –
tags: [infrastructure, docker, performance, hetzner, gunicorn, postgresql, redis, sysctl]
supersedes: []
related: [ADR-021, ADR-022, ADR-042, ADR-056, ADR-063]
---
```

---

## 2. RAM-Budget — Kritischer Arithmetik-Fehler

### F-2.1 🔴 CRITICAL — §3.1 Budget-Tabelle schließt db-Container aus

**Befund**: Die Tabelle in §3.1 zeigt `db | 512M | shared* | —` und summiert db
NICHT in den Total. Der Fußnotentext "Apps sharing the bfagent postgres" gilt nur für
**weltenhub** (1 App). Die anderen 6 Apps haben jeweils einen eigenen PostgreSQL-Container.

**Arithmetik-Nachweis**:

| Service | Limit | Anzahl | Summe |
|---------|-------|--------|-------|
| web | 384M | ×7 | 2.688 GB |
| worker | 512M | ×7 | 3.584 GB |
| beat | 128M | ×7 | 0.896 GB |
| redis | 128M | ×7 | 0.896 GB |
| db | 512M | ×6 (nicht weltenhub) | 3.072 GB |
| OS + Docker | — | — | 0.800 GB |
| **Tatsächlich** | | | **11.936 GB** ❌ |
| Verfügbar (CPX32) | | | **8.192 GB** |
| **Überlauf** | | | **+3.744 GB** |

**Risiko**: Das ADR gibt ein falsches Stabilitätsversprechen. Wenn alle 7 Apps gleichzeitig
ihre Memory-Limits ausschöpfen, triggert der OOM-Killer — genau das Problem das verhindert
werden sollte. Die `deploy.resources.limits` sind **Obergrenzen, keine Garantien** —
sie verhindern Einzelcontainer-Explosionen aber nicht kollektive Überlastung wenn alle
Apps gleichzeitig belastet sind.

**Empfehlung**: Das ADR muss eine ehrlichere Budget-Darstellung liefern und eine
**Tiering-Strategie** dokumentieren, die das tatsächliche Profil adressiert:

```
Strategie: Limits ≠ Gleichzeitige Nutzung
- Memory-Limits sind Sicherheitsobergrenzen (Ceiling), nicht Reservierungen
- Praktischer P50-Betrieb: ca. 60% der Limits → ~7.16 GB
- Kritische Maßnahme: Monitoring + Alerting bei >75% RAM-Gesamtnutzung
- Eskalation: CPX42 (16 GB) wenn P95-Nutzung >80% über 7 Tage
```

Korrekte Tabelle für das ADR:

```markdown
| Service | Limit | ×N | Subtotal | Reservation | ×N | Subtotal |
|---------|-------|-----|----------|-------------|-----|----------|
| web     | 384M  | ×7  | 2.688 GB | 192M        | ×7  | 1.344 GB |
| worker  | 512M  | ×7  | 3.584 GB | 256M        | ×7  | 1.792 GB |
| beat    | 128M  | ×7  | 0.896 GB | 64M         | ×7  | 0.448 GB |
| redis   | 128M  | ×7  | 0.896 GB | 48M         | ×7  | 0.336 GB |
| db      | 512M  | ×6¹ | 3.072 GB | 256M        | ×6  | 1.536 GB |
| OS/Docker| —   | —   | 0.800 GB | —           | —   | 0.800 GB |
| **Max (Ceiling)**| | | **11.936 GB** ⚠️ | **Guaranteed Min** | | **6.256 GB** ✓ |

¹ weltenhub teilt bfagent-postgres, daher 6 statt 7 db-Instanzen.

> **Wichtig**: Max-Ceiling (11.9 GB) überschreitet RAM (8 GB).
> Das ist **by design zulässig** weil nie alle Container gleichzeitig
> ihr Limit ausschöpfen. Monitoring-Alert bei >6.5 GB Gesamtnutzung
> erforderlich (→ ADR-008 Observability Stack).
```

---

### F-2.2 🟠 HIGH — Beat-Container in §3.3 Tier-Tabelle, aber nicht im Budget

**Befund**: §3.2 definiert `beat` mit 128M Limit. §3.3 App-Tier-Tabelle erwähnt beat
**nicht** in der Spaltenstruktur. Nicht alle 7 Apps brauchen beat (travel-beat,
weltenhub, risk-hub sind wahrscheinlich ohne Celery Beat) — aber das ADR klärt das nicht.

**Empfehlung**: §3.3 erweitern um `beat: ja/nein` Spalte und Budget-Impact klarstellen.

---

## 3. Compose-Template — Invarianten-Verletzung

### F-3.1 🔴 CRITICAL — `healthcheck` fehlt im §3.2 Compose-Template

**Befund**: Das `web`-Service-Template in §3.2 hat **kein `healthcheck`**. ADR-022 §3.5
ist explizit: *"Pflicht fuer jeden Service: `healthcheck` (fuer db, redis, web)"*.
Das `docker compose up --wait` im CD-Workflow blockiert auf diesem Healthcheck —
ohne es wartet der Deploy nicht auf App-Bereitschaft.

**Risiko**: Regression der ADR-022-Invariante. Jede App die dieses Template blind
übernimmt verliert ihre Docker-Healthcheck-Semantik.

**Empfehlung**: Vollständiges, kommentiertes web-Service-Template:

```yaml
  web:
    image: "ghcr.io/achimdehnert/${APP_NAME}:${IMAGE_TAG:-latest}"  # ADR-022: GHCR only
    command: ["web"]
    env_file: .env.prod                # ADR-022: env_file, nie environment: ${VAR}
    ports:
      - "127.0.0.1:${APP_PORT:-8000}:8000"  # ADR-022: localhost-only binding
    depends_on:                        # ADR-022: Pflicht — verhindert Start vor Migration
      migrate:
        condition: service_completed_successfully
      db:
        condition: service_healthy
    healthcheck:                       # ADR-022: Pflicht — python urllib, kein curl
      test:
        - "CMD"
        - "python"
        - "-c"
        - "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/livez/')"
      interval: 30s
      timeout: 5s
      start_period: 30s
      retries: 3
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          memory: 384M
          cpus: "1.0"
        reservations:
          memory: 192M
          cpus: "0.25"
```

---

### F-3.2 🟠 HIGH — `depends_on` fehlt im §3.2 Template

**Befund**: Das `web`-Template hat kein `depends_on`. Ohne den
`migrate: service_completed_successfully` Guard kann der web-Container vor Abschluss der
Migrations starten → Django wirft `OperationalError: column does not exist`.

**Empfehlung**: Siehe F-3.1 — `depends_on` im korrigierten Template enthalten.

---

### F-3.3 🟡 MEDIUM — `image:` fehlt im §3.2 Template

**Befund**: Das Compose-Template in §3.2 ist ein Partial-Snippet ohne `image:` Zeile.
Als Referenz-Template (das in alle 7 Repos kopiert werden soll) ist das gefährlich —
ein Entwickler ergänzt womöglich `image: <app>:latest` ohne GHCR-Prefix.

**Empfehlung**: Jeder Service im Template muss `image: ghcr.io/achimdehnert/${APP_NAME}:${IMAGE_TAG:-latest}`
enthalten (nach ADR-022 §3.5 Image-Konvention).

---

## 4. Sicherheits-Befunde

### F-4.1 🟠 HIGH — `StrictHostKeyChecking=no` in CI-Integration

**Befund**: Der Verification-Block am Ende des ADR enthält:
```bash
ssh root@88.198.191.108 'bash /opt/scripts/bf-tuning-audit.sh --json'
```
Kein `-o StrictHostKeyChecking` — implizit per System-Default. Im CI-Kontext (GitHub Actions)
ist das Problem, dass das CI-Environment keinen `known_hosts` für 88.198.191.108 hat, was
zu interaktivem Prompt oder `StrictHostKeyChecking=no` führt.

**ADR-Review-Checklist §2.3**: *"`StrictHostKeyChecking=no` absent — `ssh-keyscan` used instead"*

**Risiko**: MITM-Angriff auf den Deploy-Kanal möglich wenn `StrictHostKeyChecking=no`
implizit oder explizit verwendet wird.

**Empfehlung**:
```yaml
# In Workflow:
- name: Add PROD host key
  run: |
    mkdir -p ~/.ssh
    # Host key wird einmalig via ssh-keyscan ermittelt und als Secret gespeichert
    echo "${{ secrets.DEPLOY_HOST_KEY }}" >> ~/.ssh/known_hosts
    chmod 600 ~/.ssh/known_hosts

- name: Infrastructure tuning audit
  run: |
    ssh -o BatchMode=yes \
        -o StrictHostKeyChecking=yes \
        -i "${{ secrets.DEPLOY_SSH_KEY }}" \
        root@${{ secrets.DEPLOY_HOST }} \
        'bash /opt/scripts/bf-tuning-audit.sh --json' \
    | jq -e '.totals.fail == 0'
```

---

### F-4.2 🟡 MEDIUM — `userland-proxy: false` Hairpin-NAT Nebenwirkung undokumentiert

**Befund**: `"userland-proxy": false` ändert Docker-Portforwarding auf kernel-iptables.
Bekannte Nebenwirkung: **Hairpin-NAT** (Container → eigener exposed Port) funktioniert
nicht auf allen Kernel-Versionen. Hetzner CPX32 verwendet KVM — betroffen wenn Apps
sich selbst via `localhost:PORT` ansprechen (z.B. Health-Checks in Django zwischen Services).

**Risiko**: Sporadic connection failures wenn ein Container versucht seinen eigenen
exponierten Port via Host-IP anzusprechen.

**Empfehlung**: Dokumentiere als bekannte Einschränkung:
```markdown
> **Hinweis**: `userland-proxy: false` deaktiviert Docker's Userspace-Proxy zugunsten
> von kernel-iptables. Container sollten untereinander via Service-Namen (Docker DNS)
> kommunizieren, nicht via Host-IP + exposed Port. Healthchecks via `127.0.0.1:8000`
> (container-intern) sind nicht betroffen.
```

---

## 5. Invarianten-Verletzungen

### F-5.1 🟠 HIGH — Redis `--save "" --appendonly no` scope zu breit

**Befund**: §6 deaktiviert Redis-Persistenz global für alle Apps mit der Begründung
*"Celery task state is ephemeral"*. Das ist korrekt für Celery-Broker-Nutzung aber
**nicht** für alle möglichen Redis-Verwendungen. Falls eine App Redis als Django-Session-Store
konfiguriert hat (`SESSION_ENGINE = 'django.contrib.sessions.backends.cache'`),
gehen alle User-Sessions bei Redis-Neustart verloren.

**Risiko**: Unerwarteter Session-Verlust bei Redis-Restart (z.B. nach `docker compose up -d`).
Besonders kritisch für `bfagent` (Auth-Sessions für AI-Workflows).

**Empfehlung**: Scope explizit einschränken:
```markdown
> **Voraussetzung**: Diese Konfiguration setzt voraus, dass Redis ausschließlich
> als Celery-Broker und Cache (`allkeys-lru`) verwendet wird.
> Falls eine App `SESSION_ENGINE = 'django.contrib.sessions.backends.cache'` verwendet,
> MUSS sie auf `cached_db` umgestellt werden vor Anwendung dieser Konfiguration.
> Prüfbefehl: `grep -r "sessions.backends.cache" */config/settings/`
```

---

### F-5.2 🟡 MEDIUM — `vm.overcommit_memory=1` Nebenwirkung undokumentiert

**Befund**: `vm.overcommit_memory=1` ist die korrekte Docker-Empfehlung, hat aber eine
dokumentationswürdige Nebenwirkung: Der Kernel erlaubt unbegrenzte Memory-Commits
ohne Prüfung der physischen Verfügbarkeit. Bei `swappiness=10` (kein Swap aktiv) und
Overcommit-Aktivierung kann der OOM-Killer ohne jede Vorwarnung feuern.

**Empfehlung**: Ergänze in §2 Sysctl:
```bash
# vm.overcommit_memory=1: Docker-Pflicht (fork()-Optimierung für Copy-on-Write)
# Nebenwirkung: Kernel prüft Speicherverfügbarkeit erst bei tatsächlichem Zugriff.
# Mitigation: Monitoring auf /proc/meminfo:MemAvailable < 512MB (→ ADR-008 Alert)
vm.overcommit_memory = 1
```

---

## 6. Migrations-Risiken

### F-6.1 🔴 CRITICAL — Kein Rollback-Plan dokumentiert

**Befund**: Das ADR enthält eine Priority Matrix mit Änderungsreihenfolge aber
**keinen Rollback-Plan** für den Fall dass Änderungen Probleme verursachen.
Beispiele für wahrscheinliche Rollback-Szenarien:

- `random_page_cost=1.1` führt für spezifische Query-Pattern zu schlechteren Plans
- `max_connections=50` verursacht `FATAL: sorry, too many clients` bei Traffic-Spitzen
- `live-restore: true` + Daemon-Neustart führt zu Netzwerk-Inkonsistenz (bekanntes Docker-Issue)

**Risiko**: Bei Problemen im Prod-Betrieb existiert kein dokumentierter Rückfallpfad.

**Empfehlung**: Ergänze Rollback-Tabelle:

```markdown
### Rollback Procedures

| Änderung | Rollback-Befehl | Downtime |
|---------|----------------|----------|
| random_page_cost | `docker exec <db> psql -U postgres -c "ALTER SYSTEM RESET random_page_cost; SELECT pg_reload_conf();"` | Keine |
| max_connections | `docker exec <db> psql -U postgres -c "ALTER SYSTEM SET max_connections = 100; SELECT pg_reload_conf();"` + Neustart DB | ~10s |
| live-restore | `/etc/docker/daemon.json`: `"live-restore": false` + `systemctl restart docker` | Alle Container stop/start |
| sysctl params | `sysctl -p /etc/sysctl.d/99-docker-orig.conf` (Backup vorher anlegen!) | Keine |
| cpu/mem limits | Entferne `deploy.resources` aus compose + `docker compose up -d` | 0 (rolling) |

> **Vor jeder Änderung**: `cp /etc/sysctl.conf /etc/sysctl.d/99-docker-backup-$(date +%Y%m%d).conf`
```

---

### F-6.2 🟠 HIGH — `max_connections=50` Migrations-Reihenfolge undefiniert

**Befund**: Das Ändern von `max_connections` auf einem laufenden PostgreSQL erfordert
einen DB-Neustart (nicht nur `pg_reload_conf()`). Das Vorgehen bei laufenden
Connections (Django DB-Pool hält Connections) ist nicht spezifiziert.

**Risiko**: Abrupter DB-Restart während aktiver Requests → HTTP 500 für laufende Anfragen.

**Empfehlung**: Migrations-Reihenfolge dokumentieren:
```bash
# 1. Graceful: Reduziere zunächst Django-seitige Connections
#    In .env.prod: DATABASE_URL=...?conn_max_age=0  (deaktiviert persistent connections)
#    dann: docker compose up -d web  (Rolling restart, kein Downtime)

# 2. Änderung in compose db command anwenden
#    docker compose stop db
#    docker compose up -d db
#    (db-Neustart: ~3-5s Downtime für DB, web retries via CONN_MAX_AGE)

# 3. Nach Stabilisierung: conn_max_age zurücksetzen
```

---

### F-6.3 🟡 MEDIUM — `apply-server-tuning.sh` referenziert aber nicht geliefert

**Befund**: §Implementation/Tooling referenziert `scripts/server/apply-server-tuning.sh`
als zu erstellende Datei, liefert aber nur das Audit-Script. Das ADR ist damit
unvollständig als ausführbare Spezifikation.

**Empfehlung**: Liefere `apply-server-tuning.sh` als vollständige idempotente Bash-Datei
im ADR-Body (wie `entrypoint.sh` in ADR-022). Mindestanforderungen:

```bash
#!/usr/bin/env bash
# apply-server-tuning.sh — Idempotentes Server-Tuning (ADR-098)
# Sicher für mehrfache Ausführung (idempotent)
# Keine Container-Neustarts — nur daemon.json + sysctl
set -euo pipefail

# Backup vor Änderung
cp /etc/sysctl.conf "/etc/sysctl.d/99-pre-tuning-backup-$(date +%Y%m%d).conf" 2>/dev/null || true

# ... (vollständige Implementierung)
```

---

## 7. Gunicorn-Konfiguration

### F-7.1 🟡 MEDIUM — Platform `entrypoint.sh` wird nicht explizit aktualisiert

**Befund**: §5 führt neue ENV-Variablen ein (`GUNICORN_THREADS`, `GUNICORN_WORKER_CLASS`,
`GUNICORN_KEEPALIVE`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_MAX_REQUESTS_JITTER`) die im
kanonischen `input/entrypoint.sh` (ADR-022 §3.6) **nicht vorhanden sind**.

**Risiko**: ADR-022 bleibt als Referenz bestehen aber das zentrale Template ist veraltet.
Neue Repos die `input/entrypoint.sh` kopieren erhalten nicht das ADR-098 Gunicorn-Profil.

**Empfehlung**: Das ADR muss explizit dokumentieren:
```markdown
### Entrypoint Update (supersedes ADR-022 §3.6 partial)

Das kanonische `docs/adr/_archive/inputs/entrypoint.sh` wird durch diese ADR
um folgende Parameter erweitert. Alle bestehenden Repos SOLLEN ihre `entrypoint.sh`
nach diesem Template aktualisieren (P1 in Priority Matrix).
```

Und liefere das vollständige aktualisierte `entrypoint.sh` im ADR-Body.

---

## 8. Platform-Pattern-Checks (ADR-Review-Checklist §8)

| Check | Status | Befund |
|-------|--------|--------|
| §8.9 Drift-Detector-Felder | ❌ | Kein `<!-- Drift-Detector-Felder -->` Kommentar |
| §8.1 MCP write-ops via GitHub Actions | ✅ | Kein MCP für Deploy-Ops verwendet |
| §2.3 StrictHostKeyChecking=no absent | ❌ | Siehe F-4.1 |
| §2.7 Deploy-Pfad-Konvention | ✅ | `/opt/<repo>` referenziert |
| §2.8 Health-Endpoints | ✅ | `/livez/` + `/healthz/` korrekt |
| §1.9 Confirmation-Block | ❌ | Fehlt — Siehe F-1.2 |
| §1.5 Considered Options ≥3 | ❌ | Fehlt — Siehe F-1.1 |

---

## 9. Review Scoring

| Kategorie | Score (1–5) | Notizen |
|-----------|-------------|---------|
| MADR 4.0 Compliance | 2 | Kein Options-Block, kein Confirmation, falscher Titel |
| Platform Infrastructure Specifics | 3 | Ports/Pfade korrekt, aber RAM-Budget falsch |
| CI/CD & Docker Conventions | 2 | healthcheck + depends_on fehlen im Template |
| Database & Migration Safety | 3 | max_connections sinnvoll, aber Rollback fehlt |
| Security & Secrets | 3 | StrictHostKeyChecking-Problem |
| Architectural Consistency | 3 | Redis-Scope-Problem, entrypoint.sh nicht aktualisiert |
| Open Questions | 1 | Keine offenen Fragen explizit gemacht |
| Modern Platform Patterns | 2 | Drift-Detector fehlt |
| **Overall** | **2.4** | |

---

## 10. Empfehlung

**❌ Reject — Rework Required**

### Pflicht-Korrekturen (Blocking)

1. **F-2.1** RAM-Budget-Tabelle korrigieren — db-Container korrekt einrechnen,
   `beat` explizit, Ceiling vs. Guaranteed-Min dokumentieren
2. **F-3.1** `healthcheck` + `depends_on` ins §3.2 Compose-Template
3. **F-6.1** Rollback-Tabelle ergänzen
4. **F-1.1** Considered Options (≥3) + Pros/Cons ergänzen
5. **F-1.2** `### Confirmation` Block mit korrigiertem SSH-Befehl (ohne StrictHostKeyChecking=no)

### Empfohlene Korrekturen (Non-Blocking aber dringend)

6. **F-5.1** Redis-Session-Scope-Warnung
7. **F-7.1** `input/entrypoint.sh` als vollständige aktualisierte Datei liefern
8. **F-6.3** `apply-server-tuning.sh` als vollständige Datei liefern
9. **F-4.2** `userland-proxy` Hairpin-NAT Caveat dokumentieren

### Kleinere Korrekturen

10. **F-1.3** Frontmatter auf MADR 4.0 anpassen
11. Drift-Detector-Felder ergänzen

---

## Anhang: Korrigierte Schlüssel-Artefakte

### A1 — Korrigiertes `entrypoint.sh` (ADR-098 §5)

```bash
#!/bin/bash
# ===========================================================================
# entrypoint.sh — Platform Standard Entrypoint (ADR-022 + ADR-098)
# ===========================================================================
# Modes: web | worker | beat
#
# Environment variables (all optional with sane defaults):
#   DJANGO_SETTINGS_MODULE    (required — fail-fast if unset)
#   GUNICORN_WORKERS          (default: 2)
#   GUNICORN_THREADS          (default: 2, ADR-098)
#   GUNICORN_WORKER_CLASS     (default: gthread, ADR-098)
#   GUNICORN_TIMEOUT          (default: 30, ADR-098: reduced from 120)
#   GUNICORN_KEEPALIVE        (default: 5, ADR-098)
#   GUNICORN_MAX_REQUESTS     (default: 1000, ADR-098 — memory leak protection)
#   GUNICORN_MAX_REQUESTS_JITTER (default: 100, ADR-098)
#   CELERY_LOG_LEVEL          (default: info)
#   CELERY_CONCURRENCY        (default: 2)
#   ENTRYPOINT_MIGRATE        (default: false — migration via separate compose service)
#
# Exit codes:
#   0  — clean shutdown
#   1  — invalid arguments or missing env
#   2  — migration failure (only if ENTRYPOINT_MIGRATE=true)
# ===========================================================================
set -euo pipefail

# --- Validate required environment — fail loud, not silent -----------------
: "${DJANGO_SETTINGS_MODULE:?ERROR: DJANGO_SETTINGS_MODULE must be set}"

# --- Optional: run migrations (escape-hatch, default off) ------------------
# Default: false — migration runs in separate 'migrate' compose service (ADR-022 A1)
if [ "${ENTRYPOINT_MIGRATE:-false}" = "true" ]; then
    echo "[entrypoint] Running migrations (ENTRYPOINT_MIGRATE=true)..." >&2
    python manage.py migrate --noinput --skip-checks || exit 2
fi

# --- Select service mode ---------------------------------------------------
MODE="${1:?ERROR: Usage: entrypoint.sh [web|worker|beat]}"

case "${MODE}" in
    web)
        echo "[entrypoint] Starting gunicorn" \
             "(workers=${GUNICORN_WORKERS:-2}" \
             "threads=${GUNICORN_THREADS:-2}" \
             "class=${GUNICORN_WORKER_CLASS:-gthread}" \
             "max-req=${GUNICORN_MAX_REQUESTS:-1000})" >&2
        # collectstatic is done at Docker build time — not here (ADR-022 A3)
        exec gunicorn config.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers                    "${GUNICORN_WORKERS:-2}" \
            --threads                    "${GUNICORN_THREADS:-2}" \
            --worker-class               "${GUNICORN_WORKER_CLASS:-gthread}" \
            --timeout                    "${GUNICORN_TIMEOUT:-30}" \
            --keep-alive                 "${GUNICORN_KEEPALIVE:-5}" \
            --max-requests               "${GUNICORN_MAX_REQUESTS:-1000}" \
            --max-requests-jitter        "${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
            --access-logfile - \
            --error-logfile - \
            --log-level info \
            --forwarded-allow-ips "*"
        ;;

    worker)
        echo "[entrypoint] Starting celery worker" \
             "(concurrency=${CELERY_CONCURRENCY:-2})" >&2
        exec celery -A config worker \
            -l "${CELERY_LOG_LEVEL:-info}" \
            --concurrency="${CELERY_CONCURRENCY:-2}"
        ;;

    beat)
        echo "[entrypoint] Starting celery beat" >&2
        exec celery -A config beat \
            -l "${CELERY_LOG_LEVEL:-info}" \
            --schedule=/tmp/celerybeat-schedule
        ;;

    *)
        echo "ERROR: Unknown mode '${MODE}'. Usage: entrypoint.sh [web|worker|beat]" >&2
        exit 1
        ;;
esac
```

### A2 — `apply-server-tuning.sh` (referenziert in §Implementation/Tooling)

```bash
#!/usr/bin/env bash
# ===========================================================================
# apply-server-tuning.sh — Idempotentes Server-Tuning (ADR-098)
# ===========================================================================
# Wendet Layer-0 Änderungen an: daemon.json + sysctl
# Idempotent: mehrfaches Ausführen ist sicher
# Kein Container-Neustart — nur Host-Level-Konfiguration
#
# Läuft auf: PROD (88.198.191.108) und DEV (46.225.113.1)
# Führt KEINEN Docker-Daemon-Neustart durch (manuell nach Prüfung)
#
# Usage:
#   sudo ./apply-server-tuning.sh             # Dry-run (zeigt Änderungen)
#   sudo ./apply-server-tuning.sh --apply     # Wende sysctl sofort an
#   sudo ./apply-server-tuning.sh --daemon    # Wende daemon.json an + restart Docker
#
# Requires: bash 5+, docker
# ===========================================================================
set -euo pipefail

readonly SYSCTL_FILE="/etc/sysctl.d/99-docker-perf.conf"
readonly DAEMON_JSON="/etc/docker/daemon.json"
readonly BACKUP_DIR="/etc/docker/backups"
readonly SCRIPT_VERSION="1.0.0"

APPLY=false
DAEMON=false
DRY_RUN=true

for arg in "$@"; do
    case "$arg" in
        --apply)  APPLY=true;  DRY_RUN=false ;;
        --daemon) DAEMON=true; DRY_RUN=false ;;
        --help)
            sed -n '2,20p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
    esac
done

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; RESET='\033[0m'

log()  { echo -e "${CYAN}[apply]${RESET} $*"; }
ok()   { echo -e "${GREEN}[ok]${RESET}    $*"; }
warn() { echo -e "${YELLOW}[warn]${RESET}  $*"; }
err()  { echo -e "${RED}[error]${RESET} $*" >&2; exit 1; }
dry()  { echo -e "${YELLOW}[dry-run]${RESET} Would: $*"; }

# ── Require root ──────────────────────────────────────────────────────────────
[[ "${EUID:-$(id -u)}" -eq 0 ]] || err "Must run as root (sudo)"

# ── Backup existing config ────────────────────────────────────────────────────
backup_existing() {
    mkdir -p "${BACKUP_DIR}"
    local ts
    ts=$(date +%Y%m%d-%H%M%S)

    if [[ -f "${DAEMON_JSON}" ]]; then
        cp "${DAEMON_JSON}" "${BACKUP_DIR}/daemon.json.${ts}.bak"
        ok "Backed up daemon.json → ${BACKUP_DIR}/daemon.json.${ts}.bak"
    fi
    if [[ -f "${SYSCTL_FILE}" ]]; then
        cp "${SYSCTL_FILE}" "${BACKUP_DIR}/99-docker-perf.conf.${ts}.bak"
        ok "Backed up sysctl → ${BACKUP_DIR}/99-docker-perf.conf.${ts}.bak"
    fi
}

# ── Apply sysctl ──────────────────────────────────────────────────────────────
apply_sysctl() {
    log "Writing ${SYSCTL_FILE}..."

    # ADR-098 §2 — canonical sysctl values
    cat > "${SYSCTL_FILE}" << 'SYSCTL'
# =============================================================================
# BF Agent Platform — Linux kernel tuning (ADR-098 §2)
# Applied by: apply-server-tuning.sh
# DO NOT EDIT manually — regenerate via apply-server-tuning.sh
# =============================================================================

# ── Network performance ────────────────────────────────────────────────────────
# Default 128 is too low for 7 Gunicorn stacks behind Nginx
net.core.somaxconn = 65535
# Limit concurrent half-open connections
net.ipv4.tcp_max_syn_backlog = 65535
# Expand ephemeral port range (Docker uses many ports)
net.ipv4.ip_local_port_range = 1024 65535
# Allow reuse of TIME_WAIT sockets — reduces port exhaustion
net.ipv4.tcp_tw_reuse = 1
# Reduce TIME_WAIT duration (default: 60s)
net.ipv4.tcp_fin_timeout = 30

# ── Memory management ─────────────────────────────────────────────────────────
# Avoid swap on NVMe — swapping defeats latency advantages of SSD
vm.swappiness = 10
# Required for Docker: allows fork() without pre-checking memory availability
# Side effect: OOM killer fires without warning — mitigate via monitoring
vm.overcommit_memory = 1
# Reduce dirty-page flushing threshold (reduces I/O spikes)
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5

# ── File handles (7 apps × 4 services × many sockets) ─────────────────────────
fs.file-max = 2097152
# Required for Docker inotify watchers (insufficient default: 8192)
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
SYSCTL

    ok "Written ${SYSCTL_FILE}"

    if $APPLY; then
        sysctl -p "${SYSCTL_FILE}"
        ok "sysctl applied immediately (live)"
    else
        warn "sysctl written but NOT applied yet. Run: sysctl -p ${SYSCTL_FILE}"
        warn "Or rerun with --apply to apply immediately"
    fi
}

# ── Apply daemon.json ─────────────────────────────────────────────────────────
apply_daemon() {
    log "Writing ${DAEMON_JSON}..."

    # Validate jq available
    command -v jq &>/dev/null || err "jq required for daemon.json manipulation"

    # Merge with existing config (idempotent)
    local existing="{}"
    [[ -f "${DAEMON_JSON}" ]] && existing=$(cat "${DAEMON_JSON}")

    # ADR-098 §1 — canonical daemon config
    local new_config
    new_config=$(echo "${existing}" | jq '. * {
        "log-driver": "json-file",
        "log-opts": {
            "max-size": "10m",
            "max-file": "5",
            "compress": "true"
        },
        "storage-driver": "overlay2",
        "default-ulimits": {
            "nofile": { "Name": "nofile", "Hard": 65536, "Soft": 65536 }
        },
        "live-restore": true,
        "userland-proxy": false,
        "no-new-privileges": true,
        "max-concurrent-downloads": 6,
        "max-concurrent-uploads": 3,
        "builder": {
            "gc": {
                "enabled": true,
                "defaultKeepStorage": "5GB",
                "policy": [
                    { "keepStorage": "2GB", "filter": ["unused-for=168h"] },
                    { "keepStorage": "5GB", "all": true }
                ]
            }
        }
    }')

    echo "${new_config}" > "${DAEMON_JSON}"
    ok "Written ${DAEMON_JSON}"

    if $DAEMON; then
        warn "Docker daemon restart required to apply daemon.json changes."
        warn "live-restore=true means existing containers keep running."
        warn "Proceeding with daemon restart in 5 seconds (Ctrl+C to abort)..."
        sleep 5
        systemctl restart docker
        ok "Docker daemon restarted"

        # Verify daemon applied config
        local applied_live_restore
        applied_live_restore=$(docker info --format '{{.LiveRestoreEnabled}}' 2>/dev/null || echo "unknown")
        [[ "${applied_live_restore}" == "true" ]] \
            && ok "live-restore: confirmed active" \
            || warn "live-restore: not confirmed — check 'docker info'"
    else
        warn "daemon.json written but Docker NOT restarted."
        warn "Rerun with --daemon to restart Docker (existing containers survive with live-restore)."
    fi
}

# ── Dry-run summary ───────────────────────────────────────────────────────────
dry_run_summary() {
    log "DRY-RUN mode — no changes applied"
    echo ""
    dry "Write sysctl config to ${SYSCTL_FILE}"
    dry "Apply: sysctl -p ${SYSCTL_FILE}"
    dry "Write Docker daemon config to ${DAEMON_JSON}"
    dry "Restart Docker daemon (systemctl restart docker)"
    echo ""
    warn "Run with --apply to apply sysctl changes"
    warn "Run with --daemon to apply daemon.json + restart Docker"
    warn "Run with --apply --daemon to apply everything"
    echo ""
    log "Verify afterwards: ./bf-tuning-audit.sh"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "  BF Agent Platform — Server Tuning (ADR-098 v${SCRIPT_VERSION})"
    echo "  Host: $(hostname) | Date: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    if $DRY_RUN; then
        dry_run_summary
        exit 0
    fi

    backup_existing
    apply_sysctl
    [[ $DAEMON == true ]] && apply_daemon

    echo ""
    ok "Tuning applied. Run bf-tuning-audit.sh to verify:"
    ok "  bash /opt/scripts/bf-tuning-audit.sh"
}

main
```

---

*Review version 1.0 — 2026-03-04 | Template: adr-review-checklist.md v2.0*
