#!/bin/bash
# register-runners.sh
# Registers one GitHub Actions self-hosted runner per repo.
# Usage: ./register-runners.sh <PAT>
# The PAT needs repo-level access (no admin:org needed).
# Each runner runs as the github-runner user.

set -euo pipefail

PAT="${1:-}"
if [ -z "$PAT" ]; then
  echo "Usage: $0 <GITHUB_PAT>"
  exit 1
fi

RUNNER_BASE="/home/github-runner"
RUNNER_SRC="$RUNNER_BASE/actions-runner"
LABELS="self-hosted,hetzner,dev"

REPOS=(
  "achimdehnert/platform"
  "achimdehnert/risk-hub"
  "achimdehnert/bfagent"
  "achimdehnert/travel-beat"
  "achimdehnert/weltenhub"
  "achimdehnert/pptx-hub"
  "achimdehnert/trading-hub"
)

for REPO in "${REPOS[@]}"; do
  REPO_SLUG="${REPO//\//-}"
  RUNNER_DIR="$RUNNER_BASE/runner-$REPO_SLUG"

  echo ""
  echo "=== Setting up runner for $REPO ==="

  # Skip if already registered and running
  SERVICE_NAME="actions.runner.${REPO//\//.}.dev-hetzner"
  if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "  Runner already active: $SERVICE_NAME — skipping"
    continue
  fi

  # Get registration token
  TOKEN=$(curl -s -X POST \
    -H "Authorization: Bearer $PAT" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO/actions/runners/registration-token" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('token','ERROR'))")

  if [ "$TOKEN" = "ERROR" ]; then
    echo "  ERROR: Could not get token for $REPO — skipping"
    continue
  fi

  # Create runner directory
  mkdir -p "$RUNNER_DIR"
  cp -r "$RUNNER_SRC/bin" "$RUNNER_DIR/"
  cp "$RUNNER_SRC/config.sh" "$RUNNER_DIR/"
  cp "$RUNNER_SRC/env.sh" "$RUNNER_DIR/"
  cp "$RUNNER_SRC/run-helper.sh.template" "$RUNNER_DIR/" 2>/dev/null || true
  chown -R github-runner:github-runner "$RUNNER_DIR"

  # Configure runner
  sudo -u github-runner bash -c "
    cd $RUNNER_DIR
    ./config.sh \
      --url https://github.com/$REPO \
      --token $TOKEN \
      --name dev-hetzner \
      --labels '$LABELS' \
      --work '_work' \
      --unattended 2>&1 | tail -5
  "

  # Install and start as systemd service
  pushd "$RUNNER_DIR" > /dev/null
  sudo -u github-runner bash -c "cd $RUNNER_DIR && ./config.sh --help" > /dev/null 2>&1 || true

  # Create systemd service manually
  cat > "/etc/systemd/system/actions.runner.${REPO_SLUG}.service" << UNIT
[Unit]
Description=GitHub Actions Runner ($REPO)
After=network.target

[Service]
Type=simple
User=github-runner
WorkingDirectory=$RUNNER_DIR
ExecStart=$RUNNER_DIR/bin/Runner.Listener run --startuptype service
Restart=always
RestartSec=10
KillMode=process
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
UNIT

  systemctl daemon-reload
  systemctl enable "actions.runner.${REPO_SLUG}.service"
  systemctl start "actions.runner.${REPO_SLUG}.service"
  sleep 3
  systemctl is-active "actions.runner.${REPO_SLUG}.service" && echo "  Started OK" || echo "  FAILED to start"
  popd > /dev/null
done

echo ""
echo "=== Runner Status ==="
systemctl list-units "actions.runner.*" --no-legend | awk '{print $1, $4}'
