# Platform — Repo Context

> Meta-Repo des IIL-Ökosystems: ADRs, Workflows, Governance, `shared_contracts`.
> **Kein App-Code, kein Django** — der lebt in den Hub-Repos (dev-hub, risk-hub, …).

## SSoT: zuerst `CORE_CONTEXT.md` lesen

Die maßgebliche Repo-Doku ist **[`CORE_CONTEXT.md`](CORE_CONTEXT.md)** — Rolle,
Verzeichnis-Karte, Tech-Stack, **Konventionen**, Pflicht-Lesestoff und Infra
stehen dort und werden **nur dort** gepflegt. Diese Datei dupliziert das nicht,
sondern wird von Claude Code automatisch geladen und zeigt auf die SSoT.

Vor dem ersten Keystroke zusätzlich: `AGENT_HANDOVER.md` (aktueller Stand).
Drift-Episoden & Lessons leben im **CC-Memory-Index** (auto-geladen) + pgvector —
**nicht** mehr in `AGENT_MEMORY.md` (Cascade-Ära, deprecated, alle Einträge expired).

## Precedence (höchste gewinnt)

1. **dieses `CLAUDE.md` + `CORE_CONTEXT.md`** (repo-spezifisch)
2. **Orchestrator MCP** (`orchestrator.iil.pet`) — Live-Shared-Memory, wo geladen
3. **`~/.claude/policies/<topic>.md`** — file-basierte Defaults (immer geladen)

## Auto-Load-Guardrails (Details → `CORE_CONTEXT.md`)

- **Brauche ich ein ADR?** → `~/.claude/policies/adr-threshold.md` ist maßgeblich.
  Reine Ergänzung nach bestehendem Muster = **kein** ADR (CHANGELOG/PR genügt);
  ADR nur bei echter Architektur-Entscheidung. Nicht überschießend gaten.
- **ADR-Nummern**: zur Merge-Zeit allokiert (ADR-228, amends ADR-065), monoton,
  nie wiederverwendet. Bestand live: `ls docs/adr/ADR-*.md | wc -l`.
- **Commits in `docs/adr/`**: scope = `adr`, nicht `docs`.
- **Secrets** nie ins Repo — immer `~/.secrets/`.
