#!/usr/bin/env bash
# gh-app-token.sh [account] — kurzlebiger (~1 h) GitHub-App-Installation-Token
# für Profil B (siehe docs/PROFILE_B.md). Gibt NUR den Token auf stdout aus.
#
#   gh-app-token.sh              → Default-Account (GH_APP_DEFAULT_ACCOUNT)
#   gh-app-token.sh iilgmbh      → Token für die iilgmbh-Installation
#   gh-app-token.sh bahn-sqf     → Token für die bahn-sqf-Installation
#
# Die Install-ID wird LIVE per App-JWT aufgelöst (kein hartkodiertes Mapping) —
# sobald die App auf einer weiteren Org installiert ist, greift ihr Name sofort.
#
# Env (in ~/.bashrc):
#   GH_APP_ID                App ID
#   GH_APP_KEY               PEM-Pfad (Default ~/.secrets/github_app_iilgmbh_admin.pem)
#   GH_APP_DEFAULT_ACCOUNT   Account ohne Argument (z. B. achimdehnert)
set -euo pipefail

APP_ID="${GH_APP_ID:?GH_APP_ID nicht gesetzt — siehe docs/PROFILE_B.md}"
KEY="${GH_APP_KEY:-$HOME/.secrets/github_app_iilgmbh_admin.pem}"
ACCOUNT="${1:-${GH_APP_DEFAULT_ACCOUNT:-}}"
[ -r "$KEY" ] || { echo "Private Key nicht lesbar: $KEY" >&2; exit 1; }

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
now=$(date +%s)
header="$(printf '{"alg":"RS256","typ":"JWT"}' | b64url)"
payload="$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' "$((now - 60))" "$((now + 540))" "$APP_ID" | b64url)"
sig="$(printf '%s.%s' "$header" "$payload" | openssl dgst -sha256 -sign "$KEY" -binary | b64url)"
jwt="${header}.${payload}.${sig}"

api() { curl -sS -H "Authorization: Bearer ${jwt}" -H "Accept: application/vnd.github+json" "$@"; }

# Install-ID des gewünschten Accounts live auflösen
iid="$(api https://api.github.com/app/installations | ACCOUNT="$ACCOUNT" python3 -c '
import sys, os, json
d = json.load(sys.stdin)
if isinstance(d, dict):
    sys.exit("API-Fehler: " + str(d.get("message")))
acc = os.environ.get("ACCOUNT", "")
hit = [i for i in d if (not acc or i["account"]["login"].lower() == acc.lower())]
if not hit:
    sys.exit("Keine Installation fuer %r. Installiert auf: %s"
             % (acc, ", ".join(i["account"]["login"] for i in d)))
print(hit[0]["id"])')"

# JWT → kurzlebiger Installation-Token (wandert nie in gh-Config)
api -X POST "https://api.github.com/app/installations/${iid}/access_tokens" \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["token"])'
