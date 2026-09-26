#!/usr/bin/env bash
# Stellt das Offsite-Ziel von netcup (rest-server) auf S3-Objektspeicher um.
#
# Anlass: ADR-289 §3.1a — netcup ist am 2026-09-08 ausgefallen, letzter
# erfolgreicher Snapshot 2026-09-07 03:30. Der Transport selbst
# (offsite-backup.sh, Cron 02:30) ist intakt; es fehlt nur das Ziel. Die
# Umstellung ist deshalb eine KONFIGURATIONS-Aenderung, keine Code-Aenderung:
# offsite-backup.sh laedt die Env-Datei mit `set -a` und exportiert damit auch
# AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY, ohne sie kennen zu muessen.
#
#     bash deployment/scripts/offsite-auf-objectstorage-umstellen.sh
#     TROCKEN=1 bash deployment/scripts/offsite-auf-objectstorage-umstellen.sh
#
# Erwartet ~/.secrets/hetzner-objectstorage.env mit GENAU diesen Schluesseln
# (Werte gehoeren dorthin — nie in dieses Repo, nie in eine Chat-Nachricht):
#
#     OS_ENDPOINT=https://<standort>.your-objectstorage.com
#     OS_BUCKET=<bucketname>
#     AWS_ACCESS_KEY_ID=...
#     AWS_SECRET_ACCESS_KEY=...
#
# Die Zeile RESTIC_PASSWORD_FILE auf dem Host bleibt UNANGETASTET — dieses
# Skript liest ihren Wert nicht und schreibt ihn nicht neu. Der Key-Escrow aus
# ADR-241 §2 aendert sich damit nicht, und das ist Absicht: ein neues Ziel ist
# kein Grund, den Schluessel zu drehen. Ein gedrehter Schluessel machte
# ausserdem die alten Snapshots unlesbar.
set -euo pipefail

GEHEIM="${OS_ENV_FILE:-$HOME/.secrets/hetzner-objectstorage.env}"
HOST="${PROD_HOST:-hetzner-prod}"
ZIEL_ENV="/etc/offsite-backup.env"
TROCKEN="${TROCKEN:-0}"
STAND="$(date +%Y-%m-%d)"

fehler() { echo "FEHLER: $*" >&2; exit 1; }

[ -f "$GEHEIM" ] || fehler "$GEHEIM fehlt. Anlegen mit den vier Schluesseln aus dem Kopf dieser Datei."

set -a
# shellcheck disable=SC1090
. "$GEHEIM"
set +a
: "${OS_ENDPOINT:?OS_ENDPOINT fehlt}"
: "${OS_BUCKET:?OS_BUCKET fehlt}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID fehlt}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY fehlt}"

REPO="s3:${OS_ENDPOINT}/${OS_BUCKET}"
echo "Ziel: ${REPO}"   # Endpunkt und Bucketname sind keine Geheimnisse

# ── 1. Object Lock pruefen ─────────────────────────────────────────────────
# Der Punkt, der spaeter nicht mehr korrigierbar ist: Object Lock laesst sich
# laut Hetzner-Doku NUR beim Anlegen des Buckets aktivieren. Faellt die
# Pruefung durch, muss der Bucket neu gebaut werden — deshalb steht sie vor
# allem anderen und bricht hart ab, statt zu warnen und weiterzumachen.
echo "== 1. Object Lock am Bucket pruefen =="
command -v mc >/dev/null 2>&1 \
  || fehler "mc (MinIO Client) fehlt — ohne ihn ist Object Lock nicht pruefbar. Ohne Pruefung wird nicht umgestellt."

mc alias set offsite-ziel "$OS_ENDPOINT" "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" >/dev/null 2>&1 \
  || fehler "Anmeldung am Objektspeicher fehlgeschlagen — Endpunkt oder Zugangsdaten pruefen"

SPERRE="$(mc retention info "offsite-ziel/${OS_BUCKET}" 2>&1 || true)"
echo "$SPERRE" | head -3
case "$SPERRE" in
  *[Cc]ompliance*|*COMPLIANCE*)
    echo "  -> Compliance-Modus aktiv" ;;
  *[Gg]overnance*|*GOVERNANCE*)
    fehler "Object Lock steht auf GOVERNANCE. ADR-289 §3.1a verlangt COMPLIANCE — Governance laesst sich mit genug Rechten umgehen, und genau davor soll die Sperre schuetzen." ;;
  *)
    fehler "Kein Object Lock am Bucket erkennbar. Nachtraeglich NICHT aktivierbar — der Bucket muss mit Object Lock neu angelegt werden (ADR-289 §3.1a, Auflage 1)." ;;
esac

if [ "$TROCKEN" = "1" ]; then
  echo "== TROCKEN: Object Lock ok. Es wuerde jetzt umgestellt, initialisiert und gesichert. =="
  exit 0
fi

# ── 2. Env-Datei an Ort und Stelle umstellen ───────────────────────────────
# Bewusst KEIN Neuschreiben der ganzen Datei: RESTIC_PASSWORD_FILE bleibt so
# stehen, wie es ist, und muss dafuer nicht gelesen werden.
#
# RESTIC_CACERT faellt weg — es zeigte auf das CA des netcup-rest-servers.
# Bliebe es stehen, pruefte restic die oeffentliche TLS-Kette des
# Objektspeichers gegen ein fremdes CA und braeche ab.
echo "== 2. ${ZIEL_ENV} umstellen (alte Fassung wird gesichert) =="
ssh "$HOST" "cp -a ${ZIEL_ENV} ${ZIEL_ENV}.vor-${STAND} \
  && sed -i -E '/^(RESTIC_REPOSITORY|RESTIC_CACERT|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY)=/d' ${ZIEL_ENV} \
  && umask 077 && { \
       printf '%s\n' 'RESTIC_REPOSITORY=${REPO}'; \
       printf '%s\n' 'AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}'; \
       printf '%s\n' 'AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}'; \
     } >> ${ZIEL_ENV} \
  && chmod 600 ${ZIEL_ENV} && chown root:root ${ZIEL_ENV}"

echo -n "  Schluessel in der neuen Datei: "
ssh "$HOST" "grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' ${ZIEL_ENV} | tr -d '=' | tr '\n' ' '"
echo

# ── 3. Repository anlegen ──────────────────────────────────────────────────
echo "== 3. restic-Repository initialisieren =="
ssh "$HOST" "set -a; . ${ZIEL_ENV}; set +a; \
  if restic cat config >/dev/null 2>&1; then echo '  Repository existiert bereits'; \
  else restic init 2>&1 | tail -3; fi"

# ── 4. Erster Lauf ueber den regulaeren Transport ──────────────────────────
# Bewusst das Cron-Skript und nicht ein Handgriff: geprueft werden soll der
# Weg, der nachts wirklich laeuft.
echo "== 4. Erster Sicherungslauf (regulaerer Weg) =="
ssh "$HOST" "/usr/local/bin/prod-offsite-daily.sh" 2>&1 | tail -8

# ── 5. Gegenprobe ──────────────────────────────────────────────────────────
echo "== 5. Gegenprobe am Ziel =="
ssh "$HOST" "set -a; . ${ZIEL_ENV}; set +a; restic snapshots --compact 2>&1 | tail -6"

echo
echo "Zurueck im Fehlerfall:"
echo "  ssh ${HOST} 'cp -a ${ZIEL_ENV}.vor-${STAND} ${ZIEL_ENV}'"
