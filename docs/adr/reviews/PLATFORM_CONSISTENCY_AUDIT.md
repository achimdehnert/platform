# Platform Consistency Audit — 2026-02-10

## Zusammenfassung

Systematische Analyse aller 7 Repos auf Inkonsistenzen, falsche Referenzen und
Konfigurationsfehler. Ergebnis: **23 Findings in 6 Kategorien**, davon 7 kritisch.

---

## Kategorie A: Git Remote URLs (SICHERHEIT)

**Problem**: 3 von 7 Repos nutzen HTTPS mit eingebettetem PAT-Token statt SSH.
Das Token ist im `.git/config` im Klartext und kann durch `git remote -v` geleakt werden.

| Repo       | Remote-Typ | Status |
|------------|-----------|--------|
| platform   | SSH ✅     | OK     |
| risk-hub   | SSH ✅     | OK     |
| travel-beat| SSH ✅     | OK     |
| weltenhub  | SSH ✅     | OK     |
| pptx-hub   | HTTPS ❌  | Token im Klartext |
| bfagent    | HTTPS ❌  | Token im Klartext |
| mcp-hub    | HTTPS ❌  | Token im Klartext |

**Fix A1** (KRITISCH): Alle 3 Repos auf SSH umstellen:
```bash
git remote set-url origin git@github.com:achimdehnert/<repo>.git
```

**Fix A2**: Global Rules Memory korrigieren — referenziert `~/.ssh/github_ed25519`,
die Datei existiert aber NICHT. Korrekt ist `~/.ssh/id_ed25519`.

---

## Kategorie B: SSH-Key Referenzen

**Problem**: 3 verschiedene SSH-Key-Namen in verschiedenen Configs.

| Quelle                        | Key-Pfad              | Existiert? |
|-------------------------------|-----------------------|-----------|
| `settings.py` (default)      | `~/.ssh/id_rsa`       | ❌ NEIN   |
| `.env.example`                | `~/.ssh/id_ed25519`   | ✅ JA     |
| `start-deployment-mcp.sh`    | `~/.ssh/id_ed25519`   | ✅ JA     |
| `mcp_config.json` (Windsurf) | `~/.ssh/id_ed25519`   | ✅ JA     |
| Global Rules (Memory)        | `~/.ssh/github_ed25519`| ❌ NEIN  |

**Fix B1**: `settings.py` default von `id_rsa` auf `id_ed25519` ändern.
**Fix B2**: Global Rules Memory korrigieren (`github_ed25519` → `id_ed25519`).

---

## Kategorie C: Server-Deploy-Strategien (INKONSISTENT)

**Problem**: Jedes Projekt deployt anders. Kein einheitliches Pattern.

| Repo        | Server-Pfad    | Deploy-Methode        | Git auf Server? |
|-------------|----------------|-----------------------|----------------|
| bfagent     | /opt/bfagent-app | Git clone + compose  | ✅ Ja          |
| risk-hub    | /opt/risk-hub  | Docker image pull     | ❌ Nein (nur compose) |
| travel-beat | /opt/travel-beat | Docker image pull + scripts | ❌ Nein |
| weltenhub   | /opt/weltenhub | rsync/copy (voller Source) | ❌ Nein (kein .git) |

**Fix C1**: Dokumentieren, welches Deploy-Pattern jedes Projekt nutzt.
**Fix C2**: ADR-021 aktualisieren mit tatsächlichen Deploy-Strategien pro Projekt.

---

## Kategorie D: Docker-Compose Duplikate (travel-beat)

**Problem**: travel-beat hat 3 verschiedene `docker-compose.prod.yml` Dateien:
- `docker/docker-compose.prod.yml` (unsere Änderungen — gehärtet)
- `deploy/docker-compose.prod.yml` (alt, ungehärtet)
- `scripts/docker-compose.prod.yml` (alt, ungehärtet)

Alle 3 haben verschiedene Inhalte (verschiedene MD5-Hashes).
**Aber auf dem Server liegt eine vierte Version** unter `/opt/travel-beat/docker-compose.prod.yml`.

**Fix D1** (KRITISCH): Kanonische Datei definieren (`docker/docker-compose.prod.yml`).
**Fix D2**: Duplikate löschen oder durch Symlinks/README ersetzen.
**Fix D3**: Server-Compose mit der kanonischen Version synchronisieren.

---

## Kategorie E: Container-Probleme auf dem Server

**Problem**: weltenhub_celery und weltenhub_beat sind in einer Restart-Loop.

```
weltenhub_celery    Restarting (2) 55 seconds ago
weltenhub_beat      Restarting (2) 55 seconds ago
```

Mögliche Ursachen:
- Fehlende Environment-Variablen
- Redis-Verbindungsprobleme (shared `bfagent_redis`)
- Python-Import-Fehler nach Code-Änderungen

**Fix E1** (KRITISCH): Logs prüfen und Root-Cause beheben:
```bash
docker logs weltenhub_celery --tail 50
```

---

## Kategorie F: MCP-Tool Zuverlässigkeit

**Problem**: `deployment-mcp` SSH-Tool (`mcp5_ssh_manage`) wird bei jedem Aufruf
"canceled by user". Direkte SSH-Befehle via Terminal funktionieren einwandfrei.

Mögliche Ursachen:
- `asyncssh` Timeout-Probleme in WSL-Kontext
- Windsurf MCP-Tool Timeout zu kurz
- SSH-Agent nicht verfügbar für asyncssh

**Fix F1**: asyncssh-Verbindung debuggen (Logs aktivieren).
**Fix F2**: Fallback auf subprocess-basiertes SSH statt asyncssh evaluieren.
**Fix F3**: MCP orchestrator `run_command_safe` CWD-Einschränkung lockern
  (aktuell nur `/home/dehnert/github/` erlaubt).

---

## Optimaler Fix-Ablauf (Priorisiert)

### Phase 1: Sicherheit (sofort, lokal)
1. **A1**: Git Remotes auf SSH umstellen (pptx-hub, bfagent, mcp-hub)
2. **B1**: `settings.py` SSH-Key default korrigieren
3. **B2**: Global Rules Memory korrigieren

### Phase 2: Server-Stabilität (sofort, remote)
4. **E1**: weltenhub_celery/beat Restart-Loop diagnostizieren + fixen
5. **D3**: travel-beat Server-Compose mit kanonischer Version synchronisieren

### Phase 3: Aufräumen (lokal)
6. **D1+D2**: travel-beat Compose-Duplikate bereinigen
7. **A2**: Prüfen ob PAT-Token in git reflog/history geleakt ist

### Phase 4: Infrastruktur-Verbesserung
8. **F1+F2**: deployment-mcp SSH-Tool debuggen/fixen
9. **F3**: MCP orchestrator CWD-Einschränkung evaluieren
10. **C1+C2**: ADR-021 mit tatsächlichen Deploy-Strategien aktualisieren

---

## Geschätzte Aufwände

| Phase | Aufwand | Risiko |
|-------|---------|--------|
| Phase 1 | 10 min | Niedrig |
| Phase 2 | 30 min | Mittel (Prod-Server) |
| Phase 3 | 15 min | Niedrig |
| Phase 4 | 60 min | Mittel |
| **Gesamt** | **~2h** | |
