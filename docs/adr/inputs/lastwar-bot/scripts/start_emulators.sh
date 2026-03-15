#!/bin/bash
# =============================================================================
# start_emulators.sh — Alle 3 AVDs headless starten + warten bis bereit
# =============================================================================
set -euo pipefail

export ANDROID_SDK_ROOT="$HOME/android-sdk"
export PATH="$PATH:$ANDROID_SDK_ROOT/emulator:$ANDROID_SDK_ROOT/platform-tools"

# AVD → ADB-Port Mapping
declare -A AVD_PORTS=(
  [lastwar-bot-1]=5554
  [lastwar-bot-2]=5556
  [lastwar-bot-3]=5558
)

echo "$(date): Starte Last War Emulatoren..."

for AVD_NAME in "${!AVD_PORTS[@]}"; do
  PORT="${AVD_PORTS[$AVD_NAME]}"
  SERIAL="emulator-${PORT}"

  # Bereits laufend?
  if adb devices | grep -q "$SERIAL"; then
    echo "✓ $AVD_NAME (Port $PORT) läuft bereits"
    continue
  fi

  echo "  Starte $AVD_NAME auf Port $PORT..."
  nohup emulator \
    -avd "$AVD_NAME" \
    -port "$PORT" \
    -no-audio \
    -no-window \
    -no-snapshot \
    -no-boot-anim \
    -gpu swiftshader_indirect \
    -memory 2048 \
    > "/var/log/emulator-${AVD_NAME}.log" 2>&1 &

  echo "  PID: $!"
done

echo "Warte auf Boot aller Emulatoren..."

for AVD_NAME in "${!AVD_PORTS[@]}"; do
  PORT="${AVD_PORTS[$AVD_NAME]}"
  SERIAL="emulator-${PORT}"
  TIMEOUT=120
  ELAPSED=0

  until adb -s "$SERIAL" shell getprop sys.boot_completed 2>/dev/null | grep -q "1"; do
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    if [ $ELAPSED -ge $TIMEOUT ]; then
      echo "FEHLER: $AVD_NAME Timeout nach ${TIMEOUT}s"
      exit 1
    fi
  done

  echo "✓ $AVD_NAME bereit (${ELAPSED}s)"
done

echo "$(date): Alle 3 Emulatoren bereit."
adb devices
