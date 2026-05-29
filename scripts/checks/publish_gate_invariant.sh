#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# ADR-226 enforcement — publish-gate invariant + #191/#198 API-free guard
#
# Makes two ADR-226 invariants STRUCTURAL (were prose-only in the ADR; see
# ADR-226 "External review follow-ups", REC-1 + REC-3):
#
#   (1) Publish-gate invariant: every .github/workflows/publish-*.yml MUST
#       reference the shared `gitleaks-scan` composite action (the pre-publish
#       secret-scan that closes the irreversible-artifact risk by construction).
#
#   (2) #191/#198 reusable-permission trap guard: the shared gitleaks-scan
#       action and _ci-pypi.yml MUST NOT call the GitHub API (api.github.com /
#       gh api / github.rest / actions/github-script). An API call re-couples
#       the scan to caller permissions and reopens the trap PR #198 closed.
#
# Self-activating: a no-op until the gitleaks-scan composite action lands
# (with ADR-226 / its implementing PR). Green on pre-ADR-226 main.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

cd "$(git rev-parse --show-toplevel)"

ACTION=".github/actions/gitleaks-scan/action.yml"
CI_PYPI=".github/workflows/_ci-pypi.yml"
fail=0

if [[ ! -f "$ACTION" ]]; then
  echo "ℹ️  gitleaks-scan composite action not present yet (pre-ADR-226) — invariant inactive."
  exit 0
fi

echo "=== (1) publish-*.yml must reference gitleaks-scan ==="
shopt -s nullglob
publish_wfs=(.github/workflows/publish-*.yml)
if [[ ${#publish_wfs[@]} -eq 0 ]]; then
  echo "  (no publish-*.yml found)"
fi
for wf in "${publish_wfs[@]}"; do
  if grep -q 'gitleaks-scan' "$wf"; then
    echo "  ✅ $wf"
  else
    echo "::error file=$wf::ADR-226 publish-gate invariant: publish workflow does not reference gitleaks-scan before upload"
    fail=1
  fi
done

echo "=== (2) #191/#198 guard: no GitHub-API in the secret-scan path ==="
for f in "$ACTION" "$CI_PYPI"; do
  [[ -f "$f" ]] || continue
  if grep -qiE 'api\.github\.com|gh api |github\.rest|actions/github-script' "$f"; then
    echo "::error file=$f::ADR-226 Guard: GitHub-API call in the secret-scan path reopens the #191/#198 reusable-permission trap"
    fail=1
  else
    echo "  ✅ $f — API-free"
  fi
done

echo "==================================="
if [[ "$fail" -eq 0 ]]; then
  echo "✅ ADR-226 publish-gate invariant + #191/#198 API-free guard hold."
else
  echo "❌ ADR-226 invariant violation(s) — see ::error annotations above."
fi
exit "$fail"
