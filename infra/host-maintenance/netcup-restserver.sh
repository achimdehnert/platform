#!/usr/bin/env bash
# netcup-restserver.sh — restic-Repository auf netcup (ADR-289 R1, Phase 5)
#
# Richtet auf dem netcup-Host den Ziel-Dienst fuer die Offsite-Sicherung ein:
# rest-server im Container mit --append-only, hinter TLS, mit Basic-Auth.
#
# WARUM rest-server und nicht SFTP: Nur rest-server kann Append-only TECHNISCH
# erzwingen. Ueber SFTP koennte ein uebernommener Quell-Host seine eigenen
# Sicherungen loeschen — genau die Fehlerklasse, gegen die ein Offsite-Backup
# existiert. Das ist der Grund, warum ADR-289 einen Server und keine Ablage waehlt.
#
# WARUM TLS: Die Basic-Auth-Kennung ginge sonst im Klartext ueber das Netz. Die
# Nutzdaten sind durch restic ohnehin clientseitig verschluesselt, die Kennung nicht.
#
# Das Zertifikat ist selbstsigniert und wird auf dem Client gezielt vertraut
# (restic --cacert). Begruendung im Skript, Abschnitt 2.
#
# Idempotent. Vorschau: DRY_RUN=1 bash netcup-restserver.sh
#
# Secrets: Dieses Skript ERZEUGT die Basic-Auth-Kennung und legt sie mit 0600 ab.
# Es gibt sie NIE auf stdout aus. Der Wert wird am Ende nur als PFAD genannt.

set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
FQDN="${FQDN:-v2202604344838448611.goodsrv.de}"
DATA_DIR="/srv/restic"
CONF_DIR="/etc/restserver"
REST_USER="${REST_USER:-prod-backup}"
HOST_IP="${HOST_IP:-152.53.136.219}"
CERT_DIR="/etc/restserver/tls"

log() { printf '\n=== %s\n' "$*"; }
did() { printf '  → %s\n' "$*"; }
skip() { printf '  ✓ %s (schon vorhanden)\n' "$*"; }
run() { if [[ "$DRY_RUN" == "1" ]]; then printf '  [dry-run] %s\n' "$*"; else eval "$@"; fi; }

[[ "$(id -u)" -eq 0 ]] || { echo "FEHLER: root noetig." >&2; exit 1; }
command -v docker >/dev/null || { echo "FEHLER: Docker fehlt — erst netcup-bootstrap.sh." >&2; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
log "1. Verzeichnisse"
for d in "$DATA_DIR" "$CONF_DIR"; do
  if [[ -d "$d" ]]; then skip "$d"; else run "mkdir -p '$d'"; did "$d angelegt"; fi
done
run "chmod 700 '$CONF_DIR'"

# ─────────────────────────────────────────────────────────────────────────────
log "2. TLS-Zertifikat (eigene CA, 10 Jahre)"
# Bewusst KEIN Let's Encrypt: Der netcup-Standardhostname liegt unter der GETEILTEN
# Domain goodsrv.de, deren LE-Wochenkontingent (50 Zertifikate) von anderen Kunden
# aufgebraucht wird — verifiziert 2026-07-30: "too many certificates (50) already
# issued for goodsrv.de". Das ist kein Ausrutscher, sondern strukturell: wir teilen
# das Kontingent mit Fremden.
# Fuer einen Punkt-zu-Punkt-Kanal mit GENAU EINEM Client ist ein eigenes Zertifikat
# ohnehin die bessere Wahl — kein Rate-Limit, keine 90-Tage-Erneuerung, kein
# oeffentlich aufloesbarer Name noetig. Der Client vertraut gezielt diesem einen
# Zertifikat (restic --cacert), nicht einer oeffentlichen CA.
if [[ -f "$CERT_DIR/fullchain.pem" ]]; then
  skip "Zertifikat vorhanden"
else
  run "mkdir -p '$CERT_DIR'"
  run "openssl req -x509 -newkey rsa:4096 -nodes -days 3650 \
        -keyout '$CERT_DIR/privkey.pem' -out '$CERT_DIR/fullchain.pem' \
        -subj '/CN=${FQDN}' \
        -addext 'subjectAltName=DNS:${FQDN},IP:${HOST_IP}' 2>/dev/null"
  run "chmod 600 '$CERT_DIR/privkey.pem'"
  did "Selbstsigniertes Zertifikat erzeugt (10 Jahre, CN=${FQDN})"
fi

# ─────────────────────────────────────────────────────────────────────────────
log "3. Basic-Auth-Kennung (wird NIE ausgegeben)"
if [[ -s "$CONF_DIR/.htpasswd" ]]; then
  skip ".htpasswd vorhanden"
else
  run "apt-get install -y -qq apache2-utils"
  # Kennung erzeugen, direkt in Datei, nie ueber stdout oder Prozessliste.
  run "umask 077; pw=\$(openssl rand -base64 30); \
       htpasswd -cbB '$CONF_DIR/.htpasswd' '$REST_USER' \"\$pw\" >/dev/null; \
       printf '%s\n' \"\$pw\" > '$CONF_DIR/rest-user.pass'; unset pw"
  run "chmod 600 '$CONF_DIR/.htpasswd' '$CONF_DIR/rest-user.pass'"
  did "Kennung erzeugt fuer Benutzer '$REST_USER'"
fi

# ─────────────────────────────────────────────────────────────────────────────
log "4. rest-server (--append-only, TLS)"
if docker ps --format '{{.Names}}' | grep -qx restserver; then
  skip "Container laeuft"
else
  run "docker rm -f restserver >/dev/null 2>&1 || true"
  # Das Image hat einen eigenen Entrypoint: Optionen kommen ueber OPTIONS, NICHT
  # als Kommando-Argumente (sonst: exec "--path": executable file not found).
  run "docker run -d --name restserver --restart unless-stopped \
        -p 8443:8000 \
        -v '$DATA_DIR':/data \
        -v '$CONF_DIR/.htpasswd':/data/.htpasswd:ro \
        -v '$CERT_DIR':/certs:ro \
        -e OPTIONS='--append-only --tls --tls-cert /certs/fullchain.pem --tls-key /certs/privkey.pem' \
        restic/rest-server:latest"
  did "Container gestartet auf :8443 (append-only, TLS)"
fi

# ─────────────────────────────────────────────────────────────────────────────
log "5. Ergebnis"
if [[ "$DRY_RUN" == "1" ]]; then echo "  [dry-run] nichts geaendert."; exit 0; fi
docker ps --filter name=restserver --format '  Container: {{.Names}} {{.Status}}'
printf '  Endpunkt : rest:https://%s:8443/\n' "$FQDN"
printf '  Benutzer : %s\n' "$REST_USER"
printf '  Kennung  : %s  (0600, NICHT ausgeben — von hier in den Passwortspeicher)\n' \
  "$CONF_DIR/rest-user.pass"
printf '  Daten    : %s\n' "$DATA_DIR"

cat <<'HINWEIS'

  ⚠ ZWEI DINGE, DIE JETZT ZWINGEND FOLGEN

  1. Die Basic-Auth-Kennung und spaeter das restic-Repository-Passwort muessen
     AUSSERHALB dieses Hosts UND ausserhalb von prod gesichert werden. Liegt das
     Repository-Passwort nur auf dem Quell-Host, ist die Sicherung nach dessen
     Totalverlust unbrauchbar — genau der Fall, fuer den sie gemacht ist.

  2. Port 8443 ist jetzt offen erreichbar. Die netcup-Panel-Firewall steht auf
     "aktiv, ohne Regelsatz". Sinnvoll: 8443 auf die Quell-Host-IP begrenzen,
     22 auf die Arbeitsplatz-IP. Das ist nur im netcup-Panel moeglich, nicht per SSH.

HINWEIS
