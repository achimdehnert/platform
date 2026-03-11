#!/usr/bin/env bash
# =============================================================================
# platform/scripts/ship-workflow.sh — ADR-120 Deploy via GitHub Actions
# =============================================================================
#
#   Ein Repo deployen:
#     ./scripts/ship-workflow.sh risk-hub
#
#   Alle Repos deployen:
#     ./scripts/ship-workflow.sh --all
#
#   Rollback auf bestimmten Tag:
#     ./scripts/ship-workflow.sh risk-hub --tag v1.2.3
#
#   Status prüfen:
#     ./scripts/ship-workflow.sh --status
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
  echo "Usage:"
  echo "  $(basename "$0") <repo>              Deploy ein Repo (workflow_dispatch)"
  echo "  $(basename "$0") <repo> --tag v1.2.3 Rollback auf Tag"
  echo "  $(basename "$0") --all               Deploy ALLE 18 Repos"
  echo "  $(basename "$0") --status            Letzten Deploy-Status aller Repos zeigen"
  echo "  $(basename "$0") --status <repo>     Letzten Deploy-Status eines Repos zeigen"
  echo ""
  echo "Repos: ${ALL_REPOS[*]}"
  exit 1
}

trigger_deploy() {
  local repo="$1"
  local tag="${2:-}"

  if [[ -n "$tag" ]]; then
    gh workflow run deploy.yml -R "$OWNER/$repo" -f "image_tag_override=$tag" 2>&1
  else
    gh workflow run deploy.yml -R "$OWNER/$repo" 2>&1
  fi
}

show_status() {
  local repos=("$@")
  [[ ${#repos[@]} -eq 0 ]] && repos=("${ALL_REPOS[@]}")

  printf "%-22s %-12s %-10s %s\n" "REPO" "STATUS" "DAUER" "DATUM"
  printf "%-22s %-12s %-10s %s\n" "────────────────────" "──────────" "────────" "──────────────────"

  for repo in "${repos[@]}"; do
    local result
    result=$(gh run list -R "$OWNER/$repo" -w "Deploy" --limit 1 \
      --json conclusion,status,updatedAt,runStartedAt \
      -q '.[0] | "\(.conclusion // .status)\t\(.updatedAt)"' 2>/dev/null || echo "no-runs	-")

    local conclusion duration_str
    conclusion=$(echo "$result" | cut -f1)
    local updated=$(echo "$result" | cut -f2)

    case "$conclusion" in
      success)         printf "%-22s ${GREEN}%-12s${NC}" "$repo" "✅ success" ;;
      failure)         printf "%-22s ${RED}%-12s${NC}" "$repo" "❌ failure" ;;
      startup_failure) printf "%-22s ${RED}%-12s${NC}" "$repo" "❌ startup" ;;
      in_progress)     printf "%-22s ${YELLOW}%-12s${NC}" "$repo" "⏳ running" ;;
      queued)          printf "%-22s ${YELLOW}%-12s${NC}" "$repo" "⏳ queued" ;;
      no-runs)         printf "%-22s ${CYAN}%-12s${NC}" "$repo" "— no runs" ;;
      *)               printf "%-22s %-12s" "$repo" "$conclusion" ;;
    esac

    if [[ "$updated" != "-" && "$updated" != "" ]]; then
      printf " %s" "${updated:0:16}"
    fi
    echo ""
  done
}

# --- Argument Parsing ---
[[ $# -eq 0 ]] && usage

MODE=""
REPO=""
TAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)    MODE="all"; shift ;;
    --status) MODE="status"; shift ;;
    --tag)    TAG="$2"; shift 2 ;;
    --help|-h) usage ;;
    *)
      if [[ -z "$REPO" ]]; then
        REPO="$1"
      fi
      shift ;;
  esac
done

# --- Execute ---
case "$MODE" in
  all)
    echo ""
    echo "🚀 ADR-120 Deploy — ALLE ${#ALL_REPOS[@]} Repos"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    TRIGGERED=0
    FAILED=0
    for repo in "${ALL_REPOS[@]}"; do
      if trigger_deploy "$repo" "$TAG" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $repo triggered"
        TRIGGERED=$((TRIGGERED + 1))
      else
        echo -e "  ${RED}✗${NC} $repo FAILED"
        FAILED=$((FAILED + 1))
      fi
    done
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "Triggered: ${GREEN}$TRIGGERED${NC}  Failed: ${RED}$FAILED${NC}"
    echo ""
    echo "Status prüfen mit: $(basename "$0") --status"
    ;;

  status)
    echo ""
    echo "📊 ADR-120 Deploy Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [[ -n "$REPO" ]]; then
      show_status "$REPO"
    else
      show_status
    fi
    echo ""
    ;;

  *)
    if [[ -z "$REPO" ]]; then
      usage
    fi

    # Validate repo name
    VALID=false
    for r in "${ALL_REPOS[@]}"; do
      [[ "$r" == "$REPO" ]] && VALID=true && break
    done
    if [[ "$VALID" != "true" ]]; then
      echo -e "${RED}ERROR:${NC} '$REPO' ist kein bekanntes ADR-120 Repo."
      echo "Bekannte Repos: ${ALL_REPOS[*]}"
      exit 1
    fi

    echo ""
    if [[ -n "$TAG" ]]; then
      echo "🚀 ADR-120 Deploy — $REPO (Rollback → $TAG)"
    else
      echo "🚀 ADR-120 Deploy — $REPO"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if trigger_deploy "$REPO" "$TAG"; then
      echo -e "  ${GREEN}✓${NC} Workflow triggered"
      echo ""
      echo "Status prüfen: $(basename "$0") --status $REPO"
      echo "GitHub:         https://github.com/$OWNER/$REPO/actions"
    else
      echo -e "  ${RED}✗${NC} Trigger fehlgeschlagen"
      exit 1
    fi
    echo ""
    ;;
esac
