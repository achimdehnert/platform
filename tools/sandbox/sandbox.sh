#!/usr/bin/env bash
# sandbox.sh — vollautonomer Lauf in einem Wegwerf-Container (platform#3685).
#
#   tools/sandbox/sandbox.sh --auftrag <datei.md> [--repo <lokaler-klon>]… [Budget] [--nur-pruefen]
#
# Budget (Vorgaben = S5): --max-tokens 1000000 --max-agenten 5 --max-stunden 4 --max-usd 50
# GitHub-Modus nur mit --token-datei (Fine-grained Token, Scope nur --org); sonst Lokal-Modus.
#
# Abschottung: Repos kommen als Kopie OHNE Remote in den Lauf; eingehaengt wird nur das
# Lauf-Verzeichnis. Kein ~/.secrets, kein ~/.ssh, kein Docker-Socket. Zugangsdaten nur per
# --env-file (nicht in der Prozessliste), danach geloescht. Ergebnis: <lauf>/ausgang/.
# Vor dem Start: Secret-Scan ueber die volle Historie jeder Kopie (geheimnis_scan.py).
# Netz: internes Docker-Netz ohne Gateway, raus nur ueber den Allowlist-Proxy
# (egress_proxy.py); dessen Protokoll liegt ausserhalb des Laufs in <lauf>.egress.jsonl.
set -euo pipefail

HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRET_LESEN="$HIER/../secret_lesen.sh"
BILD="iil-sandbox:latest"
LAEUFE="${SANDBOX_LAEUFE:-$HOME/sandbox-laeufe}"
ORG="iilsandbox"  # vom Owner angelegt 2026-10-04
# Modell-Zugang: Abo-Token (`claude setup-token`) vor API-Schluessel, falls vorhanden.
ABO_TOKEN="$HOME/.secrets/claude_oauth_token"
MODELL_SCHLUESSEL="$HOME/.secrets/anthropic_api_key"
AUFTRAG="" TOKEN_DATEI="" NUR_PRUEFEN=""
REPOS=() KOPIEN=() WAECHTER=()

while [ $# -gt 0 ]; do
  case "$1" in
    --auftrag) AUFTRAG="$2"; shift 2 ;;
    --repo) REPOS+=("$2"); shift 2 ;;
    --org) ORG="$2"; shift 2 ;;
    --token-datei) TOKEN_DATEI="$2"; shift 2 ;;
    --max-tokens|--max-agenten|--max-stunden|--max-usd|--modell) WAECHTER+=("$1" "$2"); shift 2 ;;
    --nur-pruefen) NUR_PRUEFEN=1; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unbekannt: $1" >&2; exit 64 ;;
  esac
done
[ -n "$NUR_PRUEFEN" ] || [ -f "$AUFTRAG" ] || { echo "--auftrag <datei.md> fehlt" >&2; exit 64; }

docker build -q -t "$BILD" "$HIER" >/dev/null

LAUF="$LAEUFE/$(date +%Y-%m-%dT%H%M%S)-$$"
mkdir -p "$LAUF/eingang/repos" "$LAUF/ausgang"
[ -n "$AUFTRAG" ] && cp "$AUFTRAG" "$LAUF/eingang/auftrag.md"
for repo in "${REPOS[@]}"; do
  ziel="$LAUF/eingang/repos/$(basename "$repo")"
  # Nur der Standard-Branch ohne Tags: der Scan deckt dann jedes Objekt der Kopie ab.
  git clone -q --no-local --single-branch --no-tags "$repo" "$ziel"
  git -C "$ziel" remote remove origin
  KOPIEN+=("$ziel")
done
# Positivkontrolle laeuft immer, auch ohne Repos — ohne sehenden Scan kein Lauf.
python3 "$HIER/geheimnis_scan.py" "${KOPIEN[@]}" || {
  echo "Lauf abgebrochen vor dem Start: Secret-Scan (Kopien bleiben in $LAUF)" >&2
  exit 1
}

ENVDATEI="$(mktemp)"
chmod 600 "$ENVDATEI"
NAME="$(basename "$LAUF")"
NETZ="sandbox-netz-$NAME" PROXY="sandbox-egress-$NAME"
aufraeumen() {
  rm -f "$ENVDATEI"
  docker logs "$PROXY" >"$LAUF.egress.jsonl" 2>/dev/null || true
  docker rm -f "$PROXY" >/dev/null 2>&1 || true
  docker network rm "$NETZ" >/dev/null 2>&1 || true
}
trap aufraeumen EXIT
docker network create --internal "$NETZ" >/dev/null
docker run -d --name "$PROXY" --network bridge \
  --cap-drop ALL --security-opt no-new-privileges --read-only \
  --memory 256m --pids-limit 256 \
  --entrypoint python3 "$BILD" /sandbox/egress_proxy.py >/dev/null
docker network connect --alias egress "$NETZ" "$PROXY"
{
  echo "IIL_SANDBOX=1"
  echo "SANDBOX_ORG=$ORG"
  echo "HTTPS_PROXY=http://egress:3128"
  echo "https_proxy=http://egress:3128"
  echo "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1"
  if [ -z "$NUR_PRUEFEN" ]; then
    if [ -f "$ABO_TOKEN" ]; then
      echo "CLAUDE_CODE_OAUTH_TOKEN=$("$SECRET_LESEN" "$ABO_TOKEN")"
    else
      echo "ANTHROPIC_API_KEY=$("$SECRET_LESEN" "$MODELL_SCHLUESSEL")"
    fi
  fi
  [ -z "$TOKEN_DATEI" ] || echo "GH_TOKEN=$("$SECRET_LESEN" "$TOKEN_DATEI")"
} >"$ENVDATEI"

set +e
docker run --rm --name "sandbox-$(basename "$LAUF")" \
  --env-file "$ENVDATEI" \
  --network "$NETZ" \
  -v "$LAUF:/arbeit" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 8g --cpus 4 --pids-limit 1024 \
  "$BILD" ${NUR_PRUEFEN:+--nur-pruefen} "${WAECHTER[@]}"
RC=$?
set -e
echo "Lauf: $LAUF"
[ -f "$LAUF/ausgang/status.json" ] && cat "$LAUF/ausgang/status.json"
exit $RC
