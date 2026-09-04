#!/usr/bin/env bash
# registry-probe.sh — misst laufend, ob dieser Host die Container-Registry erreicht.
#
# ## Warum es das gibt
#
# Am 2026-09-02 scheiterten vier Prod-Deploys daran, dass `prod` ghcr.io nur noch in
# 4 von 10 Versuchen erreichte, während github.com 10 von 10 schaffte und ICMP zum
# selben Rechner verlustfrei lief. Zwei Stunden später war der Zustand von selbst
# vorbei (40/40). Die Ursache ist damit nachträglich nicht mehr bestimmbar: der
# Schritt, der sie entschieden hätte — ein Paketmitschnitt WÄHREND eines Fehlschlags —
# war nicht mehr möglich, weil nichts mehr fehlschlug (platform#2685).
#
# Aufgefallen ist die Störung nur über die vier Deploy-Läufe. Kein Melder beobachtet
# diese Strecke: `grep ghcr tools/session_start_checks.sh` ist leer, und
# `erreichbarkeit_melder.py` fragt unsere eigenen Prod-Domains ab, keine Registry.
#
# Dieses Skript schließt die Lücke — nicht, indem es die Störung verhindert, sondern
# indem das NÄCHSTE Fenster Evidenz hinterlässt statt einer zweiten Untersuchung von
# vorn.
#
# ## Was gemessen wird
#
# Je Lauf N Verbindungsaufbauten gegen die Registry UND dieselbe Zahl gegen einen
# Kontrollarm (github.com, dieselbe Anbieterkette, benachbarte Adresse im selben /24).
# Der Kontrollarm ist nicht Beiwerk: ohne ihn ist "Registry schlecht erreichbar" nicht
# von "Leitung dieses Hosts schlecht" zu unterscheiden — und genau diese Unterscheidung
# war am 2026-09-02 der tragende Befund.
#
# ## Was im Fehlerfall passiert
#
# Unterschreitet die Registry-Quote die Schwelle, WÄHREND der Kontrollarm sauber ist,
# schneidet das Skript kurz mit: das ist der Zustand, den niemand nachstellen kann.
# Der Mitschnitt ist auf Dauer und Größe begrenzt und nur der Header-Anfang jedes
# Pakets — er soll zeigen, ob auf das ClientHello gar keine Antwort kommt (Verwerfen),
# ein RST (aktive Ablehnung) oder eine verspätete (Überlast). Drei Ursachen, drei
# verschiedene Bilder.
#
# Ist der Kontrollarm ebenfalls schlecht, wird NICHT mitgeschnitten: dann ist es die
# Leitung des Hosts, und dafür gibt es andere Melder.
#
# ## Aufruf
#   registry-probe.sh              # ein Lauf, hängt eine Zeile ans Protokoll
#   registry-probe.sh --dry-run    # misst, schreibt nichts, schneidet nichts mit
set -uo pipefail

ZIEL="${REGISTRY_PROBE_ZIEL:-https://ghcr.io/v2/}"
KONTROLLE="${REGISTRY_PROBE_KONTROLLE:-https://github.com/}"
N="${REGISTRY_PROBE_N:-5}"
SCHWELLE="${REGISTRY_PROBE_SCHWELLE:-4}"        # ok-Zahl, ab der es KEIN Befund ist
TIMEOUT="${REGISTRY_PROBE_TIMEOUT:-12}"
LOG_DIR="${REGISTRY_PROBE_LOG_DIR:-/var/log/registry-probe}"
LOG="$LOG_DIR/probe.log"
MITSCHNITT_DIR="$LOG_DIR/mitschnitte"
MITSCHNITT_SEK="${REGISTRY_PROBE_MITSCHNITT_SEK:-30}"
MITSCHNITT_MB="${REGISTRY_PROBE_MITSCHNITT_MB:-5}"
# Nicht bei jedem Fehlschlag neu mitschneiden — ein anhaltendes Fenster würde sonst
# die Platte füllen. Ein Mitschnitt je Abklingzeit reicht: er zeigt den Mechanismus,
# und der ändert sich innerhalb eines Fensters nicht.
MITSCHNITT_ABKLINGZEIT_MIN="${REGISTRY_PROBE_ABKLINGZEIT_MIN:-60}"
TROCKEN=0
[[ "${1:-}" == "--dry-run" ]] && TROCKEN=1

messen() { # messen <url> -> "ok anzahl"
  local url="$1" ok=0
  for _ in $(seq 1 "$N"); do
    curl -s -o /dev/null --max-time "$TIMEOUT" "$url" >/dev/null 2>&1 && ok=$((ok + 1))
  done
  printf '%s' "$ok"
}

ZIEL_HOST=$(sed -E 's#^https?://##; s#/.*##' <<< "$ZIEL")
ZIEL_IP=$(getent ahosts "$ZIEL_HOST" 2>/dev/null | awk '{print $1}' | sort -u | head -1)

ZIEL_OK=$(messen "$ZIEL")
KON_OK=$(messen "$KONTROLLE")

if [[ "$ZIEL_OK" -ge "$SCHWELLE" ]]; then
  BEFUND="ok"
elif [[ "$KON_OK" -lt "$SCHWELLE" ]]; then
  # Beide schlecht → Leitung des Hosts, nicht die Registry. Kein Mitschnitt.
  BEFUND="leitung"
else
  BEFUND="registry"
fi

ZEILE=$(printf '%s host=%s ziel=%s/%s kontrolle=%s/%s ip=%s befund=%s' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(hostname -s)" \
  "$ZIEL_OK" "$N" "$KON_OK" "$N" "${ZIEL_IP:-?}" "$BEFUND")

if [[ $TROCKEN -eq 1 ]]; then
  echo "$ZEILE"
  echo "(dry-run — nichts geschrieben, nichts mitgeschnitten)"
  exit 0
fi

mkdir -p "$LOG_DIR" "$MITSCHNITT_DIR" 2>/dev/null || true
echo "$ZEILE" >> "$LOG"

[[ "$BEFUND" == "registry" ]] || exit 0

# Abklingzeit: liegt der jüngste Mitschnitt noch keine N Minuten zurück, reicht er.
juengster=$(find "$MITSCHNITT_DIR" -name '*.pcap' -mmin "-$MITSCHNITT_ABKLINGZEIT_MIN" 2>/dev/null | head -1)
if [[ -n "$juengster" ]]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) mitschnitt uebersprungen (juengerer vorhanden: $(basename "$juengster"))" >> "$LOG"
  exit 0
fi

command -v tcpdump >/dev/null 2>&1 || {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) mitschnitt nicht moeglich — kein tcpdump" >> "$LOG"
  exit 0
}
[[ -n "$ZIEL_IP" ]] || {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) mitschnitt nicht moeglich — Ziel-IP unbekannt" >> "$LOG"
  exit 0
}

PCAP="$MITSCHNITT_DIR/$(date -u +%Y%m%dT%H%M%SZ)-$(hostname -s).pcap"
# -s 100: nur die Header. Der Inhalt ist TLS-verschlüsselt und für die Frage
# ("kommt eine Antwort?") ohnehin bedeutungslos — ihn nicht zu speichern ist die
# sparsamere UND die datensparsamere Wahl.
timeout $((MITSCHNITT_SEK + 5)) tcpdump -i any -n -s 100 -C "$MITSCHNITT_MB" -W 1 \
  -G "$MITSCHNITT_SEK" -W 1 -w "$PCAP" "host $ZIEL_IP and tcp port 443" >/dev/null 2>&1 &
TD=$!
# Währenddessen Verkehr erzeugen — ohne Verbindungsversuche schneidet man Stille mit.
for _ in $(seq 1 "$MITSCHNITT_SEK"); do
  curl -s -o /dev/null --max-time 3 "$ZIEL" >/dev/null 2>&1
done
wait $TD 2>/dev/null
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) mitschnitt $(basename "$PCAP") ($(du -h "$PCAP" 2>/dev/null | cut -f1))" >> "$LOG"

# Alte Mitschnitte und Protokollzeilen aufräumen — ein Melder, der die Platte füllt,
# erzeugt den nächsten Befund (Session-Start 0.7.18 misst die Vorlaufzeit).
find "$MITSCHNITT_DIR" -name '*.pcap' -mtime +14 -delete 2>/dev/null || true
if [[ -f "$LOG" ]] && [[ $(wc -l < "$LOG") -gt 20000 ]]; then
  tail -10000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
exit 0
