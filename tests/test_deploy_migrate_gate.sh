#!/usr/bin/env bash
# tests/test_deploy_migrate_gate.sh — Vertragstest für den Migrations-Block in
# scripts/deploy.sh (illustration-hub#66).
#
# Warum als Test und nicht "einmal von Hand geprüft": der Block läuft bei JEDEM
# Deploy JEDES Hubs. Ein späteres Refactor, das eine der vier Zusagen unten
# still aufweicht, wäre am Deploy-Log nicht zu erkennen — ein grüner Deploy sieht
# dann genauso aus wie vorher. Genau diese Unsichtbarkeit war die Ursache von #66.
#
# Geprüfte Zusagen:
#   1. migrate scheitert            → Exit 2, kein `up -d`, .env zurückgesetzt
#   2. nach migrate weiter pending  → Exit 2, kein `up -d`, .env zurückgesetzt
#   3. Nicht-Django-Stack           → No-op, Deploy läuft weiter (Exit 0)
#   4. DEPLOY_MIGRATE=0             → No-op, Deploy läuft weiter (Exit 0)
#
# Der Block wird 1:1 aus scripts/deploy.sh extrahiert (keine Nachbildung, die
# auseinanderlaufen könnte) und gegen einen `docker`-Stub gefahren — der Test
# braucht daher weder Docker noch Netz und läuft auf jedem Runner.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/scripts/deploy.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

BLOCK="$TMP/block.sh"
sed -n '/^# ── Schema-Migrationen/,/^docker compose "\${COMPOSE_ARGS\[@\]}" "\${LABEL_ARGS\[@\]}" up -d/p' \
  "$SRC" | head -n -1 > "$BLOCK"

if [[ ! -s "$BLOCK" ]]; then
  echo "FAIL: Migrations-Block nicht aus $SRC extrahierbar — Marker geändert?" >&2
  exit 1
fi

# Harness: minimale Umgebung des Skripts + docker-Stub. MIGRATE_RC/CHECK_RC/
# SERVICES steuern das simulierte Verhalten.
make_harness() {
  cat > "$TMP/harness.sh" <<'EOF'
set -uo pipefail
APP_PATH=/tmp; IMAGE_TAG="test"; PREVIOUS_TAG="v-old"
COMPOSE_ARGS=(-f /dev/null); LABEL_ARGS=()
_restore_image_tag() { echo "RESTORE_CALLED"; }
docker() {
  local all="$*"
  case "$all" in
    *"config --services"*)    echo "${SERVICES}"; return 0 ;;
    *"test -f manage.py"*)    return "${MANAGE_RC:-0}" ;;
    *"config --format json"*) echo '{"services":{"app-web":{"depends_on":{}}}}'; return 0 ;;
    *"--no-recreate"*)        return 0 ;;
    *"migrate --check"*)      return "${CHECK_RC:-0}" ;;
    *"migrate --noinput"*)    return "${MIGRATE_RC:-0}" ;;
  esac
  return 0
}
source "$1"
echo "BLOCK_COMPLETED"
EOF
}
make_harness

fail=0
check() { # check <name> <erwarteter-exit> <muss-enthalten> <darf-nicht-enthalten>
  local name="$1" want_rc="$2" must="$3" must_not="${4:-}"
  local out rc
  out=$(bash "$TMP/harness.sh" "$BLOCK" 2>&1); rc=$?
  local ok=1
  [[ "$rc" == "$want_rc" ]] || { ok=0; echo "  ✗ Exit $rc, erwartet $want_rc"; }
  grep -q "$must" <<<"$out" || { ok=0; echo "  ✗ fehlt in Ausgabe: '$must'"; }
  if [[ -n "$must_not" ]] && grep -q "$must_not" <<<"$out"; then
    ok=0; echo "  ✗ unerwartet in Ausgabe: '$must_not'"
  fi
  if [[ $ok == 1 ]]; then echo "  ✓ $name"; else echo "  ✗ $name"; echo "$out" | sed 's/^/      /'; fail=1; fi
}

echo "Vertragstest Migrations-Gate ($(wc -l < "$BLOCK") Zeilen aus scripts/deploy.sh)"

# 1) migrate scheitert → fail-closed, kein up -d
export SERVICES="app-web" MIGRATE_RC=1 CHECK_RC=0 MANAGE_RC=0
check "migrate scheitert → Exit 2 + .env zurückgesetzt" 2 "RESTORE_CALLED" "BLOCK_COMPLETED"

# 2) pending nach migrate → fail-closed
export SERVICES="app-web" MIGRATE_RC=0 CHECK_RC=1 MANAGE_RC=0
check "pending nach migrate → Exit 2 (Schema-Drift)" 2 "pending" "BLOCK_COMPLETED"

# 3) Nicht-Django-Stack → No-op, Deploy läuft weiter
export SERVICES="redis" MIGRATE_RC=0 CHECK_RC=0 MANAGE_RC=0
check "kein *web-Service → No-op" 0 "BLOCK_COMPLETED" "RESTORE_CALLED"

# 3b) *web ohne manage.py → laute Warnung, aber Deploy läuft weiter
export SERVICES="app-web" MIGRATE_RC=0 CHECK_RC=0 MANAGE_RC=1
check "*web ohne manage.py → Warnung, kein Abbruch" 0 "::warning::" "RESTORE_CALLED"

# 4) Opt-out
export SERVICES="app-web" MIGRATE_RC=1 CHECK_RC=1 MANAGE_RC=0 DEPLOY_MIGRATE=0
check "DEPLOY_MIGRATE=0 → No-op trotz kaputter Migration" 0 "BLOCK_COMPLETED" "RESTORE_CALLED"
unset DEPLOY_MIGRATE

# 5) Happy Path
export SERVICES="app-web" MIGRATE_RC=0 CHECK_RC=0 MANAGE_RC=0
check "alles sauber → Block läuft durch" 0 "Schema aktuell" "RESTORE_CALLED"

if [[ $fail == 0 ]]; then
  echo "RESULT: OK — alle Zusagen des Migrations-Gates gehalten"
else
  echo "RESULT: FAIL — Migrations-Gate verletzt seinen Vertrag" >&2
fi
exit $fail
