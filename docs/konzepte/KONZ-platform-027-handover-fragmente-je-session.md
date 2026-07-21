---
concept_id: KONZ-platform-027
title: Handover-Fragmente je Session statt geteilter Prosa-Region
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []          # keine Klickdummy/Spec — reine Repo-Prozess-Konvention (ADR-233-Folge)
adr_threshold: kein neuer ADR für den platform-Pilot (Konvention + Tool); ADR-233-Amendment ERST beim Fleet-Rollout (Cross-Repo = T3-Gate, s. Kill-Gate)
review_by: 2026-09-01
kill_criteria: "Wenn bis 2026-09-01 im platform-Pilot (a) weiter ≥1 Same-Day-Multi-Handover-PR-Kollision auftritt, ODER (b) der Assembler ≥1× manuelle Konfliktauflösung braucht, ODER (c) session-start je eine STALE assemblierte Region liest (Fragment neuer als gerendert) → Fragment-Modell gescheitert, zurück auf geteilte Datei + Disziplin (Phase 0a-handover-pr). Exception-Budget: 1 dokumentierte Kollision im Pilotfenster (z.B. Migrations-Race), danach Kill."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "tools/agent-handover/generate.py (AUTO_START/AUTO_END, build_auto, inject)", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C2, source_path: "tools/agent-handover/README.md (Auto-Block-Prinzip, Inject-Modus)", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C3, source_path: "scripts/checks/agent_handover_freshness_check.py (Gate handover-stale-vor-merge)", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C4, source_path: "gh pr list handover in:title — Same-Day-Multi-PR an ≥10 Tagen (06-19/06-24/07-02/07-06×3/07-10×3/07-12/07-15×3/07-18/07-19×3/07-21×3)", commit_or_pr: "live 2026-07-21", opened_in_session: true}
  - {claim_id: C5, source_path: ".windsurf/workflows/session-ende.md (Phase 0a-handover-pr PFLICHT, Phase 0c)", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C6, source_path: "docs/adr/ADR-233-parallel-session-worktree-convention.md §7.3 (Handover NICHT in Scope)", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C7, source_path: "achimdehnert/platform#1284 (A2-Gap dieser Session: #1283 schrieb keinen neuen Aktueller-Stand, Tools-Strang fehlte)", commit_or_pr: "#1284", opened_in_session: true}
created: 2026-07-21
---

## Kernthese

Der `agent-handover`-Generator assembliert **Maschinen-Anker** bereits kollisionsfrei aus einem markierten Auto-Block (C1) — dieselbe „gezogen-statt-getippt"-Mechanik auf die **Session-Narrative** (`## Aktueller Stand`) ausgeweitet, indem jede Session ein eigenes Fragment schreibt und ein Assembler sie rendert, entfernt die A2-Kollisionsklasse *strukturell* statt per Disziplin.

## Steelman (bester Fall für das Konzept, vor Kritik)

Der Beweis, dass das Muster trägt, steht schon im Repo: der Auto-Block zwischen `AGENT_HANDOVER:AUTO START/END` (C1) wird bei jedem Re-Run ersetzt, von Hand gepflegte Abschnitte bleiben — diese Region **kollidiert nie**, weil niemand sie hand-editiert. Die einzige verbleibende hand-editierte, geteilte Region ist die `## Aktueller Stand`-Prosa. Sie ist per Konstruktion ein Single-Writer-Objekt in einer Multi-Writer-Welt → die Kollision ist nicht Pech, sondern zwangsläufig (C4: ~wöchentlich, oft 3 PRs). Fragmente lösen das an der Wurzel: disjunkte Dateien haben keinen Merge-Konflikt, keine „wer schreibt"-Absprache, und jede Session-Contribution wird attribuierbar (Provenienz). Bonus: der C1/Lease-Sichtbarkeitsmechanismus kann „N Fragmente unassembliert" anzeigen — Fragmentierung und Sichtbarkeit greifen ineinander.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| L1 | Der Generator assembliert nur Maschinen-Anker, NICHT die Session-Narrative — `## Aktueller Stand` ist ein Hand-Abschnitt (C1: `build_auto` rendert nur Anker/CI/SHA; Prosa ist Platzhalter „vom Bearbeiter pflegen") | Entscheidung (Root-Cause) | C1 verifiziert: Auto-Block endet vor der Prosa; `inject` erhält Hand-Abschnitte unverändert | belegt |
| L2 | Die Kollision ist chronisch, nicht selten — Same-Day-Multi-Handover-PRs an ≥10 Tagen, mehrfach 3 gleichzeitig | Annahme→belegt | C4 (gh-Abfrage live) | belegt |
| L3 | Die echte Fehlerform ist **disjunkte Handover, keiner vollständig** — nicht der Merge-Konflikt zweier Branches | Entscheidung | C7 (#1284 dieser Session: #1283 überschrieb nichts, ließ aber den Tools-Strang ganz weg) | belegt |
| L4 | Disziplin-Absicherungen existieren bereits (Phase 0a-handover-pr PFLICHT, 0c) und **verhindern die Kollision nicht** | Annahme→belegt | C5 (Regel seit 07-14) + C4 (07-15/07-19/07-21 trotzdem 3 PRs) | belegt |
| L5 | Fragmente lösen A2-**Kollision**, aber NICHT A2-**Omission** (vergisst eine Session ihr Fragment, fehlt ihr Beitrag weiter) | Risiko (ehrliche Grenze) | Design-Analyse; Omission bleibt Sache der session-ende-Checkliste | offen |
| L6 | Das Freshness-Gate (C3) prüft „Überschrift-Datum ≤ STALE_DAYS vs. letzter Commit" — der Assembler MUSS das neueste Fragment-Datum in die gerenderte Überschrift stempeln, sonst rötet er das Gate | Risiko | C3 verifiziert: Gate liest Datum aus den ersten HEAD_LINES | offen (MVC-Auflage) |
| L7 | Fragment-Dir = Quelle, gerenderte Region = generiert (wie Auto-Block) — sonst entsteht eine zweite Wahrheit (AD-1) | Entscheidung (SSoT) | Design-Setzung; Alternative wäre „beides hand-pflegen" = Status quo | offen |

## MVC (konkret — Dateien / Felder / Gate)

1. **Fragment-Verzeichnis** `docs/handover.d/` je Repo. Eine Session schreibt genau eine Datei `YYYY-MM-DD-<session-id>.md` (session-id = derselbe `--task`-Slug wie Worktree/Lease/Memory-Key aus A1 — ein Diskriminator über alle vier Artefakte). Reiner Prosa-Block im heutigen `## Aktueller Stand`-Stil.
2. **Assembler** = Erweiterung von `tools/agent-handover/generate.py` (C1): neuer markierter Block `<!-- HANDOVER:NARRATIVE START/END -->` zwischen H1 und dem Anker-Auto-Block. `generate.py` konkateniert die N jüngsten Fragmente aus `docs/handover.d/` (nach Datum absteigend) in diese Region und stempelt das **neueste** Fragment-Datum in die Überschrift (erfüllt L6/C3). Ältere Fragmente wandern nach `docs/handover.d/archive/` (analog AGENT_HANDOVER_ARCHIVE.md).
3. **session-ende** schreibt künftig sein Fragment statt die geteilte Region zu editieren; ruft danach `generate.py --write` (Assemble). Kein Hand-Edit der NARRATIVE-Region mehr.
4. **CI-Gate** (Erweiterung des bestehenden `handover-stale-vor-merge`, C3): (a) die NARRATIVE-Region muss byte-identisch dem Assembler-Output der Fragmente sein (verhindert Hand-Edit-Bypass, AD-5); (b) Freshness wie gehabt. Ein Hand-Edit der Region ohne passendes Fragment → rot.

## Kill-Gate + Threshold

Siehe Frontmatter `kill_criteria` (messbar: Same-Day-Multi-PR-Kollision / manuelle Konfliktauflösung / stale assemblierte Region). **Threshold-Begründung für die neue Boundary** (`docs/handover.d/`): sie ist gerechtfertigt, weil die bestehende Single-Region die Multi-Writer-Realität (C4) nicht trägt und die Disziplin-Absicherung (L4) empirisch versagt — nicht weil „mehr Struktur schöner" wäre. Exception-Budget: 1 dokumentierte Kollision im Pilotfenster.

## Kriterium → Status (Kill-Gate-Tracking)

| Kriterium | Status | Beleg |
|---|---|---|
| (a) keine Same-Day-Multi-Handover-Kollision mehr im Pilot | offen | Pilot noch nicht gestartet (idea) |
| (b) Assembler braucht 0× manuelle Konfliktauflösung | offen | — |
| (c) session-start liest nie stale assemblierte Region | offen | hängt an L6-Datumsstempel-Impl |

## Befunde inkl. Advocatus Diabolus (T2)

| id | Befund | Antwort / Mitigation |
|---|---|---|
| AD-1 | **Doppelquelle:** Fragment-Dir UND gerenderte Region beide committet — welche ist Wahrheit? | Fragmente = Quelle, Region = generiert (L7). CI-Gate erzwingt Region == Assembler(Fragmente). |
| AD-2 | **Tool wird Boundary:** läuft der Assembler nicht, existieren Fragmente, aber die gerenderte Region ist stale → session-start liest Falsches | Assembler-Lauf in session-ende PFLICHT + CI-Gate (4b) röten bei Divergenz; degradiert nicht schlechter als heute (heute stale ist unentdeckt, hier detektiert). |
| AD-3 | **Manuelle Pflicht ohne Enforcement:** vergisst eine Session ihr Fragment, fehlt ihr Beitrag — wie heute (L5) | Ehrlich: löst Kollision, nicht Omission. Omission bleibt bei der session-ende-Checkliste (C5). Kein Overclaim. |
| AD-5 | **Formal erfüllen, praktisch umgehen:** Session editiert die gerenderte Region direkt statt ein Fragment zu schreiben | CI-Gate 4b weist Hand-Edit der markierten Region ab (wie Auto-Block „nicht von Hand editieren", C1). |
| AD-6 | **Verschlimmert das Freshness-Gate (C3)?** | Nein, sofern L6 erfüllt (neuestes Fragment-Datum in Überschrift gestempelt) — sonst ja. Darum L6 als MVC-Auflage, nicht Option. |
| AD-7 | **„Sichtbar" schwächer als „verhindern"?** | Fragmente *verhindern* (disjunkte Dateien), stärker als C1 (zeigt nur, wer aktiv ist). C1 bleibt komplementär. |

## Alternativen (2, als Zeilen)

| Alt | Ansatz | Verworfen weil |
|---|---|---|
| Alt-1 | **Status quo + Disziplin** (geteilte Datei, Phase 0a-handover-pr + „nur eine Session schreibt") | Empirisch falsifiziert: die Disziplin-Regel existiert seit 07-14 (C5), Kollisionen an 07-15/07-19/07-21 trotzdem je 3 PRs (C4/L4). Genau das Muster, das der Skill „sichtbar < verhindern" nennt. |
| Alt-2 | **Merge-/Handover-Lease** (B1 aus der Parallel-Session-Analyse — Handover-Writes serialisieren) | Serialisiert Wall-Clock, braucht Kooperation beider Sessions, und die Kollision liegt auf einem **gemergten Artefakt**, nicht an einem Live-Lock — ein Lease auf einen asynchronen PR-Merge greift zu spät. Löst zudem Omission (L5) nicht. |

## Off-Ramp

Wird das Konzept angenommen → `pipeline_status: pilot`, Umsetzungs-PR platform-lokal (Assembler + session-ende + Gate), `docs/handover.d/` nur in platform. **Fleet-Rollout (24 Repos mit AGENT_HANDOVER.md, C-Grep) ist eine SEPARATE T3-Entscheidung** (Cross-Repo-Trigger + ADR-233-Amendment) — nicht Teil dieses T2-Piloten. Wird es verworfen → `sunset` + Begründung.
