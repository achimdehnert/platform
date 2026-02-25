# Platform Bootstrap Scripts

**Ziel:** Ein einziger Einstiegspunkt der jede Maschine (WSL-Dev, Prod-Server,
neuer Entwickler) in einen konsistenten, deployfaehigen Zustand bringt.

## Dateien

| Datei | Beschreibung |
|-------|-------------|
| `platform.conf` | Deklarative Config (Source of Truth) |
| `platform-setup.sh` | Dev-Maschine Bootstrap (WSL/Linux/macOS) |
| `server-setup.sh` | Remote Server Bootstrap via SSH |
| `verify.sh` | Smoke-Test mit JSON-Output fuer CI |

## Quick Start

```bash
cd platform/scripts/setup
chmod +x *.sh

# 1. Dev-Maschine einrichten
./platform-setup.sh              # Full setup
./platform-setup.sh --dry-run    # Vorschau
./platform-setup.sh --git-only   # Nur Git-Config

# 2. Server einrichten (laeuft lokal, pushed via SSH)
./server-setup.sh
./server-setup.sh --dry-run

# 3. Alles pruefen
./verify.sh                      # Full check
./verify.sh --local-only         # Ohne Server-Checks
./verify.sh --json               # JSON fuer CI
```

## Architektur

- **Deklarativ**: `platform.conf` definiert Soll-Zustand, Scripts bringen Ist auf Soll
- **Idempotent**: Alle Scripts sind safe to re-run
- **Kein Ansible/Terraform**: Overkill fuer 1 Dev + 2 Server (<500 Zeilen gesamt)
- **Bash only**: Muss vor Python-Installation laufen koennen

## Was die Scripts konfigurieren

### platform-setup.sh (Dev)
1. SSH-Keys generieren (Ed25519)
2. `~/.ssh/config` mit Platform-Block (GitHub + alle Server)
3. SSH-Agent Auto-Start (WSL)
4. Git config --global (Identity, Pull-Strategy, Extras)
5. Connection Tests (GitHub + Server)

### server-setup.sh (Remote)
1. Git config auf Server (identity, pull.rebase, safe.directory)
2. GitHub Deploy Key (credential-freies git pull)
3. Repo-Verzeichnisse pruefen, HTTPS->SSH umstellen
4. Docker/GHCR Login pruefen

### verify.sh (Smoke Test)
- SSH Keys + Permissions
- SSH Config (Platform-Block)
- Git Config (alle Werte aus platform.conf)
- Connectivity (GitHub + Server)
- Server-Side (Git, Deploy Key, Docker, Repos)

## Supersedes

`mcp-hub/scripts/git-bootstrap.sh` -- die Git-Config-Funktionalitaet
ist vollstaendig in `platform-setup.sh` enthalten.
