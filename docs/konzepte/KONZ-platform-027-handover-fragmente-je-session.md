---
concept_id: KONZ-platform-027
title: Handover-Fragmente je Session statt geteilter Prosa-Region
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []          # keine Klickdummy/Spec — reine Repo-Prozess-Konvention (ADR-233-Folge)
adr_threshold: kein neuer ADR für den platform-Pilot (Konvention + Tool); ADR-233-Amendment ERST beim Fleet-Rollout (Cross-Repo = T3-Gate, s. Kill-Gate)
external_sparring_by: openai-o3@2026-07-21 + zweiter-provider@2026-07-21 (2 unabhängige Runden, beide „überarbeiten"; Tag-Tabelle §Externes Sparring)
review_by: 2026-09-01
kill_criteria: "Der Pilot SCHEITERT (→ zurück auf geteilte Datei + Disziplin, Feature-Flag aus), wenn bis 2026-09-01 EINES eintritt: (a) MEHR ALS EINE dokumentierte Same-Day-Handover-Kollision (die erste verbraucht das Exception-Budget); ODER (b) der Assembler braucht ≥1× manuelle Konfliktauflösung; ODER (c) session-start liest je eine STALE assemblierte Region (Fragment neuer als gerendert); ODER (d) VOLLSTÄNDIGKEIT verletzt — die gerenderte Region enthält je weniger als alle nicht-konsumierten Fragmente (neue Fehlerform aus dem externen Review, AD-3: still verlorene Arbeit ohne Kollision). Kill-Messpunkt ist der resultierende main-HEAD nach Merge, NICHT der PR-Branch."
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

> **Revision R1 (2026-07-21, nach 2 externen Reviews — beide „überarbeiten").** Der **Kern** (session-eigene Fragment-Dateien) hat beide Steelmans überlebt. Die **ursprüngliche Ausführung** hatte drei fatale, unabhängig doppelt gefundene Fehler, die den Pilot sein eigenes Kill-Gate hätten bestehen lassen, während er Arbeit verliert: (1) festes `N=2` droppt am 3-Session-Tag — dem gemessenen Pathologiefall — das 3. Fragment **still** ins Archiv; (2) das Kill-Gate war für genau diese neue Fehlerform blind; (3) die auf dem Session-Branch committete, regenerierte Region reproduziert die geteilte-Region-Kollision eine Ebene höher. Ledger + MVC unten sind die revidierte Fassung; die Tag-Tabelle steht in §Externes Sparring.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| L1 | Der Generator assembliert nur Maschinen-Anker, NICHT die Session-Narrative — `## Aktueller Stand` ist ein Hand-Abschnitt | Entscheidung (Root-Cause) | C1 verifiziert | belegt |
| L2 | Die Kollision ist chronisch — Same-Day-Multi-Handover-PRs an ≥10 Tagen, mehrfach 3 gleichzeitig | Annahme→belegt | C4 | belegt |
| L3 | Die echte Fehlerform ist **disjunkte Handover, keiner vollständig** | Entscheidung | C7 (#1284) | belegt |
| L4 | Disziplin-Absicherungen (Phase 0a-handover-pr) **verhindern die Kollision nicht** | Annahme→belegt | C5 + C4 | belegt |
| L5 | Fragmente lösen A2-**Kollision**, NICHT A2-**Omission** (vergessenes Fragment) | Risiko (ehrliche Grenze) | Design; Omission bleibt session-ende-Checkliste | offen |
| L6 | **Vollständigkeit vor Kürze:** die gerenderte Region MUSS *alle nicht-konsumierten* Fragmente enthalten, kein festes `N`-Fenster (sonst still verlorene Arbeit am 3-Session-Tag) | Entscheidung (Kern-Revision) | Externes Sparring AD-1/AD-3 doppelt bestätigt; falsifiziert das ursprüngliche `N=2` | **neu (R1)** |
| L7 | **Nur EIN Schreiber der gerenderten Region:** ein Post-Merge-Job auf `main` (bzw. render-on-read), NIE ein Session-Branch — sonst re-kollidiert die Region + Byte-Gate | Entscheidung (Kern-Revision) | Externes Sparring AD-4/OOTB-3 doppelt bestätigt; falsifiziert „session-ende committet die Region" | **neu (R1)** |
| L8 | **Freshness ≠ Vollständigkeit:** getrennte Invarianten. Freshness = Zeit-Signal (Datum); Vollständigkeit = Manifest erwarteter Fragment-IDs | Entscheidung | Externes Sparring AD-5/AD-7 | **neu (R1)** |
| L9 | Fragmente sind **post-merge immutable**; Korrektur via neues referenzierendes Fragment, nie rückwirkender Edit | Entscheidung | Externes Sparring AD-9/AD-7 | **neu (R1)** |
| L10 | Reversibilität „durch Entfernen EINER Sache" = **ein Feature-Flag** im Generator (`narrative-assembler: off` → Fallback geteilte Region) | Entscheidung | Externes Sparring M28-2 | **neu (R1)** |

## MVC (revidiert R1 — Dateien / Felder / Gate)

1. **Fragment-Verzeichnis** `docs/handover.d/`. Eine Session schreibt genau eine Datei `YYYY-MM-DDTHH-MM-SSZ-<session-id>.md` — **UTC-Zeitstempel** (nicht nur Tag, denn „Same-Day" IST die Kollisionseinheit) + `session-id` als stabiler Tiebreaker (derselbe Diskriminator wie Worktree/Lease/Memory-Key aus A1). Zweiter Schreibvorgang derselben session-id → **Suffix, kein Overwrite** (L9). Fragment trägt minimale Struktur: `Scope · Erledigt · Offen · Risiken · beanspruchte Zustände (Deploy/Migration/Version)`.
2. **Assembler** = Erweiterung `tools/agent-handover/generate.py` (C1): markierter Block `<!-- HANDOVER:NARRATIVE START/END -->`. Konkateniert **ALLE nicht-konsumierten** Fragmente (nicht `N`-Fenster, L6), sortiert nach `(timestamp, session-id)`. Rendert je Fragment eine `## ⚡ Aktueller Stand (<ts> — <sid>)`-Überschrift; widersprüchliche `beanspruchte Zustände` werden **explizit als Konflikt markiert**, nicht stumm konkateniert (AD-7). Header trägt **getrennte** Felder: „zuletzt gerendert", „neuestes Fragment", „Anzahl nicht-konsumierter Fragmente" (L8).
3. **Ort des Laufs (Kern-Revision, L7):** die NARRATIVE-Region wird **NICHT** von Session-Branches committet. Stattdessen EIN Post-Merge-Job auf `main` (oder render-on-read beim session-start). Session-PRs fügen **nur** ihr Fragment hinzu — reines Add, nie Edit der Region → genau ein Schreiber → keine Region-Re-Kollision.
4. **Konsum-/Checkpoint-Mechanik** (towncrier-Muster, ersetzt Zeit-Archivierung): ein Fragment verlässt die Region erst, wenn eine Folge-Session/ein Checkpoint es nachweislich **konsumiert** hat → dann nach `docs/handover.d/archive/`. Archivierung **ausschließlich post-merge/im Checkpoint**, nie im Session-PR (AD-5-alt / L6). Kein `N` schneidet still ab.
5. **CI-Gate** (Erweiterung `handover-stale-vor-merge`, C3), **drei getrennte Invarianten**: (a) **Freshness** wie gehabt (Zeit); (b) **Vollständigkeit** — Manifest/Hash aller erwarteten nicht-konsumierten Fragment-IDs, geprüft gegen **main-HEAD nach Merge**, nicht den PR-Branch (AD-4); (c) **Provenienz** — kein Hand-Edit der markierten Region ohne passendes Fragment. Golden-Master-Tests für Sortierung, gleiche Zeitstempel, Zeilenenden, Unicode, leere/überzählige Fragmente.

## Kill-Gate + Threshold

Siehe Frontmatter `kill_criteria` (jetzt widerspruchsfrei + um Kriterium **(d) Vollständigkeit** erweitert; Messpunkt = main-HEAD nach Merge). **Threshold-Begründung** für die Boundary `docs/handover.d/`: gerechtfertigt, weil die Single-Region die Multi-Writer-Realität (C4) nicht trägt und die Disziplin (L4) empirisch versagt. **Vor Pilot-Start:** die Fragment-/Rendering-Konvention als kleine versionierte Mini-Spec festhalten (M28-2/REC-13) — ohne damit den Fleet-Rollout zu entscheiden.

## Kriterium → Status (Kill-Gate-Tracking)

| Kriterium | Status | Beleg |
|---|---|---|
| (a) ≤1 Same-Day-Handover-Kollision im Pilot (1. = Exception-Budget) | offen | Pilot noch nicht gestartet (idea) |
| (b) Assembler braucht 0× manuelle Konfliktauflösung | offen | — |
| (c) session-start liest nie stale assemblierte Region | offen | render-on-read/post-merge (L7) |
| (d) Vollständigkeit: Region enthält je alle nicht-konsumierten Fragmente | offen | Manifest-Check gegen main-HEAD (MVC-5b) |

## Befunde inkl. Advocatus Diabolus (T2, R1-aktualisiert)

| id | Befund | Antwort / Mitigation |
|---|---|---|
| AD-1 | **Doppelquelle:** Fragment-Dir UND Region beide committet | Fragmente = Quelle, Region = generiert von EINEM Post-Merge-Job (L7). Session-PRs adden nur Fragmente. |
| AD-2 | **Tool wird Boundary:** läuft der Assembler nicht, ist die Region stale | Post-Merge-Job + Vollständigkeits-Gate (MVC-5) röten bei Divergenz; render-on-read hat gar keine committete Region, die stale sein könnte. |
| AD-3 | **Omission:** vergessenes Fragment fehlt weiter (L5) | Ehrlich: löst Kollision, nicht Omission. Bleibt session-ende-Checkliste (C5). |
| AD-4 (extern, FATAL) | **N=2 droppt am 3-Session-Tag still** | Behoben: assemble-all-pending, kein `N` (L6); Kill-Kriterium (d) misst es. |
| AD-5 (extern, FATAL) | **Region-Re-Kollision auf Session-Branch** | Behoben: nur EIN Schreiber post-merge (L7). |
| AD-6 (extern) | **Freshness wird Gummistempel** | Behoben: Freshness/Vollständigkeit getrennte Invarianten (L8, MVC-5). |
| AD-7 (extern) | **Semantische Widersprüche stumm konkateniert** | Assembler markiert widersprüchliche `beanspruchte Zustände` explizit als Konflikt (MVC-2). |

## Alternativen (R1-erweitert)

| Alt | Ansatz | Verdikt |
|---|---|---|
| Alt-1 | **Status quo + Disziplin** (geteilte Datei, Phase 0a-handover-pr + „nur eine Session schreibt") | **Verworfen:** empirisch falsifiziert — Regel seit 07-14 (C5), Kollisionen an 07-15/07-19/07-21 trotzdem je 3 PRs (C4/L4). „sichtbar < verhindern". |
| Alt-2 | **Merge-/Handover-Lease** (B1 — Handover-Writes serialisieren) | **Verworfen:** serialisiert Wall-Clock, braucht Kooperation, Kollision liegt auf gemergtem Artefakt (Lease greift zu spät), löst Omission nicht. |
| Alt-3 (NEU, extern OOTB-1) | **Append-only + git `.gitattributes merge=union`** — niemand editiert, jede Session hängt an, `merge=union` vereint beide Seiten (~5 Zeilen, kein Assembler/Archiv) | **Als Pilot-Vergleichsbasis aufgenommen (REC-7):** billigste Lösung derselben Schreib-Kollision; die Fragment-Maschinerie ist nur gerechtfertigt, wenn sie gegenüber `merge=union` **messbar mehr** liefert (Same-Line-Robustheit, Konsum-Semantik, Konflikt-Markierung). Risiko: unbegrenztes Wachstum ohne Pruning, Interleaving bei Same-Line-Edits. |
| Alt-4 (NEU, extern OOTB-2) | **towncrier-Muster** (erprobtes newsfragment-Dir + „assemble-all-pending" + „consume") | **Muster übernommen, Tool verworfen:** release-/versionszentrisch (Kadenz-Mismatch zur täglichen Handover-Realität), zusätzliche Dependency — aber das *Muster* „assemble-all-pending, dann konsumieren" ist genau der Fix für das N-Fenster und in MVC-4/L6 eingearbeitet. |

## Off-Ramp

Wird das Konzept angenommen → `pipeline_status: pilot`, Umsetzungs-PR platform-lokal, `docs/handover.d/` nur in platform, **Alt-3 (`merge=union`) als billige Vergleichsbasis im selben Pilot** (REC-7). **Fleet-Rollout (24 Repos, C-Grep) = SEPARATE T3-Entscheidung** (Cross-Repo + ADR-233-Amendment) — nicht Teil des T2-Piloten. Verworfen → `sunset` + Begründung.

## Externes Sparring (durabler Audit-Nachweis, Step 5b)

Zwei unabhängige externe Runden am 2026-07-21 (Cross-Provider zur internen Anthropic-Autorschaft), beide Verdikt **„überarbeiten"**. Briefing/Antworten waren Scratch in `~/shared` (KONZ-010); der Audit lebt hier durabel. **Bemerkenswert: beide Provider fanden dieselben drei fatalen Fehler unabhängig** — ein starkes Signal, dass sie echt waren, nicht Provider-Idiosynkrasie.

| Extern-ID (Review) | Verdikt | Aktion in R1 |
|---|---|---|
| N=2 droppt 3. Fragment still (R1-AD2 / R2-AD1/M28-1) | [valid] FATAL | L6: assemble-all-pending; Kill-Kriterium (d) |
| Kill-Gate blind für neue Fehlerform (R1-AD8 / R2-AD3) | [valid] FATAL | Kill-Kriterium (d) Vollständigkeit + Messpunkt main-HEAD |
| Region committed auf Session-Branch re-kollidiert (R1-AD1/AD4 / R2-AD4/AD6) | [valid] FATAL | L7: nur EIN Schreiber post-merge / render-on-read |
| Same-Day-Sortierung unentscheidbar (R1-AD3 / R2-AD2) | [valid] | MVC-1: UTC-Timestamp-Dateiname + Tiebreaker |
| Freshness wird Gummistempel (R1-AD7 / R2-AD5) | [valid] | L8: Freshness ≠ Vollständigkeit getrennt |
| Kill-Gate in sich widersprüchlich (R1-AD8) | [valid] | Frontmatter: „>1 Kollision; 1. verbraucht Budget" |
| Archiv-Move = konkurrierender Write (R1-AD5 / R2-M28-3) | [valid] | MVC-4: Archivierung nur post-merge/Checkpoint |
| Reversibilität „eine Sache" verletzt (R2-M28-2) | [valid] | L10: ein Feature-Flag |
| Fragment-Immutability undefiniert (R1-AD9 / R2-AD7) | [valid] | L9: post-merge immutable, Korrektur via neues Fragment |
| `merge=union` billige Basis (R2-OOTB1) | [valid] | Alt-3 als Pilot-Vergleichsbasis |
| towncrier-Muster (R2-OOTB2) | [valid] | Alt-4/MVC-4 Muster übernommen |
| Strukturierte Fragment-Felder / Konflikt-Markierung (R1-AD6/REC7) | [valid] | MVC-1/MVC-2 |
| Golden-Master-Tests (R1-REC12) | [valid] | MVC-5 + Impl-Issue |
| Mini-Spec vor Pilot (R1-REC13 / R2) | [valid] | Kill-Gate-Abschnitt |
| Getrennte Header-Felder (R1-REC14 / R2-REC5) | [valid] | MVC-2 |
| Merge-Queue-mit-Rebase *falls Region eingecheckt* (R1-REC2) | [valid-aber-obsolet] | Durch L7 (render-on-read) gegenstandslos — Wurzel- statt Pflaster-Lösung |

**Bilanz: 16 Befunde, 15 [valid] eingearbeitet, 1 [valid-aber-obsolet] (durch eine andere akzeptierte Entscheidung überflüssig). 0 abgelehnt.** Der Konzept-**Kern** (Fragment-Dateien) überlebte; die **Ausführung** wurde an 3 fatalen + 7 mittleren Stellen korrigiert.
