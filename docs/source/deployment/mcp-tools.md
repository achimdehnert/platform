# Deployment MCP — Tool-Referenz

Das **Deployment MCP** (`mcp-hub/deployment_mcp`) stellt autonome
Infrastruktur-Tools via Model Context Protocol bereit. Cascade nutzt
diese Tools für Server-, Container-, Datenbank- und Git-Management.

## Architektur

```text
┌─────────────────────────────────────────────┐
│              Deployment MCP Server           │
├──────────────┬──────────────────────────────┤
│ server.py    │  MCP Protocol (stdio)        │
│ tool_registry│  Declarative tool specs      │
├──────────────┴──────────────────────────────┤
│                  Tools Layer                 │
├────────────┬────────────┬───────────────────┤
│ hetzner    │ docker     │ postgres          │
│ ssh        │ ssl        │ dns               │
│ env        │ bfagent    │ system            │
│ git        │ debug      │ github_actions    │
└────────────┴────────────┴───────────────────┘
         │              │
    SSHClient      Hetzner/DNS API
         │              │
    Remote Host     Cloud APIs
```

**Dateien:**

| Datei | Zweck |
|-------|-------|
| `server.py` | MCP Server, Handler-Registry, Dispatch |
| `tool_registry.py` | Deklarative Tool-Spezifikationen (JSON Schema) |
| `tools/__init__.py` | Re-Export aller Tool-Funktionen |
| `tools/<domain>_tools.py` | Domain-spezifische Tool-Implementierungen |

## Hetzner Server Tools

| Tool | Beschreibung |
|------|-------------|
| `server_list` | Alle Hetzner Cloud Server auflisten |
| `server_status` | Server-Status nach ID oder Name |
| `server_power` | Power-Aktion (poweron, poweroff, reboot, reset, shutdown) |
| `server_create` | Neuen Server erstellen (confirm=true) |
| `server_delete` | Server löschen (confirm=true) |
| `server_rebuild` | Server mit neuem Image neu aufsetzen |
| `server_types_list` | Verfügbare Server-Typen |
| `images_list` | Verfügbare OS-Images |
| `locations_list` | Verfügbare Datacenter-Standorte |

## Firewall Tools

| Tool | Beschreibung |
|------|-------------|
| `firewall_list` | Alle Firewalls auflisten |
| `firewall_get` | Firewall-Details inkl. Regeln |
| `firewall_create` | Neue Firewall erstellen |
| `firewall_delete` | Firewall löschen (confirm=true) |
| `firewall_set_rules` | Firewall-Regeln setzen (ersetzt alle) |
| `firewall_apply` | Firewall auf Server anwenden |
| `firewall_remove` | Firewall von Server entfernen |

## SSH Key Tools (Hetzner)

| Tool | Beschreibung |
|------|-------------|
| `ssh_key_list` | Alle SSH-Keys in Hetzner |
| `ssh_key_create` | Neuen SSH-Key erstellen |
| `ssh_key_delete` | SSH-Key löschen (confirm=true) |

## Docker Container Tools

| Tool | Beschreibung |
|------|-------------|
| `container_list` | Docker-Container auflisten |
| `container_status` | Container-Status und Stats |
| `container_logs` | Container-Logs (default: 100 Zeilen) |
| `container_restart` | Container neustarten |
| `container_start` | Container starten |
| `container_stop` | Container stoppen |

## Docker Compose Tools

| Tool | Beschreibung |
|------|-------------|
| `compose_ps` | Compose-Services auflisten |
| `compose_up` | Services starten |
| `compose_down` | Services stoppen |
| `compose_logs` | Service-Logs |
| `compose_pull` | Images pullen |
| `compose_restart` | Services neustarten |

## BF Agent Deploy

| Tool | Beschreibung |
|------|-------------|
| `bfagent_deploy_web` | Full-Stack Deploy: `.env` → pull → up → HTTP verify |

Parameter: `image_tag` (required), `host`, `project_dir`, `compose_file`,
`env_file`, `service`, `image_repo`, `verify_url`, `expect_http_status`,
`pull`, `recreate`.

## PostgreSQL Tools

| Tool | Beschreibung |
|------|-------------|
| `db_list` | Alle Datenbanken auflisten |
| `db_status` | PostgreSQL Server-Status |
| `db_create` | Neue Datenbank erstellen |
| `db_drop` | Datenbank löschen (confirm=true) |
| `db_query` | SQL-Query ausführen (read-only empfohlen) |
| `db_backup` | Backup erstellen (custom/plain/tar) |
| `db_backup_list` | Verfügbare Backups auflisten |
| `db_restore` | Backup wiederherstellen (confirm=true) |
| `db_migrate` | Alembic/Django Migrations ausführen |

## Environment & Secret Tools

| Tool | Beschreibung |
|------|-------------|
| `env_list` | `.env`-Variablen auflisten (maskiert) |
| `env_get` | Einzelne Variable lesen |
| `env_set` | Variable setzen |
| `env_delete` | Variable löschen (confirm=true) |
| `env_validate` | Required Keys validieren |
| `secret_list` | Secrets auflisten (ohne Werte) |
| `secret_set` | Secret setzen |
| `secret_delete` | Secret löschen (confirm=true) |

## SSL Tools

| Tool | Beschreibung |
|------|-------------|
| `ssl_status` | Zertifikat-Status für Domain |
| `ssl_expiring` | Bald ablaufende Zertifikate (default: 30 Tage) |
| `ssl_renew` | Zertifikat erneuern (confirm=true) |
| `ssl_obtain` | Neues Zertifikat anfordern (confirm=true) |
| `ssl_revoke` | Zertifikat widerrufen (confirm=true) |
| `ssl_delete` | Zertifikat aus certbot löschen (confirm=true) |
| `ssl_certbot_info` | Certbot-Installation Info |

## DNS Tools (Hetzner DNS)

| Tool | Beschreibung |
|------|-------------|
| `dns_zone_list` | Alle DNS-Zonen |
| `dns_zone_get` | Zone-Details |
| `dns_zone_create` | Zone erstellen (confirm=true) |
| `dns_zone_delete` | Zone löschen (confirm=true) |
| `dns_record_list` | Records in Zone auflisten |
| `dns_record_get` | Record-Details |
| `dns_record_create` | Record erstellen |
| `dns_record_update` | Record aktualisieren |
| `dns_record_delete` | Record löschen (confirm=true) |
| `dns_find_records` | Records nach Name/Typ suchen |
| `dns_set_a_record` | A-Record setzen (create/update) |
| `dns_set_cname_record` | CNAME setzen (create/update) |

## SSH Remote Tools

| Tool | Beschreibung |
|------|-------------|
| `ssh_exec` | Beliebigen Befehl remote ausführen |
| `ssh_file_read` | Datei remote lesen (head/tail) |
| `ssh_file_write` | Datei remote schreiben (mode, mkdir, append) |
| `ssh_file_exists` | Datei/Verzeichnis prüfen |
| `ssh_dir_list` | Verzeichnisinhalt auflisten |
| `http_check` | HTTP Health-Check (lokal oder remote) |

## Git Tools

Vollständige Git-Operationen auf Remote-Hosts via SSH.

| Tool | Beschreibung | Pflichtparameter |
|------|-------------|-----------------|
| `git_status` | Branch, Changes, Ahead/Behind | `repo_path` |
| `git_log` | Commit-Historie | `repo_path` |
| `git_pull` | Von Remote pullen (optional rebase) | `repo_path` |
| `git_push` | Zu Remote pushen (force-with-lease, tags) | `repo_path` |
| `git_clone` | Repository klonen | `url`, `target_path` |
| `git_checkout` | Branch/Tag/Commit auschecken | `repo_path`, `ref` |
| `git_branch_list` | Branches auflisten (lokal/alle) | `repo_path` |
| `git_diff` | Diff anzeigen (staged, refs, stat) | `repo_path` |
| `git_commit` | Änderungen committen (add_all, files) | `repo_path`, `message` |
| `git_tag` | Tags verwalten (list/create/delete) | `repo_path` |
| `git_stash` | Stash: list/push/pop/drop/clear | `repo_path` |
| `git_merge` | Branch mergen (no-ff, abort) | `repo_path`, `branch` |
| `git_remote` | Remotes mit URLs auflisten | `repo_path` |

### Beispiel: Git-Status prüfen

```json
{
  "tool": "git_status",
  "arguments": {
    "repo_path": "/opt/bfagent-app",
    "host": "88.198.191.108"
  }
}
```

Rückgabe:

```json
{
  "success": true,
  "branch": "main",
  "clean": true,
  "changed_files": 0,
  "ahead": 0,
  "behind": 0,
  "stash_count": 0
}
```

## System Tools

| Tool | Beschreibung |
|------|-------------|
| `system_info` | Disk, Memory, CPU, Uptime |
| `system_processes` | Top-Prozesse nach CPU/Memory |
| `service_status` | Systemd Service-Status |
| `service_action` | Service starten/stoppen/restart/enable |
| `nginx_status` | Nginx: Config-Test, Sites, Listener |
| `nginx_reload` | Nginx Config testen und reloaden |
| `log_search` | Logs via journalctl/grep durchsuchen |
| `cron_list` | Crontab-Einträge auflisten |

## Debug Tools

| Tool | Beschreibung |
|------|-------------|
| `mcp_runtime_info` | MCP Runtime-Info (Python-Version, Tools, Settings) |

## GitHub Actions Tools

| Tool | Beschreibung |
|------|-------------|
| `github_workflow_runs` | Workflow-Runs auflisten |
| `github_workflow_run_status` | Run-Status im Detail |
| `github_workflow_run_logs` | Run-Logs abrufen |
| `github_workflow_dispatch` | Workflow manuell triggern |
| `github_workflow_cancel` | Laufenden Workflow abbrechen |
| `github_workflow_rerun` | Workflow erneut ausführen |

## Sicherheitskonzept

Destruktive Aktionen erfordern **`confirm=true`**:

- `server_create`, `server_delete`, `server_rebuild`
- `firewall_delete`
- `ssh_key_delete`
- `compose_down`
- `db_drop`, `db_restore`
- `env_delete`, `secret_delete`
- `ssl_renew`, `ssl_obtain`, `ssl_revoke`, `ssl_delete`
- `dns_zone_create`, `dns_zone_delete`, `dns_record_delete`
- `service_action`

**Allowlist-Filter:** Über `DEPLOYMENT_MCP_TOOL_ALLOWLIST` (komma-getrennt)
können verfügbare Tools eingeschränkt werden.

**Output-Truncation:** Git-Tool-Ausgaben werden auf 50.000 Zeichen begrenzt.

## Konfiguration

Windsurf MCP-Konfiguration (`mcp_config.json`):

```json
{
  "deployment-mcp": {
    "command": "uv",
    "args": ["run", "--directory", "<path>/deployment_mcp", "deployment-mcp"],
    "env": {
      "SSH_HOST": "88.198.191.108",
      "SSH_USER": "root",
      "SSH_KEY_PATH": "~/.ssh/id_ed25519",
      "HETZNER_API_TOKEN": "<token>",
      "HETZNER_DNS_TOKEN": "<token>"
    }
  }
}
```
