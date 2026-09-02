#!/usr/bin/env bash
# tests/test_deploy_ghcr_isolation.sh — Vertragstest für die GHCR-Credential-Isolation
# in scripts/deploy.sh (platform#1078 Befund 4).
#
# Warum als Test: der Block läuft bei JEDEM Deploy JEDES Hubs, und sein Bruch ist
# unsichtbar. Ein Deploy, der wieder in die geteilte ~/.docker/config.json schreibt,
# sieht im Log exakt aus wie ein isolierter — der Schaden zeigt sich erst Tage später
# an einem FREMDEN Pull auf demselben Host (so geschehen in platform#1845). Genau die
# Unsichtbarkeit, gegen die schon test_deploy_migrate_gate.sh existiert.
#
# Geprüfte Zusagen:
#   1. Mit GHCR_TOKEN            → docker login läuft mit isoliertem DOCKER_CONFIG
#   2. Die geteilte Config       → bleibt unangetastet (kein Byte geschrieben)
#   3. Nach Skript-Ende          → das temporäre Verzeichnis ist weg
#   4. Ohne Token/Host-Datei     → kein login, kein DOCKER_CONFIG, kein Temp-Verzeichnis
#
# Der Block wird 1:1 aus scripts/deploy.sh extrahiert (keine Nachbildung, die
# auseinanderlaufen könnte) und gegen einen `docker`-Stub gefahren — weder Docker
# noch Netz nötig.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/scripts/deploy.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

BLOCK="$TMP/block.sh"
# Die Anmeldung läuft seit 2026-09-02 über `_mit_wiederholung` (platform#2685) —
# ein transienter Registry-Aussetzer soll den Deploy nicht mehr kosten. Der Helfer
# steht im Skript VOR diesem Block und wäre isoliert nicht definiert; ohne ihn
# liefe der Login hier ins Leere und der Test wäre grün, weil gar nichts passiert.
# Deshalb wird er mit extrahiert — nicht nachgebaut.
sed -n '/^: "\${DEPLOY_REGISTRY_RETRIES/,/^}$/p' "$SRC" > "$BLOCK"
if ! grep -q '_mit_wiederholung()' "$BLOCK"; then
  echo "FAIL: Wiederholungs-Helfer nicht aus $SRC extrahierbar — Marker geändert?" >&2
  exit 1
fi
sed -n '/^# CREDENTIAL-ISOLATION/,/^fi$/p' "$SRC" >> "$BLOCK"

if [[ ! -s "$BLOCK" ]]; then
  echo "FAIL: Isolations-Block nicht aus $SRC extrahierbar — Marker geändert?" >&2
  exit 1
fi

# Gegenprobe gegen einen stillen Rückbau: der Block MUSS DOCKER_CONFIG setzen.
# Ohne diese Zeile wäre der Test grün, auch wenn jemand die Isolation entfernt
# und nur den Kommentar stehen lässt.
if ! grep -q 'export DOCKER_CONFIG=' "$BLOCK"; then
  echo "FAIL: Block setzt kein DOCKER_CONFIG — Isolation entfernt?" >&2
  exit 1
fi

FAILED=0
pruefe() {
  local name="$1" bedingung="$2"
  if eval "$bedingung"; then
    echo "  ✓ $name"
  else
    echo "  ✗ $name  (Bedingung: $bedingung)" >&2
    FAILED=1
  fi
}

# Harness: docker-Stub protokolliert, WAS er sah — insbesondere DOCKER_CONFIG.
lauf() {
  local ghcr_token="$1"
  rm -rf "$TMP/run"; mkdir -p "$TMP/run/bin" "$TMP/run/home/.docker"
  # Die "geteilte" Config mit bekanntem Inhalt: verändert der Deploy sie, fällt es auf.
  echo '{"auths":{}}' > "$TMP/run/home/.docker/config.json"

  cat > "$TMP/run/bin/docker" <<'EOF'
#!/usr/bin/env bash
echo "DOCKER_CONFIG=${DOCKER_CONFIG:-<unset>}" >> "$STUBLOG"
echo "args=$*" >> "$STUBLOG"
cat > /dev/null   # stdin (--password-stdin) verwerfen, nie protokollieren
exit 0
EOF
  chmod +x "$TMP/run/bin/docker"

  cat > "$TMP/run/script.sh" <<EOF
set -uo pipefail
export PATH="$TMP/run/bin:\$PATH"
export HOME="$TMP/run/home"
export STUBLOG="$TMP/run/stub.log"
unset DOCKER_CONFIG
$( [[ -n "$ghcr_token" ]] && echo "export GHCR_TOKEN='$ghcr_token'" )
$(cat "$BLOCK")
# Das Temp-Verzeichnis für die Nachprüfung nach außen reichen.
echo "\${_GHCR_CONFIG_DIR:-<leer>}" > "$TMP/run/tmpdir.txt"
EOF
  ( bash "$TMP/run/script.sh" ) >/dev/null 2>&1
}

echo "Vertragstest GHCR-Credential-Isolation ($(wc -l < "$BLOCK") Zeilen aus scripts/deploy.sh)"

# --- Fall 1: mit Token ------------------------------------------------------
lauf "geheim-nur-im-test"
STUB="$TMP/run/stub.log"
TMPDIR_USED="$(cat "$TMP/run/tmpdir.txt" 2>/dev/null || echo '<leer>')"

pruefe "docker login wurde aufgerufen" \
  'grep -q "args=login ghcr.io" "$STUB"'
pruefe "login sah ein isoliertes DOCKER_CONFIG" \
  '! grep -q "DOCKER_CONFIG=<unset>" "$STUB"'
pruefe "DOCKER_CONFIG zeigte NICHT auf die geteilte Config" \
  '! grep -q "DOCKER_CONFIG=$TMP/run/home/.docker" "$STUB"'
pruefe "geteilte ~/.docker/config.json unverändert" \
  '[[ "$(cat "$TMP/run/home/.docker/config.json")" == "{\"auths\":{}}" ]]'
pruefe "temporäres Verzeichnis nach Skript-Ende entfernt" \
  '[[ "$TMPDIR_USED" != "<leer>" && ! -d "$TMPDIR_USED" ]]'
pruefe "Token steht nicht im Stub-Protokoll" \
  '! grep -q "geheim-nur-im-test" "$STUB"'

# --- Fall 2: ohne Token und ohne Host-Datei ---------------------------------
# (die Host-Datei /opt/scripts/.ghcr_token existiert auf dem Runner nicht)
if [[ ! -f /opt/scripts/.ghcr_token ]]; then
  lauf ""
  pruefe "ohne Token: kein docker-Aufruf" \
    '[[ ! -s "$TMP/run/stub.log" ]]'
  pruefe "ohne Token: kein Temp-Verzeichnis angelegt" \
    '[[ "$(cat "$TMP/run/tmpdir.txt")" == "<leer>" ]]'
else
  echo "  ⚠ Fall 2 übersprungen — /opt/scripts/.ghcr_token existiert auf diesem Host"
fi

if [[ "$FAILED" -eq 0 ]]; then
  echo "RESULT: OK — Credential-Isolation hält ihre Zusagen"
  exit 0
fi
echo "RESULT: FAIL" >&2
exit 1
