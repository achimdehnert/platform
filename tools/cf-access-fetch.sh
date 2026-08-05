#!/usr/bin/env bash
# cf-access-fetch.sh — HTTP-Abruf hinter der Cloudflare-Access-Wand.
#
# WOZU
#   Domains hinter Cloudflare Access antworten jedem nicht angemeldeten Aufruf
#   mit 302 auf die Anmeldeseite. Ein Agent oder CI-Job sieht davon nur den
#   Redirect und kann nichts pruefen — weder ob eine Seite existiert, noch was
#   auf ihr steht. Das fuehrte zweimal zu einer stillgelegten Pruefung statt zu
#   einer Loesung (apo-hub: `skip_external_verify` dauerhaft an; risk-hub: die
#   Merkregel "Cloudflare ist kein Pruefmittel").
#
#   Cloudflare kennt dafuer ein Service-Token: zwei Kopfzeilen, keine Anmeldung,
#   kein Browser. Es liegt bereits im Schluesselkasten
#   (~/.secrets/cf_svc_client_id, ~/.secrets/cf_svc_client_secret) — es wurde
#   nur nie benutzt. Dieses Skript ist die eine Stelle, die es kennt.
#
# BENUTZUNG
#   tools/cf-access-fetch.sh https://iil.pet/kd/risk-hub/
#   tools/cf-access-fetch.sh https://iil.pet/kd/ -o /dev/null -w '%{http_code}\n'
#   tools/cf-access-fetch.sh --selftest      # beweist, dass die Pruefung beisst
#   tools/cf-access-fetch.sh --coverage      # welche Hosts der Token abdeckt
#
#   Alle weiteren Argumente gehen unveraendert an curl.
#
# ABDECKUNG (gemessen 2026-08-05, `--coverage` misst es neu)
#   iil.pet                  ja
#   staging-*.iil.pet        ja   (eigene Access-App, Token gilt trotzdem)
#   knowledge.iil.pet        ja
#   kd.iil.pet               NEIN (eigene Access-App, Token nicht berechtigt)
#   orchestrator.iil.pet     n/a  (keine Access-Wand; API-Key statt dessen)
#
# SICHERHEIT
#   Die Werte erscheinen nie auf stdout/stderr und nie in der Prozessliste
#   (Uebergabe an curl per --config aus einer Datei mit 0600, nicht per -H).
#   `set -x` wird bewusst nicht unterstuetzt.
#
# RUECKBAU (ausdruecklich mitgedacht)
#   Dieses Skript ist eine Kruecke um eine Zugangswand, kein Baustein einer
#   Architektur. Es gehoert geloescht, sobald einer dieser Faelle eintritt:
#
#     1. Cloudflare Access faellt fuer die betroffenen Hosts weg
#        -> `--coverage` zeigt fuer ALLE Zeilen "mit == ohne".
#     2. Das Service-Token wird zurueckgezogen
#        -> `--selftest` schlaegt fehl (und zwar laut, nicht still).
#     3. Es wird ein Jahr lang von nichts ausser sich selbst aufgerufen
#        -> Pruefung: `grep -rl cf-access-fetch ~/github --include='*.sh' \
#             --include='*.yml' --include='*.md' | grep -v platform/tools`
#           Leer = kein Nutzer = weg damit.
#
#   Der Rueckbau ist EIN `git rm tools/cf-access-fetch.sh` plus die Zeile in
#   `docs/conventions/`. Es gibt keinen Zustand, keine Migration, keine
#   Abhaengigkeit in andere Richtung — bewusst so gebaut. Wer es entfernt,
#   muss nichts nachziehen ausser den Aufrufern, und die findet der grep oben.
#
#   Kill-Gate-Datum: 2027-08-05. Bis dahin einmal gegen die drei Faelle pruefen.

set -euo pipefail

SECRET_DIR="${CF_SECRET_DIR:-$HOME/.secrets}"
ID_FILE="$SECRET_DIR/cf_svc_client_id"
SECRET_FILE="$SECRET_DIR/cf_svc_client_secret"

# Host, an dem der Selbsttest misst. Muss hinter Access liegen, sonst kann der
# Test nicht zwischen "Token wirkt" und "Wand ist offen" unterscheiden.
SELFTEST_URL="${CF_SELFTEST_URL:-https://iil.pet/}"

COVERAGE_HOSTS=(
  "https://iil.pet/"
  "https://knowledge.iil.pet/"
  "https://kd.iil.pet/"
)

fehler() {
  echo "cf-access-fetch: $*" >&2
  exit 1
}

token_pruefen() {
  [ -r "$ID_FILE" ] || fehler "Schluessel fehlt: $ID_FILE (Name, nicht Wert)"
  [ -r "$SECRET_FILE" ] || fehler "Schluessel fehlt: $SECRET_FILE (Name, nicht Wert)"
  [ -s "$ID_FILE" ] || fehler "leer: $ID_FILE"
  [ -s "$SECRET_FILE" ] || fehler "leer: $SECRET_FILE"
}

# curl-Konfigdatei mit den Kopfzeilen bauen. Ueber --config, damit die Werte
# nicht in der Prozessliste stehen (`ps aux` zeigt -H-Argumente im Klartext).
config_datei() {
  local datei
  datei="$(mktemp)"
  chmod 600 "$datei"
  {
    printf 'header = "CF-Access-Client-Id: %s"\n' "$(tr -d '\r\n' <"$ID_FILE")"
    printf 'header = "CF-Access-Client-Secret: %s"\n' "$(tr -d '\r\n' <"$SECRET_FILE")"
  } >"$datei"
  echo "$datei"
}

mit_token() {
  local cfg rc
  cfg="$(config_datei)"
  # shellcheck disable=SC2064 — Pfad soll JETZT eingesetzt werden
  trap "rm -f '$cfg'" RETURN
  set +e
  curl --config "$cfg" "$@"
  rc=$?
  set -e
  return $rc
}

status_mit() { mit_token -sS -o /dev/null -w '%{http_code}' --max-time 20 "$1" || echo "ERR"; }
status_ohne() { curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$1" 2>/dev/null || echo "ERR"; }

selftest() {
  token_pruefen
  local mit ohne
  mit="$(status_mit "$SELFTEST_URL")"
  ohne="$(status_ohne "$SELFTEST_URL")"

  echo "Selbsttest gegen $SELFTEST_URL"
  echo "  mit Token : $mit"
  echo "  ohne Token: $ohne"

  # Die Rot-Fixture: ohne Gegenprobe waere ein 200 wertlos — es koennte auch
  # heissen, dass vor dem Host gar keine Wand steht.
  if [ "$ohne" != "302" ]; then
    fehler "FAIL — ohne Token kam $ohne statt 302. Entweder steht keine
        Access-Wand mehr vor $SELFTEST_URL (dann ist dieses Skript ueberfluessig,
        siehe RUECKBAU Fall 1), oder die Messung ist kaputt."
  fi
  if [ "$mit" != "200" ]; then
    fehler "FAIL — mit Token kam $mit statt 200. Das Service-Token ist fuer
        diesen Host nicht (mehr) berechtigt (siehe RUECKBAU Fall 2).
        Pruefen: Cloudflare Zero Trust -> Access -> Applications -> Policies."
  fi
  echo "OK — Token wirkt, und die Messung kann den Unterschied sehen."
}

coverage() {
  token_pruefen
  printf '%-32s %-10s %-10s %s\n' "Host" "mit" "ohne" "Befund"
  local wirkt=0
  for url in "${COVERAGE_HOSTS[@]}"; do
    local mit ohne befund
    mit="$(status_mit "$url")"
    ohne="$(status_ohne "$url")"
    if [ "$mit" = "$ohne" ]; then
      befund="keine Wirkung (eigene Access-App oder keine Wand)"
    else
      befund="Token wirkt"
      wirkt=$((wirkt + 1))
    fi
    printf '%-32s %-10s %-10s %s\n' "${url#https://}" "$mit" "$ohne" "$befund"
  done
  echo
  if [ "$wirkt" -eq 0 ]; then
    echo "Kein Host profitiert mehr vom Token — RUECKBAU Fall 1 pruefen." >&2
    return 1
  fi
}

case "${1:-}" in
  --selftest) selftest ;;
  --coverage) coverage ;;
  "" | -h | --help)
    sed -n '2,60p' "$0" | sed 's/^# \{0,1\}//'
    ;;
  *)
    token_pruefen
    mit_token "$@"
    ;;
esac
