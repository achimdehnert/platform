#!/usr/bin/env bash
# pre_push_platform_gates.sh — lokaler Pre-Push-Gate für platform-Hard-Invarianten.
#
# Spiegelt die schnellen, strukturellen CI-Hard-Gates LOKAL, damit man sie vor
# dem Push prüft statt rote CI als Pre-Code-Check zu missbrauchen
# (Session-Retro 2026-06-30: claim-before-cheapest-check / lint-failure-no-local-gate;
# Realfall PR #743 brach zwei dieser Gates, beide lokal in <3s fangbar).
#
# Bewusst NUR schnelle Struktur-Checks (keine Tests/ruff — die laufen in CI):
#   1) Registry-View-Reader-Guard (ADR-234 §11.1 REC-4)
#   2) ADR-226 publish-gate invariant (gitleaks vor publish-*.yml)
#   3) check_publish_gate gegen die eigenen Workflows (Inv. c)
#
# Usage:
#   bash scripts/checks/pre_push_platform_gates.sh            # Gates laufen, exit 1 bei Fail
#   bash scripts/checks/pre_push_platform_gates.sh --install-hook   # als .git/hooks/pre-push setzen
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "kein git-Repo"; exit 0; }
cd "$REPO_ROOT"

install_hook() {
  local hookdir; hookdir="$(git rev-parse --git-path hooks)"
  mkdir -p "$hookdir"
  local hook="$hookdir/pre-push"
  if [ -e "$hook" ] && ! grep -q 'pre_push_platform_gates' "$hook" 2>/dev/null; then
    echo "⚠️  pre-push-Hook existiert bereits und ist fremd: $hook — NICHT überschrieben." >&2
    return 1
  fi
  cat > "$hook" <<'HOOK'
#!/usr/bin/env bash
# installed by pre_push_platform_gates.sh (Retro 2026-06-30 A5)
root="$(git rev-parse --show-toplevel)"
gate="$root/scripts/checks/pre_push_platform_gates.sh"
[ -x "$gate" ] && exec bash "$gate"
exit 0
HOOK
  chmod +x "$hook"
  echo "✓ pre-push-Hook gesetzt: $hook"
  return 0
}

if [ "${1:-}" = "--install-hook" ]; then
  install_hook
  exit $?
fi

# --- Gates (nur die laufen lassen, die im Repo vorhanden sind = best effort) ---
failed=0
run() {  # run <label> <cmd...>
  local label="$1"; shift
  echo "=== $label ==="
  if "$@"; then
    echo "  ✓ ok"
  else
    echo "  ✗ FAIL"
    failed=$((failed + 1))
  fi
}

[ -f tools/check_registry_view_readers.py ] && \
  run "Registry-View-Reader-Guard (ADR-234 §11.1)" python3 tools/check_registry_view_readers.py
[ -f scripts/checks/publish_gate_invariant.sh ] && \
  run "ADR-226 publish-gate invariant" bash scripts/checks/publish_gate_invariant.sh
[ -f tools/check_publish_gate.py ] && \
  run "check_publish_gate (eigene Workflows)" python3 tools/check_publish_gate.py .

echo "==================================="
if [ "$failed" -eq 0 ]; then
  echo "ALLE PLATFORM-GATES GRÜN — Push frei."
  exit 0
fi
echo "$failed Gate(s) FAILED — Push blockiert. Lokal fixen, bevor du pushst."
exit 1
