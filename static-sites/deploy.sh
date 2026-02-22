#!/bin/bash
set -euo pipefail

SITE="${1:?Usage: deploy.sh <site-dir>  (e.g. iil.pet)}"
HOST="88.198.191.108"  # noqa: hardcode
SRC="static-sites/${SITE}/"
DST="/var/www/${SITE}/"

if [ ! -d "${SRC}" ]; then
    echo "ERROR: ${SRC} not found"
    exit 1
fi

echo "==> Backing up ${DST} on ${HOST}..."
ssh "root@${HOST}" \
    "mkdir -p /var/www/.backup && cp -r ${DST} /var/www/.backup/${SITE}-\$(date +%Y%m%d-%H%M%S)" \
    2>/dev/null || echo "    (no existing site to backup)"

echo "==> Deploying ${SRC} → ${HOST}:${DST}"
rsync -avz --checksum "${SRC}" "root@${HOST}:${DST}"

echo "==> Done. Deployed ${SITE} v$(date +%Y%m%d-%H%M%S)"
