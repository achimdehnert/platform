# Policy: Claude-Code Skills (Slash-Commands)

**Trigger words:** skill, slash command, /command, workflow, cc-skill

## Was ist eine CC-Skill?

Markdown-Workflow mit YAML-Frontmatter, im Verzeichnis `platform-workflows/.windsurf/workflows/`. Verfügbar als Slash-Command in **beiden** Tools:
- Claude Code via Symlink `~/.claude/commands/` → `~/github/platform-workflows/.windsurf/workflows/`
- Windsurf Cascade nativ

Abgrenzung zu anderen Konzepten:
- **Django Platform-Agents** (`dev-hub/apps/<agent>/`, siehe `platform-agents.md`) — Headless, scheduled, lange Laufzeit
- **CC-Sub-Agents** (`~/.claude/agents/`) — Claude-only, isolierter Context, kein Cross-Tool

## Wann eine neue Skill bauen?

CC-Skill ist die **Default-Antwort** bei:
- Wiederkehrender Workflow >3× pro Woche manuell ausgeführt
- Kombination aus 2+ MCP-Calls + Output-Aggregation
- Bedarf für Cross-Tool-Verfügbarkeit (CC + Windsurf)
- Read-only-Analyse oder Reporting

**Nicht** als Skill:
- Single-MCP-Wrapper (direkter MCP-Call genügt)
- Einmaliges Skript (Bash-Snippet in PR-Beschreibung)
- Anything-Write ohne klare Gates (Skill darf write, aber muss Gate explizit machen)

## Pflicht-Strukturelemente

```markdown
---
description: <1-line, action-orientiert, ≤120 Zeichen>
mode: read-only | write
---

# /skill-name — <Tagline>

> **Wann:** ...
> **Wann NICHT:** Verweis auf abgrenzende Skills

## Verwendung
\`\`\`
/skill-name <args>
\`\`\`

## Step 0: Repo-Kontext aus project-facts.md
... (NIEMALS hardcoden)

## Step N: <Schritte>

## Output-Format
\`\`\`
<Schema des Outputs>
\`\`\`

## Anti-Patterns
- ❌ ...

## Changelog
- YYYY-MM-DD: ...
```

## MCP-Signaturen — Pflicht-Verifikation

**Vor Commit:** Jeden im Skill genannten MCP-Call mit dem aktuellen Schema verifizieren. Wrong-Signature-Bugs sind häufig und CI-relevant.

Verifikations-Optionen:
1. `ToolSearch` mit `select:<mcp-tool-name>` und Argument-Schema gegen Skill abgleichen
2. Dry-Run mit echtem MCP-Call im Dogfood-Test
3. (Future) CI-Smoke-Test gegen Schema-Snapshot

## Read-Only Default

Skills sind by-default **read-only**. Write-Modus erfordert:
- Explizites `mode: write` im Frontmatter
- Anti-Pattern-Sektion mit konkreten "darf NICHT" Aufzählungen
- Idempotenz-Garantie ODER explizites "non-idempotent — confirm before re-run"

## Hardcoding-Verbot

**NIEMALS** in Skills:
- Repo-Pfade (`~/github/platform/docs/adr/`)
- MCP-Prefixes (`mcp2_`)
- Owner/Org-Namen (`achimdehnert`)
- Server-IPs

Quelle: **project-facts.md** (always_on rule im Ziel-Repo). Skill liest Werte zur Laufzeit aus.

## 🌀-Memory-Zitate

Skills die auf Drift-Lehren verweisen sollen **echte Memory-IDs** zitieren, nicht erfundene Namespaces. Beispiel:
- ✅ `agent_memory_search(query="ADR-141 vs 179 canonical numbers")` (semantic)
- ❌ `agent_memory_search(query="drift:adr-canonical-numbers")` (kein realer Namespace)

Drift-Lehren leben in lokaler CC-Memory bis sie via `agent_memory_upsert` in Orchestrator promoted werden. Skill darf beide Quellen ansprechen, aber muss den **Discovery-Pfad** beschreiben (CC-Memory zuerst, Fallback Orchestrator).

## Pflicht-Review-Gate

PR der eine neue Skill enthält oder eine bestehende ändert:
1. Mindestens **1 Dogfood-Test** im PR-Body dokumentiert (Tool-Output zitiert)
2. MCP-Signaturen verifiziert (siehe oben)
3. Anti-Patterns-Sektion vollständig
4. Output-Format als Code-Block exemplifiziert
5. CHANGELOG-Eintrag in der Skill-Datei

## Verteilung

`~/.claude/commands` Symlink ist **single-machine**. Cross-Machine-Sync für CC-Sessions auf Dev-Server/Prod:
- Plan: zukünftig Plugin-basiertes Distribution (Backlog)
- Aktuell: `git pull` in `~/github/platform-workflows` auf jeder Maschine

## Changelog

- 2026-05-15: Initial. Geschrieben nach Dogfood-Findings der ersten 2 CC-Skills (`/adr-curator`, `/adr-challenger`, PR #168). Schließt Policy-Lücke die `platform-agents.md` offen ließ.
- 2026-05-15: Pushed to orchestrator memory (`entry_key: policy:claude-skills`).
