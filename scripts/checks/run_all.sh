#!/bin/bash
# ADR-210 — Run all staging strategy checks (R1-R8).
# Exit code = 1 if any check fails.
set -uo pipefail

cd "$(dirname "$0")"

CHECKS=(
  staging_dns_schema.sh
  staging_host_locality.sh
  staging_naming.sh
  staging_port_range.sh
  staging_tunnel_ingress.sh
  staging_oidc_redirects.sh
  staging_generated_drift.sh
  staging_devdesktop_clean.sh
)

failed=0
for c in "${CHECKS[@]}"; do
  echo "=== $c ==="
  if ! bash "$c"; then
    failed=$((failed + 1))
  fi
  echo
done

echo "==================================="
if [ $failed -eq 0 ]; then
  echo "ALL CHECKS PASSED"
  exit 0
else
  echo "$failed check(s) FAILED"
  exit 1
fi
