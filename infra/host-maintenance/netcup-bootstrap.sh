#!/usr/bin/env bash
# netcup-bootstrap.sh — Grundinstallation des netcup-Hosts (ADR-289 Phase 1)
#
# Zweck: bringt den netcup-Host (152.53.136.219, Debian 13) auf den Stand, den
#        JEDE der in ADR-289 beschlossenen Rollen (R1 Backup, R2 Monitoring,
#        R3 CI-Runner) braucht. Rollen-neutral — installiert KEINE Rolle.
#
# Warum als Skript und nicht als Handarbeit: ADR-289 §4.2 verlangt die Angleichung
# an ADR-098 (daemon.json, sysctl). Ein Host-Eingriff ohne IaC-Spiegelung driftet
# beim naechsten Host sofort wieder auseinander.
#
# Idempotent: mehrfaches Ausfuehren aendert nichts. Jeder Schritt prueft erst.
# Read-only-Vorschau: DRY_RUN=1 bash netcup-bootstrap.sh
#
# ⚠ Die FIREWALL ist NICHT Teil dieses Skripts — siehe Abschnitt am Ende.
#
# Aufruf (vom Arbeitsplatz):
#   scp infra/host-maintenance/netcup-bootstrap.sh root@152.53.136.219:/root/
#   ssh root@152.53.136.219 'bash /root/netcup-bootstrap.sh'

set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
SWAP_FILE="/swapfile"
SWAP_SIZE_MB="${SWAP_SIZE_MB:-8192}"   # 8 GB bei 31 GB RAM; Bestand faehrt 4-8 GB

log()  { printf '\n=== %s\n' "$*"; }
skip() { printf '  ✓ %s (schon vorhanden, uebersprungen)\n' "$*"; }
did()  { printf '  → %s\n' "$*"; }

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '  [dry-run] %s\n' "$*"
  else
    eval "$@"
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# 0. Vorbedingungen pruefen — abbrechen, bevor irgendetwas geaendert wird
# ─────────────────────────────────────────────────────────────────────────────
log "0. Vorbedingungen"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "FEHLER: root benoetigt." >&2
  exit 1
fi

if ! grep -qi 'debian' /etc/os-release; then
  echo "FEHLER: erwartet Debian (dieses Skript ist fuer den netcup-Host, Debian 13)." >&2
  exit 1
fi

did "OS: $(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"
did "RAM: $(free -m | awk '/Mem:/{print $2}') MiB, CPU: $(nproc)"
did "Disk /: $(df -h --output=avail / | tail -1 | tr -d ' ') frei"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Swap — der Host hat heute KEINEN. Bei 31 GB RAM ohne Swap kippt der
#    OOM-Killer sofort, statt erst zu verlangsamen (Lehre prod 2026-07-20).
# ─────────────────────────────────────────────────────────────────────────────
log "1. Swap (${SWAP_SIZE_MB} MiB)"

if [[ "$(swapon --show --noheadings | wc -l)" -gt 0 ]]; then
  skip "Swap aktiv: $(swapon --show=NAME,SIZE --noheadings | tr '\n' ' ')"
elif [[ -f "$SWAP_FILE" ]]; then
  skip "$SWAP_FILE existiert, wird aktiviert"
  run "swapon '$SWAP_FILE'"
else
  run "fallocate -l ${SWAP_SIZE_MB}M '$SWAP_FILE' || dd if=/dev/zero of='$SWAP_FILE' bs=1M count=${SWAP_SIZE_MB} status=none"
  run "chmod 600 '$SWAP_FILE'"
  run "mkswap '$SWAP_FILE' >/dev/null"
  run "swapon '$SWAP_FILE'"
  did "Swap angelegt und aktiv"
fi

if ! grep -qF "$SWAP_FILE" /etc/fstab; then
  run "printf '%s none swap sw 0 0\n' '$SWAP_FILE' >> /etc/fstab"
  did "fstab-Eintrag ergaenzt (ueberlebt Reboot)"
else
  skip "fstab-Eintrag vorhanden"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 2. sysctl nach ADR-098 §2
#    vm.overcommit_memory=1 ist Pflicht fuer Redis; somaxconn fuer Ingress-Last.
#    vm.swappiness niedrig: Swap als Notreserve, nicht als Dauerbetrieb.
# ─────────────────────────────────────────────────────────────────────────────
log "2. sysctl (ADR-098 §2)"

SYSCTL_FILE="/etc/sysctl.d/99-iil-platform.conf"
if [[ -f "$SYSCTL_FILE" ]]; then
  skip "$SYSCTL_FILE vorhanden"
else
  run "cat > '$SYSCTL_FILE' <<'EOF'
# IIL Platform — ADR-098 §2 (Infrastructure Tuning Standard)
vm.overcommit_memory = 1
net.core.somaxconn = 65535
# Swap als Notreserve, nicht als Dauerbetrieb (Lehre: staging 88.99.38.75 fuhr
# Swap dauerhaft auf 100 %, gemessen 2026-07-30)
vm.swappiness = 10
EOF"
  did "$SYSCTL_FILE geschrieben"
fi
run "sysctl -p '$SYSCTL_FILE' >/dev/null"
did "aktiv: overcommit=$(sysctl -n vm.overcommit_memory) somaxconn=$(sysctl -n net.core.somaxconn) swappiness=$(sysctl -n vm.swappiness)"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Docker + Compose aus dem offiziellen Docker-Repo
#    Debian-eigenes docker.io ist zu alt fuer Compose v2 als Plugin.
# ─────────────────────────────────────────────────────────────────────────────
log "3. Docker + Compose"

if command -v docker >/dev/null 2>&1; then
  skip "Docker vorhanden: $(docker --version)"
else
  run "apt-get update -qq"
  run "apt-get install -y -qq ca-certificates curl gnupg"
  run "install -m 0755 -d /etc/apt/keyrings"
  run "curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc"
  run "chmod a+r /etc/apt/keyrings/docker.asc"
  run "printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian %s stable\n' \
        \"\$(dpkg --print-architecture)\" \"\$(. /etc/os-release && echo \$VERSION_CODENAME)\" \
        > /etc/apt/sources.list.d/docker.list"
  run "apt-get update -qq"
  run "apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
  did "Docker installiert"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 4. daemon.json nach ADR-098 §1
#    Vorlage ist infra/host-maintenance/daemon.json.recommended im platform-Repo.
#    live-restore: Container ueberleben einen Daemon-Neustart.
# ─────────────────────────────────────────────────────────────────────────────
log "4. Docker daemon.json (ADR-098 §1)"

DAEMON_JSON="/etc/docker/daemon.json"
if [[ -f "$DAEMON_JSON" ]] && grep -q 'max-size' "$DAEMON_JSON" 2>/dev/null; then
  skip "$DAEMON_JSON bereits konfiguriert"
else
  run "mkdir -p /etc/docker"
  [[ -f "$DAEMON_JSON" ]] && run "cp '$DAEMON_JSON' '${DAEMON_JSON}.bak-\$(date +%Y%m%d%H%M%S)'"
  run "cat > '$DAEMON_JSON' <<'EOF'
{
  \"log-driver\": \"json-file\",
  \"log-opts\": { \"max-size\": \"20m\", \"max-file\": \"3\" },
  \"builder\": { \"gc\": { \"enabled\": true, \"defaultKeepStorage\": \"20GB\" } },
  \"live-restore\": true
}
EOF"
  run "systemctl restart docker"
  did "daemon.json geschrieben, Docker neu gestartet"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 5. fio — fuer die Nachmessung, die ADR-289 als Vorbedingung von R3 verlangt
# ─────────────────────────────────────────────────────────────────────────────
log "5. fio (Messwerkzeug, ADR-289 §5 Phase 5)"

if command -v fio >/dev/null 2>&1; then
  skip "fio vorhanden: $(fio --version)"
else
  run "apt-get install -y -qq fio"
  did "fio installiert"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 6. Abschlussbericht
# ─────────────────────────────────────────────────────────────────────────────
log "6. Ergebnis"
if [[ "$DRY_RUN" == "1" ]]; then
  echo "  [dry-run] nichts geaendert."
  exit 0
fi
printf '  Swap    : %s\n' "$(swapon --show=NAME,SIZE --noheadings | tr '\n' ' ' || echo 'KEINER')"
printf '  Docker  : %s\n' "$(docker --version 2>/dev/null || echo 'FEHLT')"
printf '  Compose : %s\n' "$(docker compose version --short 2>/dev/null || echo 'FEHLT')"
printf '  fio     : %s\n' "$(fio --version 2>/dev/null || echo 'FEHLT')"
printf '  sysctl  : overcommit=%s somaxconn=%s swappiness=%s\n' \
  "$(sysctl -n vm.overcommit_memory)" "$(sysctl -n net.core.somaxconn)" "$(sysctl -n vm.swappiness)"

cat <<'HINWEIS'

  ⚠ FIREWALL — bewusst NICHT in diesem Skript

  Der netcup-Host hat zwei Firewall-Ebenen, und die wirksame liegt AUSSERHALB
  dieses Skripts:

  1. netcup-Panel-Firewall — im Panel als "Aktiv (0)" gefuehrt: eingeschaltet,
     aber ohne jede Regel. Sie ist nur ueber das netcup-Kundenpanel pflegbar,
     nicht per SSH. DAS ist der richtige Ort fuer die Regeln, weil sie vor dem
     Host greift.
  2. Host-Firewall (nftables/ufw) — hier bewusst nicht aktiviert. Eine
     Host-Firewall aus einer SSH-Sitzung heraus zu aktivieren, kann die eigene
     Sitzung und damit jeden weiteren Zugang abschneiden; ein Aussperren waere
     nur ueber die netcup-Konsole heilbar.

  Aktuell lauscht auf diesem Host ausschliesslich SSH (Port 22) — die
  Angriffsflaeche ist damit minimal. Firewall-Regeln werden erst noetig, wenn
  Rolle R2 (Monitoring) Ports oeffnet. Bis dahin ist Nichtstun die sichere Wahl.

HINWEIS
