#!/usr/bin/env bash
# Schleuse zwischen Dev-Host und GPU-Box (Windows, 10.99.0.2) — platform#1888 K4.
#
# WARUM ES DAS BRAUCHT
#
# Der Dev-Host erreicht die Box nicht. Gemessen 2026-08-10: `10.99.0.2:8000` tot,
# Gegenprobe `88.198.191.108:22` mit derselben Methode offen — die Methode taugt also,
# die Route fehlt. `ip route get 10.99.0.2` laeuft ins Standard-Gateway; auf dem Dev-Host
# gibt es kein WireGuard. Jeder Weg zur Box fuehrt ueber Prod.
#
# Die Box wiederum hat bereits eine SMB-Verbindung nach Prod (`net use` zeigt
# `\\10.99.0.1\...`). Genau die wird hier zum Transportweg: Prod ist die Relais-Station,
# beide Seiten legen dort ab und holen dort.
#
#     Box  --SMB-->  Prod:/opt/paperless-consume/schleuse/  <--ssh--  Dev-Host
#
# WARUM DIESER ORDNER
#
# Er liegt unter der bestehenden Samba-Freigabe `scans`, damit KEINE Samba-Aenderung und
# kein Dienst-Neustart noetig ist (das waere Gate 2). Geprueft am 2026-08-10: der Pfad
# `/opt/paperless-consume` ist in keinem laufenden Container gemountet (Gegenprobe: dasselbe
# Muster findet den echten Paperless-Mount sehr wohl) und steht in keinem Cron-Eintrag
# (Gegenprobe: die crontab hat 18 Zeilen, ist also lesbar). Es wird dort nichts verarbeitet.
#
# Sauberer waere eine eigene Freigabe `[schleuse]` mit eigenem Pfad — das aendert
# `smb.conf` und verlangt einen Samba-Reload, also Gate 2. Als Vorschlag notiert, nicht
# umgesetzt.
#
# KEINE SECRETS. Die Schleuse ist ein Durchgang, kein Lager — sie ist fuer den
# scansnap-Nutzer lesbar und wird nicht ueberwacht.
#
# VERWENDUNG
#
#     box-schleuse.sh hol [ziel]        # von-box/  -> lokal (Default: ~/shared/von-box/)
#     box-schleuse.sh bring <datei>...  # lokal     -> zur-box/
#     box-schleuse.sh liste             # was liegt in beiden Richtungen
#     box-schleuse.sh leere von-box     # aufraeumen (nur nach dem Abholen)
#
# Auf der Box (PowerShell, einzeilig, ohne Anfuehrungszeichen):
#
#     copy <quelle> \\10.99.0.1\scans\schleuse\von-box\
#     copy \\10.99.0.1\scans\schleuse\zur-box\<datei> <ziel>

set -euo pipefail

RELAIS="${BOX_SCHLEUSE_HOST:-root@88.198.191.108}"
FERN="${BOX_SCHLEUSE_PFAD:-/opt/paperless-consume/schleuse}"
LOKAL="${BOX_SCHLEUSE_LOKAL:-$HOME/shared}"

: "${1:?Verwendung: hol [ziel] | bring <datei>... | liste | leere <von-box|zur-box>}"
BEFEHL="$1"; shift || true

# Nach jedem Schreiben in die Schleuse: Gruppe und Rechte geradeziehen. Ohne das kann die
# Box (als scansnap) eine vom Dev-Host abgelegte Datei nicht lesen — ein Fehler, der erst
# drueben auffaellt und dort schwer zu deuten ist.
_rechte_richten() {
    ssh "$RELAIS" "chgrp -R scanner '$FERN' 2>/dev/null; chmod -R g+rw '$FERN' 2>/dev/null; true"
}

case "$BEFEHL" in
  hol)
    ZIEL="${1:-$LOKAL/von-box}"
    mkdir -p "$ZIEL"
    # -q, weil die Schleuse auch leer sein darf; das meldet die Zaehlung danach.
    scp -q -r "$RELAIS:$FERN/von-box/." "$ZIEL/" 2>/dev/null || true
    ANZAHL=$(find "$ZIEL" -type f ! -name '.gitkeep' | wc -l)
    echo "geholt nach $ZIEL — $ANZAHL Datei(en) liegen dort"
    [ "$ANZAHL" -eq 0 ] && echo "  (leer — hat die Box schon abgelegt?)"
    ;;

  bring)
    [ "$#" -ge 1 ] || { echo "bring braucht mindestens eine Datei" >&2; exit 2; }
    for f in "$@"; do
        [ -e "$f" ] || { echo "gibt es nicht: $f" >&2; exit 2; }
    done
    scp -q -r "$@" "$RELAIS:$FERN/zur-box/"
    _rechte_richten
    echo "abgelegt in zur-box — auf der Box abzuholen unter:"
    for f in "$@"; do echo "  \\\\10.99.0.1\\scans\\schleuse\\zur-box\\$(basename "$f")"; done
    ;;

  liste)
    ssh "$RELAIS" "for r in von-box zur-box; do
        echo \"--- \$r\"
        ls -lh '$FERN'/\$r 2>/dev/null | tail -n +2 || echo '  (leer)'
    done"
    ;;

  leere)
    RICHTUNG="${1:?leere braucht von-box oder zur-box}"
    case "$RICHTUNG" in von-box|zur-box) ;; *) echo "nur von-box oder zur-box" >&2; exit 2 ;; esac
    # Bewusst kein rm -rf auf dem Ordner selbst: der Ordner traegt die Rechte, die die
    # Box zum Schreiben braucht. Nur der Inhalt weicht.
    ssh "$RELAIS" "find '$FERN/$RICHTUNG' -mindepth 1 -delete"
    echo "$RICHTUNG geleert"
    ;;

  *)
    echo "unbekannt: $BEFEHL — hol | bring | liste | leere" >&2
    exit 2
    ;;
esac
