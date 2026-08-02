# Platform — Repo Context

> Meta-Repo des IIL-Ökosystems: ADRs, Workflows, Governance, `shared_contracts`.
> **Kein App-Code, kein Django** — der lebt in den Hub-Repos (dev-hub, risk-hub, …).

## ⚠️ Dieses Repo ist ÖFFENTLICH

`achimdehnert/platform` ist **public** (geprüft 2026-08-02). `dev-hub` und die Hub-Repos sind
privat — **platform ist die Ausnahme**, und genau darin liegt die Falle.

**Jeder Commit hierher ist eine Veröffentlichung.** Keine Personendaten, keine Zugangsdaten,
keine Infrastruktur-Details, die nicht draußen stehen sollen. Testdaten aus echten Quellen
(Postfach, Prod-Datenbank, Kundendokumente) **immer** entpersonalisieren — und die Bereinigung
mit einer Kontrollprobe belegen (roh N Treffer → bereinigt 0), nicht nur behaupten.

**Warum das hier steht:** Am 2026-08-02 wurde ein `--admin`-Bypass mit der Begründung „wegen
privat" freigegeben, und beinahe wäre eine Test-Fixture mit Namen Studierender und einer
Anschrift hier gelandet ([#1670](https://github.com/achimdehnert/platform/pull/1670)). Falsch
war die Prämisse, nicht die Sorgfalt. Ob das so bleibt, behandelt
[`KONZ-platform-039`](docs/konzepte/KONZ-platform-039-sichtbarkeit-platform-repo.md) — bis zu
einer Entscheidung gilt: **öffentlich**.

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
- **Konventionen** (ADR-Nummern, Commit-Scopes, Secrets, …): siehe `CORE_CONTEXT.md` §Konventionen.
