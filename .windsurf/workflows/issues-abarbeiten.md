# /issues-abarbeiten — Handoff-Resumer

> **Zweck:** Eine dokumentierte NÄCHSTE-AKTIONEN-Liste aus einem Handoff
> sequenziell abarbeiten — *ohne* Re-Exploration, *ohne* PR-Duplikate,
> mit harten Stopp-Gates bei Judgment/Infra.
> **Abgrenzung:** `/process-agent-queue` *füllt + triagiert* eine frische
> `auto`-Queue. `/issues-abarbeiten` *setzt einen bereits geplanten Stand
> fort* — typischer Session-Übergang Opus→Sonnet.
>
> **Argument (optional):** `$ARGUMENTS` = Name der Handoff-Memory bzw.
> Stichwort. Default: jüngsten Handoff finden (Memory mit
> „NÄCHSTE-AKTIONEN" + Orchestrator `queue-run:*` / `agent_handoff`).

---

## Phase 0: Handoff laden (nur lesen)

1. Handoff-Quelle bestimmen:
   - `$ARGUMENTS` gesetzt → diese Memory-Datei lesen
     (`~/.claude/projects/*/memory/<name>.md`).
   - sonst: `MEMORY.md` nach Einträgen mit „Handoff" / „NÄCHSTE-AKTIONEN"
     scannen + Orchestrator `agent_memory_search("handoff next actions")`
     bzw. jüngster `queue-run:<datum>`.
2. Aus dem Handoff extrahieren: **NÄCHSTE-AKTIONEN-Liste** (geordnet),
   **bereits gelieferte Artefakte** (PRs/Issues — NICHT neu erzeugen),
   **Stopp-Punkte** (markierte Judgment-/Infra-Fälle).
3. Wenn kein Handoff auffindbar → **abbrechen**, User fragen welche
   Quelle gemeint ist. Niemals raten und „alle offenen Issues" annehmen.

## Phase 1: Plan materialisieren

- Jede NÄCHSTE-AKTION als Task (`TaskCreate`), in Handoff-Reihenfolge,
  Abhängigkeiten via `addBlockedBy` (z. B. „#10 vor #9").
- Pro Aktion vermerken: Repo, Typ, ob Gate-frei oder Stopp-Punkt.

## Phase 2: Guardrails (vor jeder Aktion)

1. **Kein Duplikat:** vor PR/Issue-Erstellung `gh pr list` / `gh issue
   list` (bzw. GitHub-MCP) prüfen — existiert das Artefakt aus dem
   Handoff bereits, nur fortführen (mergen/rebasen/kommentieren), **nie
   neu anlegen**.
2. **Scope-Lock (ADR-081):** nur was die Aktion/das Issue benennt.
   Nebenbefunde → Folge-Issue, nicht mitfixen.
3. **Branch-Hygiene:** Änderungen nie auf `main`; Branch off
   `origin/main`; bei dirty/fremdem lokalen Checkout **git worktree**
   statt `git checkout`.

## Phase 3: Stopp-Gates (HART — fragen, nicht handeln)

Aktion **nicht** autonom ausführen, sondern User fragen, wenn:
- Deploy / Infra / Server-State / Secrets / SSH (Gate 3+).
- Architektur- oder Tech-Entscheid (z. B. „vendorn vs. PyPI", Test-vs-Code).
- Handoff markiert den Punkt explizit als Stopp / `needs-human` / `blocked`.
- Mehrdeutigkeit, die plausibel-falsch „gelöst" werden könnte.

Alles andere (Merge grüner PRs, Rebase, mechanische Fixes, Folge-Issues
anlegen, Logs/CI lesen) wird ausgeführt.

## Phase 4: Ausführung (sequenziell)

Pro Task: `in_progress` → ausführen → verifizieren (CI/`gh pr checks`,
Tests, Lint je nach Typ) → Issue/PR kommentieren → `completed`.
Bei Fail: 1 Retry, dann Task `in_progress` lassen + Blocker-Task
anlegen + weiter mit nächster unabhängiger Aktion. Nie geschlossene
Artefakte „grün-reden".

## Phase 5: Abschluss + neuer Handoff

- Zusammenfassung: erledigt / gestoppt (Grund) / offen.
- Handoff-Memory **aktualisieren** (gleiche Datei, nicht duplizieren):
  neuer Stand + neue NÄCHSTE-AKTIONEN.
- Orchestrator `agent_memory_upsert` (`entry_type: agent_handoff`,
  key `handoff:<repo-oder-thema>:<datum>`).
- Optional `discord_notify` (Summary), wenn Webhook gesetzt.

---

## Beispiele

```
/issues-abarbeiten
/issues-abarbeiten project_ci_green_program
/issues-abarbeiten queue-run:2026-05-18
```

## Referenzen
- `/process-agent-queue` — frische Queue füllen + triagieren
- `/agentic-coding` v6 — Gate-Modell + Auto-Dispatch-Router
- ADR-081 — Scope-Lock · ADR-154 — Memory-Run-History
