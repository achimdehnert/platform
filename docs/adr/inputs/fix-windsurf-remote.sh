#!/usr/bin/env bash
# =============================================================================
# fix-windsurf-remote.sh — Windsurf Remote-SSH Stabilisierung
# =============================================================================
#
# Problem:  Windsurf-Server auf Remote crasht → ECONNREFUSED 127.0.0.1:44341
#           Server kann Port nicht neu binden weil alter Prozess noch läuft.
#
# Ursachen:
#   1. Zombie-Prozesse des alten Windsurf-Servers blockieren den Port
#   2. SSH-Verbindung dropped (Keepalive zu schwach)
#   3. Node.js OOM auf kleinen Hetzner VMs (CX32 = 4GB RAM)
#   4. Windsurf-Server schreibt Lock-Dateien die beim Crash nicht aufgeräumt werden
#
# Verwendung:
#   Auf dem REMOTE-Server (hetzner-dev) ausführen:
#     bash fix-windsurf-remote.sh              # Einmal fixen + Prävention installieren
#     bash fix-windsurf-remote.sh --menu       # Interaktives Menü (empfohlen bei Problemen)
#     bash fix-windsurf-remote.sh --clean      # Sanft: Nur stale Prozesse (>1h)
#     bash fix-windsurf-remote.sh --force      # Aggressiv: ALLE Prozesse killen
#
# Referenz: ADR-042 §3.3 (Windsurf IDE Configuration)
# =============================================================================
set -euo pipefail

# ── Farben ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

info()  { echo -e "${GREEN}[INFO]${RESET}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*"; }

# ── Argument Parsing ─────────────────────────────────────────────────────────
MODE="install"  # Default: full install
TARGET_WORKSPACE=""
FORCE_KILL=false
SHOW_MENU=false

for arg in "$@"; do
    case "$arg" in
        --menu|-m)
            SHOW_MENU=true
            MODE="clean"
            ;;
        --clean|-c)
            MODE="clean"
            ;;
        --force|-f)
            MODE="clean"
            FORCE_KILL=true
            ;;
        --workspace=*)
            MODE="clean"
            TARGET_WORKSPACE="${arg#*=}"
            ;;
        --help|-h)
            echo "Windsurf Remote-SSH Fix"
            echo ""
            echo "Usage: $0 [OPTION]"
            echo ""
            echo "Optionen:"
            echo "  (keine)      Vollständige Installation + Prävention"
            echo "  --menu, -m   Interaktives Menü (empfohlen)"
            echo "  --clean, -c  Sanfter Cleanup (nur stale Prozesse)"
            echo "  --force, -f  Aggressiv: ALLE Prozesse killen"
            echo "  --help, -h   Diese Hilfe anzeigen"
            exit 0
            ;;
        *)
            error "Unknown argument: $arg"
            echo "Usage: $0 [--menu] [--clean] [--force] [--help]"
            exit 1
            ;;
    esac
done

# ── Interaktives Menü ───────────────────────────────────────────────────────
show_menu() {
    echo ""
    echo -e "${BOLD}═══ Windsurf Cleanup Menü ═══${RESET}"
    echo ""
    echo "  1) Sanft      — Nur stale Prozesse (>1h), aktive Sessions bleiben"
    echo "  2) Workspace  — Nur einen bestimmten Workspace bereinigen"
    echo "  3) Force      — ALLE Windsurf-Prozesse killen (Notfall)"
    echo "  4) Status     — Aktive Windsurf-Sessions anzeigen"
    echo "  q) Abbrechen"
    echo ""
    read -rp "Auswahl [1-4, q]: " choice
    
    case "$choice" in
        1)
            MODE="clean"
            FORCE_KILL=false
            ;;
        2)
            echo ""
            echo "Verfügbare Workspaces:"
            pgrep -af "workspace_id" -u "${WINDSURF_USER:-deploy}" 2>/dev/null | \
                grep -oP "workspace_id \K[^ ]+" | sort -u | sed 's/^/  - /' || echo "  (keine gefunden)"
            echo ""
            read -rp "Workspace-Name (z.B. platform): " ws_name
            if [ -n "$ws_name" ]; then
                TARGET_WORKSPACE="$ws_name"
                MODE="clean"
            else
                error "Kein Workspace angegeben."
                exit 1
            fi
            ;;
        3)
            echo ""
            warn "ACHTUNG: Dies killt ALLE Windsurf-Sessions!"
            read -rp "Wirklich fortfahren? [j/N]: " confirm
            if [[ "$confirm" =~ ^[jJyY]$ ]]; then
                MODE="clean"
                FORCE_KILL=true
            else
                info "Abgebrochen."
                exit 0
            fi
            ;;
        4)
            echo ""
            echo -e "${BOLD}Aktive Windsurf-Sessions:${RESET}"
            pgrep -af "workspace_id" -u "${WINDSURF_USER:-deploy}" 2>/dev/null | \
                grep -oP "workspace_id \K[^ ]+" | sort -u | while read -r ws; do
                    echo "  ✔ $ws"
                done || echo "  (keine aktiven Sessions)"
            echo ""
            echo -e "${BOLD}Windsurf-Prozesse:${RESET}"
            pgrep -c -f "windsurf-server" -u "${WINDSURF_USER:-deploy}" 2>/dev/null || echo "0"
            echo " Prozesse laufen."
            exit 0
            ;;
        q|Q)
            info "Abgebrochen."
            exit 0
            ;;
        *)
            error "Ungültige Auswahl: $choice"
            exit 1
            ;;
    esac
}

if [ "$SHOW_MENU" = true ]; then
    show_menu
fi

# ── Wer bin ich? ─────────────────────────────────────────────────────────────
CURRENT_USER="$(whoami)"
# Windsurf läuft oft unter 'deploy', nicht 'root' — beide prüfen
TARGET_USER="${WINDSURF_USER:-deploy}"
WINDSURF_DIR="/home/${TARGET_USER}/.windsurf-server"
if [ "$CURRENT_USER" = "$TARGET_USER" ]; then
    WINDSURF_DIR="$HOME/.windsurf-server"
fi

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  Windsurf Remote-SSH Fix — ECONNREFUSED 44341            ${RESET}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════${RESET}"
echo ""
info "User: ${CURRENT_USER} (Target: ${TARGET_USER})"
info "Windsurf-Dir: ${WINDSURF_DIR}"
echo ""

# =============================================================================
# SCHRITT 1: Zombie-Prozesse killen (Multi-Session aware)
# =============================================================================
echo -e "${BOLD}── Schritt 1: Stale Windsurf-Server-Prozesse aufräumen ──${RESET}"

if [ -n "$TARGET_WORKSPACE" ]; then
    # Workspace-spezifischer Kill: Nur Extension-Host und Language-Server für diesen Workspace
    info "Workspace-spezifischer Cleanup: ${TARGET_WORKSPACE}"
    WORKSPACE_PIDS=$(pgrep -af "workspace_id.*${TARGET_WORKSPACE}" -u "$TARGET_USER" 2>/dev/null | awk '{print $1}' || true)
    if [ -n "$WORKSPACE_PIDS" ]; then
        warn "Gefundene Prozesse für Workspace ${TARGET_WORKSPACE}:"
        # shellcheck disable=SC2086
        ps -fp $WORKSPACE_PIDS 2>/dev/null || true
        echo ""
        info "Sende SIGTERM..."
        # shellcheck disable=SC2086
        kill $WORKSPACE_PIDS 2>/dev/null || true
        sleep 2
        # Force kill remaining
        REMAINING=$(pgrep -af "workspace_id.*${TARGET_WORKSPACE}" -u "$TARGET_USER" 2>/dev/null | awk '{print $1}' || true)
        if [ -n "$REMAINING" ]; then
            # shellcheck disable=SC2086
            kill -9 $REMAINING 2>/dev/null || true
        fi
        info "Workspace ${TARGET_WORKSPACE} bereinigt."
    else
        info "Keine Prozesse für Workspace ${TARGET_WORKSPACE} gefunden."
    fi

elif [ "$FORCE_KILL" = true ]; then
    # Aggressiver Modus: ALLE Windsurf-Prozesse killen
    warn "FORCE MODE: Alle Windsurf-Prozesse werden gekillt!"
    WINDSURF_PIDS=$(pgrep -f "windsurf-server|\.windsurf-server" -u "$TARGET_USER" 2>/dev/null || true)
    if [ -n "$WINDSURF_PIDS" ]; then
        warn "Gefundene Windsurf-Server-Prozesse:"
        # shellcheck disable=SC2086
        ps -fp $WINDSURF_PIDS 2>/dev/null || true
        echo ""
        info "Sende SIGTERM..."
        # shellcheck disable=SC2086
        kill $WINDSURF_PIDS 2>/dev/null || true
        sleep 2
        REMAINING=$(pgrep -f "windsurf-server|\.windsurf-server" -u "$TARGET_USER" 2>/dev/null || true)
        if [ -n "$REMAINING" ]; then
            warn "Prozesse reagieren nicht — SIGKILL..."
            # shellcheck disable=SC2086
            kill -9 $REMAINING 2>/dev/null || true
            sleep 1
        fi
        info "Alle Windsurf-Server-Prozesse bereinigt."
    else
        info "Keine Windsurf-Prozesse gefunden."
    fi

else
    # Sanfter Modus (Default): Nur Prozesse älter als 1 Stunde (3600s) ohne aktive SSH
    info "Sanfter Modus: Nur stale Prozesse (>1h) werden bereinigt."
    STALE_PIDS=""
    for pid in $(pgrep -f "windsurf-server" -u "$TARGET_USER" 2>/dev/null || true); do
        ELAPSED=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d " " || echo "0")
        if [ "$ELAPSED" -gt 3600 ]; then
            # Prüfe ob dieser Prozess noch eine aktive SSH-Verbindung hat
            # (vereinfacht: wenn der Parent-Prozess sshd ist, ist er aktiv)
            PPID_NAME=$(ps -o comm= -p "$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')" 2>/dev/null || echo "")
            if [ "$PPID_NAME" != "sshd" ]; then
                STALE_PIDS="$STALE_PIDS $pid"
            fi
        fi
    done
    
    if [ -n "$STALE_PIDS" ]; then
        warn "Gefundene stale Prozesse (>1h, keine SSH-Verbindung):"
        # shellcheck disable=SC2086
        ps -fp $STALE_PIDS 2>/dev/null || true
        echo ""
        info "Sende SIGTERM..."
        # shellcheck disable=SC2086
        kill $STALE_PIDS 2>/dev/null || true
        sleep 2
        info "Stale Prozesse bereinigt."
    else
        info "Keine stale Prozesse gefunden. Aktive Sessions bleiben erhalten."
        info "Tipp: Verwende --force um ALLE Prozesse zu killen."
    fi
fi

# 1b: Ports freigeben (nur bei --force, sonst werden aktive Sessions zerstört)
if [ "$FORCE_KILL" = true ]; then
    WINDSURF_PORTS=$(lsof -i -P -n 2>/dev/null | grep -E "node.*LISTEN" | grep "$TARGET_USER" | awk '{print $9}' | cut -d: -f2 | sort -u || true)
    if [ -n "$WINDSURF_PORTS" ]; then
        for port in $WINDSURF_PORTS; do
            PORT_PID=$(lsof -ti :"$port" 2>/dev/null || true)
            if [ -n "$PORT_PID" ]; then
                warn "Port ${port} belegt von PID ${PORT_PID} — wird freigegeben..."
                kill -9 "$PORT_PID" 2>/dev/null || true
            fi
        done
        sleep 1
        info "Windsurf-Ports freigegeben."
    else
        info "Keine blockierten Windsurf-Ports gefunden."
    fi
else
    info "Port-Cleanup übersprungen (sanfter Modus). Verwende --force für Port-Cleanup."
fi

# 1c: Node.js Orphan-Prozesse (nur bei --force)
if [ "$FORCE_KILL" = true ]; then
    NODE_ORPHANS=$(pgrep -f "node.*windsurf" -u "$TARGET_USER" 2>/dev/null || true)
    if [ -n "$NODE_ORPHANS" ]; then
        warn "Node.js Windsurf-Orphans gefunden — bereinige..."
        # shellcheck disable=SC2086
        kill $NODE_ORPHANS 2>/dev/null || true
        sleep 1
    fi
fi

echo ""

# =============================================================================
# SCHRITT 2: Lock-Dateien und Cache aufräumen
# =============================================================================
echo -e "${BOLD}── Schritt 2: Lock-Dateien und stale Cache bereinigen ──${RESET}"

if [ -d "$WINDSURF_DIR" ]; then
    # Lock-Dateien entfernen (verhindern Neustart)
    LOCKS_FOUND=0
    while IFS= read -r -d '' lockfile; do
        rm -f "$lockfile"
        LOCKS_FOUND=$((LOCKS_FOUND + 1))
    done < <(find "$WINDSURF_DIR" -name "*.lock" -print0 2>/dev/null)

    if [ "$LOCKS_FOUND" -gt 0 ]; then
        info "${LOCKS_FOUND} Lock-Dateien entfernt."
    else
        info "Keine Lock-Dateien gefunden."
    fi

    # IPC-Sockets aufräumen (können stale sein)
    SOCKETS_FOUND=0
    while IFS= read -r -d '' sock; do
        rm -f "$sock"
        SOCKETS_FOUND=$((SOCKETS_FOUND + 1))
    done < <(find "$WINDSURF_DIR" -name "*.sock" -print0 2>/dev/null)

    if [ "$SOCKETS_FOUND" -gt 0 ]; then
        info "${SOCKETS_FOUND} stale Sockets entfernt."
    fi

    # Crash-Logs anzeigen (letzte 5 Zeilen für Diagnostik)
    CRASH_LOG=$(find "$WINDSURF_DIR" -name "*.log" -newer /tmp/.windsurf-fix-marker 2>/dev/null | head -1 || true)
    if [ -n "$CRASH_LOG" ] && [ -f "$CRASH_LOG" ]; then
        warn "Letzter Crash-Log (${CRASH_LOG}):"
        tail -5 "$CRASH_LOG" 2>/dev/null || true
        echo ""
    fi
else
    info "Kein Windsurf-Server-Verzeichnis gefunden (Erstinstallation)."
fi

# Marker für nächsten Lauf
touch /tmp/.windsurf-fix-marker

echo ""

# =============================================================================
# SCHRITT 3: Wenn --clean → hier stoppen
# =============================================================================
if [ "${1:-}" = "--clean" ]; then
    echo -e "${GREEN}${BOLD}✅ Cleanup abgeschlossen. Windsurf neu verbinden.${RESET}"
    exit 0
fi

# =============================================================================
# SCHRITT 3: SSH-Keepalive auf dem Server härten
# =============================================================================
echo -e "${BOLD}── Schritt 3: SSH-Server Keepalive härten ──${RESET}"

SSHD_CONFIG="/etc/ssh/sshd_config"

# Prüfe ob wir Root-Rechte haben (oder sudo)
if [ "$CURRENT_USER" = "root" ] || sudo -n true 2>/dev/null; then
    # Aktuelle Werte prüfen
    CURRENT_INTERVAL=$(grep -E "^ClientAliveInterval" "$SSHD_CONFIG" 2>/dev/null | awk '{print $2}' || echo "0")
    CURRENT_MAX=$(grep -E "^ClientAliveCountMax" "$SSHD_CONFIG" 2>/dev/null | awk '{print $2}' || echo "3")

    NEEDS_UPDATE=false

    # ClientAliveInterval: Server sendet Keepalive alle 30s
    # (verhindert dass NAT/Firewall die Verbindung killt)
    if [ "${CURRENT_INTERVAL:-0}" -ne 30 ]; then
        NEEDS_UPDATE=true
    fi

    # ClientAliveCountMax: Nach 4 verpassten Keepalives → Disconnect
    # (30s × 4 = 120s Toleranz)
    if [ "${CURRENT_MAX:-3}" -ne 4 ]; then
        NEEDS_UPDATE=true
    fi

    if [ "$NEEDS_UPDATE" = true ]; then
        info "Aktualisiere sshd_config (ClientAliveInterval=30, ClientAliveCountMax=4)..."

        # Backup (Dateiname in Variable für korrektes Restore)
        BACKUP_FILE="${SSHD_CONFIG}.bak.$(date +%Y%m%d%H%M%S)"
        sudo cp "$SSHD_CONFIG" "$BACKUP_FILE"

        # Bestehende Einträge entfernen (idempotent)
        sudo sed -i '/^ClientAliveInterval/d' "$SSHD_CONFIG"
        sudo sed -i '/^ClientAliveCountMax/d' "$SSHD_CONFIG"
        sudo sed -i '/^#.*ClientAliveInterval/d' "$SSHD_CONFIG"
        sudo sed -i '/^#.*ClientAliveCountMax/d' "$SSHD_CONFIG"

        # Neue Werte setzen
        {
            echo ""
            echo "# ── Windsurf Remote-SSH Stabilisierung (ADR-042) ──"
            echo "ClientAliveInterval 30"
            echo "ClientAliveCountMax 4"
        } | sudo tee -a "$SSHD_CONFIG" > /dev/null

        # sshd Config validieren VOR Restart (verhindert Lockout!)
        if sudo sshd -t; then
            # Debian/Ubuntu: ssh.service, RHEL/CentOS: sshd.service
            if systemctl list-units --type=service | grep -q "ssh.service"; then
                sudo systemctl reload ssh
            else
                sudo systemctl reload sshd
            fi
            info "SSH-Server neu geladen — Keepalive aktiv."
        else
            error "sshd Config ungültig! Restore Backup..."
            sudo cp "$BACKUP_FILE" "$SSHD_CONFIG"
            if systemctl list-units --type=service | grep -q "ssh.service"; then
                sudo systemctl reload ssh
            else
                sudo systemctl reload sshd
            fi
            error "Backup restored. Bitte manuell prüfen."
            exit 1
        fi
    else
        info "SSH-Keepalive bereits korrekt konfiguriert (30s/4)."
    fi
else
    warn "Keine Root/Sudo-Rechte — SSH-Keepalive muss manuell konfiguriert werden."
    warn "Benötigt in ${SSHD_CONFIG}:"
    warn "  ClientAliveInterval 30"
    warn "  ClientAliveCountMax 4"
fi

echo ""

# =============================================================================
# SCHRITT 4: Systemd-Watchdog für Windsurf-Server
# =============================================================================
echo -e "${BOLD}── Schritt 4: Windsurf-Server Cleanup-Timer installieren ──${RESET}"

# Erstelle einen systemd user-timer der stale Prozesse regelmäßig aufräumt
# Timer muss unter TARGET_USER laufen, nicht unter root!
TARGET_HOME="/home/${TARGET_USER}"
if [ "$CURRENT_USER" = "$TARGET_USER" ]; then
    TARGET_HOME="$HOME"
fi
TIMER_DIR="${TARGET_HOME}/.config/systemd/user"
mkdir -p "$TIMER_DIR"

# Service: Räumt stale Windsurf-Prozesse auf
cat > "${TIMER_DIR}/windsurf-cleanup.service" << 'UNIT'
[Unit]
Description=Cleanup stale Windsurf Remote-SSH server processes

[Service]
Type=oneshot
# Finde Windsurf-Server-Prozesse die älter als 24h sind (definitiv stale)
ExecStart=/bin/bash -c '\
  for pid in $(pgrep -f "windsurf-server" -u $USER 2>/dev/null || true); do \
    ELAPSED=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d " " || echo "0"); \
    if [ "$ELAPSED" -gt 86400 ]; then \
      echo "Killing stale Windsurf process $pid (age: ${ELAPSED}s)"; \
      kill "$pid" 2>/dev/null || true; \
    fi; \
  done'
UNIT

# Timer: Läuft alle 4 Stunden
cat > "${TIMER_DIR}/windsurf-cleanup.timer" << 'TIMER'
[Unit]
Description=Periodic cleanup of stale Windsurf server processes

[Timer]
OnCalendar=*-*-* 00/4:00:00
Persistent=true

[Install]
WantedBy=timers.target
TIMER

# Aktivieren (als User-Service unter TARGET_USER)
if [ "$CURRENT_USER" = "$TARGET_USER" ]; then
    systemctl --user daemon-reload
    systemctl --user enable --now windsurf-cleanup.timer 2>/dev/null || {
        warn "User-Systemd nicht verfügbar — Timer manuell starten:"
        warn "  systemctl --user enable --now windsurf-cleanup.timer"
    }
else
    # Als root: Berechtigungen korrigieren und Linger aktivieren
    chown -R "$TARGET_USER":"$TARGET_USER" "$TIMER_DIR" 2>/dev/null || true
    loginctl enable-linger "$TARGET_USER" 2>/dev/null || true
    
    # Timer für TARGET_USER aktivieren via sudo
    sudo -u "$TARGET_USER" XDG_RUNTIME_DIR="/run/user/$(id -u "$TARGET_USER")" \
        systemctl --user daemon-reload 2>/dev/null || true
    sudo -u "$TARGET_USER" XDG_RUNTIME_DIR="/run/user/$(id -u "$TARGET_USER")" \
        systemctl --user enable --now windsurf-cleanup.timer 2>/dev/null || {
        warn "User-Systemd für ${TARGET_USER} nicht verfügbar."
        warn "Timer manuell aktivieren als ${TARGET_USER}:"
        warn "  systemctl --user enable --now windsurf-cleanup.timer"
    }
fi

info "Cleanup-Timer installiert (alle 4h, stale Prozesse >24h)."
echo ""

# =============================================================================
# SCHRITT 5: Client-seitige SSH-Config Empfehlung
# =============================================================================
echo -e "${BOLD}── Schritt 5: SSH-Client-Config (auf deinem Windows/WSL) ──${RESET}"
echo ""
echo -e "Stelle sicher dass deine ${BOLD}~/.ssh/config${RESET} diese Werte hat:"
echo ""
cat << 'SSH_CONF'
# ── Hetzner Dev-Server (Windsurf Remote-SSH) ─────────────────────
Host hetzner-dev
    HostName <DEV-SERVER-IP>
    User deploy
    IdentityFile ~/.ssh/id_ed25519
    ForwardAgent yes

    # ── Keepalive: Verhindert NAT/Firewall-Timeout ───────────────
    ServerAliveInterval 15
    ServerAliveCountMax 6

    # ── Connection Multiplexing: Beschleunigt Reconnect ──────────
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h-%p
    ControlPersist 600

    # ── Verbindungsrobustheit ────────────────────────────────────
    TCPKeepAlive yes
    ConnectionAttempts 3
    ConnectTimeout 10
SSH_CONF
echo ""
warn "WICHTIG: mkdir -p ~/.ssh/sockets (einmalig auf dem Client)"
echo ""

# =============================================================================
# SCHRITT 6: Node.js Memory-Limit für Windsurf-Server
# =============================================================================
echo -e "${BOLD}── Schritt 6: Node.js Memory-Limit setzen ──${RESET}"

# Windsurf-Server ist Node.js-basiert und kann bei großen Projekten OOM gehen
# NODE_OPTIONS muss in der .bashrc des TARGET_USER gesetzt werden, nicht des ausführenden Users
TARGET_BASHRC="/home/${TARGET_USER}/.bashrc"
if [ "$CURRENT_USER" = "$TARGET_USER" ]; then
    TARGET_BASHRC="$HOME/.bashrc"
fi

if ! grep -q "NODE_OPTIONS.*max-old-space-size" "$TARGET_BASHRC" 2>/dev/null; then
    {
        echo ""
        echo "# ── Windsurf Remote-SSH: Node.js Memory Limit (ADR-042) ──"
        echo "# Verhindert OOM auf CX32 (4GB RAM) bei großen Workspaces"
        echo "export NODE_OPTIONS=\"--max-old-space-size=2048\""
    } >> "$TARGET_BASHRC"
    info "NODE_OPTIONS in ${TARGET_BASHRC} gesetzt (max 2GB für Node.js)."
else
    info "NODE_OPTIONS bereits in .bashrc vorhanden."
fi

echo ""

# =============================================================================
# ZUSAMMENFASSUNG
# =============================================================================
echo -e "${BOLD}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Fix abgeschlossen!                                      ║"
echo "║                                                           ║"
echo "║  Was wurde gemacht:                                       ║"
echo "║  ✅ Stale Windsurf-Prozesse gekillt                      ║"
echo "║  ✅ Port 44341 freigegeben                                ║"
echo "║  ✅ Lock-Dateien bereinigt                                ║"
echo "║  ✅ SSH-Server Keepalive gehärtet (30s/4)                 ║"
echo "║  ✅ Cleanup-Timer installiert (alle 4h)                   ║"
echo "║  ✅ Node.js Memory-Limit gesetzt (2GB)                   ║"
echo "║                                                           ║"
echo "║  Nächster Schritt:                                        ║"
echo "║  → Windsurf auf dem Client schließen                      ║"
echo "║  → SSH-Config auf Client anpassen (siehe oben)            ║"
echo "║  → mkdir -p ~/.ssh/sockets                                ║"
echo "║  → Windsurf neu verbinden                                 ║"
echo "║                                                           ║"
echo "║  Bei erneutem Auftreten:                                  ║"
echo "║    ssh hetzner-dev 'bash ~/fix-windsurf-remote.sh --clean'║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"
