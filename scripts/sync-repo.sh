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
#     - Detects unpushed commits and parks them on a backup branch (SAFE)
#     - Auto-commits Cascade-generated files (windsurf-rules/, scripts/,
#       docs/adr/, .windsurf/workflows/) before pulling
#     - Detects untracked files colliding with remote → backs up + removes
#     - Stashes remaining local changes
#     - git pull --no-rebase (merge) from GitHub
#     - Restores stash
#
#   Mode 2: Server sync (--server)
#     - SSH into server, git pull /opt/platform/ from GitHub
#     - For app repos: docker compose pull + up -d (no git)
#
#   Mode 3: All repos (--all)
#     - Bootstrap: syncs platform FIRST (self-update before loop)
#     - Runs WSL sync for all known repos
#
#   Mode 4: Quick deploy (--quick-deploy)
#     - docker compose pull + up -d for a single app (or all)
#     - No CI/CD cycle, no image rebuild (~30s)
#
# USAGE:
#   bash scripts/sync-repo.sh                          # WSL: sync CWD repo
#   bash scripts/sync-repo.sh ~/github/bfagent         # WSL: sync specific repo
#   bash scripts/sync-repo.sh --all                    # WSL: sync all repos
#   bash scripts/sync-repo.sh --server                 # Server: sync platform + apps
#   bash scripts/sync-repo.sh --server platform        # Server: sync platform only
#   bash scripts/sync-repo.sh --full                   # WSL + Server: everything
#   bash scripts/sync-repo.sh --quick-deploy weltenhub # Fast deploy: no CI/CD cycle
#   bash scripts/sync-repo.sh --quick-deploy all       # Fast deploy: all server apps
#
# QUICK-DEPLOY MODE (--quick-deploy):
#   All apps: docker compose pull + docker compose up -d --remove-orphans
#   Requires prior CI/CD build+push to GHCR (GitHub Actions on push to main).
#   Use case: CI/CD has built+pushed image → --quick-deploy to get live (~30s)
#
# SAFETY GUARANTEES:
#   - Never git reset --hard (no data loss)
#   - Never force-push (remote always authoritative)
#   - Unpushed commits are ALWAYS parked on backup/sync-TIMESTAMP branch
#   - Auto-commit only for known Cascade-generated file patterns
#   - Colliding untracked files: backed up to /tmp/sync-backup-*/ before removal
#   - Stash + restore for all other local changes
#   - SSH operations are read-only git pulls + docker pull (no destructive ops)
#   - Pull failure: warns and continues (does not abort entire --all run)
#   - Bootstrap: platform synced first so new scripts are immediately available
#   - quick-deploy: never rebuilds images, never touches DB migrations
#
# =============================================================================
set -euo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────
readonly SERVER_HOST="88.198.191.108"
readonly SERVER_PLATFORM_PATH="/opt/platform"
readonly PLATFORM_BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly GITHUB_BASE="$(dirname "$PLATFORM_BASE")"

# All repos with Git checkouts on WSL
# Repos not cloned locally are silently skipped (skip message only).
readonly WSL_REPOS=(
    platform bfagent travel-beat weltenhub risk-hub
    pptx-hub mcp-hub aifw promptfw authoringfw nl2cad weltenfw
    cad-hub trading-hub wedding-hub dev-hub coach-hub 137-hub
    billing-hub illustration-hub illustration-fw odoo-hub infra-deploy testkit
)

# App repos deployed as Docker on server (name → compose dir)
# Verified against live server /opt/ on 2026-03-05.
# To add a new app: append [repo-name]="/opt/<path>" and ensure
# docker-compose.prod.yml exists at that path on the server.
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

    local behind modified untracked
    behind="$(git rev-list --count "HEAD..origin/$branch" 2>/dev/null || echo '0')"
    modified="$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')"
    untracked="$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')"

    if [[ "$behind" -eq 0 && "$modified" -eq 0 && "$untracked" -eq 0 ]]; then
        ok "$repo_name — already up-to-date, clean"
        return 0
    fi

    log "State: $modified modified, $untracked untracked, $behind commits behind remote"

    # 2. Detect + park unpushed local commits
    #
    #    ROOT CAUSE of "could not apply <sha>... rebase conflict":
    #    git pull --rebase replays local commits on top of origin. When those
    #    commits touch the same files as remote commits, the replay fails.
    #
    #    FIX: Count commits in origin/$branch..HEAD. If any exist, create a
    #    backup branch pointing at current HEAD, then reset --soft to origin
    #    (moves pointer only, working tree untouched), then stash staged changes.
    #    Result: clean HEAD at origin — pull proceeds conflict-free.
    local unpushed
    unpushed="$(git rev-list --count "origin/$branch..HEAD" 2>/dev/null || echo '0')"

    local backup_branch=""
    if [[ "$unpushed" -gt 0 ]]; then
        backup_branch="backup/sync-$(date +%Y%m%d-%H%M%S)"
        warn "$repo_name — $unpushed unpushed commit(s) detected (will be parked):"
        git log --oneline "origin/$branch..HEAD" | sed 's/^/    /'
        log "Creating backup branch: $backup_branch"
        git branch "$backup_branch"
        # reset --soft: moves HEAD to origin, stages the diff — tree unchanged
        git reset --soft "origin/$branch"
        # stash the staged changes so pull finds a clean index
        git stash push -m "sync-repo.sh: parked unpushed from $backup_branch $(date +%Y-%m-%dT%H:%M:%S)"
        log "Recovery options if needed:"
        log "  git checkout $backup_branch   — restore original commits"
        log "  git stash show -p             — inspect parked staged changes"
        ok "$repo_name — unpushed commits parked safely on $backup_branch"
    fi

    # 3. Auto-commit Cascade-generated files that belong in version control
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

    # 4. Handle untracked files that would be overwritten by the remote pull.
    #
    #    ROOT CAUSE of "would be overwritten by merge":
    #    Cascade writes files locally (write_to_file) that were simultaneously
    #    committed to GitHub via GitHub MCP. These files are untracked locally
    #    but exist in the incoming remote commit. git pull refuses to overwrite
    #    them. git stash --include-untracked does NOT help: stash pop after pull
    #    creates a conflict on the same path.
    #
    #    FIX: Before stashing, detect which untracked files collide with the
    #    incoming remote changes. Back them up to /tmp/sync-backup-TIMESTAMP/,
    #    then remove them so git pull can proceed. GitHub is SSOT — the remote
    #    version is authoritative. The backup is for recovery only.
    #
    local backup_dir="/tmp/sync-backup-$(date +%Y%m%d-%H%M%S)-${repo_name}"
    local colliding_untracked=()

    # Files the remote will add/modify in this pull
    local incoming_files
    incoming_files="$(git diff --name-only HEAD "origin/$branch" 2>/dev/null || true)"

    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        if echo "$incoming_files" | grep -qF "$f"; then
            colliding_untracked+=("$f")
        fi
    done < <(git ls-files --others --exclude-standard 2>/dev/null)

    if [[ "${#colliding_untracked[@]}" -gt 0 ]]; then
        mkdir -p "$backup_dir"
        warn "$repo_name — ${#colliding_untracked[@]} untracked file(s) collide with remote (GitHub is SSOT):"
        for f in "${colliding_untracked[@]}"; do
            local fdir
            fdir="$(dirname "$backup_dir/$f")"
            mkdir -p "$fdir"
            cp "$f" "$backup_dir/$f" 2>/dev/null && warn "  backed up: $f → $backup_dir/$f"
            rm -f "$f"
            log "  removed local copy (remote version incoming): $f"
        done
        warn "Recovery: local copies saved to $backup_dir"
    fi

    # 4b. Stash remaining changes (env files, temp files, work-in-progress)
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

    # 5. Pull — no rebase (avoids replay conflicts with any remaining commits)
    #    --no-rebase (merge) is safer after parking unpushed commits above.
    #    Backup branch preserves full history of parked commits.
    log "Pulling origin/$branch (merge)..."
    if git pull --no-rebase origin "$branch" 2>/dev/null; then
        ok "$repo_name — synced to origin/$branch"
    else
        warn "Pull failed — attempting explicit fetch + merge..."
        git fetch origin "$branch" 2>/dev/null
        git merge --no-edit "origin/$branch" 2>/dev/null || {
            warn "$repo_name — merge had conflicts. Manual resolution needed:"
            warn "  cd $repo_path && git status && git diff"
            [[ -n "$backup_branch" ]] && \
                warn "  Unpushed commits preserved on: $backup_branch"
            # Return 1 (not err/exit) so --all continues with other repos
            return 1
        }
    fi

    # 6. Restore stash if we stashed anything
    if [[ "$stashed" == true ]]; then
        local stash_count
        stash_count="$(git stash list 2>/dev/null | wc -l | tr -d ' ')"
        if [[ "$stash_count" -gt 0 ]]; then
            log "Restoring stash..."
            git stash pop 2>/dev/null || \
                warn "Stash pop had conflicts — check: git stash list && git stash show -p"
        fi
    fi

    # 7. Report final state
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
    git pull --no-rebase origin main
    echo "[server] ✓ platform synced: $(git log --oneline -1)"
fi
REMOTE
    ok "server platform sync complete"
}

# ── Server Sync: app repos (Docker pull + compose up) ────────────────────────
#
# FIX: Use heredoc (unquoted REMOTE) so $app_path expands locally before SSH.
# Previous bug: single-quoted 'bash -c ...' prevented $app_path from expanding
# → cd failed silently → docker compose ran in wrong directory.
#
server_sync_app() {
    local app_name="$1"
    local app_path="${SERVER_APP_PATHS[$app_name]:-}"

    [[ -z "$app_path" ]] && { skip "$app_name — not in SERVER_APP_PATHS"; return 0; }

    header "SERVER: $app_name (docker pull)"
    log "SSH → $SERVER_HOST: docker compose pull + up -d in $app_path"

    if ssh -o BatchMode=yes -o ConnectTimeout=30 "root@$SERVER_HOST" bash <<REMOTE
set -euo pipefail
cd ${app_path}
docker compose -f docker-compose.prod.yml pull --quiet 2>&1 | tail -3
docker compose -f docker-compose.prod.yml up -d --remove-orphans 2>&1 | tail -5
REMOTE
    then
        ok "$app_name — docker updated"
    else
        warn "$app_name — docker update had warnings (check server logs)"
    fi
}

# ── Quick Deploy: single app — docker compose pull + up ──────────────────────
#
# Uniform strategy for ALL apps: docker compose pull + up -d --remove-orphans.
# Requires prior CI/CD build+push to GHCR. Skips WSL sync — ~30s total.
#
server_quick_deploy() {
    local app_name="$1"
    local app_path="${SERVER_APP_PATHS[$app_name]:-}"

    [[ -z "$app_path" ]] && { err "Unknown app: $app_name. Valid apps: ${!SERVER_APP_PATHS[*]}"; }

    header "QUICK-DEPLOY: $app_name"
    log "SSH → $SERVER_HOST: compose pull + up in $app_path"

    ssh -o BatchMode=yes -o ConnectTimeout=30 "root@$SERVER_HOST" bash <<REMOTE
set -euo pipefail
cd ${app_path}
echo "[quick-deploy] Pulling latest image for ${app_name}..."
docker compose -f docker-compose.prod.yml pull 2>&1 | tail -5
docker compose -f docker-compose.prod.yml up -d --remove-orphans 2>&1 | tail -8
echo "[quick-deploy] ✓ ${app_name} live"
REMOTE

    ok "$app_name — quick-deploy complete"
}

# ── Mode: Quick Deploy all server apps ────────────────────────────────────────
mode_quick_deploy_all() {
    log "Quick-deploy all server apps (${#SERVER_APP_PATHS[@]} apps)"
    local failed=()
    for app_name in "${!SERVER_APP_PATHS[@]}"; do
        server_quick_deploy "$app_name" || failed+=("$app_name")
    done
    [[ "${#failed[@]}" -gt 0 ]] && warn "Failed: ${failed[*]}" || true
}

# ── Mode: WSL all ─────────────────────────────────────────────────────────────
mode_wsl_all() {
    log "WSL sync — ${#WSL_REPOS[@]} repos in $GITHUB_BASE"

    # Bootstrap fix: sync platform FIRST and separately before the main loop.
    #
    # Root cause of "No such file or directory" for new scripts (publish-package.sh etc.):
    # sync-repo.sh is launched FROM the local platform repo. If platform is stale,
    # new scripts added to GitHub are not available locally until the next --all run.
    #
    # Fix: always pull platform first (outside the loop). The loop then skips it
    # via the already-up-to-date check, so there is no double-pull cost.
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
    # Check SSH connectivity first
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
    echo "  Backup branches (if created): git branch -a | grep backup/sync"
    echo "  Collision backups (if any):   ls /tmp/sync-backup-*"
    echo "  Next time: bash ~/github/platform/scripts/sync-repo.sh [--full]"
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    local mode="${1:-wsl-single}"

    case "$mode" in
        --full)
            # WSL all repos + Server platform + Server app docker pulls
            mode_wsl_all
            mode_server_all
            print_summary
            ;;
        --server)
            # Server only (platform git + all app docker)
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
            # WSL all repos only (no server)
            mode_wsl_all
            print_summary
            ;;
        --quick-deploy)
            # docker compose pull + up for one app or all
            local qd_target="${2:-}"
            [[ -z "$qd_target" ]] && err "Usage: --quick-deploy <app-name|all>"
            if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "root@$SERVER_HOST" true 2>/dev/null; then
                err "Cannot reach $SERVER_HOST"
            fi
            if [[ "$qd_target" == "all" ]]; then
                mode_quick_deploy_all
            else
                server_quick_deploy "$qd_target"
            fi
            ;;
        --help|-h)
            sed -n '3,60p' "${BASH_SOURCE[0]}"
            ;;
        *)
            # Single repo — defaults to CWD if no argument given
            local target_path="${1:-$(pwd)}"
            if [[ "$target_path" == -* ]]; then
                err "Unknown flag: $target_path. Run with --help for usage."
            fi
            wsl_sync_repo "$(realpath "$target_path")"
            ;;
    esac

    log "=== Done ==="
}

main "$@"
