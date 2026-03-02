---
description: Sync WSL repo(s) with GitHub remote — löst den "overwritten by merge" Fehler dauerhaft
---

# Sync Repo Workflow

**Trigger:** Immer wenn `git pull` mit "Your local changes would be overwritten" oder "untracked files" scheitert.

**Problem:** Cascade schreibt Dateien sowohl lokal (filesystem MCP) als auch direkt auf GitHub (GitHub MCP). Das lokale Repo divergiert dabei — lokale Dateien existieren bereits wenn das Remote sie hinzufügt.

**Lösung:** `scripts/sync-repo.sh` committet wertvolle lokale Dateien automatisch, stasht den Rest, und pullt dann sauber.

---

## Step 1: Einzelnes Repo syncen (Normalfall)

Für `platform`:

// turbo
```bash
cd ~/github/platform && bash scripts/sync-repo.sh
```

Für ein anderes Repo:

```bash
bash ~/github/platform/scripts/sync-repo.sh ~/github/bfagent
```

## Step 2: Alle Repos auf einmal syncen

```bash
bash ~/github/platform/scripts/sync-repo.sh --all
```

Synct: `platform`, `bfagent`, `travel-beat`, `weltenhub`, `risk-hub`, `pptx-hub`, `mcp-hub`, `aifw`, `promptfw`, `authoringfw`

## Step 3: Status prüfen

```bash
cd ~/github/platform && git log --oneline -5
```

---

## Was das Script macht (Sicherheitsgarantien)

- **Nie `--hard` reset** — keine Datenverluste
- **Nie force-push** — Remote bleibt unberührt
- **Auto-commit** für: `windsurf-rules/`, `scripts/`, `docs/adr/`, `.windsurf/workflows/`
- **Stash** für alles andere (`.env`, temp files, etc.)
- **Stash-restore** nach dem Pull — lokale Arbeit bleibt erhalten
- **Rebase-Fallback** auf merge wenn rebase scheitert

## Wann diesen Workflow verwenden

- Nach jeder Cascade-Session die ADRs oder windsurf-rules geschrieben hat
- Bevor eine neue Cascade-Session startet (als Teil von `/agent-session-start`)
- Wenn `git pull` mit obigem Fehler abbricht

## Integration in agent-session-start

Empfehlung: Am Anfang jeder Session einmalig ausführen:

```bash
bash ~/github/platform/scripts/sync-repo.sh
```

Dauer: ~5 Sekunden pro Repo.
