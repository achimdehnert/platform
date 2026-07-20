---
concept_id: KONZ-platform-020
title: Code-ausführendes Headless-Backend im Orchestrator — ADR-186 von LLM-only zu command-fähigen Agenten in Prod aktivieren
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: [ADR-186, ADR-045]
adr_threshold: "ADR-186-Amendment ODER neuer ADR — neue Security-Perimeter (code-exec-Agent + Creds in Prod), Cross-Repo-Enforcement-Boundary, laufender Spend, reversibel nur durch Backend-Entfernung"
review_by: 2026-07-27
kill_criteria: "Nicht deployen, wenn bis 2026-09-01 NICHT alle erfüllt: (a) mindestens EIN Consumer zeigt in einem Pilot einen konkreten Mehrwert aus Command-Ausführung/Code-Edits, den LLM-only (aifw) NICHT liefert (z.B. quality_sweep mit realem Fix, test-generation) — belegt durch einen gemergten Agent-PR; (b) Security-Review bestätigt: ephemerer Worktree + ScopeLock allow/deny + Budget-Cap greifen für ein code-exec-Backend (Fault-Injection: Scope-Verletzung wird verworfen, Budget-Überschreitung stoppt); (c) erzwungener Dry-Run-in-CI beweist Token/Secret/Netz-Verdrahtung (Gate autonomous-no-human-review). Bei Nichterfüllung: LLM-only bleibt, Konzept sunset."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "mcp-hub/orchestrator_mcp/headless/adapters/aifw_adapter.py", commit_or_pr: "Docstring Z.1 'Pure Python, no CLI subprocess' — LLM-only, keine Shell", opened_in_session: true}
  - {claim_id: C2, source_path: "mcp-hub/orchestrator_mcp/headless/mcp_tool.py", commit_or_pr: "_resolve_adapter: 'claude'→ClaudeCodeAdapter (CLI); Kommentar 'orchestrator container has no Claude-Code CLI'", opened_in_session: true}
  - {claim_id: C3, source_path: "dev-hub#135", commit_or_pr: "Live-Prod-Test 2026-07-13: strategy_research-Lauf scheiterte gestaffelt Netz→Repo-Checkout→'CLI backend claude not available'", opened_in_session: true}
  - {claim_id: C4, source_path: "dev-hub/apps/quality_agent/tasks.py", commit_or_pr: "nutzt backend='aifw' (LLM-only) — quality_sweep macht daher KEINE realen Edits, nur Analyse", opened_in_session: true}
  - {claim_id: C5, source_path: "mcp-hub/orchestrator_mcp/headless/services/scope_lock.py + cost_tracker.py", commit_or_pr: "Sandbox-Bausteine existieren (allow/deny-Globs, atomarer Budget-Reserve) — für ein exec-Backend nutzbar", opened_in_session: true}
created: 2026-07-13
---

# KONZ-platform-020 — Code-ausführendes Headless-Backend im Orchestrator

> **Tier T3.** Begründung (harte Auto-Eskalations-Trigger): neue **Security-Perimeter**
> (ein command-ausführender Agent mit Prod-Git-Zugriff + LLM-Credentials im
> Orchestrator-Container), **Cross-Repo**-Wirkung (alle Headless-Consumer), **laufender
> Spend** (Agent-Läufe > Einzel-LLM-Call), und ein **Reversal-Stake** (ADR-186 versprach
> command-fähige Agenten; heute ist nur LLM-only deployt).

## 1. Problem

ADR-186 („Headless Agent-Coding Pipeline") wurde für **autonome, code-ausführende**
Agenten entworfen: `quality_sweep` mit realen Fixes, `test_generation`, `refactoring`.
In Prod ist aber **nur** der `AifwHeadlessAdapter` deployt — laut Docstring *„Pure
Python, no CLI subprocess"* (C1): reine LLM-Analyse mit SEARCH/REPLACE, **keine
Shell-Ausführung**. Der `claude`-Backend (ClaudeCodeAdapter) bräuchte die Claude-Code-CLI
im Container, die dort nicht existiert (C2).

**Konsequenz:** Die ADR-186-Pipeline kann in Prod keine Commands ausführen und keine
echten Code-Edits machen. Aufgedeckt am 2026-07-13, als der erste echte Lauf
(trading-hub strategy_research) gestaffelt scheiterte — Netz, dann Repo-Checkout, dann
`CLI backend claude not available` (C3, dev-hub#135). Auch `quality_agent` ist betroffen:
es nutzt `backend="aifw"` und macht daher nur Analyse, **keine** realen Fixes (C4).

## 2. Kontext & was schon da ist

Die **Sandbox-Bausteine existieren bereits** (C5): ephemerer Worktree pro Lauf,
`ScopeLock` mit allow/deny-Globs (read-only bis eng-erlaubt), atomarer `CostTracker`
mit Budget-Cap pro Kategorie. Was fehlt, ist ausschließlich ein **ausführendes Backend**
im Container + dessen Credentials.

**Wichtig — Abgrenzung:** Für den ursprünglichen Auslöser (strategy_research-Report auf
Paper-Daten) ist dieses Konzept **nicht** nötig. Der ist über einen in-house
trading-hub-Task gelöst (Variante A2, trading-hub PR #132): deterministisch Metriken
rechnen + `aifw` fasst zusammen — kein command-ausführender Agent. B (dieses Konzept)
rechtfertigt sich also **nicht** aus strategy_research, sondern nur aus dem generellen
Bedarf an code-ausführender Autonomie.

## 3. Optionen (right-sized)

| # | Option | Fähigkeit | Kosten | Security | Reversibel |
|---|--------|-----------|--------|----------|------------|
| 1 | **Status quo (LLM-only aifw)** | nur Analyse/Vorschläge; Edits müssen Menschen machen | minimal | minimal | — |
| 2 | **Claude-Code-CLI-Backend** | volle Command-Ausführung + Edits | höher (Agent-Läufe) | erhöht (CLI+Creds+Git in Prod) | ja (Backend entfernen) |
| 3 | **aider-Backend** | SEARCH/REPLACE-Edits, leichter als Claude-CLI | mittel | mittel | ja |

## 4. Trade-offs

- **Security-Perimeter:** Ein code-ausführender Agent mit Prod-Git-Zugriff + LLM-Creds
  ist reale Angriffsfläche. ADR-186 adressiert das via ephemeren Worktree +
  ScopeLock-Post-Check (Verletzung → Worktree verworfen, Haupt-Repo unberührt) +
  Budget-Cap. Diese Kette muss für ein exec-Backend **fault-injection-getestet** sein
  (Kill-Gate b), nicht nur „vorhanden".
- **Credentials (ADR-045):** LLM-API-Key im Orchestrator-Container — als `SecretStr` /
  `/run/secrets`, nicht plaintext. Neuer Secret-Scope.
- **Spend:** Agent-Läufe kosten mehr als ein Einzel-LLM-Call; `CostTracker`/`Budget`
  aus ADR-186 gaten das bereits pro Kategorie — Budgets müssen realistisch gesetzt und
  überwacht werden.
- **Reversibilität:** Backend entfernen → zurück zu LLM-only. Kein Daten-/Schema-Lock.

## 5. Empfehlung

**Nicht als Big-Bang.** Option 2 oder 3 als **bewusst gegateter Pilot**, nur wenn echter
Bedarf an code-ausführender Autonomie besteht (quality_agent-Fixes, test-generation) —
nicht spekulativ. Sequenz:

1. **Ein** Low-Risk-Repo, enger ScopeLock (`test_generation`: nur `tests/**`), kleines
   Budget, `backend=aider` (leichter) ODER `claude`.
2. **Erzwungener Dry-Run-in-CI** (Gate `autonomous-no-human-review`), der Token/Secret/
   Netz-Verdrahtung beweist — ein lokaler Lauf zählt nicht.
3. Fault-Injection: bewusste Scope-Verletzung → Worktree verworfen; Budget-Überschreitung
   → Stopp. Beide dokumentiert.
4. Messen (ein gemergter Agent-PR mit echtem Mehrwert), **dann** Ausweitung.

## 6. Kill-Gate

Siehe Frontmatter `kill_criteria`. Kurz: kein belegter Mehrwert aus Command-Ausführung
über LLM-only hinaus **oder** Security/Spend-Review besteht nicht bis 2026-09-01 →
**nicht deployen**, LLM-only bleibt, Konzept sunset.

## 7. Bezug zu ADR-186

Dies ist die **Aktivierung** der ADR-186-Vision (Phase: ausführendes Backend deployen),
die bisher nur konzeptionell existierte. Ergebnis wird ein **ADR-186-Amendment**
(oder eigener ADR, falls die Security-Posture als neue Entscheidung gilt), das die
Backend-Wahl, das Credential-Modell (ADR-045), die Budget-Grenzen und die
Pilot→Rollout-Sequenz festschreibt.

## 8. Lifecycle

- `pipeline_status: idea` → `pilot` erst nach Kill-Gate-Vorbereitung + Owner-Freigabe des
  Spend-/Security-Gates.
- Follow-ups verlinkt: dev-hub#135 (Auslöser + A2-Abgrenzung), trading-hub#132 (A2).
