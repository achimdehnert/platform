#!/usr/bin/env bash
# =============================================================================
# BF Agent Platform — Developer Environment Setup
# =============================================================================
#
# Richtet die lokale Entwicklungsumgebung ein:
#   1. Prüft Voraussetzungen (Python, Git)
#   2. Installiert pre-commit
#   3. Installiert Git Hooks (pre-commit + commit-msg)
#   4. Führt initialen Testlauf durch
#
# Verwendung:
#   chmod +x scripts/setup-dev-env.sh
#   ./scripts/setup-dev-env.sh
#
# Voraussetzungen:
#   - Python >= 3.12
#   - Git >= 2.28 (für `init.defaultBranch`)
#   - pip oder pipx
#
# Exit Codes:
#   0 = Erfolgreich
#   1 = Voraussetzung fehlt
#   2 = Installation fehlgeschlagen
# =============================================================================

set -euo pipefail

# ── Farben ──────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' BOLD='' RESET=''
fi

info()    { echo -e "${BLUE}ℹ️  $1${RESET}"; }
success() { echo -e "${GREEN}✅ $1${RESET}"; }
warn()    { echo -e "${YELLOW}⚠️  $1${RESET}"; }
error()   { echo -e "${RED}❌ $1${RESET}" >&2; }

# ── Header ──────────────────────────────────────────────────────────────────
echo -e "${BOLD}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     BF Agent Platform — Developer Setup                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# ── 1. Voraussetzungen prüfen ───────────────────────────────────────────────
info "Prüfe Voraussetzungen..."

# Git
if ! command -v git &> /dev/null; then
    error "Git nicht gefunden. Bitte installieren: https://git-scm.com/"
    exit 1
fi
GIT_VERSION=$(git --version | grep -oE '[0-9]+\.[0-9]+')
success "Git $(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"

# Python
if ! command -v python3 &> /dev/null; then
    error "Python 3 nicht gefunden."
    exit 1
fi
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    error "Python >= 3.11 erforderlich (gefunden: $PY_VERSION)"
    exit 1
fi
success "Python $PY_VERSION"

# Git-Repo prüfen
if ! git rev-parse --is-inside-work-tree &> /dev/null; then
    error "Nicht in einem Git-Repository. Bitte aus dem Repo-Root ausführen."
    exit 1
fi
success "Git-Repository erkannt: $(basename "$(git rev-parse --show-toplevel)")"

# ── 2. pre-commit installieren ──────────────────────────────────────────────
info "Installiere pre-commit..."

if command -v pre-commit &> /dev/null; then
    PC_VERSION=$(pre-commit --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    success "pre-commit bereits installiert (v${PC_VERSION})"
else
    # Versuche pip, dann pipx
    if command -v pipx &> /dev/null; then
        info "Installiere via pipx..."
        pipx install pre-commit
    elif command -v pip &> /dev/null; then
        info "Installiere via pip..."
        pip install pre-commit --break-system-packages 2>/dev/null || pip install pre-commit
    else
        error "Weder pip noch pipx gefunden. Bitte manuell installieren:"
        error "  pip install pre-commit"
        exit 2
    fi
    success "pre-commit installiert"
fi

# ── 3. .pre-commit-config.yaml prüfen ──────────────────────────────────────
if [ ! -f ".pre-commit-config.yaml" ]; then
    error ".pre-commit-config.yaml nicht gefunden im Repo-Root."
    error "Bitte zuerst die Konfiguration aus dem Deliverables-Ordner kopieren."
    exit 1
fi
success ".pre-commit-config.yaml gefunden"

# ── 4. Git Hooks installieren ───────────────────────────────────────────────
info "Installiere Git Hooks..."

# pre-commit Stage (Linting, Formatting, Security)
pre-commit install --hook-type pre-commit
success "pre-commit Hook installiert"

# commit-msg Stage (Commit-Message-Validierung)
pre-commit install --hook-type commit-msg
success "commit-msg Hook installiert"

# ── 5. Commit-Message-Script ausführbar machen ──────────────────────────────
if [ -f "scripts/check-commit-msg.sh" ]; then
    chmod +x scripts/check-commit-msg.sh
    success "scripts/check-commit-msg.sh ausführbar gemacht"
else
    warn "scripts/check-commit-msg.sh nicht gefunden — Commit-Message-Hook wird ohne Custom-Script laufen"
fi

# ── 6. Initialer Testlauf ──────────────────────────────────────────────────
info "Führe initialen Hook-Testlauf durch..."
echo ""

# Ersten Lauf durchführen (installiert Hook-Environments)
if pre-commit run --all-files; then
    success "Alle Hooks bestanden!"
else
    warn "Einige Hooks haben Fehler gefunden (siehe oben)."
    warn "Das ist normal beim ersten Lauf — die Hooks haben evtl. Auto-Fixes angewendet."
    warn "Prüfe die Änderungen mit: git diff"
fi

# ── 7. Zusammenfassung ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Setup abgeschlossen!                                    ║"
echo "║                                                           ║"
echo "║  Installierte Hooks:                                      ║"
echo "║    • pre-commit: Ruff Lint, Format, Security, Hygiene     ║"
echo "║    • commit-msg: [TAG] module: description                ║"
echo "║                                                           ║"
echo "║  Nützliche Befehle:                                       ║"
echo "║    pre-commit run --all-files    # Alle Hooks manuell     ║"
echo "║    pre-commit autoupdate         # Hook-Versionen updaten ║"
echo "║    pre-commit run ruff-check     # Nur Ruff Lint          ║"
echo "║    git commit --no-verify        # Hooks überspringen     ║"
echo "║                                  # (nur im Notfall!)      ║"
echo "║                                                           ║"
echo "║  Commit-Format:                                           ║"
echo "║    [FIX] travel-beat: prevent duplicate booking           ║"
echo "║    [IMP] mcp-hub: add retry logic to tool calls           ║"
echo "║    [MIG] bfagent: add genre FK replacing string field     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"
