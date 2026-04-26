# Multi-Environment Development Setup

> Parallele Entwicklung auf Ubuntu, Windows 11 (WSL2) und Remote-Servern

---

## Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitHub (achimdehnert/*)                         │
│                        Single Source of Truth                           │
│                    25+ Repos, CI/CD Workflows, ADRs                     │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │                            │                            │
    ▼                            ▼                            ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   Development    │   │     Staging      │   │   Production     │
│                  │   │                  │   │                  │
│ ┌──────────────┐ │   │ 178.104.184.168  │   │ 88.198.191.108   │
│ │ Lokal        │ │   │ Hetzner Staging  │   │ Hetzner Prod     │
│ │ Ubuntu/WSL2  │ │   │                  │   │                  │
│ │ Windows 11   │ │   │ • Docker only    │   │ • Docker only    │
│ └──────────────┘ │   │ • Pre-prod test  │   │ • Live traffic   │
│        +         │   │ • Same ports     │   │ • Backups        │
│ ┌──────────────┐ │   └──────────────────┘   └──────────────────┘
│ │ Dev-Server   │ │
│ │ 88.99.38.75  │ │
│ │ Remote Dev   │ │
│ └──────────────┘ │
│                  │
│ • Git Checkout   │
│ • venv/Docker    │
│ • DB lokal/Tunnel│
└──────────────────┘
```

---

## Quick Start

### Option 1: Bootstrap-Script (empfohlen)

```bash
# Auf neuem Ubuntu/WSL2 System:
git clone git@github.com:achimdehnert/platform.git ~/github/platform
cd ~/github/platform
bash scripts/bootstrap-dev-env.sh --full
```

### Option 2: Manuell

```bash
# 1. Repos klonen
mkdir -p ~/github && cd ~/github
for repo in platform mcp-hub bfagent risk-hub travel-beat; do
    git clone git@github.com:achimdehnert/$repo.git
done

# 2. SSH-Tunnel für PostgreSQL
ssh -N -L 15435:localhost:5432 root@88.198.191.108 &

# 3. Platform-Package installieren
cd ~/github/platform
python3 -m venv .venv
.venv/bin/pip install -e packages/platform-context
```

---

## Umgebungen

### Development (lokal — Ubuntu/WSL2/Windows)

| Aspekt | Konfiguration |
|--------|---------------|
| **Code** | Git Checkout in `~/github/<repo>` |
| **Python** | venv pro Repo oder global |
| **Database** | SSH-Tunnel zu Prod (localhost:15435) oder lokales PostgreSQL |
| **Redis** | Lokal (`docker run -d -p 6379:6379 redis:7`) |
| **Ports** | Wie in `infra/ports.yaml` definiert |

```bash
# Beispiel: risk-hub lokal starten
cd ~/github/risk-hub
python manage.py runserver 8090  # Port aus ports.yaml
```

### Development (Remote — Dev-Server 88.99.38.75)

| Aspekt | Konfiguration |
|--------|---------------|
| **Code** | Git Checkout in `/home/devuser/github/<repo>` |
| **Zugang** | VS Code Remote SSH oder `ssh hetzner-dev` |
| **Python** | venv auf Server |
| **Database** | Lokales PostgreSQL auf Dev-Server |
| **Redis** | Lokales Redis auf Dev-Server |
| **Ports** | Wie in `infra/ports.yaml` definiert |

```bash
# Option A: VS Code Remote SSH
# 1. VS Code öffnen
# 2. Cmd+Shift+P → "Remote-SSH: Connect to Host" → hetzner-dev
# 3. Ordner öffnen: /home/devuser/github/risk-hub

# Option B: Terminal
ssh hetzner-dev
cd /home/devuser/github/risk-hub
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8090
```

**Vorteil Dev-Server:**
- Schnellere Netzwerkverbindung zu Prod-DB
- Keine lokale Docker/PostgreSQL-Installation nötig
- Persistente Entwicklungsumgebung

### Staging (178.104.184.168)

| Aspekt | Konfiguration |
|--------|---------------|
| **Deploy** | `docker compose -f docker-compose.prod.yml up -d` |
| **Ports** | Identisch zu Production |
| **Domains** | `staging-*.iil.pet` oder `staging.*.de` |
| **Zugang** | `ssh hetzner-staging` |

```bash
# Deploy auf Staging
ssh hetzner-staging
cd /opt/risk-hub
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Production (88.198.191.108)

| Aspekt | Konfiguration |
|--------|---------------|
| **Deploy** | Nur via CI/CD (GitHub Actions) |
| **Ports** | Definiert in `infra/ports.yaml` |
| **Domains** | Live-Domains (schutztat.de, etc.) |
| **Zugang** | `ssh hetzner-prod` (read-only für Agents) |

```bash
# NIEMALS direkt deployen! Nur via:
git push origin main  # Triggert CI/CD
# oder
bash scripts/ship.sh risk-hub
```

---

## Port-Übersicht (Auszug)

| Service | Dev | Staging | Prod | Domain |
|---------|-----|---------|------|--------|
| coach-hub | 8007 | 8007 | 8007 | kiohnerisiko.de |
| weltenhub | 8081 | 8081 | 8081 | weltenforger.com |
| risk-hub | 8090 | 8090 | 8090 | schutztat.de |
| bfagent | 8091 | 8091 | 8091 | iil.pet |
| billing-hub | 8092 | 8092 | 8092 | billing.iil.pet |

**Vollständige Liste:** `platform/infra/ports.yaml`

---

## SSH-Konfiguration

Füge zu `~/.ssh/config` hinzu:

```ssh-config
Host hetzner-prod
    HostName 88.198.191.108
    User root
    IdentityFile ~/.ssh/id_ed25519

Host hetzner-staging
    HostName 178.104.184.168
    User root
    IdentityFile ~/.ssh/id_ed25519

Host hetzner-dev
    HostName 88.99.38.75
    User root
    IdentityFile ~/.ssh/id_ed25519
```

---

## Datenbank-Zugang

### Option A: SSH-Tunnel (empfohlen)

**pgvector läuft als `mcp_hub_db` Container auf Prod `88.198.191.108`, gebunden auf `127.0.0.1:15435`.**
Der Tunnel muss daher auf Port `15435` zeigen (nicht `5432`).

```bash
# Einmalig: systemd Service erstellen
sudo tee /etc/systemd/system/ssh-tunnel-postgres.service <<'EOF'
[Unit]
Description=SSH Tunnel to Production PostgreSQL (pgvector — localhost:15435)
After=network-online.target
Wants=network-online.target
StartLimitBurst=5
StartLimitIntervalSec=60

[Service]
Type=simple
User=adehnert
ExecStart=/usr/bin/ssh \
  -N \
  -o ServerAliveInterval=60 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -o StrictHostKeyChecking=yes \
  -o BatchMode=yes \
  -i /home/adehnert/.ssh/id_ed25519 \
  -L 15435:localhost:15435 \
  root@88.198.191.108
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ssh-tunnel-postgres

# Verbindung testen
ss -tlnp | grep 15435
systemctl is-active ssh-tunnel-postgres
```

> **Wichtig:** Tunnel-Ziel ist `localhost:15435` (Container-Port) — **nicht** `localhost:5432`.

### Option B: Lokales PostgreSQL

```bash
docker run -d \
    --name postgres-dev \
    -e POSTGRES_PASSWORD=devpassword \
    -p 5432:5432 \
    -v pgdata:/var/lib/postgresql/data \
    postgres:16
```

---

## Repo-Synchronisation

### Alle Repos synchronisieren

```bash
cd ~/github/platform
bash scripts/sync-repo.sh --all
```

### Einzelnes Repo

```bash
cd ~/github/risk-hub
bash ~/github/platform/scripts/sync-repo.sh .
```

### Server synchronisieren

```bash
# Platform + alle Apps auf Server
bash scripts/sync-repo.sh --server

# Quick-Deploy (nur docker pull + up)
bash scripts/sync-repo.sh --quick-deploy weltenhub
```

---

## Windsurf/Cascade Workflows

Nach dem Klonen: Workflows in alle Repos verteilen:

```bash
GITHUB_DIR=~/github bash ~/github/platform/scripts/sync-workflows.sh
```

Wichtige Workflows:
- `/session-start` — Session initialisieren
- `/session-ende` — Session abschließen
- `/ship` — App deployen
- `/deploy-check` — Deploy-Status prüfen

---

## Windows 11 Spezifika

### WSL2 installieren

```powershell
# PowerShell als Admin
wsl --install -d Ubuntu-22.04
```

### Docker Desktop

1. Docker Desktop installieren
2. Settings → Resources → WSL Integration → Ubuntu aktivieren

### VS Code / Windsurf

1. "Remote - WSL" Extension installieren
2. In WSL: `code .` oder `windsurf .` öffnet IDE mit WSL-Backend

---

## Troubleshooting

### SSH-Tunnel bricht ab

```bash
# Status prüfen
sudo systemctl status ssh-tunnel-postgres

# Logs
journalctl -u ssh-tunnel-postgres -f

# Neustart
sudo systemctl restart ssh-tunnel-postgres
```

### Port bereits belegt

```bash
# Wer nutzt Port 8090?
sudo lsof -i :8090

# Prozess beenden
sudo kill -9 <PID>
```

### Git-Konflikte nach Sync

```bash
# Backup-Branch prüfen
git branch -a | grep backup/sync

# Stash anzeigen
git stash list
git stash show -p
```

---

## Referenzen

- **ADR-042**: Dev Environment Deploy Workflow
- **ADR-157**: Staging Environment Strategy
- **ADR-164**: Port-Strategie
- **ports.yaml**: `platform/infra/ports.yaml`
- **sync-repo.sh**: `platform/scripts/sync-repo.sh`
