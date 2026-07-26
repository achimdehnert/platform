---
retro_schema: 1
date: 2026-07-26
repo_scope: [illustration-hub]
session_id: a9b435
footprint: full
footprint_reduction_reason: "Rule-B deep (Prod-Schritt) → full: (a) alle Prod-Schritte menschlich freigegeben/ausgeführt (#81 vom User gemergt, #82 explizit '1 go', Env-Flip per ! vom User), (b) voll rollback-fähig, gleiche Bereitstellung, keine DB-Migration, (c) findings_total ≤10."
findings_total: 9
findings_survived: 7
refuted_rate: 0.22
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [handover-stale-vor-merge, claim-before-cheapest-check, deferred-item-no-tracking-issue, fragile-inline-remote-command-not-file]
recurring_findings: [handover-stale-vor-merge, claim-before-cheapest-check, deferred-item-no-tracking-issue, fragile-inline-remote-command-not-file]
---

# Session-Retro 2026-07-26 — illustration-hub (a9b435)

## 1. Executive Summary
- Zwei saubere PRs geliefert und live: **#81** (SECRET_KEY-Prod-Guard, fail-closed) + **#82** (ADR-003 Rev 4 → `implemented`). CI grün, Deploys success, Prod-Health 200, **null Red Flags** (keine dangling/Duplikat-PRs, keine roten Gates, keine Migrations-Kollision).
- Kern-Erfolg: ComfyUI-Primärpfad auf Prod **E2E belegt** (`provider=comfyui, degraded_from=None`) — der seit Juni offene Render-Strang ist geschlossen; Failover zu fal funktioniert sauber.
- **7 von 9 Befunden überleben** die Falsifikation. Der Ausgang war stark **prozess-** und **risiko_debt-**lastig, nicht correctness-lastig: die beiden gemergten Diffs selbst sind sauber (Guard verifiziert fail-closed, ADR-Wiring korrekt).
- **Drei Survivors treffen bereits gate-pflichtige Längsschnitt-Slugs** (`retro_kpis.py`, ≥2 über 53 Retros): `claim-before-cheapest-check`, `handover-stale-vor-merge`, `deferred-item-no-tracking-issue`. Das sind keine neuen Lehren — es sind bekannte Gates, die erneut feuerten.
- Größte Einzel-Reibung: **~5 User-Roundtrips für EIN Kommando** (Shell-Quoting/Paste-Artefakte), lösbar spätestens nach Versuch 2.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|--------|-----------|----------|---------|-------|------------|
| 1 | `AGENT_HANDOVER.md` nach der Session nicht aktualisiert — beschreibt ComfyUI noch als „ein Schalter fehlt", erwähnt weder Cleanup noch Checkpoint-Risiko | process-gap | HIGH | SURVIVES | `git log origin/main -- AGENT_HANDOVER.md` letzter Touch `9270c23` (07-25); beide 07-26-Commits fassen sie nicht an; `origin/main:AGENT_HANDOVER.md` Z.32/131-134 noch „es fehlt genau ein Schalter" | `handover-stale-vor-merge` (gate-pflichtig ≥2) |
| 2 | Prod-DB-Hard-Delete (Cleanup-Script, 2 Projekte+Jobs+Assets) ohne jedes Artefakt (kein Commit/PR/Issue) | process-gap / missing-validation | HIGH | SURVIVES | `git log --all --since=2026-07-26 --name-status`: nur ADR + settings berührt, kein Cleanup-Artefakt. (Contract-Verletzungs-Framing überzogen: `buch-illustration-kontrakt.md` scoped no-hard-delete auf „je über die API ausgeliefert" — Smoke-Rows fallen raus) | `deferred-item-no-tracking-issue` (gate-pflichtig ≥2) |
| 3 | Entdeckter SPOF (RTX-Box hatte NULL Checkpoints, manuell/ungebackupt provisioniert) inline gefixt, aber nicht als Issue/Runbook getrackt | process-gap / knowledge-gap | MEDIUM | SURVIVES | `gh issue list --state all` + `gh search issues` checkpoint/RTX/safetensors → 0 Treffer org-weit; ADR-003 D2 nennt Infra-Dependency, aber NICHT empty-checkpoint-Klasse | `deferred-item-no-tracking-issue` (gate-pflichtig ≥2) |
| 4 | ADR-003 auf `implemented` gesetzt, obwohl der Beleg die eigene §7-Confirmation-Latte nicht trifft (forced provider, Wegwerf-Prompt, gelöschte Smoke-Rows — kein realer writing-hub-Buch-Job mit Auslieferung) | missing-validation / premature-commitment | MEDIUM | SURVIVES | `origin/main:docs/adr/ADR-003…` §7 Pkt 1 verlangt „realer IllustrationJob (writing-hub-Buch) → … → Auslieferung"; PR #82 Body nennt keinen `source_ref`/Buch-Bezug; `gh pr view 82 --json reviews` = `[]`, self-merged/self-graded | `claim-before-cheapest-check` (gate-pflichtig ≥2) |
| 5 | ~5 User-Roundtrips für EIN E2E-Kommando; Versuche 1-4 scheiterten alle an Shell-Quoting/Paste-Artefakten; Script-File (Versuch 5) war spätestens nach Versuch 2 fällig | tooling / process-gap | HIGH | SURVIVES | **in-context/Transkript** (kein Repo-Artefakt, s. §8); ADR-003-Changelog korroboriert „Erster Render scheiterte…"; Kausallogik unwiderlegt (längere base64-Einzelzeile kann Newline-Injection nicht heilen) | `fragile-inline-remote-command-not-file` (neu, ×1; verwandt `no-backticks-in-gh-commit-args`) |
| 6 | ComfyUI-Checkpoint-Inventar nicht VOR dem ersten Render geprüft; Erreichbarkeit (system_stats 200) als Readiness behandelt → 400 + verbrannter Render-Zyklus | missing-validation | MEDIUM-HIGH | SURVIVES | ADR-003 Rev4-Changelog verbatim: „Erster Render scheiterte an einem leeren Checkpoint-Ordner (/prompt 400 → Failover fal)"; `GET /object_info/CheckpointLoaderSimple` (später eh gelaufen) hätte es billig vorab gezeigt | `claim-before-cheapest-check` (gate-pflichtig ≥2) |
| 7 | „Handover stale / Doppelarbeit-Risiko" aus dem SessionStart-Hook-Banner behauptet, BEVOR die Primärquelle (das Doc) geprüft war; selbst korrigiert | process-gap / communication | LOW | SURVIVES | in-conversation, unwiderlegt; self-corrected via Live-Hook-Rerun | `claim-before-cheapest-check` (gate-pflichtig ≥2) |
| — | (REFUTED) Scope wuchs ohne Scope-Checkpoint-Reflexion | communication | LOW | REFUTED | **Transkript**: User trieb jeden Schritt explizit („flip it autonomously", „1 go", „re-check ComfyUI") — kein blankes „mach autonom"; Zweck der Regel (unbemerkter Drift) nicht gefährdet | — |
| — | (REFUTED) Modell-Tier einmal geflaggt, nie wiederholt | process-gap / cost | LOW | REFUTED | `session-routing.md` verlangt wörtlich „once early… Do not nag" — Nicht-Wiederholen IST das policy-konforme Verhalten | — |

## 3. Scorecard (1–5, ganzzahlig, an Befunden verankert)

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle Ziele geliefert+live (R2, ComfyUI E2E); kleiner Makel: #4 (ADR-Latte überzogen) |
| architektur_design | 4 | Guard sauber (Skeptiker: fail-closed, kein fail-open-Pfad); ComfyUI-Wiring korrekt; keine Design-Mängel |
| code_konventionstreue | 4 | Worktree (ADR-233), Conventional Commits, Tests, ruff grün; keine Verstöße |
| risiko_debt | 2 | Drei ungetrackte Reste: #1 stale Handover, #2 Prod-Delete ohne Artefakt, #3 SPOF ohne Issue (Fleet-Ø 2,62 — diese Session zieht den Schwachpunkt nicht hoch) |
| prozess_effizienz | 2 | #5 (5 Roundtrips/1 Kommando) + #6 (vermeidbarer Render-Zyklus) + #7 (Misdiagnose-Roundtrip) |
| entscheidungsqualitaet | 3 | Kern-Entscheidungen tragfähig (R2-Wahl, Gate-Handling, Failover-Design); Ausreißer #4 (self-graded ADR-Closure) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert-#)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Session endete mit Merge #82, Handover blieb auf 07-25-Stand (Z.32/131-134) | Vor Session-Ende einer Prod-berührenden Session: Handover-Freshness-Check als Gate — offene Prios gegen die real gemergten PRs abgleichen, ComfyUI-Zeile + neue Risiken nachziehen | #1 |
| Prod-Rows via Ad-hoc-Script gelöscht, kein Commit/Issue | Jede Prod-Mutation (auch self-created Testdaten-Cleanup) bekommt im selben Turn eine Ledger-/Issue-Zeile mit dem Delete-Kriterium; Script gehört ins Repo (`tools/`), nicht nur auf den Dev-Host | #2 |
| Checkpoint-SPOF inline gefixt, nirgends getrackt | Discovered-and-fixed-inline-Risiken bekommen ein Tracking-Artefakt genauso wie deferred work — hier: Issue „ComfyUI-Modell-Provisioning manuell+ungebackupt" + Runbook-Stub | #3 |
| `implemented` geschrieben+gemergt vom selben Actor, ohne §7-Wortlaut gegenzulesen | Vor einem Production-Readiness-Status-Bump: die ADR-eigene Confirmation-Sektion Wort für Wort gegen das real Ausgeführte prüfen; forced-provider/Wegwerf-Beleg explizit als solcher deklarieren, nicht als „realer Job" | #4 |
| 4 fragile Inline-Kommando-Varianten, bevor Script-File griff | Konvention: ein an einen Menschen zum Paste in eine Remote-Shell übergebenes Kommando, das mehrzeilig ODER lang ist, wird IMMER als Script-Datei geliefert — nach dem ERSTEN Paste-Fehler sofort umschalten, nicht die Quoting-Variante variieren | #5 |
| Erreichbarkeit als Readiness behandelt → Render-Zyklus an 400 verbrannt | Vor der teuren Operation (Render) der billigste Readiness-Check des Backends (`GET /object_info/CheckpointLoaderSimple`) — reachable ≠ provisioned | #6 |
| Aus dem Hook-Banner (Sekundärquelle) „Doc stale" behauptet, dann Doc geprüft | Reihenfolge umkehren: bei jeder prüfbaren Behauptung zuerst die Primärquelle (die Datei) lesen, dann behaupten — der Hook-Banner ist abgeleitet | #7 |

**Invariante:** 7 Soll-Schritte == 7 überlebende Befunde. ✅

## 5. Längsschnitt (retro_kpis.py über 53 Retros)
- **`claim-before-cheapest-check`** (gate-pflichtig ≥2) — diese Session **3×** getroffen (#4 self-graded ADR, #6 render-vor-checkpoint-check, #7 assert-vor-primärquelle). Der stärkste Recurrence-Cluster.
- **`handover-stale-vor-merge`** (gate-pflichtig ≥2) — #1. Deckt sich mit der 2026-07-15-Lehre (Handover-Checklisten-Lücke → 3 konkurrierende Handover-PRs).
- **`deferred-item-no-tracking-issue`** (gate-pflichtig ≥2) — #2 + #3. Konsistent mit `risiko_debt` als schwächster Fleet-Dimension (Ø 2,62).
- **`fragile-inline-remote-command-not-file`** — neu (×1); verwandt mit dem bestehenden `no-backticks-in-gh-commit-args`. Noch kein Gate, aber Kandidat.
- **refuted_rate 0.22** — im gesunden Band (0.2–0.8); Falsifikation war weder Theater noch Stroh (2 saubere Refutes: F4, F9 gegen Policy/User-Direktive).

## 5b. Autonomie-Kalibrierung
- **over_ask: 0** — nichts fälschlich als „dein Zug" vorgelegt, das deterministisch/reversibel war. Gate-Vorlagen (Merge, Prod-Env, Prod-Delete) waren echte Gates.
- **over_act: 0** — kein Gate autonom überschritten. Prod-.env-Edit wurde vom Harness-Classifier geblockt UND korrekt an den User übergeben; Merges nur nach explizitem Wort. Der Merge #82 durch den Agenten erfolgte nach „1 go" (verbale Freigabe wörtlich). Autonomie-Grenze sauber eingehalten — keine Charter-Schärfung nötig.

## 6. Verankerung (kopierfertig — Mensch entscheidet)

**memory_candidates:**

```markdown
---
name: remote-command-to-human-always-as-file
description: "Ein an einen Menschen zum Paste in eine (Remote-)Shell übergebenes Kommando, das mehrzeilig ODER lang ist, IMMER als Script-Datei liefern — nie als Inline-Text"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-26-fragile-inline-comfyui-smoke
---
Realfall 2026-07-26 (illustration-hub, ComfyUI-E2E): EIN Kommando brauchte ~5 User-Roundtrips.
Versuch 1 multiline `shell -c` → IndentationError (Newlines→Spaces). Versuch 2 one-line `;` →
Terminal-Wrap injizierte echte Newlines. Versuch 3 Heredoc → Paste rückte jede Zeile + den
`PY`-Terminator ein. Versuch 4 base64-one-liner → Paste-Wrap spaltete den gequoteten ssh-Befehl
(`'docker`⏎`exec -i`). Versuch 5 (.sh-Datei auf Dev-Host, `bash ~/x.sh`) → sofort ok.
**Why:** Der manuelle Paste-Kanal reformatiert langen/mehrzeiligen Inhalt (collapsed newlines,
injizierte Wraps, Auto-Indent, gespaltene Quotes) — jede Inline-Encoding-Variante ist demselben
Kanal-Defekt ausgeliefert, nicht ein je eigener Syntaxbug.
**How to apply:** Sobald ein für einen Menschen bestimmtes Kommando mehrzeilig ODER > ~einer
Terminalbreite ist → als Datei liefern (`Write` auf den erreichbaren Host, dann `bash ~/x.sh`).
Nach dem ERSTEN Paste-Fehler nicht die Quoting-Variante wechseln — sofort auf Datei umschalten.
Verwandt: [[no-backticks-in-gh-commit-args]]. Gilt zusätzlich zu [[feedback-terse-solution-output]].
```

**adr_candidates:** keine neue ADR. Stattdessen **Gate-Verankerung** der drei bereits gate-pflichtigen Slugs (Hook/CI/Skill, nicht N-tes Memo):
- `claim-before-cheapest-check` → 3× in EINER Session ist ein Signal: der Skill/Hook-Gate-Kandidat aus `retro_kpis.py` sollte priorisiert werden (Cross-Repo).
- `handover-stale-vor-merge` → ein `/session-ende`-Gate „Handover-Freshness vs. gemergte PRs" (die 2026-07-15-Lehre existiert, aber greift nicht auto).
- `deferred-item-no-tracking-issue` → gilt auch für discovered-and-fixed-inline-Risiken + Prod-Cleanups, nicht nur deferred work.

## 7. Maßnahmen (Action-Board, aus Soll-Ablauf abgeleitet)

### 🟢 Offen — dein Zug
| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|-------------|--------|-----------|
| 1 | ADR-003 `implemented`-Beleg entschärfen | illustration-hub | ADR-003 §7/#82 | 🟢 offen | forced/synthetisch deklarieren ODER auf `partial` bis realer Buch-Job |
| 2 | Handover-Freshness-Gate | platform | `/session-ende` | 🟢 offen | Gate-PR autorisieren |

### 🔵 Offen — ich kann sofort
| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|-------------|--------|-----------|
| 3 | `AGENT_HANDOVER.md` nachziehen (ComfyUI live, Cleanup, Checkpoint-Risiko) | illustration-hub | — | 🔵 ready | PR (Merge=Deploy-Gate → dein Wort) |
| 4 | Issue: ComfyUI-Modell-Provisioning manuell+ungebackupt (SPOF) | illustration-hub | — | 🔵 ready | `gh issue create` |
| 5 | Memory `remote-command-to-human-always-as-file` | (auto-memory) | — | 🔵 ready | anlegen (du bestätigst) |

### ✅ Erledigt (diese Session)
| # | Item | Beleg | Status |
|---|------|-------|--------|
| 6 | PR #81 SECRET_KEY-Guard | merged+deployed | ✅ |
| 7 | PR #82 ADR-003 Rev 4 | merged+deployed | ✅ |
| 8 | ComfyUI E2E `provider=comfyui` | render 200 | ✅ |
| 9 | Prod-Smoke-Daten gelöscht | 2 Proj/Job/Asset | ✅ |

## 8. Nicht verifiziert (Restlücken)
- **#5/#7** (Roundtrip-Anzahl, Assert-Reihenfolge): rein konversationell, kein git/gh-Artefakt — als in-context-Fakt geführt, nicht als committed evidence. Billigster Check: Transkript (existiert, aber nicht maschinell aus Repo ableitbar).
- **ADR-003 `implemented` inhaltlich**: der ComfyUI-Render lief (200, Asset provider=comfyui) — verifiziert. NICHT verifiziert: ein realer writing-hub-**Buch**-Job über die normale Provider-Selektion (nicht forced) mit Auslieferung/sichtbarem Bild. Billigster Check: ein echter source_ref-Job über die API + Asset-Sichtbarkeit.
- **Cleanup-Delete-Scope**: gemeldet „2 Projekte+2 Jobs+2 Assets (cascade)" — plausibel (tenant_id='smoke' Filter), aber ohne Artefakt nicht nachträglich auditierbar. Billigster Check wäre eine Query auf verbliebene `tenant_id='smoke'`-Rows gewesen (nicht durchgeführt).
