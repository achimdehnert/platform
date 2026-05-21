#!/bin/bash
# Klickdummy-Sync (ADR-216 Klausel-2-Patch mit per-Repo-Deploy-Keys)
set -euo pipefail

WORK="${KLICKDUMMY_WORK:-/var/lib/klickdummy-sync}"
TARGET="${KLICKDUMMY_TARGET:-/srv/klickdummy}"
REPOS_FILE="${KLICKDUMMY_REPOS:-/opt/klickdummy/repos.yaml}"

if [ "$(id -u)" = "0" ]; then
  echo "✗ sync.sh nicht als root — User klickdummy-sync"; exit 1
fi

mkdir -p "$WORK" "$TARGET"

# Parse repos.yaml: owner|name|host_alias|sync_subdir|layout
ENTRIES=$(python3 -c "
import yaml
data = yaml.safe_load(open('$REPOS_FILE'))
for r in data.get('repos', []):
    print(f\"{r['owner']}|{r['name']}|{r['host_alias']}|{r['sync_subdir']}|{r.get('layout','per-subdir')}\")
")

echo "== Klickdummy-Sync $(date -Is) =="
while IFS='|' read -r owner name host_alias subdir layout; do
  [ -z "$owner" ] && continue
  repo="$owner/$name"
  clone_dir="$WORK/$owner/$name"

  if [ ! -d "$clone_dir/.git" ]; then
    echo "→ Clone $repo via $host_alias"
    mkdir -p "$WORK/$owner"
    git clone --depth 1 "git@${host_alias}:${repo}.git" "$clone_dir"
  else
    echo "→ Pull  $repo via $host_alias"
    git -C "$clone_dir" remote set-url origin "git@${host_alias}:${repo}.git"
    git -C "$clone_dir" fetch --depth 1 origin main
    git -C "$clone_dir" reset --hard origin/main
  fi

  src="$clone_dir/$subdir"
  if [ ! -d "$src" ]; then
    echo "  ⚠ Source-Subdir nicht gefunden: $src"; continue
  fi

  mkdir -p "$TARGET/$owner"

  if [ "$layout" = "flat-html" ]; then
    # risk-hub-Pattern: *.html direkt in subdir → pro Datei ein Pseudo-Klickdummy
    flat_dst="$TARGET/$owner/$name"
    rm -rf "$flat_dst" && mkdir -p "$flat_dst"
    for html in "$src"/*.html; do
      [ -f "$html" ] || continue
      name_no_ext=$(basename "$html" .html)
      # Skip _TEMPLATE und _-Prefixes
      [[ "$name_no_ext" == _* ]] && continue
      mkdir -p "$flat_dst/$name_no_ext"
      cp "$html" "$flat_dst/$name_no_ext/shell.html"
    done
    echo "  ✓ $flat_dst (flat-html, $(ls "$flat_dst" | wc -l) Klickdummies)"
  else
    # per-subdir: Symlink direkt auf working tree
    link="$TARGET/$owner/$name"
    ln -sfn "$src" "$link"
    echo "  ✓ $link → $src (per-subdir)"
  fi
done <<< "$ENTRIES"

# Discovery + Landing generieren
# o+rx für nginx-Container-Read (klickdummy-sync-Dir hat 750 default)
find "$WORK" -type d -exec chmod o+rx {} + 2>/dev/null || true
find "$WORK" -type f -exec chmod o+r {} + 2>/dev/null || true

python3 /opt/klickdummy/generate_landing.py "$TARGET" "$REPOS_FILE" \
  --emit-json "$TARGET/_index.json" \
  --emit-html "$TARGET/index.html" 2>&1

echo "✓ Discovery + Landing"
echo "== Done $(date -Is) =="
