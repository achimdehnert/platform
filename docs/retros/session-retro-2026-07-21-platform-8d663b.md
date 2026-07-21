---
retro_schema: 1
date: 2026-07-21
repo_scope: [platform, mcp-hub]
session_id: 8d663b
footprint: full
findings_total: 11
findings_survived: 8
refuted_rate: 0.27
phase3_refuted: 2
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [parallel-session-pr-collision, claim-before-cheapest-check, fix-without-enforcement-gate, solo-repo-review-ruleset-deadlock]
recurring_findings: [parallel-session-pr-collision, claim-before-cheapest-check, workaround-without-tracking-anchor]
---

# Session-Retro 2026-07-21 — platform + mcp-hub (session 8d663b)

## 1. Executive Summary
- Reaktive Session (Start: /session-start → ADR-156-Fund) wurde nutzergetrieben zu Parallel-Session-Härtung (A1/C1), einem extern reviewten Konzept (KONZ-027) und einem A/B-Pilot-Issue. 4 PRs sauber gemergt, kein Prod/Migration.
- **8 von 11 Befunden überlebten die Falsifikation** (2 REFUTED durch breitere Prüfung, 1 Collector-Behauptung pre-refuted).
- **Zwei bereits gate-pflichtige Muster erneut produziert:** `parallel-session-pr-collision` (B6, live an 07-21) und `claim-before-cheapest-check` (B1, Docstring-Overclaim „strukturell ausgeschlossen").
- Stärkster technischer Befund: **TOCTOU-Race in der A1-„Kollisions-Garantie"** — der Docstring überclaimt, die Race betrifft nur den Fallback-Pfad ohne `--session-id`.
- Größte Prozess-Lücke: **mcp-hub#180 seit >24h grün-aber-BLOCKED** (Solo-Repo-Self-Approval-Sackgasse), Admin-Bypass vorhanden aber ungenutzt → Session-Ziel bleibt auf main unerreicht.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| B1 | TOCTOU-Race in `session-memory._free_key` — Read-Check + späterer Upsert ohne Lock; Docstring „Datenverlust strukturell ausgeschlossen" gilt nur bei `--session-id`, nicht im Fallback | Race / Overclaim | Hoch | SURVIVES | `origin/main:tools/session-memory` Z.133-159; `store.py` upsert = Last-Write-Wins | `claim-before-cheapest-check` (gate-pflichtig) |
| B2 | verify-adr156-Fix ist Pflaster: nur 2/12 Checks verschärft, 9 bleiben „nackter String", **kein CI-Workflow** ruft das Skript (nur lokal WARN) | Unvollständige Root-Cause / fehlendes Enforcement | Mittel-Hoch | SURVIVES | `grep -rn verify-adr156 .github/` = 0 Treffer (beide Repos); `origin/main:scripts/verify-adr156.sh` 12 grep-Checks | `fix-without-enforcement-gate` (neu, verwandt `always-instruction-without-enforcement`) |
| B6 | Handover-Kollision chronisch; #1280 (A1/C1) verhinderte sie NICHT — #1299/#1300 99s auseinander, #1300 ungemergt geschlossen mit Eigen-Kommentar „Fehlermodus 07-14" | Rework / Duplikat-PR | Hoch | SURVIVES | `gh pr list handover`: #1299 09:29:13Z / #1300 09:30:52Z; C1 = „read-only, kein Lock" | `parallel-session-pr-collision` (gate-pflichtig, ≥3: 07-14/20/21) |
| B7 | mcp-hub#180 >24h grün-BLOCKED: Solo-Repo (1 Collaborator=Autor) + Ruleset „1 Approval" = Self-Approval-Sackgasse; Admin-Bypass vorhanden, ungenutzt | Rote Gates / Governance-Inkonsistenz | Hoch | SURVIVES | `gh pr view 180` BLOCKED/REVIEW_REQUIRED, 14× SUCCESS; `rulesets/17621473` bypass_actors vorhanden | `solo-repo-review-ruleset-deadlock` (neu) |
| B4 | KONZ-002 §16 Kill-Kriterium (a) „GitHub bestätigt schriftlich" per Owner-Selbstattestierung erfüllt; Owner profitiert vom Nicht-Feuern, keine Vier-Augen | Gate-Aufweichung / Selbstbeurteilung | Mittel | SURVIVES | `origin/main:KONZ-002 §16` Z.201-227 (offen deklariert) | — |
| B8 | Issue #1302 verlinkt `blob/main/KONZ-027`, Datei existiert nur im offenen PR #1301 — toter Link bis Merge | Sequenzierung Issue↔PR | Mittel | SURVIVES | `git show origin/main:docs/konzepte/KONZ-027…` = nicht existent | — |
| B9 | Issue #1302 Label `model:sonnet-5` (execution-ready) trotz Prosa-Human-Gate „erst wenn Owner auf pilot"; label-filternde Auto-Session übersieht es | Verfrühte Festlegung / Label-Konvention | Mittel | SURVIVES | `gh issue view 1302` labels=[model:sonnet-5] + Gate-Blockquote | verwandt `feedback_prep_for_sonnet_pattern` |
| B10 | mcp-hub#181 ohne Labels → aus Cross-Repo-Triage schwer auffindbar | Tracking-Konsistenz | Niedrig | SURVIVES | `gh issue view 181` labels=[] | `workaround-without-tracking-anchor` (verwandt) |
| B3 | ADR-156-Nachtrag nennt `deploy_check`-Defekt „separat zu tracken" ohne Tracking-Artefakt | Tracking-Disziplin | Mittel | **REFUTED** | mcp-hub#181 EXISTIERT (Suche in mcp-hub, nicht platform); Rest-Wahrheit: ADR verlinkt #181 nicht | — |
| B5 | break_glass_meter „0" auf ungeprüfter API-Retention nicht von „API zeigt zu wenig" unterscheidbar | Unvalidiertes Instrument | Niedrig | **REFUTED** | KONZ-004 §14 „Grenzen" benennt exakt diese Lücke selbst | — |
| C0 | (Collector) „KONZ-027 R1 nicht im PR #1301" | fehlende Validierung | — | **pre_refuted** | Finder 1 zog Blob `6ce13b6` → `external_sparring_by` + L6-L10 vorhanden | — |

## 3. Scorecard (1–5, ganzzahlig, an Befunden verankert)

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | alles vom User Angeforderte geliefert; Mangel: B7 (#180 unmerged, Ziel auf main unerreicht), KONZ-027 noch offen |
| architektur_design | 3 | KONZ-027 v0 hatte 3 fatale Design-Fehler (extern gefangen+gefixt); A1 TOCTOU-Overclaim (B1). Kern korrekt, aber zwei designte Artefakte hatten reale Defekte |
| code_konventionstreue | 4 | sauber (Worktrees/PRs/Tests/ruff); Mängel B9 (#1302-Label), B10 (#181 labellos), B3-Rest (ADR ohne #181-Link) |
| risiko_debt | 3 | TOCTOU shipped mit Overclaim (B1), verify-adr156-Pflaster ohne CI-Gate (B2). Über dem Fleet-Mittel 2.66, aber realer Debt |
| prozess_effizienz | 3 | Handover-Kollision live rezidiv (B6), #180 24h+ stuck Bypass ungenutzt (B7); Retro/Parallel-Handling/Extern-Loop dagegen effizient |
| entscheidungsqualitaet | 4 | externes Review proaktiv, A/B-Framing, korrektes KONZ-Gating; Soft-Spot B4 (KONZ-002-Selbstattestierung) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #) — |Soll| == 8 Survivors

| Ist (beobachtet, Beleg) | Soll (besserer Schritt) | eliminiert |
|---|---|---|
| Docstring „Datenverlust strukturell ausgeschlossen", obwohl nur `--session-id` das garantiert (B1) | Overclaim-Selbstcheck: eine Absolutheits-Aussage („immer/nie/ausgeschlossen") vor Commit gegen den billigsten Gegenfall prüfen — hier: „was, wenn zwei ohne `--session-id`?" → Docstring auf „im Fallback best-effort, eindeutig nur mit `--session-id`" korrigieren | #B1 |
| verify-adr156 nur 2/12 Checks gehärtet, kein CI-Gate (B2) | Beim Härten eines Checks die **Gegenbeispiel-Probe** auf alle Geschwister-Checks im selben File anwenden + das Skript in CI verdrahten (nicht nur lokal WARN) | #B2 |
| A1/C1 als „Lösung" der Parallel-Kollision berichtet, obwohl A2 (Handover-Datei) ungelöst blieb → 07-21 live rezidiv (B6) | Fix-Scope explizit gegen die volle Fehlerklasse abgrenzen: „A1 löst Memory-Key, A2 bleibt offen bis KONZ-027" — und den offenen Rest NICHT als reine Sichtbarkeit (C1) verkaufen | #B6 |
| mcp-hub#180 24h+ grün-BLOCKED, Bypass ungenutzt (B7) | Bei Solo-Repo mit Review-Ruleset: Merge-Sackgasse VOR PR-Erstellung erkennen (Pre-Flight Ruleset↔Collaborator-Check); Bypass-Merge dem User als expliziten Gate-Block mit exaktem Befehl vorlegen (statt PR offen liegen lassen) | #B7 |
| KONZ-002-Kill-Kriterium per Owner-Selbstattestierung (B4) | Owner-attestierte Gate-Erfüllung an ein durables Vier-Augen-Surrogat koppeln: der PR-Kommentar mit wörtlicher Owner-Freigabe IST das Audit-Artefakt (schon da) — zusätzlich `external_confirmation: pending`-Feld führen, damit die Ersatz-Beweisform sichtbar offen bleibt | #B4 |
| Issue #1302 verlinkt main-Pfad vor PR-Merge (B8) | Folge-Artefakte, die auf noch-ungemergte Dateien zeigen, auf `blob/<branch>` oder `blob/<commit>` statt `blob/main` verlinken (oder Issue erst nach Merge erstellen) | #B8 |
| #1302 `model:sonnet-5` trotz Human-Gate (B9) | Ein Issue mit offener Owner-Entscheidung bekommt NICHT das execution-ready-Label, sondern `blocked`/`needs-decision`, bis das Gate fällt — Label muss maschinenlesbar zum Gate passen | #B9 |
| mcp-hub#181 labellos (B10) | Jedes bei einem Nebenbefund erstellte Issue bekommt im selben `gh issue create` ≥1 Label (Typ+Prio), sonst unsichtbar für Sweeps | #B10 |

## 5. Längsschnitt (retro_kpis.py, PFLICHT-Lauf)
`python3 tools/retro_kpis.py` gelaufen. **13 Slugs ≥2 = gate-pflichtig.** Für DIESE Session einschlägig:
- **`parallel-session-pr-collision`** — jetzt ≥3 Vorkommen (07-14, 07-20, 07-21), diese Session lieferte das jüngste live (B6). **Der strukturelle Fix ist bereits in Flight (KONZ-027/#1302), aber owner-gegated** — bis zur Pilot-Entscheidung bleibt es reaktiv.
- **`claim-before-cheapest-check`** — B1 (Docstring-Overclaim) ist ein frisches Vorkommen desselben gate-pflichtigen Musters.
- **`workaround-without-tracking-anchor`** — B10 (labelloses #181) streift es.
- **refuted_rate = (phase3_refuted + pre_refuted)/total = (2+1)/11 = 0.27** (Skill-KPI, Band gesund). **Echte Falsifikations-Quote = phase3_refuted/(total − pre_refuted) = 2/10 = 0.20** (unterer Rand, akzeptabel — Skeptiker war streng, nicht Theater). **risiko_debt 3** liegt über dem aktuellen Fleet-Mittel (**2.66**, n=44 aus dem `retro_kpis.py`-Lauf dieser Session — ersetzt den älteren MEMORY.md-Wert Ø 2.70; konstant schwächste Dimension).

## 5b. Autonomie-Kalibrierung
- **over_ask = 0:** mcp-hub#180 dem User als „dein Zug" vorgelegt war KORREKT — der Admin-Bypass eines Rulesets ist Gate 3 (Security/Governance-Config) UND der Merge triggert deploy.yml (Gate 2); der Classifier blockte meinen eigenen Merge-Versuch, bestätigt die Einstufung.
- **over_act = 0:** kein Prod/Publish autonom; PRs via Auto-Merge nach User-Approval (ADR-270 Tier A erlaubt), KONZ/Tool-Edits unter Gates.
- Keine Charter-Schärfung nötig.

## 6. Verankerung (kopierfertig — Mensch entscheidet)

### memory_candidates
```
name: feedback-absolute-claim-needs-cheapest-counterexample
type: feedback
body: Eine Absolutheits-Aussage in Doc/Docstring/PR („immer/nie/strukturell ausgeschlossen/garantiert") vor Commit gegen den BILLIGSTEN Gegenfall prüfen. Realfall 2026-07-21 (retro 8d663b, B1): `session-memory`-Docstring „Datenverlust strukturell ausgeschlossen" — galt nur mit `--session-id`; ohne Flag bleibt eine TOCTOU-Race (Read-Check + späterer Upsert ohne Lock, Last-Write-Wins im Store). Instanz von `claim-before-cheapest-check` (gate-pflichtig). **Why:** Overclaims überleben, weil der Autor den eigenen Happy-Path prüft, nicht den Fallback. **How to apply:** vor jeder Absolutheits-Aussage genau EINEN Gegenfall formulieren und durchspielen; hält er nicht, Aussage relativieren. [[feedback_cheapest_check_in_retro_too]]
```
```
name: feedback-solo-repo-review-ruleset-deadlock
type: feedback
body: Ein Repo mit genau EINEM Collaborator (=Autor) und Ruleset `required_approving_review_count:1` ist strukturell nicht regulär mergebar (GitHub verbietet Self-Approval). Realfall 2026-07-21 (mcp-hub#180, B7): PR 24h+ grün-BLOCKED, Admin-Bypass vorhanden aber ungenutzt. **Why:** Ruleset wurde 1:1 aus einem Repo mit 2. Owner (platform/wirdigital) übernommen, ohne die Collaborator-Voraussetzung zu prüfen. **How to apply:** Pre-Flight vor PR in seltenen Repos — `gh api repos/<o>/<r>/collaborators` vs. Ruleset-`required_approving_review_count`; bei Sackgasse den Admin-Bypass-Merge dem User als Gate-3-Block mit exaktem Befehl vorlegen, PR nicht offen liegen lassen. Kandidat für ein wiederkehrendes Governance-Gate (Ruleset-Konsistenz-Check über Repos). [[feedback_platform_pr_needs_second_owner_review]]
```

### adr_candidates
```
(keiner — alle Befunde sind Prozess/Doku/Tool-Ebene, keine Architektur-Entscheidung. KONZ-027 ist der bereits laufende Konzept-Pfad für parallel-session-pr-collision.)
```

## 7. Maßnahmen (Action-Board, aus Soll-Ablauf abgeleitet)

🟢 **Offen — dein Zug**
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | mcp-hub#180 Admin-Merge | mcp-hub | [#180](https://github.com/achimdehnert/mcp-hub/pull/180) | ⛔ Gate 2+3 | du: `gh pr merge 180 --admin --squash [skip ci]` |
| 2 | KONZ-027 Pilot-Entscheid | platform | [#1301](https://github.com/achimdehnert/platform/pull/1301) | ⛔ owner-gated | du: approven + `idea→pilot` |

🔵 **Offen — ich kann sofort** (Folge-Session)
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 3 | A1-Docstring-Overclaim korrigieren (B1) | platform | folgt | 🔵 ready | ich: „im Fallback best-effort" statt „strukturell ausgeschlossen" |
| 4 | #1302 Label `model:sonnet-5`→`needs-decision` (B9) | platform | [#1302](https://github.com/achimdehnert/platform/issues/1302) | 🔵 ready | ich: Label tauschen |
| 5 | #1302 main-Link auf branch/commit (B8) | platform | [#1302](https://github.com/achimdehnert/platform/issues/1302) | 🔵 ready | ich: Link fixen |
| 6 | mcp-hub#181 Label ergänzen (B10) | mcp-hub | [#181](https://github.com/achimdehnert/mcp-hub/issues/181) | 🔵 ready | ich: `bug`+Prio |
| 7 | ADR-156-Nachtrag #181 verlinken (B3-Rest) | platform | folgt | 🔵 ready | ich: Issue-Link in v3.6 |

🟡 **Getrackt, größer** (nicht sofort)
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 8 | verify-adr156 in CI verdrahten + 9 Geschwister-Checks (B2) | mcp-hub | folgt | 🟡 wip | Issue schneiden |

## 8. Nicht verifiziert (Restlücken)
- **Scope-Creep** (session-start → Konzept + externes Review): der Finder konnte NICHT befunden, ob jeder Eskalationsschritt user-angestoßen war — kein Artefakt-Marker, nur Transkript. Billigster Check: Konversations-Verlauf (liegt außerhalb der git/gh-Artefakte). *Aus dem Verlauf dieser Session ist es belegt user-getrieben, aber das ist Session-Gedächtnis, kein Artefakt → als Hypothese geführt.*
- **B2 „9 Geschwister-Checks gleich fragil":** der Skeptiker bestätigte den Kern (kein CI-Gate, nackte Strings), stufte die Fragilität aber als „graduell, nicht kategorisch" ein (Symbol-Grep vs. Prosa-Grep). Der genaue False-Positive-Radius je Check ist ungeprüft — billigster Check: je Check ein konstruierter Verneinungssatz.
- **GitHub server-side `merge=union`** (aus dem A/B-Issue #1302, nicht Retro-Befund): lokal verifiziert, server-side Squash/Rebase ungeprüft — Pilot-Check 1.
