# Platform Scripts — Operations & Deployment Toolkit

## Übersicht

```
platform/scripts/
├── setup/                          ← Dev-Maschine & Server Bootstrap
│   ├── platform.conf               ← Git/SSH Config (Source of Truth)
│   ├── platform-setup.sh           ← Dev-Maschine Bootstrap
│   ├── server-setup.sh             ← Prod-Server Bootstrap
│   └── verify.sh                   ← Smoke-Test ✅/❌
│
├── services.conf                   ← Service Registry (Source of Truth)
│
├── deploy.sh                       ← Atomic Deploy (v2)
├── rollback.sh                     ← Explicit Rollback (v2)
├── db-backup.sh                    ← PostgreSQL Backup (v2)
├── pre-deploy-check.sh             ← Pre-Deploy Validation
│
├── health-monitor.sh               ← Periodic Health Checks (cron)
├── ssl-check.sh                    ← SSL Expiry Alerting (cron)
├── drift-check.sh                  ← Config Drift Detection (cron)
├── docker-cleanup.sh               ← Docker Disk Cleanup (cron)
│
└── install-crons.sh                ← Cron-Job Installer
```

## Architektur-Prinzipien

1. **Single Source of Truth**: `services.conf` definiert alle Services einmal — kein Kopieren zwischen Scripts.
2. **Idempotent**: Jedes Script ist safe to re-run. Keine Seiteneffekte bei mehrfacher Ausführung.
3. **Deklarativ**: Config-Dateien beschreiben Soll-Zustand, Scripts bringen Ist auf Soll.
4. **Progressive Enhancement**: Jedes Script funktioniert standalone, zusammen bilden sie ein Ops-Toolkit.

## Installation

### Schritt 1: Dev-Maschine einrichten

```bash
cd platform/scripts/setup
# Erst anschauen was passieren würde:
./platform-setup.sh --dry-run
# Dann ausführen:
./platform-setup.sh
# Prüfen ob alles stimmt:
./verify.sh
```

### Schritt 2: Server einrichten

```bash
# Vom Dev-Rechner aus:
./server-setup.sh
```

### Schritt 3: Scripts auf Server deployen

```bash
scp services.conf deploy.sh rollback.sh db-backup.sh \
    pre-deploy-check.sh health-monitor.sh ssl-check.sh \
    drift-check.sh docker-cleanup.sh install-crons.sh \
    prod:/opt/deploy/scripts/
```

### Schritt 4: Cron-Jobs installieren

```bash
ssh prod
cd /opt/deploy/scripts
./install-crons.sh
```

## Zusammenspiel der Scripts

```
┌─────────────────────────────────────────────────────┐
│                  services.conf                       │
│          (Central Service Registry)                  │
└──────────┬──────┬──────┬──────┬──────┬──────┬───────┘
           │      │      │      │      │      │
     deploy.sh  rollback db-backup pre-check health ssl drift
           │
     ┌─────┴──────────────────────────────┐
     │ Phase 0: pre-deploy-check.sh       │
     │ Phase 1: docker compose pull       │
     │ Phase 2: db-backup.sh (if migrate) │  ← NEW: automatic
     │ Phase 2b: django migrate           │
     │ Phase 3: docker compose up         │
     │ Phase 4: health check → rollback   │
     └────────────────────────────────────┘
```

## Cron Schedule

| Zeitplan        | Script              | Funktion                         |
|-----------------|---------------------|----------------------------------|
| `*/5 * * * *`   | health-monitor.sh   | HTTP + Container + DB Checks     |
| `0 2 * * *`     | db-backup.sh --all  | PostgreSQL Dumps aller Services  |
| `0 6 * * *`     | ssl-check.sh        | Cert Expiry (14d warn, 7d crit)  |
| `0 8 * * *`     | drift-check.sh      | Git Dirty, Behind, Compose Drift |
| `0 3 * * 0`     | docker-cleanup.sh   | Image Prune, Volume Prune        |

## Neuen Service hinzufügen

Nur **eine** Zeile in `services.conf`:

```bash
"my-new-hub|/opt/my-new-hub|my-new-hub-web|docker-compose.prod.yml|https://my-new-hub.example.com/livez/|my_new_hub_db|my_new_hub|my_user|my-new-hub.example.com"
```

Fertig. Alle Scripts (deploy, rollback, backup, health, SSL, drift) erkennen den neuen Service automatisch.

## Alerting

Alle Scripts unterstützen einen optionalen Webhook:

```bash
export ALERT_WEBHOOK_URL="https://hooks.slack.com/services/T.../B.../..."
```

Alerts werden gesendet bei:
- Health: 3+ konsekutive Failures → Alert, Recovery → Alert
- SSL: Cert expires <14 Tage → Warning, <7 Tage → Critical
- Drift: Jeder erkannte Drift → Log + Syslog
