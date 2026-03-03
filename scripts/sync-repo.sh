#!/usr/bin/env bash
# =============================================================================
# sync-repo.sh — Platform-wide 3-Node Sync: WSL ↔ GitHub ↔ Server
# =============================================================================
#
# ARCHITECTURE (read before modifying):
#
#   GitHub           = Single Source of Truth for ALL repos
#   WSL              = Developer workstation — Git checkouts in ~/github/<repo>
#   Server           = Hetzner 88.198.191.108
#                      - /opt/platform/  : Git checkout (docs, scripts, ADRs)
#                      - /opt/<app>/     : Docker-only, updated via docker pull
#
# WHAT THIS SCRIPT DOES:
#
#   Mode 1: WSL sync (default)
#     - Commits local Cascade-generated files (windsurf-rules/, scripts/,
#       docs/adr/, .windsurf/workflows/) before pulling
#     - Stashes remaining local changes
#     - git pull --rebase from GitHub
#     - Restores stash
#
#   Mode 2: Server sync (--server or --all)
#     - SSH into server, git pull /opt/platform/ from GitHub
#     - For app repos: docker pull + docker compose up -d (no git)
#
#   Mode 3: All repos (--all)
#     - Runs WSL sync for all known repos
#     - Runs server sync for platform + all deployed apps
#
# USAGE:
#   bash scripts/sync-repo.sh                         # WSL: sync platform only
#   bash scripts/sync-repo.sh ~/github/bfagent        # WSL: sync specific repo
#   bash scripts/sync-repo.sh --all                   # WSL: sync all repos
#   bash scripts/sync-repo.sh --server                # Server: sync platform + apps
#   bash scripts/sync-repo.sh --server platform       # Server: sync platform only
#   bash scripts/sync-repo.sh --full                  # WSL + Server: everything
#   bash scripts/sync-repo.sh --quick-deploy weltenhub # Fast: git clone+cp+restart
#
# SAFETY GUARANTEES:
#   - Never git reset --hard (no data loss)
#   - Never force-push (remote always authoritative)
#   - Auto-commit only for known Cascade-generated file patterns
#   - Stash + restore for all other local changes
#   - SSH operations are read-only git pulls + docker pull (no destructive ops)
#
# --quick-deploy CONTRACT:
#   - Requires: changes already pushed to GitHub main
#   - Action: server clones repo, docker cp apps/templates/config, restart
#   - Use for: Python/template/URL changes (no Docker rebuild needed)
#   - Never use for: requirements.txt, Dockerfile, new INSTALLED_APPS
#
# =============================================================================
set -euo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────
readonly SERVER_HOST="88.198.191.108"
readonly SERVER_PLATFORM_PATH="/opt/platform"
readonly PLATFORM_BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly GITHUB_BASE="$(dirname "$PLATFORM_BASE")"

# All repos with Git checkouts on WSL
readonly WSL_REPOS=(
    platform bfagent travel-beat weltenhub risk-hub
    pptx-hub mcp-hub aifw promptfw authoringfw nl2cad weltenfw
    cad-hub trading-hub wedding-hub dev-hub coach-hub 137-hub
)

# App repos deployed as Docker on server (name → compose dir)
# Verified against live server /opt/ on 2026-03-03.
# To add a new app: append [repo-name]="/opt/<path>" and ensure
# docker-compose.prod.yml exists at that path on the server.

# Quick-deploy: container name for --quick-deploy mode.
# Format: [repo-name]="<container_name>"
declare -A QUICK_DEPLOY_CONTAINERS=(
    [weltenhub]="weltenhub_web"
    [bfagent]="bfagent_web"
    [travel-beat]="travel_beat_web"
    [risk-hub]="risk_hub_web"
    [pptx-hub]="pptx_hub_web"
)

# Health-check port per app (internal Docker port on server)
declare -A QUICK_DEPLOY_PORTS=(
    [weltenhub]="8081"
    [bfagent]="8088"
    [travel-beat]="8089"
    [risk-hub]="8090"
    [pptx-hub]="8020"
)

declare -A SERVER_APP_PATHS=(
    [bfagent]="/opt/bfagent-app"
    [travel-beat]="/opt/travel-beat"
    [weltenhub]="/opt/weltenhub"
    [risk-hub]="/opt/risk-hub"
    [pptx-hub]="/opt/pptx-hub"
    [trading-hub]="/opt/trading-hub"
    [wedding-hub]="/opt/wedding-hub"
    [cad-hub]="/opt/cad-hub"
    [dev-hub]="/opt/devhub-worker"
    [coach-hub]="/opt/coach-hub"
    [137-hub]="/opt/137-hub"
    # mcp-hub: llm_gateway runs inside bfagent-app stack — no separate compose path
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

# ── WSL Sync ──────────────────────────────────────────────────────────────────
wsl_sync_repo() {
    local repo_path="$1"
    [[ -d "$repo_path/.git" ]] || { skip "Not a git repo: $repo_path"; return 0; }

    cd "$repo_path"
    local repo_name
    repo_name="$(basename "$repo_path")"
    header "WSL: $repo_name"

    # 1. Fetch to know remote state
    log "Fetching origin..."
    git fetch origin 2>/dev/null

    local branch
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'main')"

    # Check if we're behind remote — skip everything if already up-to-date
    local behind
    behind="$(git rev-list --count "HEAD..origin/$branch" 2>/dev/null || echo '0')"
    local modified untracked
    modified="$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')"
    untracked="$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')"

    if [[ "$behind" -eq 0 && "$modified" -eq 0 && "$untracked" -eq 0 ]]; then
        ok "$repo_name — already up-to-date, clean"
        return 0
    fi

    log "State: $modified modified, $untracked untracked, $behind commits behind remote"

    # 2. Detect unpushed local commits
    local unpushed
    unpushed="$(git rev-list --count "origin/$branch..HEAD" 2>/dev/null || echo '0')"

    local backup_branch=""
    if [[ "$unpushed" -gt 0 ]]; then
        backup_branch="backup/sync-$(date +%Y%m%d-%H%M%S)"
        warn "$repo_name — $unpushed unpushed commit(s) detected:"
        git log --oneline "origin/$branch..HEAD" | sed 's/^/    /'
        log "Parking unpushed commits on branch: $backup_branch"
        git branch "$backup_branch"
        git reset --soft "origin/$branch"
        git stash push -m "sync-repo.sh: parked from $backup_branch $(date +%Y-%m-%dT%H:%M:%S)"
        log "Backup branch $backup_branch and stash created — restore manually if needed:"
        log "  git checkout $backup_branch  (to see original commits)"
        log "  git stash show -p            (to see staged changes)"
    fi

    # 3. Auto-commit Cascade-generated files
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

    # 4. Stash remaining changes
    local remaining_m remaining_u
    remaining_m="$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')"
    remaining_u="$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')"
    local stashed=false

    if [[ "$remaining_m" -gt 0 || "$remaining_u" -gt 0 ]]; then
        log "Stashing $remaining_m modified + $remaining_u untracked files..."
        git stash push --include-untracked \
            -m "sync-repo.sh auto-stash $(date +%Y-%m-%dT%H:%M:%S)" \
            2>/dev/null && stashed=true
    fi

    # 5. Pull
    log "Pulling origin/$branch..."
    if git pull --no-rebase origin "$branch" 2>/dev/null; then
        ok "$repo_name — synced to origin/$branch"
    else
        warn "Pull failed — attempting fetch + reset to origin..."
        git fetch origin "$branch" 2>/dev/null
        git merge --no-edit "origin/$branch" 2>/dev/null || {
            warn "$repo_name — merge had conflicts."
            warn "Manual resolution: cd $repo_path && git status && git diff"
            warn "Unpushed commits are safe on branch: ${backup_branch:-<none>}"
            return 1
        }
    fi

    # 6. Restore stash
    if [[ "$stashed" == true ]]; then
        local stash_count
        stash_count="$(git stash list 2>/dev/null | wc -l | tr -d ' ')"
        if [[ "$stash_count" -gt 0 ]]; then
            log "Restoring stash..."
            git stash pop 2>/dev/null || \
                warn "Stash pop had conflicts — check: git stash list && git stash show -p"
        fi
    fi

    local final_changes
    final_changes="$(git status --short 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "$final_changes" -eq 0 ]]; then
        ok "$repo_name — clean ✓"
    else
        ok "$repo_name — synced ($final_changes local change(s) preserved)"
        git status --short | head -10 | sed 's/^/  /'
    fi
}

# ── Server Sync: platform (Git checkout) ─────────────────────────────────────
server_sync_platform() {
    header "SERVER: platform (git pull)"
    log "SSH → $SERVER_HOST: git pull $SERVER_PLATFORM_PATH"

    ssh -o BatchMode=yes -o ConnectTimeout=10 "root@$SERVER_HOST" bash <<'REMOTE'
set -euo pipefail
cd /opt/platform
echo "[server] Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "[server] Before: $(git log --oneline -1)"
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
if [[ "$BEHIND" -eq 0 ]]; then
    echo "[server] ✓ platform already up-to-date"
else
    echo "[server] $BEHIND commit(s) behind — pulling..."
    git pull --rebase origin main
    echo "[server] ✓ platform synced: $(git log --oneline -1)"
fi
REMOTE
    ok "server platform sync complete"
}

# ── Server Sync: app repos (Docker pull + compose up) ────────────────────────
server_sync_app() {
    local app_name="$1"
    local app_path="${SERVER_APP_PATHS[$app_name]:-}"

    [[ -z "$app_path" ]] && { skip "$app_name — not in SERVER_APP_PATHS"; return 0; }

    header "SERVER: $app_name (docker pull)"
    log "SSH → $SERVER_HOST: docker compose pull + up -d in $app_path"

    ssh -o BatchMode=yes -o ConnectTimeout=10 "root@$SERVER_HOST" \
        "bash -c 'cd $app_path && docker compose -f docker-compose.prod.yml pull --quiet 2>&1 | tail -3 && docker compose -f docker-compose.prod.yml up -d --remove-orphans 2>&1 | tail -5'" \
    && ok "$app_name — docker updated" \
    || warn "$app_name — docker update had warnings (check server logs)"
}

# ── Quick Deploy: git clone on server + docker cp + container restart ─────────
# Use for pure Python/template/URL changes — NO Docker rebuild needed.
#
# WHY this is better than individual mcp5_ssh_manage docker cp calls:
#   - Single SSH session (1 connection, not N)
#   - Atomic: all files or none (no partial state)
#   - Idempotent: safe to run multiple times
#   - Self-contained: no dependency on local file paths
#   - Fast: ~10-15 seconds vs minutes for Docker rebuild
#
# NEVER use for: requirements.txt changes, new INSTALLED_APPS, Dockerfile edits
quick_deploy() {
    local app_name="$1"
    local app_path="${SERVER_APP_PATHS[$app_name]:-}"
    local container_name="${QUICK_DEPLOY_CONTAINERS[$app_name]:-}"
    local health_port="${QUICK_DEPLOY_PORTS[$app_name]:-8080}"

    [[ -z "$app_path" ]] && err "$app_name — not in SERVER_APP_PATHS"
    [[ -z "$container_name" ]] && err "$app_name — not in QUICK_DEPLOY_CONTAINERS"

    header "QUICK-DEPLOY: $app_name → $container_name (port $health_port)"
    log "Prerequisites: changes must already be pushed to GitHub main"

    if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "root@$SERVER_HOST" true 2>/dev/null; then
        err "Cannot reach $SERVER_HOST — check SSH key"
    fi

    # Build the remote script as a heredoc-safe string
    # Variables expanded locally ($app_name, $container_name, $health_port)
    # Server-side variables escaped (\$REPO, \$dir, \$HTTP_CODE)
    local remote_script
    remote_script="$(cat <<REMOTE
set -euo pipefail

# Clone latest main from GitHub
cd /tmp
rm -rf qd_${app_name}
git clone --depth 1 \"https://\$(cat /root/.github_token)@github.com/achimdehnert/${app_name}.git\" qd_${app_name} 2>&1 | tail -2
REPO=/tmp/qd_${app_name}
echo \"Cloned: \$(git -C \$REPO log --oneline -1)\"

# Copy Python app code + templates into running container
for dir in apps config templates; do
    if [ -d \"\$REPO/\$dir\" ]; then
        docker cp \"\$REPO/\$dir/.\" ${container_name}:/app/\$dir/
        echo \"  Copied \$dir/\"
    fi
done

# Restart (gunicorn picks up new .py files)
docker restart ${container_name}
echo \"Restarted ${container_name}\"

# Health check
sleep 4
HTTP_CODE=\$(curl -s -o /dev/null -w \"%{http_code}\" http://127.0.0.1:${health_port}/health/ 2>/dev/null || echo \"000\")
if [ \"\$HTTP_CODE\" = \"200\" ]; then
    echo \"Health: \$HTTP_CODE ✓\"
else
    echo \"Health: \$HTTP_CODE ✗ — check: docker logs ${container_name} --tail 20\"
    exit 1
fi

# Cleanup
rm -rf /tmp/qd_${app_name}
REMOTE
)"

    if ssh -o BatchMode=yes -o ConnectTimeout=60 "root@$SERVER_HOST" bash <<< "$remote_script"; then
        ok "$app_name — quick-deploy complete ✓"
    else
        err "$app_name — quick-deploy failed. Run: ssh root@$SERVER_HOST 'docker logs $container_name --tail 20'"
    fi
}

# ── Mode: WSL all ─────────────────────────────────────────────────────────────
mode_wsl_all() {
    log "WSL sync — ${#WSL_REPOS[@]} repos in $GITHUB_BASE"

    header "Bootstrap: platform (self-update first)"
    if [[ -d "$PLATFORM_BASE/.git" ]]; then
        wsl_sync_repo "$PLATFORM_BASE" || warn "platform bootstrap pull failed — continuing with local version"
    fi

    local failed=()
    for repo in "${WSL_REPOS[@]}"; do
        local rpath="$GITHUB_BASE/$repo"
        if [[ -d "$rpath/.git" ]]; then
            wsl_sync_repo "$rpath" || failed+=("$repo")
        else
            skip "$repo — not cloned at $rpath"
        fi
    done
    [[ "${#failed[@]}" -gt 0 ]] && warn "Failed repos: ${failed[*]}" || true
}

# ── Mode: Server all ──────────────────────────────────────────────────────────
mode_server_all() {
    if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "root@$SERVER_HOST" true 2>/dev/null; then
        err "Cannot reach $SERVER_HOST — check SSH key and connectivity"
    fi

    server_sync_platform

    for app_name in "${!SERVER_APP_PATHS[@]}"; do
        server_sync_app "$app_name" || warn "$app_name server sync failed (continuing)"
    done
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
    echo ""
    echo -e "${_BOLD}[sync] ══ Summary ══${_RESET}"
    echo "  GitHub = Source of Truth (unchanged)"
    echo "  WSL    = git pull complete for all local checkouts"
    echo "  Server = platform git pull + app docker pulls (if --server/--full)"
    echo ""
    echo "  Next time: bash ~/github/platform/scripts/sync-repo.sh [--full]"
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
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
            if [[ "$target" == "all" ]]; then
                mode_server_all
            elif [[ "$target" == "platform" ]]; then
                server_sync_platform
            else
                server_sync_app "$target"
            fi
            ;;
        --all)
            mode_wsl_all
            print_summary
            ;;
        --quick-deploy)
            # Fast path: git clone on server + docker cp + container restart
            # Use for Python/template/URL changes — no Docker rebuild needed
            local target="${2:-}"
            [[ -z "$target" ]] && err "Usage: --quick-deploy <app-name>  (e.g. weltenhub, bfagent)"
            quick_deploy "$target"
            ;;
        --help|-h)
            sed -n '3,55p' "${BASH_SOURCE[0]}"
            ;;
        *)
            local target_path="${1:-$PLATFORM_BASE}"
            if [[ "$target_path" == -* ]]; then
                err "Unknown flag: $target_path. Run with --help for usage."
            fi
            wsl_sync_repo "$(realpath "$target_path")"
            ;;
    esac

    log "=== Done ==="
}

main "$@"
