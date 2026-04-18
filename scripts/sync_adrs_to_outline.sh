#!/usr/bin/env bash
# sync_adrs_to_outline.sh — Sync finalisierte ADRs aus Git → Outline (Read-Only Mirror)
#
# Fixes K3: set -euo pipefail + idempotente Ausführung + explizite Exit-Codes
#
# Usage:
#   ./sync_adrs_to_outline.sh [--dry-run] [--adr ADR-145]
#
# Environment (from .env or CI secrets):
#   OUTLINE_URL           — z.B. https://knowledge.iil.pet
#   OUTLINE_API_TOKEN     — Personal API Token (read+write)
#   OUTLINE_COLLECTION_ADR_MIRROR — Collection ID für ADR Mirror
#
# Idempotenz-Strategie:
#   - Jedes ADR wird via documents.search gesucht (Titel-Match)
#   - Wenn vorhanden: documents.update (überschreibt Outline-Änderungen — Git ist SSOT)
#   - Wenn nicht vorhanden: documents.create
#   - Der Inhalt bekommt einen READ-ONLY-Header eingefügt

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADR_DIR="${SCRIPT_DIR}/../docs/adr"
DRY_RUN=false
SINGLE_ADR=""

readonly READONLY_HEADER="<!-- AUTO-GENERATED — Änderungen werden beim nächsten Sync überschrieben. Bearbeite die Quelldatei in Git: platform/docs/adr/ -->"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --adr)
            SINGLE_ADR="$2"
            shift 2
            ;;
        *)
            echo "ERROR: Unknown argument: $1" >&2
            echo "Usage: $0 [--dry-run] [--adr ADR-XXX]" >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
if [[ -z "${OUTLINE_URL:-}" ]]; then
    echo "ERROR: OUTLINE_URL not set." >&2
    exit 2
fi

if [[ -z "${OUTLINE_API_TOKEN:-}" ]]; then
    echo "ERROR: OUTLINE_API_TOKEN not set." >&2
    exit 2
fi

if [[ -z "${OUTLINE_COLLECTION_ADR_MIRROR:-}" ]]; then
    echo "ERROR: OUTLINE_COLLECTION_ADR_MIRROR not set." >&2
    exit 2
fi

if ! command -v curl &>/dev/null; then
    echo "ERROR: curl is required but not installed." >&2
    exit 3
fi

if ! command -v jq &>/dev/null; then
    echo "ERROR: jq is required but not installed." >&2
    exit 3
fi

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

outline_post() {
    # outline_post <endpoint> <json-payload>
    # Returns JSON response, exits non-zero on HTTP error.
    local endpoint="$1"
    local payload="$2"

    local response
    response=$(curl \
        --silent \
        --fail \
        --show-error \
        --max-time 30 \
        -X POST \
        -H "Authorization: Bearer ${OUTLINE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        "${OUTLINE_URL}/api/${endpoint}")
    echo "${response}"
}

find_document_by_title() {
    # find_document_by_title <title> <adr_id> → prints document ID or empty string
    #
    # Strategy (FIX for duplicate creation bug):
    #   1. Search by short ADR-ID prefix (e.g. "ADR-130") — avoids Outline
    #      fulltext issues with backticks, quotes, and special characters.
    #   2. Filter results for exact title match in jq.
    #   3. Fallback: paginated documents.list scan if search returns nothing
    #      (covers edge cases where Outline search index is stale).
    local title="$1"
    local adr_id="${2:-}"

    # Primary: search by ADR-ID prefix (short, no special chars)
    local search_term="${adr_id}"
    if [[ -z "${search_term}" ]]; then
        search_term="${title}"
    fi
    local escaped_search
    escaped_search=$(echo "${search_term}" | jq -Rr @json)

    local response
    response=$(outline_post "documents.search" \
        "{\"query\": ${escaped_search}, \"collectionId\": \"${OUTLINE_COLLECTION_ADR_MIRROR}\", \"limit\": 25}") || true

    local found_id
    found_id=$(echo "${response}" | jq -r --arg t "${title}" \
        '[.data[] | select(.document.title == $t) | .document.id] | first // empty' 2>/dev/null || true)

    if [[ -n "${found_id}" ]]; then
        echo "${found_id}"
        return 0
    fi

    # Fallback: paginated list scan (handles search index lag)
    local offset=0
    while true; do
        response=$(outline_post "documents.list" \
            "{\"collectionId\": \"${OUTLINE_COLLECTION_ADR_MIRROR}\", \"limit\": 100, \"offset\": ${offset}}") || true

        found_id=$(echo "${response}" | jq -r --arg t "${title}" \
            '[.data[] | select(.title == $t) | .id] | first // empty' 2>/dev/null || true)

        if [[ -n "${found_id}" ]]; then
            echo "${found_id}"
            return 0
        fi

        # Check if there are more pages
        local count
        count=$(echo "${response}" | jq -r '.data | length' 2>/dev/null || echo "0")
        if [[ "${count}" -lt 100 ]]; then
            break
        fi
        offset=$((offset + 100))
    done

    # Not found — will trigger CREATE
    echo ""
}

sync_adr_file() {
    # sync_adr_file <filepath>
    local filepath="$1"
    local filename
    filename=$(basename "${filepath}")
    local adr_id
    adr_id=$(echo "${filename}" | grep -oP '^ADR-\d+' || true)

    if [[ -z "${adr_id}" ]]; then
        echo "  SKIP: ${filename} (no ADR-NNN prefix)"
        return 0
    fi

    # Read ADR title from first H1 line
    local title
    title=$(grep -m1 '^# ' "${filepath}" | sed 's/^# //' || echo "${adr_id}")

    # Prepend read-only header to content
    local content
    content="${READONLY_HEADER}

$(cat "${filepath}")"

    local escaped_content
    escaped_content=$(echo "${content}" | jq -Rrs @json)
    local escaped_title
    escaped_title=$(echo "${title}" | jq -Rr @json)

    if [[ "${DRY_RUN}" == "true" ]]; then
        echo "  DRY-RUN: Would sync '${title}' (${filename})"
        return 0
    fi

    # Check if document already exists (idempotent)
    local existing_id
    existing_id=$(find_document_by_title "${title}" "${adr_id}")

    if [[ -n "${existing_id}" ]]; then
        echo "  UPDATE: ${title} (id=${existing_id})"
        outline_post "documents.update" \
            "{\"id\": \"${existing_id}\", \"text\": ${escaped_content}, \"done\": true}" \
            > /dev/null
    else
        echo "  CREATE: ${title}"
        outline_post "documents.create" \
            "{\"title\": ${escaped_title}, \"text\": ${escaped_content}, \"collectionId\": \"${OUTLINE_COLLECTION_ADR_MIRROR}\", \"publish\": true}" \
            > /dev/null
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

echo "=== ADR → Outline Sync ==="
echo "  Source:     ${ADR_DIR}"
echo "  Target:     ${OUTLINE_URL} (collection: ${OUTLINE_COLLECTION_ADR_MIRROR})"
echo "  Dry-run:    ${DRY_RUN}"
[[ -n "${SINGLE_ADR}" ]] && echo "  Single ADR: ${SINGLE_ADR}"
echo ""

SYNCED=0
SKIPPED=0
ERRORS=0

if [[ -n "${SINGLE_ADR}" ]]; then
    # Single ADR mode
    adr_file=$(find "${ADR_DIR}" -name "${SINGLE_ADR}*.md" | head -1 || true)
    if [[ -z "${adr_file}" ]]; then
        echo "ERROR: No file found for ${SINGLE_ADR} in ${ADR_DIR}" >&2
        exit 4
    fi
    sync_adr_file "${adr_file}" && SYNCED=$((SYNCED + 1)) || ERRORS=$((ERRORS + 1))
else
    # All ADRs
    while IFS= read -r -d '' adr_file; do
        if sync_adr_file "${adr_file}"; then
            SYNCED=$((SYNCED + 1))
        else
            ERRORS=$((ERRORS + 1))
        fi
    done < <(find "${ADR_DIR}" -name 'ADR-*.md' -print0 | sort -z)
fi

echo ""
echo "=== Done: ${SYNCED} synced, ${SKIPPED} skipped, ${ERRORS} errors ==="

if [[ "${ERRORS}" -gt 0 ]]; then
    exit 5
fi
