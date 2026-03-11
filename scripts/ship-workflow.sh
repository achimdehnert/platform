#!/usr/bin/env bash
# =============================================================================
# platform/scripts/ship-workflow.sh — ADR-120 Master Deploy Script
# =============================================================================
# EINZIGES Deploy-Script — lebt nur in platform, wird nie kopiert.
#
#   Staging:     ./scripts/ship-workflow.sh staging risk-hub
#   Production:  ./scripts/ship-workflow.sh production risk-hub
#   Promote:     ./scripts/ship-workflow.sh promote risk-hub
#   Rollback:    ./scripts/ship-workflow.sh rollback risk-hub v1.2.3
#   Status:      ./scripts/ship-workflow.sh status [repo]
#   Alle:        ./scripts/ship-workflow.sh staging --all
#
# =============================================================================
set -euo pipefail

OWNER="achimdehnert"
ALL_REPOS=(
  bfagent billing-hub cad-hub coach-hub dev-hub
  illustration-hub mcp-hub nl2cad pptx-hub risk-hub
  trading-hub travel-beat wedding-hub weltenhub
  137-hub writing-hub research-hub ausschreibungs-hub
)

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> <repo|--all> [options]

Commands:
  staging <repo>              CI → Build → Deploy Staging
  production <repo>           CI → Build → Deploy Production
  promote <repo>              Staging-Image → Production (kein Re-Build)
  rollback <repo> <tag>       Rollback auf Image-Tag (z.B. v1.2.3)
  status [repo]               Deploy-Status anzeigen (ein Repo oder alle)

Flags:
  --all                       Auf ALLE 18 Repos anwenden

Repos: ${ALL_REPOS[*]}
EOF
  exit 1
}

validate_repo() {
  local repo="$1"
  for r in "${ALL_REPOS[@]}"; do
    [[ "$r" == "$repo" ]] && return 0
  done
  echo -e "${RED}ERROR:${NC} '$repo' ist kein bekanntes ADR-120 Repo." >&2
  exit 1
}

trigger_deploy() {
  local repo="$1" env="${2:-}" tag="${3:-}"
  local -a args=()
  [[ -n "$env" ]] && args+=(-f "target_environment=$env")
  [[ -n "$tag" ]] && args+=(-f "image_tag_override=$tag")
  gh workflow run deploy.yml -R "$OWNER/$repo" "${args[@]}" 2>&1
}

get_latest_staging_tag() {
  local repo="$1"
  local sha
  sha=$(gh run list -R "$OWNER/$repo" --limit 20 \
    --json workflowName,conclusion,headSha \
    -q '[.[] | select((.workflowName == "Deploy" or (.workflowName | test("deploy\\.yml$"))) and .conclusion == "success")] | .[0].headSha' 2>/dev/null || echo "")
  if [[ -n "$sha" && "$sha" != "null" ]]; then
    echo "main-${sha:0:7}"
  fi
}

show_status() {
  local repos=("$@")
  [[ ${#repos[@]} -eq 0 ]] && repos=("${ALL_REPOS[@]}")

  printf "%-22s %-14s %s\n" "REPO" "STATUS" "DATUM"
  printf "%-22s %-14s %s\n" "────────────────────" "────────────" "────────────────"

  for repo in "${repos[@]}"; do
    local line
    line=$(gh run list -R "$OWNER/$repo" --limit 10 \
      --json workflowName,conclusion,status,updatedAt \
      -q '[.[] | select(.workflowName == "Deploy" or (.workflowName | test("deploy\\.yml$")))] | .[0] | "\(.conclusion // .status)\t\(.updatedAt // "")"' 2>/dev/null || echo "")

    local conclusion updated
    if [[ -z "$line" || "$line" == "null" ]]; then
      conclusion="no-runs"; updated=""
    else
      conclusion=$(echo "$line" | cut -f1)
      updated=$(echo "$line" | cut -f2)
      updated="${updated:0:16}"
    fi

    case "$conclusion" in
      success)         printf "%-22s ${GREEN}%-14s${NC} %s\n" "$repo" "OK" "$updated" ;;
      failure)         printf "%-22s ${RED}%-14s${NC} %s\n" "$repo" "FAIL" "$updated" ;;
      startup_failure) printf "%-22s ${RED}%-14s${NC} %s\n" "$repo" "STARTUP-FAIL" "$updated" ;;
      in_progress)     printf "%-22s ${YELLOW}%-14s${NC} %s\n" "$repo" "RUNNING" "$updated" ;;
      queued)          printf "%-22s ${YELLOW}%-14s${NC} %s\n" "$repo" "QUEUED" "$updated" ;;
      no-runs)         printf "%-22s ${CYAN}%-14s${NC}\n" "$repo" "—" ;;
      *)               printf "%-22s %-14s %s\n" "$repo" "$conclusion" "$updated" ;;
    esac
  done
}

deploy_repos() {
  local env="$1"; shift
  local tag="${1:-}"; [[ "${1:-}" == "--" ]] && shift || true
  local repos=("$@")

  echo ""
  echo "🚀 ADR-120 Deploy ${env} — ${#repos[@]} Repo(s)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  local ok=0 fail=0
  for repo in "${repos[@]}"; do
    if trigger_deploy "$repo" "$env" "$tag" >/dev/null 2>&1; then
      echo -e "  ${GREEN}✓${NC} $repo → $env"
      ok=$((ok + 1))
    else
      echo -e "  ${RED}✗${NC} $repo FAILED"
      fail=$((fail + 1))
    fi
  done
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo -e "OK: ${GREEN}$ok${NC}  Failed: ${RED}$fail${NC}"
  echo ""
}

# --- Main ---
[[ $# -eq 0 ]] && usage
CMD="$1"; shift

case "$CMD" in
  staging|production)
    if [[ "${1:-}" == "--all" ]]; then
      deploy_repos "$CMD" "" "${ALL_REPOS[@]}"
    elif [[ -n "${1:-}" ]]; then
      validate_repo "$1"
      deploy_repos "$CMD" "" "$1"
      echo "Status:  $(basename "$0") status $1"
      echo "GitHub:  https://github.com/$OWNER/$1/actions"
    else
      usage
    fi
    ;;

  promote)
    REPO="${1:?Repo fehlt: $(basename "$0") promote <repo>}"
    validate_repo "$REPO"
    TAG=$(get_latest_staging_tag "$REPO")
    if [[ -z "$TAG" ]]; then
      echo -e "${RED}ERROR:${NC} Kein erfolgreicher Staging-Deploy für $REPO gefunden."
      echo "Erst staging deployen: $(basename "$0") staging $REPO"
      exit 1
    fi
    echo -e "Promoting ${CYAN}$REPO${NC} → production mit Image ${GREEN}$TAG${NC}"
    deploy_repos "production" "$TAG" "$REPO"
    ;;

  rollback)
    REPO="${1:?Repo fehlt}"; TAG="${2:?Image-Tag fehlt (z.B. v1.2.3)}"
    validate_repo "$REPO"
    echo -e "Rollback ${CYAN}$REPO${NC} → ${YELLOW}$TAG${NC}"
    deploy_repos "production" "$TAG" "$REPO"
    ;;

  status)
    echo ""
    echo "� ADR-120 Deploy Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [[ -n "${1:-}" ]]; then
      validate_repo "$1"
      show_status "$1"
    else
      show_status
    fi
    echo ""
    ;;

  help|--help|-h) usage ;;
  *) echo -e "${RED}Unbekannter Befehl:${NC} $CMD"; usage ;;
esac
