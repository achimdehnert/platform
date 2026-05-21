#!/bin/bash
# Klickdummy-Pull-Job — ADR-216
# Pullt alle in repos.yaml gelisteten Klickdummy-Repos und spiegelt
# den jeweiligen sync_subdir in /srv/klickdummy/<owner>/<repo>/.
#
# Aufruf: /opt/klickdummy/sync.sh
# Cron:   stündlich (oder nach Bedarf)
# SSH:    Deploy-Key am Server (~/.ssh/klickdummy-deploy_ed25519), read-only

set -euo pipefail

WORK="${KLICKDUMMY_WORK:-/var/lib/klickdummy-sync}"
TARGET="${KLICKDUMMY_TARGET:-/srv/klickdummy}"
REPOS_FILE="${KLICKDUMMY_REPOS:-/opt/klickdummy/repos.yaml}"
DEPLOY_KEY="${KLICKDUMMY_DEPLOY_KEY:-$HOME/.ssh/klickdummy-deploy_ed25519}"

mkdir -p "$WORK" "$TARGET"

# Parse repos.yaml (minimal-YAML — pyyaml falls verfügbar, sonst grep)
if command -v python3 &>/dev/null; then
  ENTRIES=$(python3 -c "
import yaml
data = yaml.safe_load(open('$REPOS_FILE'))
for r in data.get('repos', []):
    print(f\"{r['owner']}|{r['name']}|{r['sync_subdir']}\")
")
else
  echo "✗ python3 nicht verfügbar — installiere python3-yaml" >&2
  exit 1
fi

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
  dst="$TARGET/$owner/$name"
  if [ ! -d "$src" ]; then
    echo "  ⚠ Source-Subdir nicht gefunden: $src" >&2
    continue
  fi
  mkdir -p "$dst"
  rsync -a --delete "$src/" "$dst/"
  echo "  ✓ $dst (von $src)"
done <<< "$ENTRIES"

# Landing-Page generieren
python3 /opt/klickdummy/generate_landing.py "$TARGET" "$REPOS_FILE" > "$TARGET/index.html"
echo "✓ Landing: $TARGET/index.html"

echo "== Done $(date -Is) =="
