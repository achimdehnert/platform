#!/usr/bin/env bash
# ADR-242: Idempotentes Script zum Anlegen/Aktualisieren von GitHub Rulesets
# für Branch-Protection (required check auf `main`).
#
# Soll-Quelle (KONZ-platform-070 Z4, Mandat #3903 WP5): die Registry-Ableitung
# `python3 tools/branch_protection_meter.py --soll-json` (Profile deployed +
# plattform = frühere Wave 1), nicht mehr eine eigene Repo-Liste. Dieses Skript
# setzt NUR den required check (Template); fordert das Profil zusätzlich
# Approvals, nennt der Meter einen eigenen `gh api`-Befehl.
#
# Usage:
#   ./tools/apply-branch-protection.sh               # alle Repos mit Profil deployed/plattform
#   ./tools/apply-branch-protection.sh --repo dev-hub # nur ein Repo
#   ./tools/apply-branch-protection.sh --soll-datei soll.json --repo demo  # Soll aus Datei (Tests)
#
# Requirements: gh (GitHub CLI), jq, python3, GH_TOKEN im ENV oder gh auth login

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_FILE="$REPO_ROOT/governance/rulesets/main-required-checks-template.json"
METER="$SCRIPT_DIR/branch_protection_meter.py"
SOLL_PROFILE=(deployed plattform)

# ---------------------------------------------------------------------------
# Dependencies check
# ---------------------------------------------------------------------------
for cmd in gh jq; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "❌ Abhängigkeit fehlt: $cmd" >&2
    exit 1
  fi
done

if [ ! -f "$TEMPLATE_FILE" ]; then
  echo "❌ Template nicht gefunden: $TEMPLATE_FILE" >&2
  exit 1
fi


# ---------------------------------------------------------------------------
# GH_TOKEN Fallback
# ---------------------------------------------------------------------------
if [ -z "${GH_TOKEN:-}" ]; then
  GH_TOKEN="$(gh auth token 2>/dev/null || true)"
  if [ -z "$GH_TOKEN" ]; then
    echo "❌ GH_TOKEN nicht gesetzt und 'gh auth token' lieferte kein Token." >&2
    echo "   Bitte 'gh auth login' ausführen oder GH_TOKEN setzen." >&2
    exit 1
  fi
  export GH_TOKEN
fi

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
FILTER_REPO=""
SOLL_DATEI=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      FILTER_REPO="$2"
      shift 2
      ;;
    --soll-datei)
      SOLL_DATEI="$2"
      shift 2
      ;;
    *)
      echo "❌ Unbekanntes Argument: $1" >&2
      echo "   Usage: $0 [--repo <repo-name>] [--soll-datei <json>]" >&2
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Soll-Liste: Registry-Ableitung via Meter (--soll-json), oder Datei (Tests).
# Eintraege: {repo, owner, required_check, profil?, approvals?, deferred?}
# ---------------------------------------------------------------------------
if [ -n "$SOLL_DATEI" ]; then
  if [ ! -f "$SOLL_DATEI" ]; then
    echo "❌ Soll-Datei nicht gefunden: $SOLL_DATEI" >&2
    exit 1
  fi
  REPOS_JSON=$(cat "$SOLL_DATEI")
  QUELLE="$SOLL_DATEI"
else
  if [ ! -f "$METER" ]; then
    echo "❌ Meter nicht gefunden: $METER (Soll-Quelle, KONZ-070 Z4)" >&2
    exit 1
  fi
  if [ -n "$FILTER_REPO" ]; then
    REPOS_JSON=$(python3 "$METER" --soll-json --repos "$FILTER_REPO")
  else
    REPOS_JSON=$(python3 "$METER" --soll-json --profile "${SOLL_PROFILE[@]}")
  fi
  QUELLE="registry (Profile ${SOLL_PROFILE[*]})"
fi

if [ -n "$FILTER_REPO" ]; then
  ENTRIES=$(echo "$REPOS_JSON" | jq --arg r "$FILTER_REPO" '[.[] | select(.repo == $r)]')
  COUNT=$(echo "$ENTRIES" | jq 'length')
  if [ "$COUNT" -eq 0 ]; then
    echo "❌ Repo '$FILTER_REPO' hat kein messbares Soll ($QUELLE) — Profil static/keins oder unbekannt." >&2
    exit 1
  fi
  DEFERRED_REASON=$(echo "$ENTRIES" | jq -r '.[0].deferred // empty')
  if [ -n "$DEFERRED_REASON" ]; then
    echo "❌ Repo '$FILTER_REPO' ist deferred: $DEFERRED_REASON" >&2
    exit 1
  fi
else
  echo "$REPOS_JSON" | jq -r '.[] | select(.deferred != null) | "⏸ \(.repo) übersprungen (deferred): \(.deferred)"'
  ENTRIES=$(echo "$REPOS_JSON" | jq '[.[] | select(.deferred == null)]')
fi
echo "$ENTRIES" | jq -r '.[] | select((.approvals // 0) > 0) | "ℹ \(.repo): Profil \(.profil) fordert \(.approvals) Approval — setzt dieses Skript nicht, Befehl: python3 tools/branch_protection_meter.py --repos \(.repo)"'

TOTAL=$(echo "$ENTRIES" | jq 'length')
SUCCESS=0
FAIL=0

# ---------------------------------------------------------------------------
# Hilfsfunktion: Ruleset anlegen oder aktualisieren
# ---------------------------------------------------------------------------
apply_ruleset() {
  local owner="$1"
  local repo="$2"
  local required_check="$3"

  # Template befüllen: __REQUIRED_CHECK__ ersetzen
  local ruleset_json
  ruleset_json=$(jq --arg check "$required_check" \
    '(.rules[] | select(.type == "required_status_checks") | .parameters.required_status_checks[0].context) = $check' \
    "$TEMPLATE_FILE")

  # Prüfen ob Ruleset bereits existiert
  local existing_id
  existing_id=$(gh api "repos/$owner/$repo/rulesets" \
    --jq '.[] | select(.name == "main-required-checks") | .id' 2>/dev/null || true)

  # SEC-1 (Issue #1198): Exit-Code des API-Calls explizit festhalten statt den
  # Funktions-Rückgabewert implizit vom letzten Befehl (immer erfolgreichem
  # `echo`) bestimmen zu lassen — sonst meldet die Funktion auch bei einem
  # fehlgeschlagenen `gh api`-Aufruf fälschlich Erfolg (return 0).
  local rc=0
  if [ -n "$existing_id" ]; then
    # Update via PATCH
    echo "$ruleset_json" | gh api "repos/$owner/$repo/rulesets/$existing_id" \
      -X PATCH --input - > /dev/null
    rc=$?
    if [ "$rc" -eq 0 ]; then
      echo "✅ $repo: Ruleset aktualisiert (ID $existing_id, check: $required_check)"
    fi
  else
    # Anlegen via POST
    local new_id
    new_id=$(echo "$ruleset_json" | gh api "repos/$owner/$repo/rulesets" \
      -X POST --input - --jq '.id' 2>/dev/null)
    rc=$?
    if [ "$rc" -eq 0 ]; then
      echo "✅ $repo: Ruleset angelegt (ID $new_id, check: $required_check)"
    fi
  fi
  return "$rc"
}

# ---------------------------------------------------------------------------
# Hauptschleife
# ---------------------------------------------------------------------------
echo "ADR-242 Branch-Protection Rollout — Soll aus $QUELLE ($TOTAL Repos)"
echo "============================================================"

for i in $(seq 0 $((TOTAL - 1))); do
  entry=$(echo "$ENTRIES" | jq ".[$i]")
  repo=$(echo "$entry"    | jq -r '.repo')
  owner=$(echo "$entry"   | jq -r '.owner')
  check=$(echo "$entry"   | jq -r '.required_check')

  if apply_ruleset "$owner" "$repo" "$check"; then
    SUCCESS=$((SUCCESS + 1))
  else
    echo "❌ $repo: Fehler beim Anlegen/Aktualisieren des Rulesets"
    FAIL=$((FAIL + 1))
  fi
done

echo "============================================================"
echo "$SUCCESS/$TOTAL Repos erfolgreich geschützt"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
