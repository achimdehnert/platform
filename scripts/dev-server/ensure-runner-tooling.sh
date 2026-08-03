#!/usr/bin/env bash
# ensure-runner-tooling.sh — Werkzeuge, die Workflow-JOBS auf einem
# self-hosted Runner voraussetzen. Als root auf dem Runner-Host ausfuehren.
#
# Idempotent und eigenstaendig aufrufbar: install-runner.sh ruft es beim
# Neuaufsetzen, auf BESTEHENDEN Hosts wird es einzeln nachgezogen. Genau das
# war die Luecke — install-runner.sh laeuft nur einmal bei der Erstinstallation,
# ein spaeter dazugekommenes Werkzeug erreicht damit keinen laufenden Host.
#
# Warum `gh` hier steht: mehrere Cron-Melder (backup-meter, sync-drift-meter)
# rufen `gh` in ihrem MELDE-Schritt auf. Fehlt es, stirbt genau dieser Schritt
# mit `gh: command not found` (exit 127) — der Melder ERKENNT seinen Fund
# korrekt (exit 1 im Schritt davor), kann ihn aber nicht mehr melden. Ein Fund,
# den niemand zu sehen bekommt, ist von einem nicht erkannten Fund nicht zu
# unterscheiden. Auf 88.198.191.108 war `gh` nie installiert, auf 88.99.38.75
# von Hand nachgezogen; die Provisionierungsliste in ADR-042 kennt es nicht.
# Realfall: platform#1508.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "FEHLER: als root ausfuehren." >&2; exit 1; }

install_gh() {
    if command -v gh >/dev/null 2>&1; then
        echo "  gh vorhanden: $(gh --version | head -1)"
        return 0
    fi
    echo "  gh fehlt — installiere aus cli.github.com ..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /etc/apt/keyrings/githubcli-archive-keyring.gpg
    chmod 0644 /etc/apt/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list
    apt-get update -qq
    apt-get install -y -qq gh
    echo "  gh installiert: $(gh --version | head -1)"
}

echo "=== Runner-Job-Werkzeuge (platform#1508) ==="
install_gh

# Abschliessende Probe: der Aufruf muss aus einer nicht-interaktiven Shell
# heraus gehen, so wie der Runner ihn ausfuehrt — `command -v` in DIESER Shell
# wuerde einen PATH-Unterschied der Service-Unit nicht bemerken.
if bash -lc 'command -v gh' >/dev/null 2>&1; then
    echo "OK: gh ist aus einer Login-Shell erreichbar."
else
    echo "WARN: gh installiert, aber nicht im PATH einer Login-Shell — PATH der Runner-Unit pruefen." >&2
    exit 1
fi
