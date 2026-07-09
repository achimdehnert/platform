---
retro_schema: 1
date: 2026-07-03
repo_scope: [platform, travel-beat]
session_id: 54a76c-incr
footprint: full
findings_total: 4
findings_survived: 4
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check, p0-check-not-in-required-checks]
recurring_findings: [claim-before-cheapest-check]
---

# Increment-Retro 2026-07-03 — Abarbeitung der Retro-Action-Items (54a76c)

Increment-Scope (NUR neue Artefakte ~09:10–10:00 UTC): Memories verankert, **Parent**-Retro-
Report committet (via #887; dieser Increment-Report selbst ist bis Action #5 uncommittet),
4 Sofort-Fixes (platform #887 merged, travel-beat #57 offen), Registry-Drift-Fix (#890 merged). Parent-Retro (54a76c) wird nicht re-litigiert; Parent-Slugs zählen als
Vorkommen-1. Pipeline: 1 Collector (haiku) + 2 gebündelte Finder + 1 gebündelter Skeptiker
(sonnet), Belege unabhängig neu gezogen.

## 1. Executive Summary
- **Alle Increment-Ziele erreicht** + Bonus: Fleet-blockierender Registry-Drift (aus Fremd-PR #883) per sanktioniertem `flip` gefixt (#890), Canary erstmals seit 10+ Runs grün (09:47), beide Prod-Endpoints live (307/200).
- **Same-day-Rezidiv `claim-before-cheapest-check` (→ ×5):** der #890-PR-Body behauptete „verifiziert: #887/#884/#885 alle rot / blockt ALLE" — #884/#885 waren beim Schreiben **16–18 Min gemergt**. Ein „verifiziert" auf stale Stand.
- **Struktureller Neu-Fund (fleet-relevant):** „Registry-Konsistenz (ADR-234 **P0**)" ist **kein Required-Check** — Branch-Protection UND Ruleset listen nur `guardian`. #883/#884/#885 mergten deshalb trotz FAILURE; #883 umging so sein *eigenes* Gate und schuf den Drift. Direkter ADR-242-Bezug (Wave 3).
- **Canary-Grün ≠ Fix-Beweis:** der 09:47-Run löste die neue Retry-Logik **nie aus** (alle 14 Hubs 200 im 1. Versuch) — der Host war erholt. „Fix wirkt" bleibt Hypothese bis ein Run einen Retry→Erfolg zeigt.
- **Entlastungen (Positiv-Feststellungen):** #890 war NICHT CI-blind gemergt (alle 7 Checks vor Merge fertig); travel-beat #57 bewusst+dokumentiert geparkt; Memory-Verankerung 1:1 mit Report; Parent-Slug `host-fix-not-mirrored-to-iac` trat im Increment NICHT erneut auf (nginx-Spiegel wurde diesmal im selben PR nachgezogen).

## 2. Befund-Tabelle
| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| A | #890-Body „verifiziert: alle rot / blockt ALLE" war beim Schreiben stale — #884 (09:18:47) + #885 (09:20:07) längst gemergt, #890 created 09:36:11 | fehlende Validierung | mittel | SURVIVES | `gh pr view 890 --json createdAt,body` vs `884/885 --json mergedAt` | **claim-before-cheapest-check ×5 (same-day ⇒ Gate-Pflicht)** |
| B | „Registry-Konsistenz (ADR-234 P0)" ist kein Required-Check — Branch-Protection `contexts:["guardian"]` UND Ruleset 17621471 nur `guardian`; 3er-Cluster #883/#884/#885 mergten trotz FAILURE (#883 umging sein eigenes Gate → Drift-Ursache) | Gate-Design / Prozess | hoch | SURVIVES | `gh api …/branches/main/protection` + `…/rules/branches/main`; statusCheckRollup 883/884/885 | neu: `p0-check-not-in-required-checks` (ADR-242-Scope) |
| C | Kausal-Claim „Canary grün dank Retry-Fix" unbelegt — Run 28652569433: Retry-Code nur als Skript-Text im Log, kein einziger ❌-Zwischenversuch; alle Hubs 200 im 1. Attempt | fehlende Validierung | mittel | SURVIVES | `gh run view 28652569433 --log` (kein Retry gefeuert) | claim-before-cheapest-check (Facette Attribution) |
| D | Fremd-verursachter main-Blocker (#883-Drift) gefixt ohne jeden Koordinations-Kommentar an Verursacher-/betroffene PRs — 6/6 Kommentare über 883/884/885/890 sind Bot | Kommunikation | niedrig | SURVIVES | `gh pr view 883 884 885 890 --json comments`: alle 6 Kommentare author=github-actions | — |

## 3. Scorecard (1–5, an Befunden verankert)
| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | alle Items erledigt + Fleet entsperrt; Abzug: Wirksamkeits-Claim C unbewiesen |
| architektur_design | 4 | kein Befund-Survivor auf Architektur-Ebene — B ist Branch-Protection-Konfig, nicht Design; sanktionierter `flip` (#890) statt Handedit; nginx-Spiegel im selben PR (Parent-Lehre angewandt) |
| code_konventionstreue | 4 | Registry-Governance eingehalten (#890); Abzug: „verifiziert"-Wortlaut im PR-Body gegen evidence-discipline (A) |
| risiko_debt | 3 | zahnloses P0-Gate aufgedeckt (B, vorbestehend); travel-beat-Host-Krücke lebt bis #57-Deploy |
| prozess_effizienz | 4 | schnell ohne Rework/Kollision; #890 nicht CI-blind (Positiv-Feststellung: alle 7 Checks completed vor mergedAt); Abzug: fehlende Koordinations-Spur (D) |
| entscheidungsqualitaet | 3 | zwei Evidenz-Disziplin-Lapsus in einem kleinen Increment (A: stale „verifiziert"; C: unbewiesene Attribution) |

## 4. Soll-Ablauf (|Soll| == 4 Survivor)
| Ist (beobachtet, Beleg) | Soll (besserer Schritt) | eliminiert |
|---|---|---|
| PR-Body schrieb „verifiziert: alle rot" auf 16-Min-altem Stand | Jeder „verifiziert"-Satz in einem PR-Body braucht den Check **im selben Atemzug** (unmittelbar vor `gh pr create` re-checken); alte Checks verfallen bei parallelen Sessions in Minuten | A |
| „P0"-Check advisory; 3 Merges trotz rot, Drift-Ursache #883 passierte ihr eigenes Gate | `Registry-Konsistenz` in die Required-Checks/Ruleset aufnehmen — bzw. ins `ci / gate`-Aggregat (exakt ADR-242-Wave-3-Muster, HANDOVER-Prio 1) | B |
| Grüner Canary-Run als Fix-Erfolg verbucht | Fix-Wirksamkeit erst behaupten, wenn der Mechanismus nachweislich **feuerte** (Log: ❌→Retry→✅); bis dahin „deployed, Wirksamkeit ausstehend" | C |
| Fremd-Blocker still gefixt (nur PR-Body erwähnt es) | Beim Fix eines fremd-verursachten main-Problems 1-Zeilen-Kommentar auf den Verursacher-PR (hier #883): Ursache + Fix-PR — Parallel-Sessions lesen keine fremden PR-Bodies | D |

## 5. Längsschnitt (retro_kpis.py, Pflicht — Increment-Zählregel)
- **`claim-before-cheapest-check`: Parent ×4 → mit diesem Increment ×5** (Zählregel: 1 Slug = max +1 pro Report). Same-day-Rezidiv trotz frisch geschriebenem Retro ⇒ die reine Memory-/Policy-Verankerung reicht **nachweislich nicht** — der bestehende Stop-Hook (`evidence_claim_scanner.py`) prüft Turn-Text, aber **nicht PR-Bodies aus Dateien** (`--body-file`). Gate-Schärfung nötig (Action #1).
- **`host-fix-not-mirrored-to-iac`: NICHT rezidiviert** — Parent-Lehre wurde im Increment angewandt (nginx-Spiegel im selben PR #887). Zähler bleibt, kein neues Vorkommen. Erste Evidenz, dass die Verankerung wirkt.
- **`p0-check-not-in-required-checks`: neu (Vorkommen 1)** — direkter ADR-242-Bezug; kein eigenes Gate nötig, sondern Anschluss an das bestehende Wave-3-Programm.
- refuted_rate 0.0 (0+0/4) — unter der 0.2-Theater-Schwelle; Kontext: die 4 Befunde waren Timestamp-/API-Fakten mit geringer Widerlegungs-Oberfläche, und der Skeptiker prüfte echte Widerleger-Pfade (Rulesets). Trend beobachten (Phase-5-KPI).

## 6. Verankerung (kopierfertig — Mensch entscheidet)
### memory_candidates
1. **Nachtrag zu `feedback_no_backticks_in_gh_commit_args` ODER neue Memory `feedback_verified_claim_expires_in_parallel_sessions`** — „Ein »verifiziert«-Claim in einem PR-Body/Commit verfällt in Minuten, wenn parallele Sessions im selben Repo mergen. Check unmittelbar vor `gh pr create` wiederholen; Realfall 2026-07-03: #890-Body behauptete Blockade von #884/#885, die 16–18 Min zuvor gemergt waren (×5-Instanz claim-before-cheapest-check)."
2. **`project_registry_gate_not_required`** (project) — „»Registry-Konsistenz (ADR-234 P0)« ist auf platform/main NICHT required (nur `guardian`, Branch-Protection + Ruleset 17621471 verifiziert 2026-07-03); rote Registry-Merges sind technisch möglich (Realfall #883/#884/#885). Fix läuft über ADR-242 Wave 3 (`ci / gate`-Aggregat), nicht als Einzel-Patch."

### adr_candidates
- Kein neues ADR — Befund B ist ADR-242-Scope (bestehendes Programm, Wave 3 via #811).

## 7. Maßnahmen (Action Board)
🟢 **Dein Zug**
| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|--------------|--------|-----------|
| 1 | Gate-Schärfung claim-before-cheapest-check (×5): `evidence_claim_scanner.py` auf PR-Body-Dateien (`--body-file`-Pfade) ausweiten | ~/.claude/hooks | Gate-Pflicht (retro_kpis) | 🟢 | Entscheid + „go hook" (ich baue) |
| 2 | Registry-Check required machen — über ADR-242 Wave 3 (`ci / gate`) | platform | #811 / ADR-242 | 🟢 | in Wave-3-Plan aufnehmen (du/via #811) |
| 3 | travel-beat #57 mergen + Redeploy + Host-Krücke `docker network rm bfagent_platform` | travel-beat | #57 | 🟢 | Deploy-Gate (du) |
🔵 **Ich sofort (auf Wort)**
| # | Item | Repo | Status | Next Step |
|---|------|------|--------|-----------|
| 4 | 1-Zeilen-Koordinations-Kommentar auf #883 (Ursache→Fix #890) nachtragen | platform | 🔵 | „go comment" |
| 5 | Increment-Report committen (dieser Report, docs/retros/) | platform | 🔵 | „commit incr" |

## 8. Nicht verifiziert (Restlücken)
- **Canary-Retry-Wirksamkeit** (C): unbewiesen bis ein Run einen echten ❌→Retry→✅-Zyklus zeigt — billigster Check: beim nächsten transienten Blip `gh run view <id> --log | grep -A2 '❌'`.
- **Ob die Fremd-Session #884/#885 in Kenntnis des roten Gates mergte** (bewusst vs. übersehen): aus Artefakten nicht feststellbar (keine Kommentare); als Hypothese offen.
- **`evidence_claim_scanner.py`-Lücke** (PR-Body via `--body-file` ungescannt): aus dem Verhalten geschlossen (Hook feuerte nicht), Hook-Code im Increment nicht erneut gelesen — billigster Check: `grep -n "body\|file" ~/.claude/hooks/evidence_claim_scanner.py`.
