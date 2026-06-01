---
description: Zeigt die 3 sinnvollsten nächsten Schritte für den aktuellen Repo (mit Tier-Tag)
---

# /next — Schnell-Orientierung

**Zweck**: in 3 Zeilen sagen, was als nächstes in diesem Repo sinnvoll ist —
mit Modell-Tier-Tag (`[Sonnet]`/`[/fast]`/`[Opus]`). Funktioniert in **jedem**
Repo, auch wenn dort noch keine `NEXT.md` existiert (Self-Healing).

## Mechanik

1. **Selbst-Heilung**: `claude-next-sync` ausführen, das aktualisiert `NEXT.md`
   aus `AGENT_HANDOVER.md` (falls vorhanden) oder aus git log (Fallback).
   Wenn `NEXT.md` aktuell ist (jünger als Source und < 14 Tage alt), ist es
   ein no-op (~0,1 s).

2. **Tier-Mismatch-Warnung**: falls eines der Top-Items mit `[Opus]` markiert
   ist und du **nicht** in einer Opus-Session bist (du siehst das im
   System-Reminder: „You are powered by claude-sonnet-…" / „claude-haiku-…"
   / „claude-opus-4-7"), gib eine klare Vorab-Warnung:

   ```
   ⚠️ Top-Item ist Tier-4 (Opus-Klasse). Aktuelle Session: <model>.
      Empfehlung: `/model claude-opus-4-7` vor Start.
   ```

3. **Output-Format**:

   ```
   📋 NEXT · <repo>   (sync: 2026-05-20 11:30, fresh)

   1. [Sonnet] Slice 1 — Cockpit echt
   2. [/fast]  Platform-Registry committen
   3. [Opus]   Hosting-ADR Sozialdaten

   → Details: cat AGENT_HANDOVER.md
   → Roster aller Repos: cat ~/.claude/state/next-roster.md
   ```

## Schritte

```bash
# 1. Self-Heal (silent if fresh)
/home/devuser/.claude/bin/claude-next-sync --repo "$(pwd)" 2>/dev/null

# 2. NEXT.md ausgeben
[ -f NEXT.md ] && cat NEXT.md || echo "kein NEXT.md — Skript-Fallback griff nicht"
```

## Was der Skill NICHT tut

- Keine Bestätigungs-Frage. Output → Ende.
- Keine Heavy-Tool-Aufrufe (Web-Fetch, Orchestrator-MCP) — läuft auch in Haiku/Fast.
- Kein Ritual. Wenn du tiefere Übersicht willst: `cat AGENT_HANDOVER.md`.

## Wann den Bootstrap neu laufen lassen

Bei neuen Repos oder wenn du den globalen Roster aktualisieren willst:

```bash
/home/devuser/.claude/bin/claude-next-init
cat ~/.claude/state/next-roster.md
```
