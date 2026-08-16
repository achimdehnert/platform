#!/usr/bin/env bash
# tools/reconcile-app-setup.sh — App-ID und Private Key des Handover-Reconcilers
# hinterlegen (platform#2006, Schritt 5+6 aus docs/runbooks/RUNBOOK-reconcile-github-app.md).
#
# Warum es dieses Skript gibt und nicht zwei Kommandozeilen im Runbook:
#   Die Runbook-Fassung enthielt Platzhalter (`--body "<App ID>"`). Ein Platzhalter
#   ist beim Einfuegen nicht kopierbar — er scheitert entweder laut (gut) oder setzt
#   still den Literal-Text `<App ID>` als Variable (schlecht: die Token-Schritte im
#   Workflow laufen dann an, `create-github-app-token` scheitert je Org, und dank
#   `continue-on-error` bleibt der Lauf GRUEN. Ein Konfigurationsfehler saehe damit
#   exakt aus wie eine fehlende Installation.) Zwei echte Argumente koennen das nicht.
#
# Der Private Key wird NUR ueber stdin an `gh` gereicht: nie als Argument (waere in
# der Prozessliste sichtbar), nie in einer Variablen mit Echo, nie in der History.
#
# Usage:
#   tools/reconcile-app-setup.sh <APP_ID> <pfad/zur/private-key.pem> [--dry-run] [--shred]
#
#   --dry-run  nur pruefen und zeigen, was passieren wuerde (schreibt nichts)
#   --shred    die .pem nach erfolgreichem Setzen sicher loeschen (bewusst OPT-IN:
#              eine fremde Datei ungefragt zu vernichten ist keine gute Vorgabe)
set -euo pipefail

REPO="${RECONCILE_REPO:-achimdehnert/platform}"
DRY=0
SHRED=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --shred)   SHRED=1 ;;
    -h|--help) sed -n '1,30p' "$0"; exit 0 ;;
    -*) echo "Unbekanntes Argument: $a" >&2; exit 64 ;;
    *) ARGS+=("$a") ;;
  esac
done

if [[ ${#ARGS[@]} -ne 2 ]]; then
  echo "Aufruf: $0 <APP_ID> <pfad/zur/private-key.pem> [--dry-run] [--shred]" >&2
  exit 64
fi
APP_ID="${ARGS[0]}"
PEM="${ARGS[1]}"

# ── Pruefungen VOR jedem Schreibzugriff ─────────────────────────────────────
# Beide Fehler waeren sonst still: eine nicht-numerische App-ID und ein
# vertauschtes Argument (Pfad an Stelle 1) erzeugen einen Lauf, der gruen bleibt
# und trotzdem nichts kann.
if [[ ! "$APP_ID" =~ ^[0-9]+$ ]]; then
  echo "FEHLER: App-ID ist keine Zahl: '$APP_ID'" >&2
  echo "        Sie steht oben auf der App-Seite (github.com/settings/apps/<name>)." >&2
  exit 65
fi
if [[ ! -r "$PEM" ]]; then
  echo "FEHLER: Private Key nicht lesbar: '$PEM'" >&2
  exit 66
fi
if ! grep -q -- "-----BEGIN" "$PEM"; then
  echo "FEHLER: '$PEM' sieht nicht nach einem PEM-Schluessel aus (keine BEGIN-Zeile)." >&2
  echo "        Erwartet wird die von GitHub heruntergeladene .private-key.pem." >&2
  exit 66
fi

echo "Repo   : $REPO"
echo "App-ID : $APP_ID"
echo "Key    : $PEM ($(wc -l < "$PEM") Zeilen, Inhalt wird NICHT ausgegeben)"

if [[ $DRY -eq 1 ]]; then
  echo
  echo "DRY-RUN — es wurde nichts gesetzt. Ohne --dry-run wuerde passieren:"
  echo "  gh variable set RECONCILE_APP_ID --repo $REPO   (Wert: $APP_ID)"
  echo "  gh secret   set RECONCILE_APP_PRIVATE_KEY --repo $REPO  (< $PEM)"
  [[ $SHRED -eq 1 ]] && echo "  danach: $PEM sicher loeschen"
  exit 0
fi

gh variable set RECONCILE_APP_ID --repo "$REPO" --body "$APP_ID"
gh secret set RECONCILE_APP_PRIVATE_KEY --repo "$REPO" < "$PEM"

# Gegenprobe: gesetzt heisst nicht angekommen.
if ! gh variable list --repo "$REPO" 2>/dev/null | grep -q "RECONCILE_APP_ID"; then
  echo "FEHLER: RECONCILE_APP_ID nach dem Setzen nicht auffindbar." >&2
  exit 70
fi
if ! gh secret list --repo "$REPO" 2>/dev/null | grep -q "RECONCILE_APP_PRIVATE_KEY"; then
  echo "FEHLER: RECONCILE_APP_PRIVATE_KEY nach dem Setzen nicht auffindbar." >&2
  exit 70
fi
echo "✅ Variable und Secret gesetzt und gegengeprueft."

if [[ $SHRED -eq 1 ]]; then
  shred -u "$PEM" 2>/dev/null || rm -f "$PEM"
  echo "✅ $PEM geloescht — der Wert lebt ab jetzt nur im Secret."
else
  echo "ℹ  Die .pem liegt noch da. Loeschen mit: shred -u \"$PEM\""
fi

cat <<EOF

Naechster Schritt — Abnahme (die Abdeckungszeile ist das Kriterium, nicht der gruene Haken):

  gh workflow run handover-reconcile.yml -R $REPO

Danach die Job-Summary lesen. Erwartet:
  Token-Abdeckung: eigener Token fuer **achimdehnert, iilgmbh, meiki-lra, ttz-lif, bahn-sqf**
EOF
