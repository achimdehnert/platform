---
description: Detect configuration drift between repos.json, ports.yaml, server state, and Outline docs
---

# /drift-check

Erkennt Abweichungen zwischen den 4 Wahrheitsquellen der Platform:
1. **repos.json** (Knowledge Graph)
2. **ports.yaml** (Port SSOT)
3. **Server-Zustand** (Docker Compose auf 88.198.191.108)
4. **Outline** (Hub-Dokumentation)

## Schritte

1. **repos.json laden**
// turbo
```
Lies ${GITHUB_DIR:-$HOME/github}/mcp-hub/platform_context_mcp/graph/repos.json
```

2. **ports.yaml laden**
// turbo
```
Lies ${GITHUB_DIR:-$HOME/github}/platform/infra/ports.yaml
```

3. **Port-Drift prüfen**
   Für jedes Repo in repos.json:
   - Port in repos.json == Port in ports.yaml?
   - Domain in repos.json == Domain in ports.yaml?
   - Melde jede Abweichung

4. **Server-Drift prüfen**
   Für jedes Repo mit Compose-Datei:
   ```
   mcp0_ssh_manage(action="exec", host="88.198.191.108",
     command="grep -oP '127.0.0.1:\\K\\d+' /opt/<repo>/docker-compose*.yml | head -1")
   ```
   - Host-Port auf Server == Port in repos.json?
   - Container-Name auf Server == container in repos.json?

5. **Nginx-Drift prüfen**
   ```
   mcp0_ssh_manage(action="exec", host="88.198.191.108",
     command="grep proxy_pass /etc/nginx/sites-enabled/<domain>.conf")
   ```
   - proxy_pass Port == Port in repos.json?

6. **Health-Endpoint-Drift prüfen**
   Für jedes Repo mit health_url:
   ```
   mcp0_ssh_manage(action="http_check", host="88.198.191.108", url="<health_url>")
   ```
   - HTTP 200? Wenn nicht → Drift oder App-Problem

7. **Outline-Drift prüfen** (optional)
   ```
   mcp3_search_knowledge(query="Platform Repo Directory")
   ```
   - Sind alle 22 Repos im Outline-Verzeichnis gelistet?

8. **Design-Token-Drift prüfen (decks-repos)** — lokal, `design-hub` muss als Geschwister-Repo vorliegen
   Für jedes Repo, das ein design-hub-Profil zu Theme/CSS regeneriert (aktuell: `decks-hub`):
// turbo
   ```
   cd ${GITHUB_DIR:-$HOME/github}/decks-hub && npm run theme && git diff --exit-code styles/
   ```
   - Exit 0 → committetes Theme == `design-hub/profiles/<brand>.yaml` (kein Drift)
   - Exit ≠ 0 → das generierte CSS ist veraltet gegenüber der design-hub-SSoT → **Drift**.
     Fix: `npm run theme` + committen (design-hub ist SSoT für Marken-Tokens).
   - **Warum hier (lokal), nicht in GitHub-CI:** `design-hub` ist privat/separat und in
     GitHub-CI nicht ausgecheckt → ein CI-`npm run theme` nähme den committeten-CSS-Fallback
     und prüfte nichts (No-Op). Drift-vom-Quell ist nur prüfbar, wo der Quell vorliegt
     (Lehre: Session-Retro 2026-06-19, Befund H — „Mandat ohne Mechanismus" vermeiden).

9. **Drift-Report erstellen**
   ```
   === Drift Report (2026-XX-XX) ===

   ✅ 18/22 repos consistent across all sources
   
   ⚠️ DRIFT DETECTED:
   - trading-hub: ports.yaml=8088, server compose=8092 → FIX compose
   - pptx-hub: repos.json port=8020, nginx proxy_pass=8093 → FIX nginx
   - learn-hub: health_url returns 502 → App not running
   
   📊 Coverage:
   - repos.json: 22 repos
   - ports.yaml: 24 services (2 infra-only)
   - Server compose: 26 stacks
   - Outline: 1 directory doc
   ```

10. **Fixes vorschlagen** — Für jeden Drift konkreten Fix mit Quelle nennen (welche SSOT hat Recht?)
   - ports.yaml ist SSOT für Ports
   - repos.json ist SSOT für Repo-Facts
   - Server-Zustand muss zu beiden passen

   **Resolution-Direction (Policy `evidence-discipline`):** Die Papier-SSOT
   gewinnt *nicht* automatisch. Wenn eine Quelle bewiesen-laufende Realität
   spiegelt (verifizierter Bind/Health) und der Gegen-Fix Zustand ändern
   würde, den du nicht inspizieren kannst (z.B. Host-Port auf einem
   SSH-gesperrten Server) → korrigiere die SSOT *zur bewiesenen Realität
   hin*, nie umgekehrt. Bind/Health, das du nicht prüfen kannst, ist eine
   Hypothese, kein Fix-Grund — als solche kennzeichnen, nicht behaupten.

## Referenzen
- ADR-021: Unified Deployment Pattern
- repos.json: `mcp-hub/platform_context_mcp/graph/repos.json`
- ports.yaml: `platform/infra/ports.yaml`
- Outline Directory: `d4c31417-10ef-41d6-899f-f38f9bef7452`
