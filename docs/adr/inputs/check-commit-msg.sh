#!/usr/bin/env bash
# =============================================================================
# BF Agent Platform — Commit Message Validator
# =============================================================================
#
# Enforces the platform commit message convention:
#
#   [TAG] module: short description (10-72 chars total)
#
#   Optional body: Explain WHY, not WHAT.
#   The diff shows WHAT changed.
#
#   Refs: ADR-009, PLATFORM_ARCHITECTURE_MASTER §2.3
#   Closes #123
#
# Allowed tags:
#   [FIX] Bug fix                    [IMP] Improvement
#   [REF] Refactoring                [SEC] Security
#   [MIG] DB Migration               [ADR] Architecture Decision Record
#   [MOV] Move files                 [REV] Revert
#   [REL] Release                    [DOC] Documentation
#   [TST] Tests                      [CI]  CI/CD
#   [MERGE] Merge commit             [WIP] Work in Progress (feature branches only)
#
# Installation:
#   pre-commit: wird automatisch über .pre-commit-config.yaml installiert
#   manuell:    cp scripts/check-commit-msg.sh .git/hooks/commit-msg && chmod +x .git/hooks/commit-msg
#
# Exit Codes:
#   0 = OK
#   1 = Validation failed (mit Fehlerbeschreibung auf stderr)
#
# Referenz: Odoo Git Guidelines (adaptiert für BF Agent Platform)
# Siehe:    CONTRIBUTING.md, Abschnitt "Commit Messages"
# =============================================================================

set -euo pipefail

# ── Konfiguration ───────────────────────────────────────────────────────────

# Erlaubte Tags — erweitert gegenüber Odoo um SEC, MIG, ADR, DOC, TST, CI, WIP
ALLOWED_TAGS="FIX|IMP|REF|SEC|MIG|ADR|MOV|REV|REL|DOC|TST|CI|MERGE|WIP"

# Minimale / maximale Länge der Header-Zeile (Tag + Modul + Beschreibung)
MIN_HEADER_LENGTH=15
MAX_HEADER_LENGTH=72

# Erlaubte Modulnamen: lowercase, Ziffern, Bindestriche, Unterstriche
# Beispiele: bfagent, travel-beat, mcp-hub, platform-core, creative-services
# Minimum 2 Zeichen: erster Buchstabe + mindestens ein weiteres Zeichen
MODULE_PATTERN='[a-z][a-z0-9_-]+'

# ── Hilfsfunktionen ────────────────────────────────────────────────────────

# Farbausgabe (nur wenn Terminal vorhanden)
if [ -t 2 ]; then
    RED='\033[0;31m'
    YELLOW='\033[0;33m'
    GREEN='\033[0;32m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED='' YELLOW='' GREEN='' BOLD='' RESET=''
fi

error() {
    echo -e "${RED}${BOLD}❌ Commit Message Fehler:${RESET} $1" >&2
}

hint() {
    echo -e "${YELLOW}   💡 $1${RESET}" >&2
}

success() {
    echo -e "${GREEN}✅ Commit message OK${RESET}" >&2
}

show_format() {
    cat >&2 <<'EOF'

   Erwartetes Format:
   ┌─────────────────────────────────────────────────────────────┐
   │ [TAG] modul: kurze Beschreibung                            │
   │                                                             │
   │ Optionaler Body: Erkläre WARUM, nicht WAS.                 │
   │ Das Diff zeigt WAS geändert wurde.                         │
   │                                                             │
   │ Refs: ADR-009                                               │
   │ Closes #123                                                 │
   └─────────────────────────────────────────────────────────────┘

   Erlaubte Tags:
     [FIX] Bug fix           [IMP] Improvement      [REF] Refactoring
     [SEC] Security          [MIG] DB Migration      [ADR] Architecture Decision
     [MOV] Move files        [REV] Revert            [REL] Release
     [DOC] Documentation     [TST] Tests             [CI]  CI/CD
     [MERGE] Merge commit    [WIP] Work in Progress (nur Feature Branches)

   Beispiele:
     [FIX] travel-beat: prevent duplicate booking on race condition
     [IMP] mcp-hub: add retry logic to llm_mcp tool calls
     [MIG] bfagent: add genre FK replacing string field
     [SEC] platform-core: add RLS policy for tenant isolation
     [DOC] creative-services: add prompt template usage guide

EOF
}

# ── Hauptlogik ──────────────────────────────────────────────────────────────

main() {
    local commit_msg_file="$1"

    # Commit-Message-Datei lesen
    if [ ! -f "$commit_msg_file" ]; then
        error "Commit-Message-Datei nicht gefunden: $commit_msg_file"
        exit 1
    fi

    # Erste Zeile extrahieren (Header)
    # Kommentare (# ...) und leere Zeilen am Anfang überspringen
    local header
    header=$(grep -v '^#' "$commit_msg_file" | grep -v '^$' | head -1)

    # Leere Commits abfangen
    if [ -z "$header" ]; then
        error "Leere Commit-Message."
        show_format
        exit 1
    fi

    # ── Merge-Commits durchlassen ───────────────────────────────────────
    # Git generiert automatisch "Merge branch ..." Messages.
    # Diese sind valide und dürfen nicht blockiert werden.
    if echo "$header" | grep -qE '^Merge (branch|pull request|remote-tracking)'; then
        success
        exit 0
    fi

    # ── Revert-Commits durchlassen ──────────────────────────────────────
    # Git generiert "Revert ..." Messages bei `git revert`.
    if echo "$header" | grep -qE '^Revert "'; then
        success
        exit 0
    fi

    # ── Tag validieren ──────────────────────────────────────────────────
    if ! echo "$header" | grep -qE "^\[(${ALLOWED_TAGS})\] "; then
        error "Ungültiger oder fehlender Tag am Anfang."
        hint "Header beginnt mit: '$header'"
        hint "Erwartete Tags: $(echo "$ALLOWED_TAGS" | tr '|' ', ')"
        show_format
        exit 1
    fi

    # Tag extrahieren für spätere Prüfungen
    local tag
    tag=$(echo "$header" | grep -oE "^\[([A-Z]+)\]" | tr -d '[]')

    # ── Modulname validieren ────────────────────────────────────────────
    # Format nach Tag: "[TAG] modul: beschreibung"
    # MERGE-Commits dürfen "various" als Modul verwenden
    if ! echo "$header" | grep -qE "^\[${tag}\] ${MODULE_PATTERN}: "; then
        error "Ungültiger oder fehlender Modulname nach [${tag}]."
        hint "Header: '$header'"
        hint "Erwartetes Format: [${tag}] modulname: beschreibung"
        hint "Modulname: nur Kleinbuchstaben, Ziffern, Bindestriche (z.B. travel-beat, mcp-hub)"
        show_format
        exit 1
    fi

    # ── Beschreibung extrahieren und prüfen ─────────────────────────────
    # Alles nach "modul: " ist die Beschreibung
    local description
    description=$(echo "$header" | sed -E "s/^\[${tag}\] ${MODULE_PATTERN}: //")

    if [ -z "$description" ]; then
        error "Beschreibung nach Modulname fehlt."
        hint "Format: [${tag}] modul: hier kommt die Beschreibung"
        show_format
        exit 1
    fi

    # Beschreibung darf nicht mit Großbuchstabe beginnen (Konvention: lowercase)
    # Ausnahme: Eigennamen, Akronyme (z.B. "Django", "RLS", "HTMX")
    local first_char
    first_char=$(echo "$description" | cut -c1)
    if echo "$first_char" | grep -qE '^[A-Z]$'; then
        # Prüfe ob es ein bekanntes Akronym/Eigenname ist
        local first_word
        first_word=$(echo "$description" | awk '{print $1}')
        # Erlaubte Eigennamen/Akronyme am Anfang
        local allowed_proper="Django|PostgreSQL|HTMX|RLS|DSGVO|API|MCP|CI|CD|GitHub|Docker|Hetzner|WSL|ORM|SQL|CSS|HTML|JS|YAML|JSON|Stripe|OpenAI|Anthropic|Pydantic|Sphinx|Terraform|Alpine"
        if ! echo "$first_word" | grep -qE "^(${allowed_proper})"; then
            hint "Beschreibung sollte mit Kleinbuchstabe beginnen: '${description}'"
            hint "Ausnahme: Akronyme/Eigennamen (RLS, Django, HTMX, ...)"
            # Warnung, kein Fehler — um Akzeptanz nicht zu gefährden
        fi
    fi

    # ── Header-Länge prüfen ─────────────────────────────────────────────
    local header_length=${#header}

    if [ "$header_length" -lt "$MIN_HEADER_LENGTH" ]; then
        error "Header zu kurz (${header_length} Zeichen, Minimum: ${MIN_HEADER_LENGTH})."
        hint "Beschreibe die Änderung aussagekräftig."
        exit 1
    fi

    if [ "$header_length" -gt "$MAX_HEADER_LENGTH" ]; then
        error "Header zu lang (${header_length} Zeichen, Maximum: ${MAX_HEADER_LENGTH})."
        hint "Kürze den Header und nutze den Body für Details."
        hint "Odoo-Konvention: ~50 Zeichen ideal, max. 72."
        exit 1
    fi

    # ── Body-Validierung (optional, aber wenn vorhanden) ────────────────
    # Zweite Zeile muss leer sein (Trenner zwischen Header und Body)
    local line_count
    line_count=$(grep -cv '^#' "$commit_msg_file" | tr -d ' ')
    local second_line
    second_line=$(grep -v '^#' "$commit_msg_file" | sed -n '2p')

    if [ "$line_count" -gt 1 ] && [ -n "$second_line" ]; then
        error "Zweite Zeile muss leer sein (Trenner zwischen Header und Body)."
        hint "Zeile 2 enthält: '${second_line}'"
        exit 1
    fi

    # ── WIP-Tag Warnung ─────────────────────────────────────────────────
    if [ "$tag" = "WIP" ]; then
        hint "⚠️  [WIP] ist nur für Feature-Branches erlaubt."
        hint "Vor dem Merge in main bitte Tag ändern (z.B. [IMP], [FIX])."
        # Kein Fehler — erlaubt auf Feature Branches
    fi

    # ── Alles OK ────────────────────────────────────────────────────────
    success
    exit 0
}

# ── Entry Point ─────────────────────────────────────────────────────────────

# pre-commit übergibt die Commit-Message-Datei als erstes Argument
if [ $# -lt 1 ]; then
    echo "Usage: $0 <commit-message-file>" >&2
    echo "       Wird normalerweise als Git commit-msg Hook aufgerufen." >&2
    exit 1
fi

main "$1"
