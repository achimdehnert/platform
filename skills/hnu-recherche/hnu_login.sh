#!/usr/bin/env bash
# Meldet sich am HNU-Katalog über ezproxy an und legt die Sitzung in hnu-cookies.txt ab.
# Zugangsdaten kommen aus ~/.secrets/hnu.env (user:/password:), nie ins Protokoll.
set -uo pipefail
S="$(dirname "$0")"
rm -f "$S/hnu-cookies.txt"
u=$(sed -n 's/^user: *//p' ~/.secrets/hnu.env)
p=$(sed -n 's/^password: *//p' ~/.secrets/hnu.env)

curl -s -L -c "$S/hnu-cookies.txt" -b "$S/hnu-cookies.txt" -o "$S/ez1.html" \
  "https://bibkat-hnu-de.ezproxy.hnu.de/vufind/"

python3 - "$S" <<'PY'
import re, html, sys, urllib.parse
s = sys.argv[1]
h = open(f"{s}/ez1.html", encoding="utf-8", errors="replace").read()
form = re.search(r"<form name='EZproxyForm'.*?</form>", h, re.S).group(0)
felder = dict(re.findall(r"name='([^']+)'\s+value='([^']*)'", form))
felder = {k: html.unescape(v) for k, v in felder.items()}
open(f"{s}/saml-post.txt", "w").write(urllib.parse.urlencode(felder))
PY

curl -s -L -c "$S/hnu-cookies.txt" -b "$S/hnu-cookies.txt" -o "$S/idp1.html" \
  -X POST --data @"$S/saml-post.txt" "https://sso.hnu.de/idp/profile/SAML2/POST/SSO"
ACTION=$(grep -o '<form action="[^"]*"' "$S/idp1.html" | head -1 | sed 's/<form action="//; s/"$//')

curl -s -L -c "$S/hnu-cookies.txt" -b "$S/hnu-cookies.txt" -o "$S/idp2.html" \
  -X POST --data-urlencode "j_username=$u" --data-urlencode "j_password=$p" \
  --data-urlencode "_eventId_proceed=" "https://sso.hnu.de$ACTION"

python3 - "$S" <<'PY'
import re, html, sys, urllib.parse
s = sys.argv[1]
h = open(f"{s}/idp2.html", encoding="utf-8", errors="replace").read()
m = re.search(r'<form[^>]*action="([^"]+)"[^>]*>(.*?)</form>', h, re.S)
if not m or "SAMLResponse" not in m.group(2):
    raise SystemExit("kein SAMLResponse — Anmeldung fehlgeschlagen")
felder = {k: html.unescape(v) for k, v in re.findall(r'name="([^"]+)"\s+value="([^"]*)"', m.group(2))}
open(f"{s}/saml-resp.txt", "w").write(urllib.parse.urlencode(felder))
open(f"{s}/saml-action.txt", "w").write(html.unescape(m.group(1)))
PY

curl -s -L -c "$S/hnu-cookies.txt" -b "$S/hnu-cookies.txt" -o /dev/null \
  -X POST --data @"$S/saml-resp.txt" "$(cat "$S/saml-action.txt")"

code=$(curl -s -o /dev/null -w "%{http_code}" -b "$S/hnu-cookies.txt" \
  "https://bibkat-hnu-de.ezproxy.hnu.de/vufind/Search/Results?lookfor=test&limit=1")
echo "Katalog antwortet: $code"
[ "$code" = "200" ] || exit 1
