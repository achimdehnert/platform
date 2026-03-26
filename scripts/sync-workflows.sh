#!/usr/bin/env bash
# sync-workflows.sh — Platform Workflows als Symlinks in alle Repos verteilen
#
# Single Source of Truth: platform/.windsurf/workflows/
# Repos bekommen Symlinks statt Kopien → immer aktuell.
#
# Usage:
#   ./scripts/sync-workflows.sh           # Alle Repos
#   ./scripts/sync-workflows.sh --dry-run # Nur anzeigen, nichts ändern
#   ./scripts/sync-workflows.sh risk-hub  # Nur ein Repo
#
# Kategorien:
#   UNIVERSAL   — Jedes Repo bekommt diese Workflows
#   DJANGO_HUB  — Nur Django-Hubs (deploybare Services)
#   PACKAGE     — Nur Python-Packages (PyPI)
#   PLATFORM    — Nur platform selbst (bleiben dort)

set -euo pipefail

GITHUB_DIR="${GITHUB_DIR:-/home/dehnert/github}"
PLATFORM_WF="${GITHUB_DIR}/platform/.windsurf/workflows"
DRY_RUN=false
SINGLE_REPO=""

# --- Workflow-Kategorien ---

# Jedes Repo bekommt diese
UNIVERSAL=(
    knowledge-capture
    agent-session-start
    agentic-coding
    adr
    adr-review
    pr-review
    governance-check
    repo-health-check
    hotfix
    windsurf-clean
    workflow-index
    sync-repo
    use-case
)

# Nur Django-Hubs (deploybare Services mit Docker)
DJANGO_HUB=(
    deploy
    deploy-check
    backup
    testing-setup
    testing-conventions
    onboard-repo
    onboard-repo-testing-addendum
    new-github-project
    stack-upgrade
)

# Nur Python-Packages (PyPI)
PACKAGE=(
    release
)

# Nur platform (werden NICHT verteilt)
# cascade-auftraege, idea-intake, agent-review

# --- Repo-Typen ---

DJANGO_HUBS=(
    risk-hub billing-hub cad-hub coach-hub trading-hub pptx-hub
    travel-beat weltenhub wedding-hub recruiting-hub dms-hub
    ausschreibungs-hub illustration-hub research-hub writing-hub
    learn-hub dev-hub odoo-hub mcp-hub 137-hub bfagent
)

PACKAGES=(
    aifw authoringfw promptfw illustration-fw learnfw weltenfw
    outlinefw researchfw testkit iil-dvelop-client openclaw
)

# --- Parse Args ---

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [repo-name]"
            echo ""
            echo "Sync platform workflows as symlinks to all repos."
            echo "  --dry-run   Show what would be done, don't change anything"
            echo "  repo-name   Only sync a single repo"
            exit 0
            ;;
        *) SINGLE_REPO="$arg" ;;
    esac
done

# --- Functions ---

in_array() {
    local needle="$1"; shift
    for item in "$@"; do
        [[ "$item" == "$needle" ]] && return 0
    done
    return 1
}

sync_workflow() {
    local repo_dir="$1"
    local workflow="$2"
    local repo_name
    repo_name=$(basename "$repo_dir")

    local wf_dir="${repo_dir}/.windsurf/workflows"
    local target="${PLATFORM_WF}/${workflow}.md"
    local link="${wf_dir}/${workflow}.md"

    # Source muss existieren
    if [[ ! -f "$target" ]]; then
        echo "  WARN: ${workflow}.md nicht in platform gefunden"
        return
    fi

    # Zielverzeichnis anlegen
    if [[ ! -d "$wf_dir" ]]; then
        if $DRY_RUN; then
            echo "  MKDIR: ${wf_dir}"
        else
            mkdir -p "$wf_dir"
        fi
    fi

    # Bereits korrekter Symlink?
    if [[ -L "$link" ]]; then
        local current
        current=$(readlink "$link")
        if [[ "$current" == "$target" ]]; then
            return  # Bereits korrekt
        fi
        # Falscher Symlink → ersetzen
        if $DRY_RUN; then
            echo "  FIX-LINK: ${workflow}.md (${current} → ${target})"
        else
            rm "$link"
            ln -s "$target" "$link"
            echo "  FIX-LINK: ${workflow}.md"
        fi
        return
    fi

    # Eigene Datei vorhanden → durch Symlink ersetzen
    if [[ -f "$link" ]]; then
        if $DRY_RUN; then
            echo "  REPLACE: ${workflow}.md (eigene Kopie → Symlink)"
        else
            rm "$link"
            ln -s "$target" "$link"
            echo "  REPLACE: ${workflow}.md"
        fi
        return
    fi

    # Neu anlegen
    if $DRY_RUN; then
        echo "  LINK: ${workflow}.md"
    else
        ln -s "$target" "$link"
        echo "  LINK: ${workflow}.md"
    fi
}

sync_repo() {
    local repo_dir="$1"
    local repo_name
    repo_name=$(basename "$repo_dir")

    # platform selbst skippen
    [[ "$repo_name" == "platform" ]] && return

    # Repo-Typ bestimmen
    local is_django=false
    local is_package=false
    in_array "$repo_name" "${DJANGO_HUBS[@]}" && is_django=true
    in_array "$repo_name" "${PACKAGES[@]}" && is_package=true

    local type_label="other"
    $is_django && type_label="django-hub"
    $is_package && type_label="package"

    local changes=0

    # Universal Workflows
    for wf in "${UNIVERSAL[@]}"; do
        local before
        before=$(sync_workflow "$repo_dir" "$wf" 2>&1)
        if [[ -n "$before" ]]; then
            if [[ $changes -eq 0 ]]; then
                echo "📦 ${repo_name} (${type_label})"
            fi
            echo "$before"
            changes=$((changes + 1))
        fi
    done

    # Django-Hub Workflows
    if $is_django; then
        for wf in "${DJANGO_HUB[@]}"; do
            local before
            before=$(sync_workflow "$repo_dir" "$wf" 2>&1)
            if [[ -n "$before" ]]; then
                if [[ $changes -eq 0 ]]; then
                    echo "📦 ${repo_name} (${type_label})"
                fi
                echo "$before"
                changes=$((changes + 1))
            fi
        done
    fi

    # Package Workflows
    if $is_package; then
        for wf in "${PACKAGE[@]}"; do
            local before
            before=$(sync_workflow "$repo_dir" "$wf" 2>&1)
            if [[ -n "$before" ]]; then
                if [[ $changes -eq 0 ]]; then
                    echo "📦 ${repo_name} (${type_label})"
                fi
                echo "$before"
                changes=$((changes + 1))
            fi
        done
    fi
}

# --- Main ---

echo "=== Workflow Sync ==="
echo "Source: ${PLATFORM_WF}"
echo "Workflows: ${#UNIVERSAL[@]} universal + ${#DJANGO_HUB[@]} django-hub + ${#PACKAGE[@]} package"
$DRY_RUN && echo "Mode: DRY-RUN (keine Änderungen)"
echo ""

if [[ -n "$SINGLE_REPO" ]]; then
    repo_dir="${GITHUB_DIR}/${SINGLE_REPO}"
    if [[ ! -d "$repo_dir" ]]; then
        echo "ERROR: Repo '${SINGLE_REPO}' nicht gefunden in ${GITHUB_DIR}"
        exit 1
    fi
    sync_repo "$repo_dir"
else
    for repo_dir in "${GITHUB_DIR}"/*/; do
        [[ -d "$repo_dir" ]] && sync_repo "$repo_dir"
    done
fi

echo ""
echo "=== Done ==="
