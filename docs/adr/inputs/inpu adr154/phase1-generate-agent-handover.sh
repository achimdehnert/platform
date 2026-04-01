#!/usr/bin/env bash
# =============================================================================
# platform/scripts/generate-agent-handover.sh
# Generiert AGENT_HANDOVER.md aus repos.json + ports.yaml (SSOT)
#
# Aufruf: ./generate-agent-handover.sh [--output PATH] [--dry-run]
# =============================================================================
set -euo pipefail
trap 'echo "ERROR at line $LINENO — exit code $?" >&2; exit 1' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPOS_JSON="${PLATFORM_ROOT}/platform/data/repos.json"
PORTS_YAML="${PLATFORM_ROOT}/platform/data/ports.yaml"
OUTPUT_PATH="${PLATFORM_ROOT}/AGENT_HANDOVER.md"
DRY_RUN=false

# ---------------------------------------------------------------------------
# Argumente parsen
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT_PATH="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unbekannter Parameter: $1" >&2; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Abhängigkeiten prüfen
# ---------------------------------------------------------------------------
for cmd in jq python3 yq; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "FEHLER: '$cmd' nicht gefunden. Bitte installieren." >&2
    exit 2
  fi
done

# ---------------------------------------------------------------------------
# Quellen validieren
# ---------------------------------------------------------------------------
if [[ ! -f "${REPOS_JSON}" ]]; then
  echo "FEHLER: repos.json nicht gefunden: ${REPOS_JSON}" >&2
  exit 3
fi

if [[ ! -f "${PORTS_YAML}" ]]; then
  echo "WARNUNG: ports.yaml nicht gefunden: ${PORTS_YAML}" >&2
  PORTS_AVAILABLE=false
else
  PORTS_AVAILABLE=true
fi

echo "[generate-agent-handover] SSOT: ${REPOS_JSON}"
echo "[generate-agent-handover] Output: ${OUTPUT_PATH}"
echo "[generate-agent-handover] Dry-run: ${DRY_RUN}"

# ---------------------------------------------------------------------------
# Python-Generator (inlined — kein externer State)
# ---------------------------------------------------------------------------
GENERATED_CONTENT="$(python3 - "${REPOS_JSON}" "${PORTS_YAML}" "${PORTS_AVAILABLE}" <<'PYTHON_EOF'
import json
import sys
import datetime
from pathlib import Path

repos_json_path = sys.argv[1]
ports_yaml_path = sys.argv[2]
ports_available = sys.argv[3].lower() == "true"

with open(repos_json_path) as f:
    repos_data = json.load(f)

ports_by_name: dict = {}
if ports_available:
    try:
        import yaml  # type: ignore
        with open(ports_yaml_path) as f:
            ports_data = yaml.safe_load(f) or {}
        for name, cfg in ports_data.get("services", {}).items():
            ports_by_name[name] = cfg
    except ImportError:
        pass  # yq checked in bash; yaml optional here

now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

lines = [
    "# AGENT_HANDOVER.md",
    "",
    "> **AUTO-GENERATED** — Nicht manuell bearbeiten.",
    f"> Generiert: {now}",
    f"> SSOT: `platform/data/repos.json`",
    "",
    "---",
    "",
    "## Platform Overview",
    "",
]

# MCP-Konfiguration
mcp_config = repos_data.get("mcp_config", {})
if mcp_config:
    lines += [
        "## MCP Tool Prefixes (aktuell)",
        "",
        "| MCP Server | Prefix | URL |",
        "|-----------|--------|-----|",
    ]
    for server_name, cfg in mcp_config.get("servers", {}).items():
        prefix = cfg.get("tool_prefix", "—")
        url = cfg.get("url", "stdio")
        lines.append(f"| `{server_name}` | `{prefix}` | `{url}` |")
    lines.append("")

# Repositories
repos = repos_data.get("repos", repos_data.get("repositories", []))
if isinstance(repos, dict):
    repos = list(repos.values())

lines += [
    "## Repositories",
    "",
    "| Repo | Stack | Default Branch | Notes |",
    "|------|-------|---------------|-------|",
]
for repo in repos:
    name = repo.get("name", repo.get("id", "—"))
    stack = repo.get("stack", "—")
    branch = repo.get("default_branch", "main")
    notes = repo.get("notes", "")
    lines.append(f"| `{name}` | {stack} | `{branch}` | {notes} |")
lines.append("")

# Port-Matrix
if ports_by_name:
    lines += [
        "## Port-Matrix",
        "",
        "| Service | Dev | Staging | Prod |",
        "|---------|-----|---------|------|",
    ]
    for svc, cfg in sorted(ports_by_name.items()):
        dev = cfg.get("dev", "—")
        staging = cfg.get("staging", "—")
        prod = cfg.get("prod", "—")
        lines.append(f"| `{svc}` | {dev} | {staging} | {prod} |")
    lines.append("")

# Platform-Standards Reminder
lines += [
    "## Non-Negotiable Platform Standards",
    "",
    "- `BigAutoField` PK + `public_id` UUIDField auf allen User-Data-Modellen",
    "- `tenant_id = BigIntegerField(db_index=True)` — kein LocalTenant-FK",
    "- Soft-Delete via `deleted_at`; kein Hard-Delete auf User-Data",
    "- `UniqueConstraint` (nicht `unique_together`)",
    "- Service-Layer: Business-Logik nie in Views oder Tasks direkt",
    "- `transaction.on_commit()` für Celery-Dispatch; `acks_late=True`",
    "- `read_secret()` für alle Credentials — nie `os.environ[` oder `config()`",
    "- `asgiref.async_to_sync` — nie `asyncio.run()` im ASGI-Kontext",
    "- `set -euo pipefail` in allen Shell-Scripts",
    "- i18n: `_()` und `{% trans %}` ab Tag 1",
    "",
    "---",
    "",
    f"*Nächste Generierung: nach jedem `sync-workflows.sh` Lauf*",
]

print("\n".join(lines))
PYTHON_EOF
)"

# ---------------------------------------------------------------------------
# Output schreiben oder anzeigen
# ---------------------------------------------------------------------------
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "--- DRY RUN OUTPUT ---"
  echo "${GENERATED_CONTENT}"
  echo "--- END DRY RUN ---"
  exit 0
fi

echo "${GENERATED_CONTENT}" > "${OUTPUT_PATH}"
echo "[generate-agent-handover] ✅ AGENT_HANDOVER.md aktualisiert: ${OUTPUT_PATH}"

# Diff anzeigen wenn git verfügbar
if git -C "${PLATFORM_ROOT}" diff --quiet HEAD -- "${OUTPUT_PATH}" 2>/dev/null; then
  echo "[generate-agent-handover] Keine Änderungen."
else
  echo "[generate-agent-handover] Änderungen:"
  git -C "${PLATFORM_ROOT}" diff HEAD -- "${OUTPUT_PATH}" 2>/dev/null || true
fi

exit 0
