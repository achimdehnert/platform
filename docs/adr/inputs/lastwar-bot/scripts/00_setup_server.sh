#!/bin/bash
# =============================================================================
# Phase 0: Last War Bot Server Setup
# Ziel: Hetzner CX42, Ubuntu 22.04 LTS
# Aufruf: bash 00_setup_server.sh
# =============================================================================
set -euo pipefail

LOG="/var/log/lastwar-setup.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== Last War Bot Server Setup === $(date)"

# -----------------------------------------------------------------------------
# 1. KVM prüfen (KRITISCH — Emulator braucht Hardware-Virtualisierung)
# -----------------------------------------------------------------------------
echo "[1/7] Prüfe KVM-Support..."
apt-get install -y cpu-checker qemu-kvm libvirt-daemon-system
if ! kvm-ok; then
  echo "FEHLER: KVM nicht verfügbar. Emulator läuft sehr langsam ohne Hardware-Acceleration."
  echo "Hetzner CX-Instanzen unterstützen KVM — ggf. anderes Rechenzentrum wählen."
  exit 1
fi
echo "✓ KVM verfügbar"

# -----------------------------------------------------------------------------
# 2. System-Dependencies
# -----------------------------------------------------------------------------
echo "[2/7] Installiere System-Dependencies..."
apt-get update -qq
apt-get install -y \
  openjdk-17-jdk \
  wget unzip curl git \
  python3-pip python3-venv \
  libgl1-mesa-glx libglib2.0-0 \
  tesseract-ocr tesseract-ocr-deu \
  adb \
  screen \
  htop

# -----------------------------------------------------------------------------
# 3. pyenv + Python 3.12
# -----------------------------------------------------------------------------
echo "[3/7] Installiere pyenv + Python 3.12..."
if [ ! -d "$HOME/.pyenv" ]; then
  curl https://pyenv.run | bash
fi

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

pyenv install -s 3.12.9
pyenv global 3.12.9
echo "✓ Python $(python --version)"

# -----------------------------------------------------------------------------
# 4. Android SDK
# -----------------------------------------------------------------------------
echo "[4/7] Installiere Android SDK..."
ANDROID_SDK="$HOME/android-sdk"
mkdir -p "$ANDROID_SDK/cmdline-tools"

if [ ! -f "$ANDROID_SDK/cmdline-tools/latest/bin/sdkmanager" ]; then
  cd "$ANDROID_SDK/cmdline-tools"
  wget -q "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
  unzip -q commandlinetools-linux-*.zip -d latest
  rm commandlinetools-linux-*.zip
fi

cat >> "$HOME/.bashrc" << 'EOF'

# Android SDK
export ANDROID_SDK_ROOT=$HOME/android-sdk
export PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_SDK_ROOT/platform-tools
export PATH=$PATH:$ANDROID_SDK_ROOT/emulator
EOF

export ANDROID_SDK_ROOT="$ANDROID_SDK"
export PATH="$PATH:$ANDROID_SDK/cmdline-tools/latest/bin:$ANDROID_SDK/platform-tools:$ANDROID_SDK/emulator"

echo "[4/7] Installiere SDK-Packages..."
yes | sdkmanager --licenses > /dev/null 2>&1 || true
sdkmanager \
  "emulator" \
  "platform-tools" \
  "system-images;android-34;google_apis;x86_64"

echo "✓ Android SDK installiert"

# -----------------------------------------------------------------------------
# 5. 3 AVDs erstellen
# -----------------------------------------------------------------------------
echo "[5/7] Erstelle 3 AVDs..."
for i in 1 2 3; do
  AVD_NAME="lastwar-bot-${i}"
  if ! avdmanager list avd | grep -q "$AVD_NAME"; then
    echo "no" | avdmanager create avd \
      -n "$AVD_NAME" \
      -k "system-images;android-34;google_apis;x86_64" \
      --device "pixel_6" \
      --force
    echo "✓ AVD $AVD_NAME erstellt"
  else
    echo "✓ AVD $AVD_NAME bereits vorhanden"
  fi
done

# RAM pro Emulator auf 2048 MB konfigurieren
for i in 1 2 3; do
  AVD_CONFIG="$HOME/.android/avd/lastwar-bot-${i}.avd/config.ini"
  if [ -f "$AVD_CONFIG" ]; then
    sed -i 's/hw.ramSize=.*/hw.ramSize=2048/' "$AVD_CONFIG" 2>/dev/null || true
    echo "hw.ramSize=2048" >> "$AVD_CONFIG"
  fi
done

# -----------------------------------------------------------------------------
# 6. Python-Umgebung für Bot
# -----------------------------------------------------------------------------
echo "[6/7] Erstelle Python venv für Bot..."
mkdir -p "$HOME/lastwar-bot"
cd "$HOME/lastwar-bot"
python -m venv .venv
source .venv/bin/activate

pip install --quiet \
  uiautomator2 \
  adbutils \
  opencv-python-headless \
  pytesseract \
  Pillow \
  celery \
  redis \
  python-dotenv

echo "✓ Python-Dependencies installiert"

# -----------------------------------------------------------------------------
# 7. Systemd Service für Auto-Start
# -----------------------------------------------------------------------------
echo "[7/7] Erstelle Systemd-Service..."
cat > /etc/systemd/system/lastwar-emulators.service << EOF
[Unit]
Description=Last War Survival Android Emulators
After=network.target

[Service]
Type=forking
User=root
ExecStart=$HOME/lastwar-bot/scripts/start_emulators.sh
ExecStop=$HOME/lastwar-bot/scripts/stop_emulators.sh
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "✓ Systemd-Service registriert (noch nicht aktiviert)"

echo ""
echo "=== Setup abgeschlossen ==="
echo "Nächste Schritte:"
echo "  1. source ~/.bashrc"
echo "  2. bash scripts/start_emulators.sh"
echo "  3. Last War APK installieren: adb -s emulator-5554 install lastwar.apk"
echo "  4. Accounts manuell einrichten (einmalig)"
echo "  5. systemctl enable --now lastwar-emulators"
