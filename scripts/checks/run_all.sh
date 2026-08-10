#!/bin/bash
# ADR-210 — Alle Staging-Strategie-Checks (R1-R8) in einem Lauf.
#
# WARUM DIESES SKRIPT DER AUFRUFER IST (2026-08-02):
# `staging-registry-checks.yml` fuhr die acht Checks als acht Jobs, jeden mit
# `continue-on-error: true`. Ergebnis am 2026-08-01: **7 von 8 Jobs failure,
# Gesamt-Conclusion `success`** — taeglich, seit mindestens fuenf Laeufen. Ein
# gruener Lauf sagte nichts ueber die Checks aus. Zugleich hatte dieses Skript,
# das die Aggregation korrekt beherrscht, ueberhaupt keinen Aufrufer.
# Die Architektur war invertiert; der Workflow ruft jetzt hier hinein.
#
# BASELINE STATT DAUERROT (repo-health-rule-discipline):
# Die sieben Befunde sind Infrastruktur-Drift ueber mehrere Repos — nicht in
# einem PR zu beheben. Ein hartes Gate waere sofort dauerrot und damit
# Alarm-Muedigkeit. Mit `--baseline` gilt: bekannte Fehlschlaege sind geduldet,
# ein NEUER Fehlschlag ist eine Regression und faellt hart.
#
#   0  alle gruen ODER Fehlschlaege sind Teilmenge der Baseline
#   1  REGRESSION — mindestens ein Check faellt, der in der Baseline gruen war
#   2  Bedienfehler (Baseline-Datei fehlt)
#
# Ohne `--baseline` bleibt das alte Verhalten: jeder Fehlschlag => exit 1.
set -uo pipefail

# Argumente VOR dem `cd` auswerten: der Aufrufer uebergibt den Baseline-Pfad
# relativ zu SEINEM Arbeitsverzeichnis. Der Workflow ruft aus der Repo-Wurzel
# `--baseline scripts/checks/staging-baseline.txt` — nach dem `cd` unten waere
# das `scripts/checks/scripts/checks/...` und damit nie auffindbar. Genau daran
# lief das Gate vom 2026-08-02 bis 2026-08-10 in neun Laeufen mit exit 2
# ("BEDIENFEHLER") ins Leere: die acht Checks liefen kein einziges Mal.
BASELINE=""
[ "${1:-}" = "--baseline" ] && { BASELINE="${2:-}"; }
case "$BASELINE" in
  ""|/*) ;;
  *) BASELINE="$PWD/$BASELINE" ;;
esac

cd "$(dirname "$0")"

[ -n "$BASELINE" ] && [ ! -f "$BASELINE" ] && {
  echo "BEDIENFEHLER: Baseline-Datei nicht gefunden: $BASELINE" >&2
  exit 2
}

CHECKS=(
  staging_dns_schema.sh
  staging_host_locality.sh
  staging_naming.sh
  staging_port_range.sh
  staging_tunnel_ingress.sh
  staging_oidc_redirects.sh
  staging_generated_drift.sh
  staging_devdesktop_clean.sh
)

gefallen=()
for c in "${CHECKS[@]}"; do
  echo "=== $c ==="
  bash "$c" || gefallen+=("$c")
  echo
done

echo "==================================="
echo "Ergebnis: $((${#CHECKS[@]} - ${#gefallen[@]})) von ${#CHECKS[@]} gruen"
[ ${#gefallen[@]} -gt 0 ] && printf '  rot: %s\n' "${gefallen[@]}"

if [ -z "$BASELINE" ]; then
  [ ${#gefallen[@]} -eq 0 ] && { echo "ALL CHECKS PASSED"; exit 0; }
  echo "${#gefallen[@]} check(s) FAILED"
  exit 1
fi

# Baseline-Modus: nur NEUE Fehlschlaege sind ein Befund.
neu=()
for c in "${gefallen[@]:-}"; do
  [ -z "$c" ] && continue
  grep -qxF "$c" "$BASELINE" || neu+=("$c")
done
# Und melden, was sich gebessert hat — sonst veraltet die Baseline stillschweigend.
behoben=()
while IFS= read -r b; do
  [ -z "$b" ] || [ "${b:0:1}" = "#" ] && continue
  printf '%s\n' "${gefallen[@]:-}" | grep -qxF "$b" || behoben+=("$b")
done < "$BASELINE"

echo "-----------------------------------"
echo "Baseline: $BASELINE"
[ ${#behoben[@]} -gt 0 ] && {
  printf '  ✓ behoben (Baseline kuerzen): %s\n' "${behoben[@]}"
}
if [ ${#neu[@]} -gt 0 ]; then
  printf '  ⛔ REGRESSION (war gruen, faellt jetzt): %s\n' "${neu[@]}"
  echo "REGRESSION — ${#neu[@]} neu gefallene(r) Check(s)"
  exit 1
fi
echo "keine Regression gegen die Baseline"
exit 0
