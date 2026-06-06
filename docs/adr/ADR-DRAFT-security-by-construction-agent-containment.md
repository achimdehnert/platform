---
status: proposed
implementation_status: none
implementation_evidence:
  - "Erste Scheibe als unmerged PRs vorbereitet: mcp-hub#99 (Shell-Injection: shlex.quote + Metachar-Reject, 16 Tests grün), mcp-hub#100 (Bearer-Auth auf /sse + /messages, 8 Tests grün) — beide no-merge, Review/Deploy ausstehend"
  - "Befund-Grundlage: Tiefen-Security-Review 2026-06-06 (code-read + Prod-Probe: GET /sse → 200 ohne Bearer; nginx-Access-Log: kein Ausnutzungs-Hinweis)"
date: 2026-06-06
decision-makers: Achim Dehnert
domains: [security, governance, agents, ci-cd]
scope: platform
relates_to: [ADR-070, ADR-081, ADR-186, ADR-015, ADR-210, ADR-233, ADR-234, ADR-235]
tags: [security, by-construction, agent-autonomy, containment, gate, untrusted-insider, kill-gate, prevention]
---

# ADR-DRAFT: Security-by-Construction als Konstruktionsprinzip — Containment symmetrisch zu Acceleration

| Attribut       | Wert                                                              |
|----------------|-------------------------------------------------------------------|
| **Status**     | Proposed                                                          |
| **Scope**      | platform (org-weit, jeder autonome Agent-Mutating-Pfad)          |
| **Repo**       | platform                                                          |
| **Erstellt**   | 2026-06-06                                                        |
| **Autor**      | Achim Dehnert                                                     |
| **Reviewer**   | /adr-review + /adr-challenger (ausstehend)                        |
| **Supersedes** | –                                                                 |
| **Relates to** | ADR-070 (Progressive Autonomy), ADR-081 (ScopeLock/Snapshot), ADR-186 (Headless-Gates), ADR-015 (LLMGateway/DB-Governance), ADR-210 (Gate am irreversiblen Rand), ADR-233/234 (Clean-State by-construction), ADR-235 (Push-Rand-Posture) |
| **Quelle**     | Tiefen-Security-Review 2026-06-06 (Orchestrator-MCP „untrusted insider") |

---

## 1. Kontext

### 1.1 Ausgangslage

Die Plattform-Vision: ein fähigeres Modell optimiert autonom das Estate (Enterprise/Orgs/Repos/Packages). Das Konstruktionsprinzip-Set, das das trägt, ist exzellent — aber **asymmetrisch angewendet**. Das Master-Prinzip P1 („den schlechten Zustand *unerreichbar* machen, nicht überwachen"; ADR-233/234) gilt rigoros für CI-Grün, Secrets (ADR-235), ADR-Nummern (ADR-065/228), Worktrees (ADR-233). Es gilt **nicht für den mächtigsten Aktor selbst — den autonomen Agenten**.

Der Implementierungs-Gradient belegt die Asymmetrie: Jede **Beschleunigungs**-Maschine ist live (Distributor-Fanout, `headless_run`, Auto-Queues, MCP-Mutating-Tools). Fast jedes **Containment**-Prinzip ist proposed/partial/dormant/advisory: ADR-081 „soft-enforcement", ADR-186 scope-lock prüft Diffs *nach* dem Run, ADR-233 main-tree-guard dormant, ADR-234 R2/R3 `none`, ADR-211 prod-guard dormant. Für eine Optimierungs-Plattform ist das ein Feature; für eine Security-Posture zeigt der Gradient in die falsche Richtung.

Verifiziert (code-read im `mcp-hub/orchestrator_mcp`, Prod-Probe):
- **Control-Plane unauth erreichbar:** `/sse` + `/messages/` (volle Mutating-Tool-Tabelle) ohne `_bearer_error`; Prod-`GET /sse` → 200 + session_id ohne Bearer (`/run` korrekt 401). *Kein* Ausnutzungs-Hinweis im Access-Log.
- **Shell-Injection:** `run_command_safe` (First-Token-Allowlist vor `bash -ic "{cmd}"`, via `;`/`$()` umgehbar), `run_git` (`commit -m "{message}"` ungeescapt).
- **Gates dekorativ:** `check_gate`/`request_approval` advisory JSON, `gate≤1`→`auto_approved`; der gate-ableitende `analyzer.get_gate` ist keyword/LLM-basiert (P13-Verstoß) und **nicht auf dem Call-Path** der Mutating-Tools.
- **Ko-Lokation:** SSH-Key (10 Repos), Admin-App-PEM (50 Repos org-admin), LLM-Keys im selben Prozess-Env auf einem Host → ein Host-Compromise = Org-Admin.

### 1.2 Problem / Lücken

1. **Capability skaliert, Containment nicht.** Die Gates wurden für den heutigen Agenten dimensioniert. Ein fähigeres Modell (a) umgeht advisory-Gates besser, (b) ist ein wertvolleres Prompt-Injection-Ziel, (c) handelt schneller (mehr Blast-Radius/Zeit). Die Prinzipien sind statisch.
2. **Evidenz-Disziplin nur auf Output.** P12 verifiziert rigoros, was Agenten *sagen* — es gibt **keinen** Provenance-Gate auf das, was sie als autoritativ *lesen* (`agent_memory_upsert`, policy-sync, discovery-upsert, Issue-Bodies). Garbage-in ist ungegated.
3. **Reversibilität deckt die billigen 80%, verfehlt die teuren 20%.** Snapshot/scope-lock macht *File-Diffs* reversibel; Exfiltration/Identity-Aktionen (irreversibel, kein Diff) bleiben ungefangen.
4. **SSoT als Verstärker.** P4 (eine SSoT, Rest generiert) + Distributor-Fanout + Agent-Push-auf-`platform` = poison-once-propagate-everywhere.

### 1.3 Constraints

- Deterministisch/strukturell, **kein LLM** für die Gating-Entscheidung (P13); neue Regeln starten als SUGGEST, validiert gegen ≥5 reale Läufe, 0 FP.
- Der Gate sitzt **unmittelbar vor der irreversiblen Aktion** (P2), nicht „irgendwo in CI".
- Reuse vor Parallel-Enforcement: `headless`-Pfad (`bridge.py`) ist bereits gehärtet (Allowlist `OWN_CODE`, `isolated_env`+`assert_no_secrets_leaked`, disposable Worktree, post-run scope-lock) — kein zweites, drift-anfälliges Gate-System (P4).
- Decision ≠ Rollout (P7): dieser ADR ratifiziert das *Prinzip*; Durchsetzung folgt gated dem frischen Zustand pro Pfad.

## 2. Entscheidung

**Security-by-Construction wird ein benanntes Konstruktionsprinzip: jeder autonome Agent-Mutating-Pfad muss durch einen *in Code erzwungenen* Gate, der unmittelbar vor der irreversiblen Aktion sitzt. Containment wird symmetrisch zu Acceleration implementiert — eine Beschleunigungs-Fähigkeit ohne ihren Containment-Gate gilt als unfertig, nicht als „live".**

Konkret:
- **C1 — De-privilegieren (P1):** Der Agent-Prozess hält keine *standing* Credentials. Standing-SSH-Key/breiter-PAT raus; privilegierte Aktionen minten kurzlebige, scope-minimale Tokens via existierendem `gh-app-token.sh`.
- **C2 — Ein erzwungener Choke-Point (P2):** Mutating-Tools laufen entweder durch den gehärteten `headless`-Pfad **oder** durch eine in-code `assert_capability(tool, action, scope_token)`-Funktion als *erste Zeile* vor der Ausführung; deterministischer `VERB_RISK[(tool,action)]`-Lookup, default-deny bei IRREVERSIBLE ohne gültiges Token. Bevorzugt: Mutating-Tools (`run_git`/`run_command_safe`) entfernen und durch `headless` routen (Reuse).
- **C3 — Capability-relatives Gating (P13):** „Fähigeres Modell ⇒ mehr Enforcement" wird deterministisch als „fähigeres/autonomeres Backend ⇒ *kleinerer* gemintete Scope" (weniger Repos, kürzere TTL, read-only-Default) — Config-Lookup, keine LLM-Urteils.
- **C4 — Provenance-typed Context (P12 auf Input):** `trust_level` auf Memory/Policy/Discovery-Rows; eine IRREVERSIBLE-Aktion, deren rechtfertigender Kontext nur `trust_level=0` (untrusted-origin) ist, wird in Code verweigert. `sync-policies`-Runner stempelt `=2` (human-PR-merged).
- **C5 — Estate-Fanout = höchster Gate:** Distributor-Writes via PR statt direct-push, nur aus `trust_level=2`-Quelle, kurzlebiger App-Token statt `PROJECT_PAT` (ADR-230-Amend).

## 3. Betrachtete Alternativen

**Form des Prinzips:**
1. **Eigenständiger ADR (gewählt, Teil A).** Hebt die Asymmetrie zur benannten, prüfbaren Invariante. Risiko „Prinzip ohne Aktuator" → adressiert durch §4 (Pflicht-Invariante).
2. **Nur Amends bestehender ADRs (081/186/070).** Baut auf Bestand, aber verteilt die Lehre; die Asymmetrie-These bleibt unbenannt. → wird zu Rollout-Schritten *unter* diesem ADR.
3. **Nur Policy-Datei `agent-containment.md`.** Leichtgewichtig, aber Policy ≠ Enforcement → reproduziert das Grundproblem. → als Begleit-Policy, nicht als Ersatz.

**Architektur des Gates:**
4. **Zweiter eigener Gate bauen.** → verworfen: P4-Drift-Risiko gegen den bereits gehärteten `headless`-Pfad.
5. **OPA/Cedar Policy-Engine.** Deterministisch, aber Overkill für ~3 Tools + Netz-Dependency auf dem Hot-Path. → aufgeschoben.
6. **Mutating-Tools durch `headless` routen + minimaler Choke-Point (gewählt).** Erbt H1-Isolation + Allowlist + Worktree-Containment; ein Gate-System.

## 4. Containment-Invariante + Kill-Gate (Accept-Bedingung, Teil D)

Dieser ADR ist **nur akzeptiert, wenn er eine messbare Invariante mit Aktuator trägt** (Standard von ADR-233/234 an sich selbst; sonst Sisyphos):

- **Invariante:** Kein autonomer Mutating-Tool-Call ohne erzwungenen Gate auf dem Call-Path. Messbar: Telemetrie `unauthorized_tool_invocation_attempts` (Calls, die `assert_capability` ablehnt) + `ungated_mutating_paths` (statischer Scan: Mutating-Tools ohne Gate-Aufruf).
- **Kill-Gate (review_by 2026-09-06):** `ungated_mutating_paths > 0` nach Rollout-Frist **oder** kein lauffähiger `assert_capability`-Enforce-Modus ⇒ Status → Deprecated, Fallback „dokumentierte Warnung + Headless-only-Mutation". `unauthorized_tool_invocation_attempts / 30d > 0` ⇒ Autonomie-Pause + Review (Tripwire, nicht nur Metrik).

## 5. Rollout (Decision ≠ Rollout, P7)

`assert_capability` startet **log-only/SUGGEST**, validiert 0 False-Blocks über reale autonome Läufe (P13 ≥5/0-FP), dann Flip auf enforce. Scheiben in Reihenfolge des Blast-Radius (P2):
1. Injection schließen (mcp-hub#99) + unauth Control-Plane (mcp-hub#100) — *Voraussetzung*: ein Gate vor injizierbarer Shell ist wertlos.
2. C1 de-privilegieren (`GIT_SSH_COMMAND` raus → `gh-app-token.sh`).
3. C4 `trust_level`-Quarantine (additive pgvector-Migration).
4. C2 `headless`-Routing / `assert_capability` enforce.
5. C5 Distributor-Two-Key (ADR-230-Amend).

## 6. Konsequenzen

**Positiv:** Der gefährlichste Pfad wird by-construction statt by-convention; Blast-Radius eines kompromittierten/injizierten Agenten sinkt von „Org-Admin" auf „eine gemintete Scope-TTL"; die Vision skaliert *sicher* mit Modellfähigkeit. **Negativ/akzeptiert:** Reibung für autonome Läufe (kurzlebige Tokens, Quarantine-Verweigerungen), initialer Bau-Aufwand, SUGGEST→enforce-Latenz. **Risiko:** Capability-Token-Gate ist nur wirksam mit *separatem* Signer (sonst signiert der Agent seine eigene Freigabe = die heutige `auto_approve`-Falle) — C2-enforce ist deshalb an C1/Broker gekoppelt, nicht eigenständig „minimal".
