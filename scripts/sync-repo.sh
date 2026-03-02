#!/usr/bin/env bash
# =============================================================================
# sync-repo.sh — Platform-wide 3-Node Sync: WSL ↔ GitHub ↔ Server
# =============================================================================
#
# ARCHITECTURE:
#   GitHub           = Single Source of Truth for ALL repos
#   WSL              = Developer workstation — Git checkouts in ~/github/<repo>
#   Server           = Hetzner 88.198.191.108
#                      - /opt/platform/  : Git checkout (docs, scripts, ADRs)
#                      - /opt/<app>/     : Docker-only, updated via docker pull
#
# USAGE:
#   bash scripts/sync-repo.sh                         # WSL: sync platform only
#   bash scripts/sync-repo.sh ~/github/bfagent        # WSL: sync specific repo
#   bash scripts/sync-repo.sh --all                   # WSL: all 14 repos
#   bash scripts/sync-repo.sh --server                # Server: platform git + all apps docker
#   bash scripts/sync-repo.sh --server platform       # Server: platform only
#   bash scripts/sync-repo.sh --server bfagent        # Server: bfagent docker pull only
#   bash scripts/sync-repo.sh --full                  # WSL --all + Server --all
#
# SAFETY GUARANTEES:
#   - Never git reset --hard (no data loss)
#   - Never force-push (remote always authoritative)
#   - Auto-commit only for known Cascade-generated file patterns
#   - Stash + restore for all other local changes
#   - SSH operations: read-only git pulls + docker pull/up (no destructive ops)
#
# =============================================================================
set -euo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────
readonly SERVER_HOST="88.198.191.108"
readonly SERVER_PLATFORM_PATH="/opt/platform"
readonly PLATFORM_BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
readonly GITHUB_BASE="$(dirname "$PLATFORM_BASE")"

# All repos with Git checkouts on WSL
readonly WSL_REPOS=(
    platform bfagent travel-beat weltenhub risk-hub
    pptx-hub mcp-hub aifw promptfw authoringfw
    cad-hub trading-hub wedding-hub dev-hub
)

# App repos on server: name → compose directory (Docker-only, no git checkout)
declare -A SERVER_APP_PATHS=(
    [bfagent]="/opt/bfagent-app"
    [travel-beat]="/opt/travel-beat"
    [weltenhub]="/opt/weltenhub"
    [risk-hub]="/opt/risk-hub"
    [pptx-hub]="/opt/pptx-hub"
    [trading-hub]="/opt/trading-hub"
    [wedding-hub]="/opt/wedding-hub"
    [cad-hub]="/opt/cad-hub"
)

# ── Logging ───────────────────────────────────────────────────────────────────
_BOLD='\033[1m'; _GREEN='\033[0;32m'; _YELLOW='\033[1;33m'
_RED='\033[0;31m'; _RESET='\033[0m'

log()    { echo -e "[sync]  $*"; }
header() { echo -e "\n${_BOLD}[sync] ══ $* ══${_RESET}"; }
ok()     { echo -e "${_GREEN}[sync] ✓${_RESET} $*"; }
warn()   { echo -e "${_YELLOW}[sync] ⚠${_RESET} $*" >&2; }
err()    { echo -e "${_RED}[sync] ✗${_RESET} $*" >&2; exit 1; }
skip()   { echo -e "[sync] – $* (skipped)"; }

# ── WSL Sync: single repo ─────────────────────────────────────────────────────
wsl_sync_repo() {
    local repo_path="$1"
    [[ -d "$repo_path/.git" ]] || { skip "Not a git repo: $repo_path"; return 0; }

    cd "$repo_path"
    local repo_name
    repo_name="$(basename "$repo_path")"
    header "WSL: $repo_name"

    # 1. Fetch to know remote state without changing anything
    log "Fetching origin..."
    git fetch origin 2>/dev/null

    local branch
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'main')"

    local behind modified untracked
    behind="$(git rev-list --count "HEAD..origin/$branch" 2>/dev/null || echo '0')"
    modified="$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')"
    untracked="$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')"

    if [[ "$behind" -eq 0 && "$modified" -eq 0 && "$untracked" -eq 0 ]]; then
        ok "$repo_name — already up-to-date, clean"
        return 0
    fi

    log "State: $modified modified, $untracked untracked, $behind commit(s) behind remote"

    # 2. Auto-commit Cascade-generated files (they belong in version control)
    if [[ "$modified" -gt 0 || "$untracked" -gt 0 ]]; then
        local to_add=()
        local -a patterns=(
            "windsurf-rules/"
            "scripts/"
            "docs/adr/"
            ".windsurf/workflows/"
            "docs/CORE_CONTEXT.md"
            "docs/AGENT_HANDOVER.md"
        )

        for pattern in "${patterns[@]}"; do
            if [[ -e "$pattern" || -d "$pattern" ]]; then
                while IFS= read -r f; do
                    [[ -n "$f" ]] && to_add+=("$f")
                done < <(git ls-files --others --exclude-standard "$pattern" 2>/dev/null)
                while IFS= read -r f; do
                    [[ -n "$f" ]] && to_add+=("$f")
                done < <(git diff --name-only HEAD -- "$pattern" 2>/dev/null)
            fi
        done

        if [[ "${#to_add[@]}" -gt 0 ]]; then
            log "Auto-committing ${#to_add[@]} Cascade-generated file(s):"
            for f in "${to_add[@]}"; do log "  + $f"; done
            git add "${to_add[@]}"
            git diff --cached --quiet || \
                git commit -m "chore: sync auto-commit — Cascade-generated files [sync-repo.sh $(date +%Y-%m-%d)]"
        fi
    fi

    # 3. Stash remaining changes (.env, temp files, WIP code)
    local remaining_m remaining_u stashed=false
    remaining_m="$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')"
    remaining_u="$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')"

    if [[ "$remaining_m" -gt 0 || "$remaining_u" -gt 0 ]]; then
        log "Stashing $remaining_m modified + $remaining_u untracked files..."
        git stash push --include-untracked \
            -m "sync-repo.sh auto-stash $(date +%Y-%m-%dT%H:%M:%S)" 2>/dev/null \
            && stashed=true
    fi

    # 4. Pull with rebase — clean linear history
    log "Pulling origin/$branch --rebase..."
    if git pull --rebase origin "$branch" 2>/dev/null; then
        ok "$repo_name — synced to origin/$branch"
    else
        warn "Rebase conflict — aborting, falling back to merge..."
        git rebase --abort 2>/dev/null || true
        git merge --no-edit "origin/$branch" \
            -m "chore: sync merge fallback [sync-repo.sh]" || {
            err "$repo_name — merge failed. Manual fix: cd $repo_path && git status"
        }
    fi

    # 5. Restore stash
    if [[ "$stashed" == true ]]; then
        local stash_count
        stash_count="$(git stash list 2>/dev/null | wc -l | tr -d ' ')"
        if [[ "$stash_count" -gt 0 ]]; then
            log "Restoring stash..."
            git stash pop 2>/dev/null || \
                warn "Stash pop had conflicts — check: git stash list && git stash show -p"
        fi
    fi

    # 6. Report
    local final
    final="$(git status --short 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "$final" -eq 0 ]]; then
        ok "$repo_name — clean ✓"
    else
        ok "$repo_name — synced ($final local change(s) preserved)"
        git status --short | head -10 | sed 's/^/  /'
    fi
}

# ── Server Sync: platform Git checkout ────────────────────────────────────────
server_sync_platform() {
    header "SERVER: platform (git pull /opt/platform)"
    ssh -o BatchMode=yes -o ConnectTimeout=10 "root@$SERVER_HOST" bash <<'REMOTE'
set -euo pipefail
cd /opt/platform
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
if [[ "$BEHIND" -eq 0 ]]; then
    echo "[server] ✓ platform already up-to-date: $(git log --oneline -1)"
else
    echo "[server] $BEHIND commit(s) behind — pulling..."
    git pull --rebase origin main
    echo "[server] ✓ synced: $(git log --oneline -1)"
fi
REMOTE
    ok "server /opt/platform synced"
}

# ── Server Sync: app Docker pull + compose up ──────────────────────────────────
server_sync_app() {
    local app_name="$1"
    local app_path="${SERVER_APP_PATHS[$app_name]:-}"
    [[ -z "$app_path" ]] && { skip "$app_name — not in SERVER_APP_PATHS"; return 0; }

    header "SERVER: $app_name (docker pull + compose up)"
    # shellcheck disable=SC2029
    ssh -o BatchMode=yes -o ConnectTimeout=10 "root@$SERVER_HOST" \
        "cd $app_path \
         && docker compose -f docker-compose.prod.yml pull --quiet 2>&1 | tail -2 \
         && docker compose -f docker-compose.prod.yml up -d --remove-orphans 2>&1 | tail -3" \
    && ok "$app_name — docker updated" \
    || warn "$app_name — docker update had warnings"
}

# ── Mode: WSL all repos ────────────────────────────────────────────────────────
mode_wsl_all() {
    log "WSL sync: ${#WSL_REPOS[@]} repos under $GITHUB_BASE"
    local failed=()
    for repo in "${WSL_REPOS[@]}"; do
        local rpath="$GITHUB_BASE/$repo"
        if [[ -d "$rpath/.git" ]]; then
            wsl_sync_repo "$rpath" || failed+=("$repo")
        else
            skip "$repo — not cloned at $rpath"
        fi
    done
    [[ "${#failed[@]}" -gt 0 ]] && warn "Failed: ${failed[*]}" || true
}

# ── Mode: Server all ───────────────────────────────────────────────────────────
mode_server_all() {
    if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "root@$SERVER_HOST" true 2>/dev/null; then
        err "Cannot reach $SERVER_HOST — check SSH connectivity"
    fi
    server_sync_platform
    for app_name in "${!SERVER_APP_PATHS[@]}"; do
        server_sync_app "$app_name" || warn "$app_name server sync failed (continuing)"
    done
}

# ── Summary ────────────────────────────────────────────────────────────────────
print_summary() {
    echo ""
    echo -e "${_BOLD}[sync] ══ Summary ══${_RESET}"
    echo "  GitHub = Source of Truth (authoritative, unchanged)"
    echo "  WSL    = all local checkouts pulled to GitHub HEAD"
    echo "  Server = /opt/platform pulled + app containers updated (if --server/--full)"
    echo ""
    echo "  Repeat: bash ~/github/platform/scripts/sync-repo.sh [--full]"
    echo ""
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
    local mode="${1:-wsl-single}"
    case "$mode" in
        --full)
            mode_wsl_all
            mode_server_all
            print_summary
            ;;
        --server)
            local target="${2:-all}"
            case "$target" in
                all)      mode_server_all ;;
                platform) server_sync_platform ;;
                *)        server_sync_app "$target" ;;
            esac
            ;;
        --all)
            mode_wsl_all
            print_summary
            ;;
        --help|-h)
            grep '^#' "${BASH_SOURCE[0]}" | head -30 | sed 's/^# \?//'
            ;;
        -*)
            err "Unknown flag: $mode. Use --help for usage."
            ;;
        *)
            # Single repo path, or default to platform
            wsl_sync_repo "$(realpath "${1:-$PLATFORM_BASE}")"
            ;;
    esac
    log "=== Done ==="
}

main "$@"
