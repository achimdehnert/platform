#!/usr/bin/env bash
# gh-app-token.sh — präge einen kurzlebigen (~1 h) GitHub-App-Installation-Token
# für Profil B (iilgmbh org/repo-Admin). Siehe docs/PROFILE_B.md.
#
# Gibt NUR den Token auf stdout aus (kein Echo des Private Keys). Gedacht für:
#   alias claude-ent='GH_TOKEN="$(~/github/platform/tools/gh-app-token.sh)" claude'
#
# Env (in ~/.bashrc setzen, nach App-Anlage):
#   GH_APP_ID          App ID (App-Settings-Seite)
#   GH_APP_KEY         Pfad zum Private-Key-PEM (Default ~/.secrets/github_app_iilgmbh_admin.pem)
#   GH_APP_INSTALL_ID  Installation ID der Ziel-Org (iilgmbh/bahn-sqf/achimdehnert)
set -euo pipefail

APP_ID="${GH_APP_ID:?GH_APP_ID nicht gesetzt — siehe docs/PROFILE_B.md}"
KEY="${GH_APP_KEY:-$HOME/.secrets/github_app_iilgmbh_admin.pem}"
INSTALL_ID="${GH_APP_INSTALL_ID:?GH_APP_INSTALL_ID nicht gesetzt — siehe docs/PROFILE_B.md}"
[ -r "$KEY" ] || { echo "Private Key nicht lesbar: $KEY" >&2; exit 1; }

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }

now=$(date +%s)
header="$(printf '{"alg":"RS256","typ":"JWT"}' | b64url)"
# iat -60s (Clock-Skew), exp +9 min (GitHub-Max 10 min)
payload="$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' "$((now - 60))" "$((now + 540))" "$APP_ID" | b64url)"
sig="$(printf '%s.%s' "$header" "$payload" | openssl dgst -sha256 -sign "$KEY" -binary | b64url)"
jwt="${header}.${payload}.${sig}"

# JWT → Installation-Token (läuft nach ~1 h ab, wandert nie in gh-Config)
gh api --method POST \
  -H "Authorization: Bearer ${jwt}" \
  -H "Accept: application/vnd.github+json" \
  "/app/installations/${INSTALL_ID}/access_tokens" \
  --jq '.token'
