#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# rollback-staging.sh — Quick rollback to previous image tag
# ═══════════════════════════════════════════════════════════════════════════════
#
# Convenience wrapper around deploy-remote.sh --rollback-to.
# Reads the saved rollback state and restores the previous deployment.
#
# Usage:
#   rollback-staging.sh --app <APP_NAME> [--tag <SPECIFIC_TAG>]
#
# If --tag is not specified, reads from .rollback_state file.
#
# Examples:
#   rollback-staging.sh --app travel-beat          # auto from .rollback_state
#   rollback-staging.sh --app risk-hub --tag abc1234  # specific tag
#
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

APP_NAME=""
ROLLBACK_TAG=""
DEPLOY_DIR=""
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --app)           APP_NAME="$2";      shift 2 ;;
        --tag)           ROLLBACK_TAG="$2";  shift 2 ;;
        --deploy-dir)    DEPLOY_DIR="$2";    shift 2 ;;
        --compose-file)  COMPOSE_FILE="$2";  shift 2 ;;
        --env-file)      ENV_FILE="$2";      shift 2 ;;
        *) echo -e "${RED}Unknown option: $1${NC}" >&2; exit 1 ;;
    esac
done

[[ -z "$APP_NAME" ]] && { echo -e "${RED}--app is required${NC}" >&2; exit 1; }

DEPLOY_DIR="${DEPLOY_DIR:-/opt/${APP_NAME}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_SCRIPT="${SCRIPT_DIR}/deploy-remote.sh"

# If no explicit tag, try to read from rollback state
if [[ -z "$ROLLBACK_TAG" ]]; then
    STATE_FILE="${DEPLOY_DIR}/.rollback_state"
    if [[ -f "$STATE_FILE" ]]; then
        ROLLBACK_TAG=$(grep -oP 'IMAGE_TAG=\K.*' "$STATE_FILE" 2>/dev/null || true)
    fi

    if [[ -z "$ROLLBACK_TAG" || "$ROLLBACK_TAG" == "unknown" ]]; then
        echo -e "${RED}No rollback tag found in ${STATE_FILE}${NC}" >&2
        echo -e "${YELLOW}Use --tag <TAG> to specify manually${NC}" >&2
        echo ""
        echo "Recent deployments:"
        tail -5 "${DEPLOY_DIR}/deployments.jsonl" 2>/dev/null || echo "  (no deployment log found)"
        exit 1
    fi
fi

echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  ROLLBACK: ${APP_NAME} → ${ROLLBACK_TAG}${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Deploy dir:   ${DEPLOY_DIR}"
echo -e "Compose file: ${COMPOSE_FILE}"
echo -e "Env file:     ${ENV_FILE}"
echo ""

read -p "Continue? [y/N] " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && { echo "Aborted."; exit 0; }

exec "$DEPLOY_SCRIPT" \
    --app "$APP_NAME" \
    --tag "$ROLLBACK_TAG" \
    --rollback-to "$ROLLBACK_TAG" \
    --deploy-dir "$DEPLOY_DIR" \
    --compose-file "$COMPOSE_FILE" \
    --env-file "$ENV_FILE" \
    --skip-backup
