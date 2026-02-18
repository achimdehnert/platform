# ADR-044 Review: deployment_mcp Tiefenanalyse

| Metadata | Value |
| -------- | ----- |
| **Status** | Review — Kritisch |
| **Datum** | 2026-02-18 |
| **Reviewer** | ADR Board (Production-Critical) |
| **Scope** | `deployment_mcp` — der produktionskritischste MCP-Server |
| **Geprüfte Dateien** | 15 Quelldateien, ~3.500 LOC |
| **Bezug** | ADR-044 (MCP-Hub Architecture Consolidation) |

---

## Executive Summary

ADR-044 bewertet `deployment_mcp` als **P3 — funktional korrekt**. Diese
Bewertung ist **falsch**. Die Tiefenanalyse deckt **6 produktionskritische
Defekte** auf, von denen einer direkt für die wiederkehrenden
Deployment-Ausfälle verantwortlich ist.

**Korrigierte Bewertung: P0 — Deployment-Blockierend.**

---

## F1: 120s-Timeout killt Deployments (P0 — SHOWSTOPPER)

### Befund

`server.py:370-373` umwickelt JEDEN Tool-Aufruf mit einem harten 120s-Timeout:

```python
# server.py:370-373
result = await asyncio.wait_for(
    handle_tool_call(name, arguments),
    timeout=120,
)
```

Aber die Deploy-Tools definieren ihre eigenen, längeren Timeouts:

| Tool | Internes Timeout | Wird erreicht? |
| ---- | ---------------- | -------------- |
| `bfagent_deploy_web` (compose pull) | 600s | **NEIN** — nach 120s gekillt |
| `bfagent_deploy_web` (compose up) | 600s | **NEIN** — nach 120s gekillt |
| `canary_deploy` (docker pull) | 600s | **NEIN** — nach 120s gekillt |
| `compose_up` (via DockerClient) | 300s | **NEIN** — nach 120s gekillt |
| `compose_pull` (via DockerClient) | 300s | **NEIN** — nach 120s gekillt |

### Auswirkung

1. `bfagent_deploy_web` wird aufgerufen
2. Env-Datei wird auf neuen Image-Tag aktualisiert (Zeile 42-44)
3. `docker pull` startet (Zeile 50-52, **nur 30s Timeout!**)
4. `docker compose pull` startet (Zeile 59-64, 600s Timeout)
5. **Nach 120s: `asyncio.TimeoutError` von `server.py`**
6. Die gesamte Funktion wird abgebrochen — **kein Rollback** (Zeile 190-232
   wird nie erreicht)
7. Server-Zustand: **Env-Datei zeigt auf neuen Tag, Container laufen
   mit altem Image**
8. Der remote `docker compose pull` Prozess läuft im Hintergrund weiter

### Zusätzliches Problem in `bfagent_deploy_web`

Zeile 50-52 (`docker pull`) nutzt `run_checked()` **ohne explizites
Timeout**:

```python
# bfagent_tools.py:50-52
pull_output = await ssh.run_checked(
    f"docker pull {q_ref}"
)
```

`run_checked()` → `run()` → `effective_timeout = timeout or self.timeout`
→ `self.timeout = settings.ssh_timeout = 30`. Ein `docker pull` für ein
300MB+ Image über eine langsame Verbindung braucht >30s. Das ergibt:

```text
RuntimeError: Command failed (exit -1): Command timed out after 30s
```

Dieser Fehler wird **nicht von der Funktion gefangen** (kein `except` in
`bfagent_deploy_web`, nur `finally`), sondern propagiert bis `server.py:343`
wo `fail(str(e))` ihn als Error-Message an den Client schickt.

### Fix

```python
# server.py — Timeout per-tool statt global
TOOL_TIMEOUTS: dict[str, int] = {
    "bfagent_deploy_web": 900,
    "canary_deploy": 900,
    "compose_up": 600,
    "compose_pull": 600,
    "compose_down": 300,
    "pip_install": 300,
    "git_clone": 300,
}
DEFAULT_TIMEOUT = 120

# In call_tool():
timeout = TOOL_TIMEOUTS.get(name, DEFAULT_TIMEOUT)
result = await asyncio.wait_for(
    handle_tool_call(name, arguments),
    timeout=timeout,
)
```

Und in `bfagent_tools.py:50`:

```python
pull_output = await ssh.run_checked(
    f"docker pull {q_ref}", timeout=600,
)
```

---

## F2: Shell-Injection in SSHClient-Methoden (P1 — Sicherheit)

### Befund

`ssh_client.py` enthält 5 Methoden die Pfade **ohne `shlex.quote()`**
in Shell-Kommandos einsetzen:

```python
# ssh_client.py:259 — path NOT quoted
async def read_file(self, path: str) -> str:
    stdout, stderr, exit_code = await self.run(
        f"cat {path}",
    )

# ssh_client.py:272 — path NOT quoted
async def write_file(self, path, content, mode="644"):
    escaped = content.replace("'", "'\"'\"'")
    await self.run_checked(f"echo '{escaped}' > {path}")

# ssh_client.py:277 — path NOT quoted
async def file_exists(self, path: str) -> bool:
    _, _, exit_code = await self.run(f"test -f {path}")

# ssh_client.py:282 — path NOT quoted
async def dir_exists(self, path: str) -> bool:
    _, _, exit_code = await self.run(f"test -d {path}")

# ssh_client.py:287 — path NOT quoted
async def ensure_dir(self, path: str) -> None:
    await self.run_checked(f"mkdir -p {path}")
```

### Analyse

Die **Tool-Level-Funktionen** in `ssh_tools.py` nutzen korrekt
`shlex.quote()`. Die Verwundbarkeit liegt nur in den SSHClient-Methoden.

**Aktuelle Aufrufer dieser Methoden:**

- `ssh_client.write_file()` → nur durch `env_client.py` indirekt
  (über `run_checked`, NICHT über `write_file` direkt)
- `ssh_client.read_file()` → nicht direkt aufgerufen (Tool nutzt eigene Impl.)
- `ssh_client.file_exists()` → nicht direkt aufgerufen
- `ssh_client.ensure_dir()` → nicht direkt aufgerufen

**Bewertung:** Aktuell kein aktiver Exploit-Pfad, aber ein Pfad mit
unescaptem Input existiert in der Client-Klasse. Jeder künftige Aufrufer
erbt die Verwundbarkeit.

### Fix (F2)

```python
async def read_file(self, path: str) -> str:
    stdout, stderr, exit_code = await self.run(
        f"cat {shlex.quote(path)}",
    )
```

Identisch für alle 5 Methoden.

---

## F3: Error-Message-Leaking auf 3 Ebenen (P1 — Sicherheit)

### Befund (F3)

Exception-Interna werden an den Client weitergeleitet — auf **drei
unabhängigen Ebenen**:

**Ebene 1 — server.py (Global Handler):**

```python
# server.py:343-353
except Exception as e:
    return fail(str(e), code="tool_exception", ...)

# server.py:381-386
except Exception as exc:
    result = json.dumps({
        "success": False,
        "error": str(exc),
    })
```

**Ebene 2 — consolidated/base.py (Dispatch):**

```python
# consolidated/base.py:291-295
except Exception as exc:
    return {"success": False, "error": str(exc)}
```

**Ebene 3 — Alle Tool-Funktionen (>30 Stellen):**

```python
# ssh_tools.py:45, 107, 148, 189, 220, 256, 307, 327
# git_tools.py:66, 355, 387, 418, 454, 500, 541, ...
# bfagent_tools.py (keine eigene Exception-Behandlung!)
except Exception as exc:
    return {"success": False, "error": str(exc)}
```

### Auswirkung (F3)

- SSH-Fehler: `"error": "Command failed (exit -1): Permission denied (publickey)"`
  → leakt SSH-Konfiguration
- Timeout-Fehler: `"error": "SSH semaphore busy for 30s (host=88.198.191.108)"`
  → leakt Server-IP und Semaphore-Zustand
- Datei-Fehler: `"error": "[Errno 2] No such file: /opt/bfagent-app/.env.prod"`
  → leakt Dateipfade

### Fix (F3)

Zentrale Error-Sanitisierung in `response.py`:

```python
def safe_fail(exc: Exception, tool_name: str) -> str:
    logger.exception("Tool %s failed", tool_name)
    return fail(
        "Interner Fehler. Siehe deployment-mcp.log.",
        code="internal_error",
    )
```

---

## F4: SSH-Chattyness — Mehrfach-Verbindungen pro Tool (P2 — Performance)

### Befund (F4)

Jeder SSH-Befehl öffnet eine neue SSH-Verbindung (TCP + Key Exchange +
Auth). Mehrere Tools machen **3-5 sequentielle SSH-Aufrufe**:

| Tool | SSH-Aufrufe | Problem |
| ---- | ----------- | ------- |
| `git_status` | **5** | branch + status + ahead + behind + stash |
| `git_push` (auto_rebase) | bis zu **4** | push + pull + push + log |
| `git_commit` (add_all) | **3** | add + commit + rev-parse |
| `git_checkout` | **2** | checkout + branch |
| `bfagent_deploy_web` (Erfolg) | **5** | grep + env + pull + compose_pull + up |
| `bfagent_deploy_web` (Fehler) | **12+** | + ps + caddy_logs + svc_logs + inspect + rollback + verify |

### Auswirkung (F4)

- `git_status` braucht 5 × (~0.3s SSH-Setup + Befehlszeit) statt 1 ×
- Bei Semaphore-Limit 4: Ein `bfagent_deploy_web` bei Fehler blockiert
  3 andere parallele Tool-Aufrufe
- Latenz addiert sich: 5 SSH-Aufrufe × 300ms Overhead = **1.5s** nur für
  TCP-Handshakes

### Fix (F4)

Befehle in einem einzigen SSH-Aufruf bündeln:

```bash
# git_status — ein SSH-Aufruf statt 5
cd /path/to/repo
echo "BRANCH:$(git branch --show-current)"
echo "STATUS:$(git status --porcelain | wc -l)"
echo "AHEAD:$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0)"
echo "BEHIND:$(git rev-list --count HEAD..@{u} 2>/dev/null || echo 0)"
echo "STASH:$(git stash list 2>/dev/null | wc -l)"
```

---

## F5: Dual-Path-Architektur Legacy + Consolidated (P2 — Wartbarkeit)

### Befund (F5)

`server.py` enthält **zwei vollständige Dispatch-Pfade**:

1. **Legacy** (Zeile 101-206): 95+ individuelle Funktions-Importe +
   `TOOL_HANDLERS` Dict
2. **Consolidated** (Zeile 240-246): 11 ConsolidatedTool-Klassen mit
   `@action`-Dekoratoren

Beide werden **immer geladen** (Zeile 23-81 importiert alle Legacy-Tools).
`CONSOLIDATED_MODE` (Standard: `true`) wählt nur den Dispatch-Pfad, aber
der Legacy-Code bleibt im Speicher.

### Probleme (F5)

- **Doppelter Wartungsaufwand**: Jede neue Action muss in
  `tools/*.py` UND `consolidated/*.py` hinzugefügt werden
- **Inkonsistente Error-Behandlung**: Legacy nutzt `fail()` aus
  `response.py`, Consolidated nutzt `dict` Returns
- **Testbarkeit**: Welcher Pfad wird getestet? Beide? Nur einer?
- **Import-Side-Effects**: Alle 95+ Tool-Funktionen werden bei Start
  importiert, auch wenn Consolidated aktiv ist

### Fix (F5)

Legacy-Pfad entfernen. In `consolidated/` fehlen nur noch `mcp_runtime_info`
und die GitHub-Actions-Tools. Nach deren Migration:

```python
# server.py — Vereinfacht
from .consolidated.registry import get_consolidated_tool_definitions

TOOLS, HANDLERS = get_consolidated_tool_definitions()

async def handle_tool_call(name, arguments):
    handler = HANDLERS.get(name)
    if not handler:
        return fail(f"Unknown tool: {name}")
    return await handler.dispatch(arguments)
```

---

## F6: Kein Lifecycle-Management für HTTP-Clients (P2 — Resource-Leak)

### Befund (F6)

`HetznerClient` und `DNSClient` erstellen lazy `httpx.AsyncClient`:

```python
# hetzner_client.py:37-48
async def _get_client(self) -> httpx.AsyncClient:
    if self._client is None:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_token}"},
            timeout=30.0,
        )
    return self._client
```

Beide haben `close()` Methoden die **nie aufgerufen werden**.
`server.py:run_server()` hat keinen Lifespan-Hook.

### Auswirkung (F6)

- Offene HTTP/2-Verbindungen akkumulieren über die Lebensdauer des
  MCP-Prozesses
- `httpx` loggt "Unclosed client" Warnungen bei Prozess-Ende
- Bei langlebigen Sessions (IDE-Betrieb: Stunden/Tage) steigt der
  Memory-Footprint
- Auf WSL2 werden TCP-Connections durch den Hyper-V-Netzwerkstack
  geroutet — offene Verbindungen verbrauchen dort mehr Ressourcen

---

## Zusätzliche Befunde (niedriger Schweregrad)

### F7: `StrictHostKeyChecking=no` (P3)

```python
# ssh_client.py:91
"-o", "StrictHostKeyChecking=no",
```

Deaktiviert SSH-Host-Key-Verifizierung. Auf einem Entwickler-Laptop
mit WSL akzeptabel, aber in einer CI/CD-Pipeline ein MITM-Risiko.

**Empfehlung:** `StrictHostKeyChecking=accept-new` nutzen.

### F8: DEBUG-Logging in Produktion (P3)

```python
# server.py:86-93
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler(_log_file, mode="a"),
        logging.StreamHandler(),
    ],
)
```

`~/.cache/deployment-mcp.log` wächst unbegrenzt. `mode="a"` ohne
Log-Rotation. Bei DEBUG-Level werden alle SSH-Befehle geloggt.

**Empfehlung:** `level=logging.INFO`, `RotatingFileHandler(maxBytes=10MB)`.

### F9: SSHClient.write_file nutzt fragile echo-Escaping (P3)

```python
# ssh_client.py:271-273 (Client-Methode, nicht Tool)
escaped = content.replace("'", "'\"'\"'")
await self.run_checked(f"echo '{escaped}' > {path}")
```

Die Tool-Level-Funktion `ssh_file_write` nutzt korrekt base64-Encoding.
Die Client-Methode existiert noch mit der fragilen Variante.

---

## Kritik an ADR-044

### Falsche Bewertungen

| ADR-044 Aussage | Korrektur |
| --------------- | --------- |
| `deployment_mcp`: P3, "funktional korrekt" | **P0** — 120s-Timeout killt jedes Deployment >120s |
| "Kein Schema-Breaking-Change bei FastMCP-Migration" | **Stimmt nicht** — Consolidated-Mode ändert Tool-Namen bereits |
| "Lifespan-Hooks vergessen" als P2 | Korrekt für Resource-Leak, aber der Timeout-Bug ist P0 |
| Error-Leaking nur in `llm_mcp` und `orchestrator_mcp` | **Auch in `deployment_mcp`** — auf 3 Ebenen |

### Übersehene Befunde in ADR-044

1. **120s-Timeout vs. 600s-Tool-Timeouts** — Hauptursache für Deployment-Probleme
2. **Shell-Injection in SSHClient-Methoden** — 5 unescapte Pfade
3. **SSH-Chattyness** — 5-12 Verbindungen pro Tool-Aufruf
4. **Dual-Path-Architektur** — doppelter Wartungsaufwand
5. **`docker pull` ohne Timeout** in `bfagent_deploy_web`
6. **Kein `except` in `bfagent_deploy_web`** — RuntimeError ohne Cleanup
7. **`StrictHostKeyChecking=no`** — MITM-Anfälligkeit
8. **Unbegrenztes DEBUG-Logging**

---

## Priorisierter Maßnahmenplan

### Sofort (heute)

| # | Fix | Datei | Aufwand |
| - | --- | ----- | ------- |
| 1 | Per-Tool Timeouts statt 120s global | `server.py` | 30min |
| 2 | `docker pull` Timeout auf 600s | `bfagent_tools.py:50` | 5min |
| 3 | `try/except` um gesamtes Deploy | `bfagent_tools.py` | 15min |

### Diese Woche

| # | Fix | Datei | Aufwand |
| - | --- | ----- | ------- |
| 4 | `shlex.quote()` in SSHClient-Methoden | `ssh_client.py` | 15min |
| 5 | Error-Sanitisierung zentral | `response.py` + alle Tools | 2h |
| 6 | SSH-Befehle bündeln (git_status etc.) | `git_tools.py` | 2h |

### Nächste Woche

| # | Fix | Datei | Aufwand |
| - | --- | ----- | ------- |
| 7 | Legacy-Dispatch entfernen | `server.py` | 3h |
| 8 | Lifespan-Hook für Clients | `server.py` | 1h |
| 9 | `StrictHostKeyChecking=accept-new` | `ssh_client.py` | 5min |
| 10 | Log-Rotation + INFO-Level | `server.py` | 15min |

---

## Verifizierungsprotokoll

| Datei | Zeilen | Befunde |
| ----- | ------ | ------- |
| `server.py` | 415 | F1, F3, F5, F8 |
| `ssh_client.py` | 321 | F2, F7, F9 |
| `docker_client.py` | 321 | Korrekt, aber Timeout <120s wird gekillt |
| `bfagent_tools.py` | 237 | F1 (30s docker-pull, 600s compose-pull), kein except |
| `ssh_tools.py` | 328 | F3, ansonsten korrekt (base64, shlex) |
| `git_tools.py` | 724 | F4 (5 SSH-Aufrufe), F3 |
| `settings.py` | 88 | `ssh_timeout=30` zu niedrig für Docker-Ops |
| `response.py` | 88 | `fail()` korrekt, wird aber mit `str(e)` gefüttert |
| `consolidated/base.py` | 321 | F3, F5 |
| `consolidated/registry.py` | 76 | 11 Tools, korrekt |
| `consolidated/ssh_tool.py` | 138 | Delegiert korrekt |
| `canary.py` | (grep) | 600s intern, von 120s gekillt |
| `pip_tools.py` | (grep) | 120s intern = OK |
| `docker_tools.py` | (grep) | Container-exec delegiert Timeout |
| `hetzner_client.py` | (grep) | F6, lazy httpx, close() nie aufgerufen |
