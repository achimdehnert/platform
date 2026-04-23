#!/usr/bin/env bash
# platform/scripts/dev.sh — Universeller lokaler Dev-Server-Starter
#
# Usage:  dev.sh <repo-name>            # z.B. dev.sh writing-hub
#         dev.sh <repo-name> --check    # Nur Konfiguration prüfen, nicht starten
#
# Port:      aus platform/infra/ports.yaml  (dev: XXXX)
# Settings:  automatisch erkannt aus dem Repo
# venv:      automatisch erkannt (.venv, venv, system python3)
# Secrets:   <repo>/.env.dev wird automatisch gesourcet (gitignored)
#
# Funktioniert für ALLE Repos — kein manuelles Pflegen nötig.
# Voraussetzung: pyyaml  (pip3 install pyyaml)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PORTS_YAML="$PLATFORM_DIR/infra/ports.yaml"
REPOS_BASE="$(cd "$PLATFORM_DIR/.." && pwd)"

REPO="${1:-}"
CHECK_ONLY="${2:-}"

# --- Usage / Liste aller Repos ---
if [[ -z "$REPO" ]]; then
  echo "Usage: dev.sh <repo-name> [--check]"
  echo ""
  echo "Alle Repos in ports.yaml (dev-Port):"
  PORTS_YAML_PATH="$PORTS_YAML" python3 - <<'PYEOF'
import yaml, os
data = yaml.safe_load(open(os.environ["PORTS_YAML_PATH"]))
for name, svc in sorted(data.get("services", {}).items(), key=lambda x: x[1].get("dev", 9999)):
    port = svc.get("dev", "?")
    print(f"  {name:<25} port={port}")
PYEOF
  exit 1
fi

REPO_DIR="$REPOS_BASE/$REPO"
if [[ ! -d "$REPO_DIR" ]]; then
  echo "FEHLER: Verzeichnis nicht gefunden: $REPO_DIR"
  exit 1
fi

# ── 1. Port aus ports.yaml ────────────────────────────────────────────────────
DEV_PORT="$(python3 - "$REPO" "$PORTS_YAML" <<'PYEOF'
import sys, yaml
repo, ports_file = sys.argv[1], sys.argv[2]
data = yaml.safe_load(open(ports_file))
svc = data.get("services", {}).get(repo)
if not svc:
    print(f"MISSING", end="")
    sys.exit(0)
print(svc.get("dev", "8000"), end="")
PYEOF
)"

if [[ "$DEV_PORT" == "MISSING" ]]; then
  echo "WARNUNG: '$REPO' nicht in ports.yaml — nutze Port 8000 als Fallback"
  DEV_PORT="8000"
fi

# ── 2. manage.py Verzeichnis auto-erkennen ────────────────────────────────────
MANAGE_DIR=""
for candidate in "$REPO_DIR" "$REPO_DIR/src" "$REPO_DIR/app"; do
  if [[ -f "$candidate/manage.py" ]]; then
    MANAGE_DIR="$candidate"
    break
  fi
done
# Tiefergehend suchen wenn nötig
if [[ -z "$MANAGE_DIR" ]]; then
  FOUND="$(find "$REPO_DIR" -maxdepth 3 -name "manage.py" \
    ! -path "*/.venv/*" ! -path "*/.claude/*" ! -path "*/node_modules/*" \
    -print -quit 2>/dev/null || true)"
  if [[ -n "$FOUND" ]]; then
    MANAGE_DIR="$(dirname "$FOUND")"
  fi
fi
if [[ -z "$MANAGE_DIR" ]]; then
  echo "FEHLER: manage.py nicht gefunden in $REPO_DIR"
  exit 1
fi

# ── 3. Settings-Modul auto-erkennen ──────────────────────────────────────────
detect_settings() {
  local base="$1"
  # Bevorzuge development.py falls vorhanden
  for try_base in "$base" "$base/src"; do
    if [[ -f "$try_base/config/settings/development.py" ]]; then
      echo "config.settings.development"; return
    fi
    if [[ -f "$try_base/config/settings/local.py" ]]; then
      echo "config.settings.local"; return
    fi
    if [[ -f "$try_base/config/settings/base.py" ]]; then
      echo "config.settings.base"; return
    fi
    if [[ -f "$try_base/config/settings.py" ]]; then
      echo "config.settings"; return
    fi
  done
  # Non-standard: suche settings.py irgendwo im Repo
  local found
  found="$(find "$base" -maxdepth 5 -name "settings.py" \
    ! -path "*/.venv/*" ! -path "*/.claude/*" ! -path "*/test*" \
    -print -quit 2>/dev/null || true)"
  if [[ -n "$found" ]]; then
    # Konvertiere Pfad → Python-Modul relativ zu MANAGE_DIR
    local rel
    rel="${found#$MANAGE_DIR/}"
    rel="${rel%.py}"
    rel="${rel//\//.}"
    echo "$rel"; return
  fi
  echo "config.settings"
}

if [[ -z "${DJANGO_SETTINGS_MODULE:-}" ]]; then
  DJANGO_SETTINGS_MODULE="$(detect_settings "$REPO_DIR")"
fi

# ── 4. Python / venv auto-erkennen ───────────────────────────────────────────
PYTHON="python3"
for venv_candidate in ".venv" "venv" ".virtualenv"; do
  if [[ -f "$REPO_DIR/$venv_candidate/bin/python" ]]; then
    PYTHON="$REPO_DIR/$venv_candidate/bin/python"
    break
  fi
done

# ── 5. .env.dev sourcen (Secrets) ────────────────────────────────────────────
ENV_LOADED=""
for env_file in "$REPO_DIR/.env.dev" "$REPO_DIR/.env"; do
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
    ENV_LOADED="$(basename "$env_file")"
    break
  fi
done

export DJANGO_SETTINGS_MODULE

# ── Ausgabe ───────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
printf "║  🚀 %-52s ║\n" "$REPO"
printf "║     %-52s ║\n" "URL:      http://127.0.0.1:$DEV_PORT"
printf "║     %-52s ║\n" "Settings: $DJANGO_SETTINGS_MODULE"
printf "║     %-52s ║\n" "Python:   $PYTHON"
printf "║     %-52s ║\n" "Dir:      $MANAGE_DIR"
[[ -n "$ENV_LOADED" ]] && printf "║     %-52s ║\n" "Env:      $ENV_LOADED geladen"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [[ "$CHECK_ONLY" == "--check" ]]; then
  echo "  (--check: kein Start)"
  exit 0
fi

cd "$MANAGE_DIR"
exec "$PYTHON" manage.py runserver "127.0.0.1:$DEV_PORT"
