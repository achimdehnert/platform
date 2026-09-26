#!/usr/bin/env bash
# Stellt das Offsite-Ziel der restic-Sicherung vom toten netcup-rest-server auf
# die vorhandene Hetzner Storage Box (SFTP) um.
#
# Anlass: ADR-289 §3.1b Revision 3 (Owner-Wort „Storage Box go", 2026-09-24,
# achimdehnert/platform#3475). Object Storage (#2968) wurde verworfen: es gibt
# bereits eine bezahlte Storage Box, und Unveraenderlichkeit laesst sich dort
# ueber den taeglichen automatischen Snapshot-Plan der Box erreichen statt
# ueber einen zweiten Vertrag mit Object Lock. Der Transport
# (prod-offsite-daily.sh, Cron 02:30) ist unveraendert; es fehlt nur das Ziel —
# Konfigurations-Aenderung, keine Code-Aenderung.
#
#     bash deployment/scripts/offsite-auf-storagebox-umstellen.sh
#     TROCKEN=1 bash deployment/scripts/offsite-auf-storagebox-umstellen.sh
#     PROD_HOST=hetzner-prod-b bash deployment/scripts/offsite-auf-storagebox-umstellen.sh
#
# Erwartet ~/.secrets/hetzner-storagebox.env (Pfad ueber SB_ENV_FILE
# ueberschreibbar) mit GENAU diesen Schluesseln (Werte gehoeren dorthin — nie
# in dieses Repo, nie in eine Chat-Nachricht, nie in eine Ausgabe dieses
# Skripts):
#
#     SB_HOST=<box>.your-storagebox.de
#     SB_USER=<unterkonto fuer diesen Host>
#     SB_PFAD=/                              # optional, Default /
#     SB_SNAPSHOTS_BESTAETIGT=1              # erst setzen, wenn der Snapshot-
#                                             # Plan der Box wirklich steht
#
# Keine Passwoerter — Auth ausschliesslich per SSH-Schluessel (der Host-
# eigene, bereits vorhandene). SB_SNAPSHOTS_BESTAETIGT ist per SFTP nicht
# pruefbar (die Snapshot-Konfiguration liegt in der Hetzner-Konsole/-API,
# nicht im Dateisystem der Box) — der Agent prueft sie separat per API und
# setzt diese Zeile erst danach. Ohne sie wird NICHT umgestellt: ADR-289
# §3.1b Nr. 2 macht den taeglichen Snapshot-Plan zur einzigen Unveraender-
# lichkeits-Eigenschaft dieses Ziels (SFTP selbst kennt kein Append-only) —
# fehlt er, ist ein kompromittierter Quell-Host in der Lage, seine eigenen
# Sicherungen restlos zu loeschen.
#
# Transportweg: ~/.ssh/config-Alias `storagebox-offsite` auf dem Ziel-Host,
# NICHT `-o sftp.command="ssh -p 23 ..."` direkt in RESTIC_REPOSITORY. Zwei
# Gruende: (1) Cron laeuft mit minimaler Umgebung; ein Host-Alias in
# /root/.ssh/config wird von jedem ssh-Aufruf (auch dem, den restic intern
# fuer das sftp-Backend startet) gleich aufgeloest, ohne dass Port,
# IdentityFile und Nutzername in der restic-Aufrufzeile selbst stehen muessen.
# (2) Dadurch taucht SB_HOST/SB_USER nirgends in RESTIC_REPOSITORY, einer
# Log-Zeile oder diesem Skript auf — nur im Alias, serverseitig. Port 23 ist
# fest (Hetzner Storage Box SFTP), StrictHostKeyChecking bleibt Standard
# (nicht accept-new): der Fingerabdruck muss laut Vorgabe VOR dem Lauf schon
# in known_hosts stehen, Tor B prueft das und bricht sonst mit Anleitung ab.
#
# Die Zeile RESTIC_PASSWORD_FILE auf dem Host bleibt UNANGETASTET — dieses
# Skript liest ihren Wert nicht und schreibt ihn nicht neu (wie schon in
# offsite-auf-objectstorage-umstellen.sh, #2968). Ein neues Ziel ist kein
# Grund, den restic-Repository-Schluessel zu drehen; gedreht wuerden sonst
# auch alle alten Snapshots unlesbar.
set -euo pipefail

SB_ENV_DATEI="${SB_ENV_FILE:-$HOME/.secrets/hetzner-storagebox.env}"
HOST="${PROD_HOST:-hetzner-prod}"
ZIEL_ENV="/etc/offsite-backup.env"
SICHERUNGS_VERZEICHNIS="/root/offsite-backup-env-backups"
TROCKEN="${TROCKEN:-0}"
STAND="$(date +%Y-%m-%d)"

fehler() { echo "FEHLER: $*" >&2; exit 1; }

# ── A. Env-Datei vollstaendig ────────────────────────────────────────────────
echo "== A. ${SB_ENV_DATEI} lesen =="
[ -f "$SB_ENV_DATEI" ] || fehler "$SB_ENV_DATEI fehlt. Anlegen mit den Schluesseln aus dem Kopf dieser Datei."

set -a
# shellcheck disable=SC1090
. "$SB_ENV_DATEI"
set +a
: "${SB_HOST:?SB_HOST fehlt in $SB_ENV_DATEI}"
: "${SB_USER:?SB_USER fehlt in $SB_ENV_DATEI}"
SB_PFAD="${SB_PFAD:-/}"

REPO="sftp:storagebox-offsite:${SB_PFAD}"
echo "  Ziel-Alias: storagebox-offsite  Pfad: ${SB_PFAD}  Host fuer die Umstellung: ${HOST}"

# ── B. Host-Key von SB_HOST:23 muss auf $HOST schon bekannt sein ───────────
echo "== B. Host-Key [SB_HOST]:23 auf ${HOST} pruefen =="
if ! ssh "$HOST" "ssh-keygen -F '[${SB_HOST}]:23'" >/dev/null 2>&1; then
  fehler "Kein Host-Key fuer das Unterkonto-Ziel in ${HOST}:~/.ssh/known_hosts. \
StrictHostKeyChecking=accept-new ist hier NICHT erlaubt (der Fingerabdruck \
muss vorher geprueft sein). Owner-Schritt, nicht automatisch ausfuehrbar: \
ssh ${HOST} 'ssh-keyscan -p 23 \$SB_HOST >> /root/.ssh/known_hosts'  # \$SB_HOST aus ${SB_ENV_DATEI}, danach Fingerabdruck manuell gegenpruefen."
fi
echo "  Host-Key vorhanden."

# ── C. SFTP-Login vom Ziel-Host aus ─────────────────────────────────────────
echo "== C. SFTP-Login des Unterkontos von ${HOST} aus pruefen =="
if ! ssh "$HOST" "printf '%s\n' pwd | sftp -b - -P 23 -o BatchMode=yes -o ConnectTimeout=10 '${SB_USER}@${SB_HOST}'" >/dev/null 2>&1; then
  fehler "SFTP-Login des Unterkontos von ${HOST} aus fehlgeschlagen. Pruefen: \
Unterkonto angelegt? SSH-Public-Key von ${HOST} im Unterkonto hinterlegt? \
BatchMode verlangt Schluessel-Auth ohne Passwort-Prompt — genau das ist die \
Vorgabe (keine Passwoerter)."
fi
echo "  SFTP-Login ok."

# ── D. Snapshot-Plan bestaetigt ─────────────────────────────────────────────
echo "== D. Snapshot-Plan-Bestaetigung pruefen =="
if [ "${SB_SNAPSHOTS_BESTAETIGT:-0}" != "1" ]; then
  fehler "SB_SNAPSHOTS_BESTAETIGT ist nicht 1 in ${SB_ENV_DATEI}. Ohne bestaetigten \
taeglichen Snapshot-Plan der Box fehlt die Unveraenderlichkeit dieses Ziels \
(ADR-289 §3.1b Nr. 2) — der Agent prueft den Plan per Hetzner-API und setzt \
diese Zeile erst danach. Kein automatisches Weiterlaufen ohne sie."
fi
echo "  Snapshot-Plan bestaetigt (SB_SNAPSHOTS_BESTAETIGT=1)."

if [ "$TROCKEN" = "1" ]; then
  echo "== TROCKEN: alle vier Tore bestanden. Es wuerde jetzt umgestellt: =="
  echo "  - /root/.ssh/config auf ${HOST}: Block 'Host storagebox-offsite' anlegen/ersetzen"
  echo "  - ${ZIEL_ENV} sichern nach ${SICHERUNGS_VERZEICHNIS}/offsite-backup.env.vor-${STAND}"
  echo "  - RESTIC_REPOSITORY -> ${REPO}, RESTIC_CACERT-Zeile entfernen, RESTIC_PASSWORD_FILE unveraendert"
  echo "  - restic snapshots gegen das neue Ziel; init nur mit SB_INIT_ERLAUBT=1"
  echo "  - Erster Lauf ueber /usr/local/bin/prod-offsite-daily.sh + Gegenprobe je Tag"
  exit 0
fi

# ── E. ~/.ssh/config auf dem Host: Block idempotent anlegen/ersetzen ───────
# Eigener SSH-Host-Alias statt inline `-o sftp.command=...` — Begruendung im
# Kopfkommentar. Idempotent ueber BEGIN/END-Marker: ein zweiter Lauf ersetzt
# den Block, statt ihn zu verdoppeln.
echo "== E. /root/.ssh/config auf ${HOST} umstellen (Alias storagebox-offsite) =="
ssh "$HOST" "SB_HOST='${SB_HOST}' SB_USER='${SB_USER}' bash -s" <<'REMOTE'
set -euo pipefail
CONF=/root/.ssh/config
START='# BEGIN storagebox-offsite (deployment/scripts/offsite-auf-storagebox-umstellen.sh)'
ENDE='# END storagebox-offsite'
touch "$CONF"
chmod 600 "$CONF"
if grep -qF "$START" "$CONF"; then
  sed -i "\#${START}#,\#${ENDE}#d" "$CONF"
fi
{
  echo "$START"
  echo "Host storagebox-offsite"
  echo "    HostName ${SB_HOST}"
  echo "    Port 23"
  echo "    User ${SB_USER}"
  echo "    IdentityFile /root/.ssh/id_ed25519"
  echo "    IdentitiesOnly yes"
  echo "$ENDE"
} >> "$CONF"
REMOTE
echo "  Alias 'storagebox-offsite' angelegt/aktualisiert."

# ── F. ${ZIEL_ENV} an Ort und Stelle umstellen ──────────────────────────────
# Sicherungskopie NICHT daneben in /etc/ — Lehre von heute (Sitzung
# 2026-09-24): eine Kopie im selben Verzeichnis wie eine aktiv eingelesene
# Konfigurationsdatei kann von Werkzeugen erfasst werden, die das Verzeichnis
# pauschal einlesen (Include-Glob). Deshalb eigenes Verzeichnis, ausserhalb
# jedes Include-Pfads.
#
# Bewusst KEIN Neuschreiben der ganzen Datei: RESTIC_PASSWORD_FILE bleibt so
# stehen, wie es ist, und wird dafuer nicht gelesen. RESTIC_CACERT faellt weg
# — es zeigte auf das CA des netcup-rest-servers; die Storage Box braucht das
# nicht (OpenSSH prueft ueber known_hosts, nicht TLS/CA).
echo "== F. ${ZIEL_ENV} umstellen (alte Fassung wird gesichert) =="
ssh "$HOST" "mkdir -p ${SICHERUNGS_VERZEICHNIS} && chmod 700 ${SICHERUNGS_VERZEICHNIS} \
  && cp -a ${ZIEL_ENV} ${SICHERUNGS_VERZEICHNIS}/offsite-backup.env.vor-${STAND} \
  && sed -i -E '/^RESTIC_CACERT=/d' ${ZIEL_ENV} \
  && if grep -q '^RESTIC_REPOSITORY=' ${ZIEL_ENV}; then \
       sed -i -E 's#^RESTIC_REPOSITORY=.*#RESTIC_REPOSITORY=${REPO}#' ${ZIEL_ENV}; \
     else \
       printf '%s\n' 'RESTIC_REPOSITORY=${REPO}' >> ${ZIEL_ENV}; \
     fi \
  && chmod 600 ${ZIEL_ENV} && chown root:root ${ZIEL_ENV}"
echo "  ${ZIEL_ENV} umgestellt, Sicherungskopie unter ${SICHERUNGS_VERZEICHNIS}/."

# ── G. restic-Repository pruefen, nur mit ausdruecklicher Erlaubnis anlegen ─
echo "== G. restic-Repository am neuen Ziel pruefen =="
SNAPSHOT_AUSGABE="$(ssh "$HOST" "set -a; . ${ZIEL_ENV}; set +a; restic snapshots --compact 2>&1" || true)"
if echo "$SNAPSHOT_AUSGABE" | grep -qiE 'repository does not exist|unable to open (config file|repository)'; then
  if [ "${SB_INIT_ERLAUBT:-0}" = "1" ]; then
    echo "  Repository fehlt, initialisiere (SB_INIT_ERLAUBT=1) ..."
    ssh "$HOST" "set -a; . ${ZIEL_ENV}; set +a; restic init 2>&1 | tail -5"
  else
    fehler "Repository unter ${REPO} existiert nicht. Kein automatisches 'restic init' \
ohne ausdrueckliche Erlaubnis — ein Init auf falschem SB_PFAD soll nicht still \
passieren. Pfad pruefen; falls das der richtige, neue Pfad ist: SB_INIT_ERLAUBT=1 \
setzen und das Skript erneut ausfuehren. Ausgabe: ${SNAPSHOT_AUSGABE}"
  fi
else
  echo "  Repository existiert bereits."
  echo "$SNAPSHOT_AUSGABE" | tail -5
fi

# ── H. Erster Lauf ueber den regulaeren Transport ──────────────────────────
# Bewusst das Cron-Skript und nicht ein Handgriff: geprueft werden soll der
# Weg, der nachts wirklich laeuft.
echo "== H. Erster Sicherungslauf (regulaerer Weg) =="
ssh "$HOST" "/usr/local/bin/prod-offsite-daily.sh" 2>&1 | tail -15

echo "== Gegenprobe am Ziel — letzte 3 Snapshots je Tag =="
for TAG in pgdump volumes config; do
  echo "-- Tag: ${TAG} --"
  ssh "$HOST" "set -a; . ${ZIEL_ENV}; set +a; restic snapshots --tag ${TAG} --latest 3 --compact 2>&1" | tail -6
done

echo
echo "Zurueck im Fehlerfall:"
echo "  ssh ${HOST} 'cp -a ${SICHERUNGS_VERZEICHNIS}/offsite-backup.env.vor-${STAND} ${ZIEL_ENV}'"
