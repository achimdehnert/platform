#!/bin/bash
# Klickdummy-Pull-Job — ADR-216 (Review-Pass nachgeschärft)
# Pullt alle in repos.yaml gelisteten Klickdummy-Repos und legt
# Symlinks in /srv/klickdummy/<owner>/<repo>/ zum sync_subdir des Clones.
#
# Aufruf: /opt/klickdummy/sync.sh
# Cron:   */15 * * * * (15-Min-Intervall, Pre-Pilot-Iteration läuft schneller)
# User:   klickdummy-sync (dediziert, NICHT root)
# SSH:    Deploy-Key (~/.ssh/klickdummy-deploy_ed25519), read-only pro Repo
#
# Datenpfade:
#   /var/lib/klickdummy-sync/<owner>/<repo>/         — Git-Clone (working tree)
#   /srv/klickdummy/<owner>/<repo>                   — Symlink → clone/sync_subdir
#   /srv/klickdummy/_index.json                      — Discovery-API-Endpoint
#   /srv/klickdummy/index.html                       — Landing-Page
#
# Symlink-Pattern statt rsync (Review-Pass 2): vermeidet doppelten Datenpfad
# und Drift-Risiko (Server-Stand kann nicht von Git divergieren).

set -euo pipefail

WORK="${KLICKDUMMY_WORK:-/var/lib/klickdummy-sync}"
TARGET="${KLICKDUMMY_TARGET:-/srv/klickdummy}"
REPOS_FILE="${KLICKDUMMY_REPOS:-/opt/klickdummy/repos.yaml}"
DEPLOY_KEY="${KLICKDUMMY_DEPLOY_KEY:-$HOME/.ssh/klickdummy-deploy_ed25519}"

# Sicherheitscheck: NICHT als root laufen
if [ "$(id -u)" = "0" ]; then
  echo "✗ sync.sh darf nicht als root laufen — verwende User 'klickdummy-sync'" >&2
  exit 1
fi

mkdir -p "$WORK" "$TARGET"

if ! command -v python3 &>/dev/null; then
  echo "✗ python3 nicht verfügbar — installiere python3-yaml" >&2
  exit 1
fi

ENTRIES=$(python3 -c "
import yaml
data = yaml.safe_load(open('$REPOS_FILE'))
for r in data.get('repos', []):
    print(f\"{r['owner']}|{r['name']}|{r['sync_subdir']}\")
")

echo "== Klickdummy-Sync $(date -Is) =="
while IFS='|' read -r owner name subdir; do
  [ -z "$owner" ] && continue
  repo="$owner/$name"
  clone_dir="$WORK/$owner/$name"

  if [ ! -d "$clone_dir/.git" ]; then
    echo "→ Clone $repo"
    mkdir -p "$WORK/$owner"
    GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes" \
      git clone --depth 1 "git@github.com:$repo.git" "$clone_dir"
  else
    echo "→ Pull  $repo"
    GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes" \
      git -C "$clone_dir" fetch --depth 1 origin main
    git -C "$clone_dir" reset --hard origin/main
  fi

  src="$clone_dir/$subdir"
  link="$TARGET/$owner/$name"
  if [ ! -d "$src" ]; then
    echo "  ⚠ Source-Subdir nicht gefunden: $src" >&2
    continue
  fi

  # Symlink statt rsync — kein doppelter Datenpfad, kein Drift-Risiko
  mkdir -p "$TARGET/$owner"
  ln -sfn "$src" "$link"
  echo "  ✓ $link → $src"
done <<< "$ENTRIES"

# Discovery-API-Endpoint (_index.json) + Landing-HTML
python3 /opt/klickdummy/generate_landing.py "$TARGET" "$REPOS_FILE" \
  --emit-json "$TARGET/_index.json" \
  --emit-html "$TARGET/index.html"

echo "✓ Discovery: $TARGET/_index.json"
echo "✓ Landing:   $TARGET/index.html"
echo "== Done $(date -Is) =="
