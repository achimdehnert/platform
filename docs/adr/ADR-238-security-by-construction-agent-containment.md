---
status: accepted
implementation_status: partial
implementation_evidence:
  - "Erste Scheibe gemergt+deployed: mcp-hub#99 (Shell-Injection: shlex.quote + Metachar-Reject), #100 (Bearer-Auth /sse+/messages — unauth→401 live verifiziert), #102 (Zwei-Key-Split /run vs /sse); MCP-Key rotiert 2026-06-06 (alter exponierter Key → /sse 403, wertlos)"
  - "Befund-Grundlage: Tiefen-Security-Review 2026-06-06 (code-read + Prod-Probe: GET /sse → 200 ohne Bearer; nginx-Access-Log: kein Ausnutzungs-Hinweis)"
  - "Externe Cross-Provider-Zweitmeinung via /adr-handoff-extern eingearbeitet (Step-5-Gate, 17 [valid]-RECs)"
decision_date: 2026-06-06
deciders: Achim Dehnert
domains: [security, governance, agents, ci-cd]
scope: platform
related: [ADR-070, ADR-081, ADR-186, ADR-015, ADR-210, ADR-233, ADR-234, ADR-235]
tags: [security, by-construction, agent-autonomy, containment, gate, untrusted-insider, kill-gate, prevention]
---

# ADR-238: Security-by-Construction als Konstruktionsprinzip — Containment symmetrisch zu Acceleration

| Attribut       | Wert                                                              |
|----------------|-------------------------------------------------------------------|
| **Status**     | Accepted                                                          |
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

- Deterministisch/strukturell, **kein LLM** für die Gating-Entscheidung (P13); neue Regeln starten als SUGGEST, validiert gegen ≥5 reale Läufe, 0 FP — **plus Negativ-Tests pro Risk-Klasse** (fehlendes/abgelaufenes/falsch-scoped Token, untrusted Evidence, unregistrierter Pfad müssen blocken; ein reiner Positivpfad beweist weder Coverage noch korrekte Blocks). [REC-10]
- Der Gate sitzt **unmittelbar vor der irreversiblen Aktion** (P2), nicht „irgendwo in CI". **Irreversibel ist nicht nur Mutation:** Exfiltration, Secret-/Key-Reads und Identity-Aktionen sind ebenfalls irreversibel und hinterlassen *keinen* File-Diff — gleichrangig zu gaten. [REC-4]
- Reuse vor Parallel-Enforcement: `headless`-Pfad (`bridge.py`) ist gehärtet (Allowlist `OWN_CODE`, `isolated_env`+`assert_no_secrets_leaked`, disposable Worktree, scope-lock). **Caveat:** der scope-lock prüft Diffs *post-run* — Reuse erfüllt P2 nur, wenn für jede irreversible Aktion ein Gate *vor* der Aktion existiert (Rollout weist das pro Aktion nach). [REC-6]
- Decision ≠ Rollout (P7): dieser ADR ratifiziert das *Prinzip*; Durchsetzung folgt gated. **Status-Granularität:** „Prinzip akzeptiert" ≠ „SUGGEST implementiert" ≠ „ENFORCE wirksam" — separat ausgewiesen. [REC-15]
- **Cross-Org (ttz-lif/meiki-lra):** platform-Settings erzwingen dort nichts; Outputs/Metriken markieren das als *Konvention*, nicht als strukturelle Sicherheit. [REC-16]

## 2. Entscheidung

**Security-by-Construction wird ein benanntes Konstruktionsprinzip: jeder autonome Agent-Mutating-Pfad muss durch einen *in Code erzwungenen* Gate, der unmittelbar vor der irreversiblen Aktion sitzt. Containment wird symmetrisch zu Acceleration implementiert — eine Beschleunigungs-Fähigkeit ohne ihren Containment-Gate gilt als unfertig, nicht als „live".**

Konkret:
- **C1 — De-privilegieren (P1):** Der Agent-Prozess hält **keine** standing Credentials — und zwar *alle*, nicht nur GitHub-Schreibrechte: SSH-Key, GitHub-App-PEM, breiter PAT, **LLM-Keys**, DB-/Memory-Zugänge, Runner-Credentials. Privilegierte Aktionen minten kurzlebige, scope-minimale Tokens über einen **separaten Broker** (erweitert das `gh-app-token.sh`-Muster). **Harte Accept-Bedingung (nicht nur Risiko-Notiz):** der Agent-Prozess darf weder App-PEM noch breiten PAT noch direkte Token-Minting-Fähigkeit besitzen — sonst signiert der Agent seine eigene Freigabe. [REC-1, REC-13]
- **C2 — Ein erzwungener Choke-Point (P2):** Mutating-/Sensitive-Aktionen laufen entweder durch den gehärteten `headless`-Pfad **oder** durch einen **unskippbaren zentralen Dispatcher** (`assert_capability`) — rohe Mutations-/Sensitive-Read-Primitive sind aus dem Agentenpfad **nicht direkt importierbar/aufrufbar**, nicht bloß „erste Zeile" (sonst wieder Konvention). Deterministischer `VERB_RISK[(tool,action)]`-Lookup über eine **kanonische, generierte** Tabelle (drift-checked, dieselbe Matrix für headless + MCP + statischen Scan; P4/ADR-015). Risk-Klassen: `READ_ONLY · MUTATING_REVERSIBLE · IRREVERSIBLE · SENSITIVE_READ · IDENTITY · FANOUT` — default-deny ohne gültiges, von einem **separaten Trust-Domain** signiertes Capability-Token (Felder: issuer/run_id/caller/tool/action/scope/ttl/max_uses/risk_class/evidence_digest — Spec im Rollout). **Inventory-Regel:** jeder autonome Mutating-/Sensitive-Read-Pfad muss registriert + klassifiziert + getestet + vom Scan erfasst sein; **unbekannte Pfade = default-deny**. Bevorzugt: direkte Mutating-Tools entfernen und durch `headless` routen. [REC-2, REC-3, REC-4, REC-5, REC-14]
- **C3 — Capability-relatives Gating (P13):** „Fähigeres Modell ⇒ mehr Enforcement" wird deterministisch als „**externes Run-Profil** ⇒ kleinerer Scope" (Repos/Pfade/TTL/Permissions/Fanout) — der Scope wird **extern gesetzt**, nicht vom agent-wählbaren Modell/Backend abgeleitet (sonst manipulierbar). Config-Lookup, kein LLM-Urteil. [REC-7]
- **C4 — Provenance-typed Context (P12 auf Input):** `trust_level` + **typed Evidence-Bundle** auf Memory/Policy/Discovery-Rows; pro Risk-Klasse deterministisch definiert, welche Provenance-Stufe + Evidence-Digests eine Aktion rechtfertigen. Eine IRREVERSIBLE/FANOUT-Aktion mit nur `trust_level=0`-Kontext wird in Code verweigert. **Anti-Trust-Laundering:** transformierte/kopierte untrusted Inhalte behalten ihre Ursprungs-Provenance, bis ein Mensch *genau diese Inhaltsänderung* bewusst als Quelle akzeptiert. `trust_level=2` = human-PR-merged, definiert über Reviewer-Identität/Zeit/diffbaren Inhalt/Hash/explizite Nutzung-als-Agent-Quelle (nicht bloß „gemergt"). [REC-8, REC-9, REC-19]
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

- **Invariante:** Kein autonomer Mutating-/Sensitive-Pfad ohne erzwungenen Gate auf dem Call-Path. Messbar: `ungated_mutating_paths` (statischer Scan: registriert? gegated?) + `unauthorized_tool_invocation_attempts`, **nach Severity getrennt** (`test_block`/`expected_deny`/`prod_policy_violation`/`suspected_compromise`) — sonst verwechselt der Tripwire einen erfolgreichen Block mit einem Notfall (Self-DoS). [REC-11]
- **Kill-Gate (review_by 2026-09-06):** operationalisiert — Erfolg = `ungated_mutating_paths == 0` **und** lauffähiger Enforce-Modus **und** Broker ohne Agent-Selbstsignierung **und** Negativ-Test-Matrix grün **und** headless-only-Fallback getestet. Verfehlt ⇒ Status Deprecated; **der Fallback ist ein technischer Aktuator** (Feature-Flag/Deployment-Mode entfernt direkte Mutating-Tools, erzwingt headless-only) — eine *dokumentierte Warnung* ist kein P1-Aktuator, höchstens Begleitmaßnahme. `suspected_compromise > 0 / 30d` ⇒ Autonomie-Pause. [REC-12, REC-20]

## 5. Rollout (Decision ≠ Rollout, P7)

`assert_capability` startet **log-only/SUGGEST**, validiert über reale Läufe (≥5/0-FP) **und** eine **Negativ-Test-Matrix** (fehlendes/abgelaufenes/falsch-scoped Token, falsche Action, untrusted Evidence, unregistrierter Pfad → müssen blocken), dann Flip auf enforce. Scheiben in Reihenfolge des Blast-Radius (P2):
1. Injection schließen (mcp-hub#99 ✅) + unauth Control-Plane (mcp-hub#100 ✅) — *Voraussetzung*: ein Gate vor injizierbarer Shell ist wertlos.
2. C1 de-privilegieren: separater Broker, **alle** standing Creds (SSH/PEM/PAT/LLM/DB/Runner) raus aus dem Agent-Prozess.
3. C4 `trust_level` + Evidence-Bundle (additive pgvector-Migration).
4. C2 unskippbarer Dispatcher + Pfad-Inventory; **pro irreversibler headless-Aktion nachweisen, dass sie *vor* der Aktion gegated ist** (nicht nur post-run scope-lock). [REC-6]
5. C5 Distributor-Two-Key (ADR-230-Amend).
6. **Direkte MCP-Mutating-Tools sind nur Übergangspfad mit Sunset** — Zielzustand: read-only MCP + headless/PR-basierte Mutation. [REC-17]
**Re-Evaluate-Trigger:** sobald >~3 Tools / Risk-Klassen / Evidence-Regeln gepflegt werden müssen, eine echte Policy-Engine (OPA/Cedar) prüfen statt handgepflegter Lookups. [REC-18]
**Zielbild höherer Autonomieklassen:** disposable OS-/Runtime-Isolation pro Lauf (minimale Netz-/FS-Freigabe, Zugriff nur über Broker/Gateways) — nicht erste Scheibe, aber der saubere Endzustand. [Out-of-Box A4]

## 6. Konsequenzen

**Positiv:** Der gefährlichste Pfad wird by-construction statt by-convention; Blast-Radius eines kompromittierten/injizierten Agenten sinkt von „Org-Admin" auf „eine gemintete Scope-TTL"; die Vision skaliert *sicher* mit Modellfähigkeit. **Negativ/akzeptiert:** Reibung für autonome Läufe (kurzlebige Tokens, Quarantine-Verweigerungen), initialer Bau-Aufwand, SUGGEST→enforce-Latenz. **Risiko:** Capability-Token-Gate ist nur wirksam mit *separatem* Signer (sonst signiert der Agent seine eigene Freigabe = die heutige `auto_approve`-Falle) — C2-enforce ist deshalb an C1/Broker gekoppelt, nicht eigenständig „minimal".

## 7. Externer Review (Provenienz)

Cross-Provider-Zweitmeinung via `/adr-handoff-extern` (Briefing `~/shared/adr-handoff-ADR-486-2026-06-06.md`). Befund: *überarbeiten* — Richtung richtig, aber der separierte Capability-Signer, die erweiterte Risk-Taxonomie (SENSITIVE_READ/IDENTITY/FANOUT) und der unskippbare Dispatcher mussten von „Risiko/erste Zeile" zu **harten Bedingungen** werden. Eingearbeitet via Rückfluss-Gate (nur `[valid]`-getaggte Befunde, als Entscheidung mit eigener Begründung): **REC-1/13** (C1, alle Creds + Broker-Bedingung) · **REC-3/14** (C2, unskippbarer Dispatcher + Inventory) · **REC-4** (Risk-Taxonomie) · **REC-2/5** (Token-Spec + kanonische VERB_RISK) · **REC-6** (headless pre-action-Nachweis) · **REC-7** (externes Run-Profil) · **REC-8/9/19** (C4 Evidence-Bundle + Anti-Laundering + trust_level=2-Definition) · **REC-10** (Negativ-Test-Matrix) · **REC-11** (Severity-Split-Metrik) · **REC-12** (technischer Kill-Gate-Aktuator) · **REC-15** (Status-Granularität) · **REC-16** (Cross-Org-Markierung) · **REC-17** (MCP-Tools-Sunset) · **REC-18** (OPA-Re-Evaluate-Trigger) · **REC-20** (operationalisierte Kill-Gate-Kriterien). Kein Befund war `[missversteht-Kontext]`/`[out-of-scope]`.

## 8. Glossar

Für Fachpersonal ohne IT-Hintergrund — die zentralen Begriffe in einfacher Sprache:

- **Agent (autonomer):** ein KI-Programm, das selbstständig Aufgaben am Code/an den Systemen ausführt (Dateien ändern, Befehle ausführen, deployen) — der „Optimierer" der Vision.
- **Broker:** ein eigener, abgetrennter Dienst, der Zugriffs-Berechtigungen kurzfristig ausstellt — der Agent bekommt nie den Dauer-Schlüssel selbst, sondern bittet den Broker pro Aktion um einen befristeten.
- **Capability-Token:** ein digitaler, kurzlebiger „Erlaubnisschein" für genau eine Aktion (welches Tool, welche Aktion, welcher Geltungsbereich, wie lange gültig).
- **Choke-Point / Dispatcher:** die eine, **nicht umgehbare** Stelle im Code, durch die jede gefährliche Aktion muss — wie eine einzige bewachte Tür statt vieler unbewachter Hintereingänge.
- **Containment vs. Acceleration:** Beschleunigung = der Agent kann viel und schnell; Containment = die Schadensbegrenzung, falls er kompromittiert wird. Dieser ADR fordert: beides muss gleich stark gebaut sein.
- **Gate:** eine Prüfung **unmittelbar vor** einer Aktion, die diese erlaubt oder blockiert.
- **Irreversibel:** nicht rückgängig zu machen — z. B. ein veröffentlichtes Geheimnis (Exfiltration) oder eine Identitäts-Änderung; im Gegensatz zu einer Datei-Änderung, die man zurückrollen kann.
- **Prompt-Injection:** ein Angriff, bei dem manipulierter Text (z. B. in einem Issue) den Agenten zu unerwünschten Handlungen verleitet.
- **Provenance / trust_level:** die belegte Herkunft einer Information; `trust_level` markiert, ob ein vom Agenten gelesener Inhalt vertrauenswürdig (z. B. von einem Menschen geprüft) oder ungeprüft ist.
- **SSE (Server-Sent Events):** der Verbindungskanal, über den der MCP-Server seine Werkzeuge bereitstellt.
- **Standing Credential:** ein dauerhaft gültiger Zugangsschlüssel (SSH-Key, Token, App-Zertifikat) — gefährlich, weil ein Diebstahl unbegrenzt nutzbar ist; Gegenmodell sind kurzlebige Tokens.
