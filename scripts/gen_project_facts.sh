#!/bin/bash
# =============================================================================
# gen_project_facts.sh — MASTER REPO IDENTIFIER & project-facts.md Generator
#
# Usage:
#   bash gen_project_facts.sh              # all repos
#   bash gen_project_facts.sh risk-hub     # single repo
#   bash gen_project_facts.sh --force      # overwrite existing
#
# Source of truth: repo-registry.yaml (same directory)
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGISTRY="$SCRIPT_DIR/repo-registry.yaml"
GITHUB=/home/devuser/github
WORKFLOWS_SRC=$GITHUB/platform/.windsurf/workflows
FORCE=false
TARGET_REPO=""

for arg in "$@"; do
  [ "$arg" = "--force" ] && FORCE=true || TARGET_REPO="$arg"
done

# ── YAML parser (pure bash, no deps) ─────────────────────────────────────────
registry_get() {
  local repo=$1 key=$2
  # Extract value from repos.<repo>.<key>: <value>
  awk "/^  ${repo}:/,/^  [a-z]/" "$REGISTRY" 2>/dev/null \
    | grep "^    ${key}:" | head -1 | sed "s/.*${key}: *//" | tr -d "'\""
}

registry_repos() {
  grep "^  [a-zA-Z0-9_-]*:$" "$REGISTRY" | sed 's/[: ]//g'
}

# ── Auto-detect from docker-compose ──────────────────────────────────────────
detect_port() {
  local repo_path=$1
  { grep -hE '"127.0.0.1:[0-9]+:' "$repo_path"/docker-compose*.yml 2>/dev/null || true; } \
    | grep -oE ':[0-9]{4,5}:' | head -1 | tr -d ':' || true
}

detect_db() {
  local repo_path=$1
  local v
  v=$({ grep -h "POSTGRES_DB:" "$repo_path"/docker-compose*.yml 2>/dev/null || true; } \
    | grep -oE ":-[a-zA-Z_]+" | head -1 | tr -d ':-' || true)
  if [ -z "$v" ]; then
    v=$({ grep -h "POSTGRES_DB:" "$repo_path"/docker-compose*.yml 2>/dev/null || true; } \
      | awk '{print $2}' | grep -v '\$' | head -1 || true)
  fi
  echo "$v"
}

detect_health() {
  local repo_path=$1
  local v
  v=$({ grep -hE "livez|/health|/readyz" "$repo_path"/docker-compose*.yml 2>/dev/null || true; } \
    | grep -oE "/(livez|health|readyz)/" | head -1 || true)
  echo "${v:-/livez/}"
}

detect_prod_url() {
  local repo_path=$1
  { grep -hE "ALLOWED_HOSTS|DJANGO_ALLOWED_HOSTS|CSRF_TRUSTED" \
    "$repo_path"/docker-compose*.yml "$repo_path"/.env.example 2>/dev/null || true; } \
    | grep -oE "[a-z0-9.-]+\.(de|com|pet|io|net)" \
    | grep -v "localhost\|127.0.0.1" | head -1 || true
}

detect_container_prefix() {
  local repo_path=$1
  { grep -h "container_name:" "$repo_path"/docker-compose*.yml 2>/dev/null || true; } \
    | awk '{print $2}' | head -1 \
    | sed 's/_web$//' | sed 's/_db$//' | sed 's/_worker$//' || true
}

detect_pypi_name() {
  local repo_path=$1
  { grep -E '^name' "$repo_path/pyproject.toml" 2>/dev/null || true; } \
    | head -1 | sed 's/.*= *//' | tr -d '"' || true
}

# ── Generate project-facts.md ────────────────────────────────────────────────
gen_facts() {
  local repo=$1
  local repo_path="$GITHUB/$repo"
  local facts_file="$repo_path/.windsurf/rules/project-facts.md"

  [ ! -d "$repo_path" ] && echo "❌ NOT FOUND: $repo" && return 1

  mkdir -p "$(dirname "$facts_file")"
  mkdir -p "$repo_path/.windsurf/workflows"

  # Copy workflows
  for wf in run-local run-staging run-prod; do
    src="$WORKFLOWS_SRC/${wf}.md"
    dest="$repo_path/.windsurf/workflows/${wf}.md"
    [ -f "$src" ] && [ "$repo_path" != "$GITHUB/platform" ] && cp "$src" "$dest" 2>/dev/null || true
  done

  # Skip if exists and not forced
  if [ -f "$facts_file" ] && [ "$FORCE" = false ]; then
    echo "SKIP (exists, use --force to overwrite): $repo"
    return 0
  fi

  # Read from registry (takes precedence)
  local type;    type=$(registry_get "$repo" "type")
  local prod_url; prod_url=$(registry_get "$repo" "prod_url")
  local staging_url; staging_url=$(registry_get "$repo" "staging_url")
  local port;    port=$(registry_get "$repo" "port")
  local db;      db=$(registry_get "$repo" "db")
  local health;  health=$(registry_get "$repo" "health")
  local pypi;    pypi=$(registry_get "$repo" "pypi")
  local note;    note=$(registry_get "$repo" "note")

  # Auto-detect fallbacks
  [ -z "$port" ]     && port=$(detect_port "$repo_path")
  [ -z "$port" ]     && port="8000"
  [ -z "$db" ]       && db=$(detect_db "$repo_path")
  [ -z "$db" ]       && db="${repo//-/_}"
  [ -z "$health" ]   && health=$(detect_health "$repo_path")
  [ -z "$prod_url" ] && prod_url=$(detect_prod_url "$repo_path")
  [ -z "$prod_url" ] && prod_url="${repo}.iil.pet"
  [ -z "$staging_url" ] && staging_url="staging.${prod_url}"
  [ -z "$pypi" ]     && pypi=$(detect_pypi_name "$repo_path")
  [ -z "$type" ]     && type="unknown"

  local prefix; prefix=$(detect_container_prefix "$repo_path")
  [ -z "$prefix" ] && prefix="${repo//-/_}"

  local has_compose; has_compose=$(find "$repo_path" -maxdepth 1 -name "docker-compose*.yml" 2>/dev/null | wc -l)
  local compose_local; compose_local="docker-compose.yml"
  [ -f "$repo_path/docker-compose.local.yml" ] && compose_local="docker-compose.local.yml"
  local compose_staging; compose_staging="docker-compose.staging.yml"
  local compose_prod; compose_prod="docker-compose.prod.yml"
  [ -f "$repo_path/docker-compose.prod.yml" ] || compose_prod="docker-compose.yml"

  # Write project-facts.md
  {
    echo "---"
    echo "trigger: always_on"
    echo "---"
    echo ""
    echo "# Project Facts: $repo"
    [ -n "$note" ] && echo "" && echo "> $note"
    echo ""
    echo "## Meta"
    echo ""
    echo "- **Type**: \`$type\`"
    echo "- **GitHub**: \`https://github.com/achimdehnert/$repo\`"
    echo "- **Branch**: \`main\` — push: \`git push\` (SSH-Key konfiguriert)"

    if [ -n "$pypi" ]; then
      echo "- **PyPI**: \`$pypi\`"
      echo "- **Venv**: \`.venv/\` — test: \`.venv/bin/python -m pytest\`"
    fi

    if [ "$has_compose" -gt 0 ]; then
      echo ""
      echo "## Environments"
      echo ""
      echo "| Env | Compose File | Host Port | Health URL | Public URL |"
      echo "|-----|-------------|-----------|------------|------------|"
      echo "| local | \`$compose_local\` | \`$port\` | \`http://localhost:$port$health\` | http://localhost:$port |"
      echo "| staging | \`$compose_staging\` | \`$port\` | \`http://localhost:$port$health\` | https://$staging_url |"
      echo "| prod | \`$compose_prod\` | \`$port\` | \`http://localhost:$port$health\` | https://$prod_url |"
      echo ""
      echo "## Docker Containers"
      echo ""
      echo "| Container | Name | Purpose |"
      echo "|-----------|------|---------|"
      echo "| web | \`${prefix}_web\` | gunicorn:8000 |"
      echo "| db | \`${prefix}_db\` | postgres:16 |"
      echo "| redis | \`${prefix}_redis\` | redis:7 |"
      echo "| worker | \`${prefix}_worker\` | celery (if present) |"
      echo ""
      echo "## Database"
      echo ""
      echo "- **DB name**: \`$db\`"
      echo "- **DB container**: \`${prefix}_db\`"
      echo "- **Migrations**: \`docker exec ${prefix}_web python manage.py migrate\`"
      echo "- **Shell**: \`docker exec -it ${prefix}_web python manage.py shell\`"
    fi

    echo ""
    echo "## System (Hetzner Server)"
    echo ""
    echo "- devuser hat **KEIN sudo-Passwort** → System-Pakete immer via SSH als root:"
    echo "  \`\`\`bash"
    echo "  ssh root@localhost \"apt-get install -y <package>\""
    echo "  \`\`\`"
    echo ""
    echo "## Secrets / Config"
    echo ""
    echo "- **Secrets**: \`.env\` (nicht in Git) — Template: \`.env.example\`"

  } > "$facts_file"

  echo "✅ $repo (type=$type, port=$port, prod=$prod_url)"
}

# ── Main ─────────────────────────────────────────────────────────────────────
echo "=== gen_project_facts.sh — Master Repo Identifier ==="
echo "Registry: $REGISTRY"
echo "Force: $FORCE"
echo ""

if [ -n "$TARGET_REPO" ]; then
  gen_facts "$TARGET_REPO"
else
  # All repos from registry first (known, with overrides)
  REGISTRY_REPOS=$(registry_repos)
  for repo in $REGISTRY_REPOS; do
    gen_facts "$repo"
  done

  # Then any NEW repos on disk not yet in registry
  echo ""
  echo "--- Scanning for unregistered repos ---"
  for repo_path in "$GITHUB"/*/; do
    repo=$(basename "$repo_path")
    [[ "$repo" == *.* ]] && continue
    echo "$REGISTRY_REPOS" | grep -qx "$repo" && continue
    echo "⚠️  UNREGISTERED: $repo — add to repo-registry.yaml"
    gen_facts "$repo"
  done
fi

echo ""
echo "=== Done. Run with --force to regenerate all ==="
