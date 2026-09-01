#!/usr/bin/env bash
# Python-Versionen in den gemeinsamen Tool-Cache eines CI-Knotens legen.
#
# WARUM (gemessen 2026-09-01 auf netcup, platform#2586):
#   `actions/setup-python` findet fuer Debian 13 KEINE herunterladbare Version —
#   das Manifest von actions/python-versions kennt keine Debian-Eintraege. Was
#   nicht im Cache liegt, laesst den Job scheitern:
#     "The version '3.11' with architecture 'x64' was not found for Debian 13."
#   Der Cache eines solchen Knotens IST damit sein Angebot. Wer ein Repo dorthin
#   umzieht, ohne die angefragte Version vorzuhalten, verlegt kein Problem —
#   er erzeugt eins.
#
#   Die Flotte fragte am 2026-09-01: 189x 3.12, 13x 3.11, 2x 3.10.
#
# ZWEITE FALLE, die eine Sichtpruefung durchgehen laesst:
#   Die offiziellen Tarballs liefern `pip3` und `python3`, aber NICHT `pip` und
#   `python`. setup-python legt bin/ auf den PATH; `pip install` findet dort
#   nichts und faellt auf /usr/bin/pip durch — auf Debian 13 endet das in
#   PEP 668 ("externally-managed-environment") gegen die System-Python.
#   Darum werden die beiden Namen unten ergaenzt und am Ende AUSGEFUEHRT.
#
# Quelle sind die offiziellen actions/python-versions-Builds fuer Ubuntu 22.04.
# Dass sie auf Debian 13 laufen, wird nicht angenommen, sondern am Schluss durch
# einen Versionsaufruf belegt.
#
# Usage:  toolcache-bestuecken.sh [3.11 3.10 ...]      (Vorgabe: 3.12 3.11 3.10)
set -u

CACHE=/opt/hostedtoolcache/Python
BESITZER=${TOOLCACHE_BESITZER:-github-ci}
VERSIONEN=("$@")
[ ${#VERSIONEN[@]} -gt 0 ] || VERSIONEN=(3.12 3.11 3.10)

mkdir -p "$CACHE"

hole() {
  local MINOR="$1" VOLL URL T
  read -r VOLL URL <<<"$(python3 - "$MINOR" <<'PY'
import json, sys, urllib.request

minor = sys.argv[1]
manifest = json.load(urllib.request.urlopen(
    "https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json"))
for eintrag in manifest:
    if not eintrag["version"].startswith(minor + ".") or not eintrag.get("stable", True):
        continue
    for datei in eintrag["files"]:
        if (datei["platform"], datei["arch"], datei.get("platform_version")) == ("linux", "x64", "22.04"):
            print(eintrag["version"], datei["download_url"])
            raise SystemExit
PY
)"
  if [ -z "${VOLL:-}" ]; then
    echo "  $MINOR: keine passende Datei im Manifest"
    return 1
  fi
  if [ -d "$CACHE/$VOLL/x64" ]; then
    echo "  $MINOR: $VOLL liegt schon"
    return 0
  fi

  echo "  $MINOR -> $VOLL"
  T=$(mktemp -d)
  curl -fsSL "$URL" -o "$T/py.tar.gz"
  mkdir -p "$T/aus" && tar -C "$T/aus" -xzf "$T/py.tar.gz"
  [ -f "$T/aus/setup.sh" ] && (cd "$T/aus" && bash setup.sh) >/dev/null 2>&1
  mkdir -p "$CACHE/$VOLL"
  rm -rf "$CACHE/$VOLL/x64"
  mv "$T/aus" "$CACHE/$VOLL/x64"
  # Ohne die .complete-Marke ignoriert setup-python den Eintrag.
  touch "$CACHE/$VOLL/x64.complete"
  # Die fehlenden Namen (siehe Kopf) — sonst greift /usr/bin/pip.
  ln -sfn "python$MINOR" "$CACHE/$VOLL/x64/bin/python"
  ln -sfn "pip$MINOR"    "$CACHE/$VOLL/x64/bin/pip"
  rm -rf "$T"
}

for M in "${VERSIONEN[@]}"; do hole "$M" || true; done

chown -R "$BESITZER:$BESITZER" /opt/hostedtoolcache
chmod -R g+rX /opt/hostedtoolcache

echo "== Gegenprobe: laeuft jede Version, oder liegt nur ein Ordner da?"
fehler=0
for D in "$CACHE"/*/; do
  V=$(basename "$D")
  PY="$D/x64/bin/python"
  PIP="$D/x64/bin/pip"
  if [ -x "$PY" ] && [ -x "$PIP" ]; then
    echo "  ✅ $V  python=$("$PY" -V 2>&1 | cut -d' ' -f2)  pip=$("$PIP" -V 2>&1 | cut -d' ' -f2)  .complete=$([ -f "$D/x64.complete" ] && echo ja || echo NEIN)"
    [ -f "$D/x64.complete" ] || fehler=1
  else
    echo "  ❌ $V  python oder pip fehlt — setup-python wuerde hier auf die System-Python durchfallen"
    fehler=1
  fi
done
echo "  Cache-Groesse: $(du -sh /opt/hostedtoolcache | cut -f1)"
exit "$fehler"
