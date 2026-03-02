#!/usr/bin/env bash
# sync-repo.sh — Robust git sync for platform repos (WSL + Server)
#
# Problem this solves:
#   When Cascade writes files both via filesystem MCP (locally) AND via GitHub MCP
#   (remote), the local repo accumulates untracked/modified files that block `git pull`.
#   Standard `git pull` fails with "overwritten by merge" / "untracked files" errors.
#
# Strategy:
#   1. Commit any valuable local changes (windsurf-rules, scripts, docs) before pulling
#   2. Pull with --rebase to avoid merge commits
#   3. Report final status
#
# Usage:
#   ./scripts/sync-repo.sh                    # sync current repo
#   ./scripts/sync-repo.sh /path/to/repo      # sync specific repo
#   ./scripts/sync-repo.sh --all              # sync all known platform repos
#
# Safe: never force-pushes, never deletes branches, never resets --hard
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
PLATFORM_BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
KNOWN_REPOS=(
    platform bfagent travel-beat weltenhub risk-hub
    pptx-hub mcp-hub aifw promptfw authoringfw
)

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo "[sync] $*"; }
ok()   { echo "[sync] ✓ $*"; }
warn() { echo "[sync] ⚠ $*" >&2; }
err()  { echo "[sync] ✗ $*" >&2; exit 1; }

sync_repo() {
    local repo_path="$1"
    [[ -d "$repo_path/.git" ]] || err "Not a git repo: $repo_path"

    cd "$repo_path"
    local repo_name
    repo_name="$(basename "$repo_path")"
    log "=== $repo_name ($(pwd)) ==="

    # ── 1. Fetch remote state ──────────────────────────────────────────────────
    log "Fetching origin..."
    git fetch origin

    local branch
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'main')"
    log "Branch: $branch"

    # ── 2. Check for local changes ────────────────────────────────────────────
    local modified untracked
    modified="$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')"
    untracked="$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')"

    if [[ "$modified" -gt 0 || "$untracked" -gt 0 ]]; then
        log "Local changes: $modified modified, $untracked untracked"

        # ── 3. Auto-commit valuable local files ───────────────────────────────
        # These file patterns are written by Cascade locally and should be
        # committed rather than stashed/discarded.
        local to_add=()

        # windsurf-rules — Cascade-generated context rules
        if [[ -d "windsurf-rules" ]]; then
            mapfile -t rules_files < <(git ls-files --others --exclude-standard windsurf-rules/ 2>/dev/null)
            mapfile -t rules_modified < <(git diff --name-only HEAD -- windsurf-rules/ 2>/dev/null)
            to_add+=("${rules_files[@]}" "${rules_modified[@]}")
        fi

        # scripts — platform utility scripts
        if [[ -d "scripts" ]]; then
            mapfile -t script_files < <(git ls-files --others --exclude-standard scripts/ 2>/dev/null)
            to_add+=("${script_files[@]}")
        fi

        # docs/adr — ADR files (the main use case)
        if [[ -d "docs/adr" ]]; then
            mapfile -t adr_files < <(git ls-files --others --exclude-standard docs/adr/ 2>/dev/null)
            mapfile -t adr_modified < <(git diff --name-only HEAD -- docs/adr/ 2>/dev/null)
            to_add+=("${adr_files[@]}" "${adr_modified[@]}")
        fi

        # .windsurf/workflows — workflow files
        if [[ -d ".windsurf/workflows" ]]; then
            mapfile -t wf_files < <(git ls-files --others --exclude-standard .windsurf/workflows/ 2>/dev/null)
            to_add+=("${wf_files[@]}")
        fi

        # Filter empty entries
        local clean_adds=()
        for f in "${to_add[@]}"; do
            [[ -n "$f" ]] && clean_adds+=("$f")
        done

        if [[ "${#clean_adds[@]}" -gt 0 ]]; then
            log "Auto-committing ${#clean_adds[@]} local file(s):"
            for f in "${clean_adds[@]}"; do log "  + $f"; done
            git add "${clean_adds[@]}"
            git commit -m "chore: local sync auto-commit [sync-repo.sh]" || true
        fi

        # ── 4. Stash remaining changes (temp files, .env, etc.) ───────────────
        local remaining_modified remaining_untracked
        remaining_modified="$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')"
        remaining_untracked="$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')"

        if [[ "$remaining_modified" -gt 0 || "$remaining_untracked" -gt 0 ]]; then
            log "Stashing $remaining_modified modified + $remaining_untracked untracked remaining files..."
            git stash push --include-untracked -m "sync-repo.sh auto-stash $(date +%Y-%m-%dT%H:%M:%S)"
        fi
    fi

    # ── 5. Pull with rebase ────────────────────────────────────────────────────
    log "Pulling origin/$branch with rebase..."
    if git pull --rebase origin "$branch"; then
        ok "$repo_name synced to origin/$branch"
    else
        warn "Rebase conflict — attempting abort + plain merge..."
        git rebase --abort 2>/dev/null || true
        git merge "origin/$branch" -m "chore: sync merge [sync-repo.sh]" || {
            err "Merge failed for $repo_name — resolve manually: cd $repo_path && git status"
        }
    fi

    # ── 6. Restore stash if any ───────────────────────────────────────────────
    local stash_count
    stash_count="$(git stash list | wc -l | tr -d ' ')"
    if [[ "$stash_count" -gt 0 ]]; then
        log "Restoring stash..."
        git stash pop || warn "Stash pop had conflicts — check: git stash list"
    fi

    # ── 7. Final status ───────────────────────────────────────────────────────
    local final_status
    final_status="$(git status --short | wc -l | tr -d ' ')"
    if [[ "$final_status" -eq 0 ]]; then
        ok "$repo_name — clean"
    else
        warn "$repo_name — $final_status change(s) remain (expected for local work):"
        git status --short | head -20
    fi
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    if [[ "${1:-}" == "--all" ]]; then
        local base
        base="$(dirname "$PLATFORM_BASE")"
        log "Syncing all known repos in $base"
        for repo in "${KNOWN_REPOS[@]}"; do
            local rpath="$base/$repo"
            if [[ -d "$rpath/.git" ]]; then
                sync_repo "$rpath" || warn "Failed: $repo (continuing)"
            else
                warn "Skipping $repo — not found at $rpath"
            fi
        done
    elif [[ -n "${1:-}" ]]; then
        sync_repo "$(realpath "$1")"
    else
        # Default: sync the repo containing this script (platform)
        sync_repo "$PLATFORM_BASE"
    fi

    log "=== Done ==="
}

main "$@"
