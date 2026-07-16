---
retro_schema: 1
date: 2026-07-16
repo_scope: [iil-klickdummy]
session_id: d80d23
footprint: lean
findings_total: 1
findings_survived: 1
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 5
  architektur_design: 5
  code_konventionstreue: 5
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [handover-stale-vor-merge]
recurring_findings: [handover-stale-vor-merge]
footprint_reduction_reason: "n/a — genuinely lean: 2 PRs, 1 repo, docs-only, kein Prod/Migration/ADR"
---

## 1. Executive Summary

- Seit dem letzten Retro dieses Repos (`0ba8b4`, 2026-07-14) gab es nur 2 neue Artefakte: PR #178 (gemergt, docs-only) und PR #180 (offen, docs-only, CI grün). Footprint `lean` — Inline-Pass, kein Subagenten-Einsatz.
- **PR #180 sitzt seit 2 Tagen grün und mergebereit** (`mergeable`, alle CI-Checks SUCCESS, erstellt 2026-07-14T18:19), ohne dass sie gemerged wurde. In der Zwischenzeit zeigt `AGENT_HANDOVER.md` auf `main` an zwei Stellen (Z. 52, Z. 293-294) weiterhin „platform#1131 … Merge steht aus" — verifiziert falsch: `platform#1131` ist bereits seit 2026-07-14T10:24:18Z gemerged.
- Das ist die **5. dokumentierte Instanz** des bereits gate-pflichtigen Musters `handover-stale-vor-merge` (`retro_kpis.py`: ×4 in `[f5e1d, 16fd96, 7f7fbd, d2522c]`, plus verwandte Erwähnungen in `2752dc`, `a50bc6`, `42bfe0`, `e17299`, `16fd96`). Ein Vorgänger-Retro (`d2522c-incr`) hat bereits notiert, dass für dieses Muster **kein systemisches Gate existiert** — dieser Fund bestätigt das erneut.
- Kein zweiter Befund überlebt die Prüfung: beide PRs sind inhaltlich korrekt, gut gescoped, CI-grün; PR #178s „Merge steht aus"-Formulierung war zum Zeitpunkt des Commits (08:11:11Z, 2h13min vor dem tatsächlichen `platform#1131`-Merge) noch zutreffend — kein Fehler, sondern Timing.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `AGENT_HANDOVER.md` auf `main` behauptet an 2 Stellen „platform#1131 … Merge steht aus", obwohl der PR seit >2 Tagen gemerged ist; die Korrektur-PR #180 liegt seit 2 Tagen grün+mergebereit unangewendet | Prozesslücke | mittel | SURVIVES | `gh pr view 1131 --repo achimdehnert/platform` → `mergedAt: 2026-07-14T10:24:18Z`; `AGENT_HANDOVER.md:52,293-294` auf `origin/main`; `gh pr view 180` → `mergeable`, alle `statusCheckRollup`-Einträge `SUCCESS`, `createdAt: 2026-07-14T18:19:26Z` | `handover-stale-vor-merge` — **5. Vorkommen** (bereits ×4 gate-pflichtig: `f5e1d, 16fd96, 7f7fbd, d2522c`) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 5 | Beide PRs liefern exakt das, was ihr Titel verspricht (Handover-Korrektur) |
| architektur_design | 5 | n/a — reine Doku-Änderungen, keine Architekturentscheidung |
| code_konventionstreue | 5 | Commit-Format `docs(handover): …` korrekt, CI vollständig grün auf #180 |
| risiko_debt | 3 | Kontaminierte Blast-Radius klein (nur Doku), aber die Stale-Info ist genau die Art Fehlinformation, die Folge-Sessions fehlleitet (Issue #176 Merge-Stand betroffen) |
| prozess_effizienz | 3 | Ein fertiger, grüner PR blieb 2 Tage liegen — reiner Merge-Klick fehlte |
| entscheidungsqualitaet | 4 | Keine falsche Entscheidung getroffen, nur eine offene Ausführung |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| PR #180 (Handover-Korrektur, CI grün seit 2026-07-14T18:19:59Z) wurde erstellt und blieb ohne weiteren Trigger 2 Tage lang offen; niemand/kein Automatismus prüfte beim nächsten Session-Start, ob ein eigener grüner Handover-PR noch offen ist | Session-Start-Preflight (dieses Repo hat bereits einen Reconciliation-Guard für Cross-Host-Memory-Drift, siehe `handover-memory-cross-host-drift`) um einen Check erweitern: „gibt es einen offenen, CI-grünen, selbst-autorisierten PR gegen `AGENT_HANDOVER.md`? → merge zuerst, bevor neue Arbeit beginnt." Das schließt die Lücke strukturell statt per Einzel-Erinnerung | #1 |

## 5. Längsschnitt

`python3 platform/tools/retro_kpis.py` (Auszug, 29 Reports):

```
🚨 GATE-PFLICHT  handover-stale-vor-merge  ×4  [f5e1d, 16fd96, 7f7fbd, d2522c]
```

Mit diesem Report wird der Zähler auf **×5**. Bereits in `session-retro-2026-07-11-platform-d2522c-incr.md` (Z. 154) vermerkt: „`handover-stale-vor-merge` bleibt ohne systemisches Gate (… M5 fixte nur die Einzelinstanz)". Der hier gefundene Fall bestätigt das exakt ein weiteres Mal — kein neues Gate wurde seither gebaut. Gegen `<auto-memory>/MEMORY.md` dieses Repos abgeglichen: kein bestehender Memory-Eintrag zu diesem Slug in `iil-klickdummy`-Memory (nur repo-lokal bei `frist-hub`/`platform` dokumentiert) — Verankerungslücke auch auf Memory-Ebene.

## 5b. Autonomie-Kalibrierung

Kein `over_ask`/`over_act` in diesem Fund — das Liegenlassen von PR #180 ist reine Prozess-Lücke (fehlender Trigger), keine Autonomie-Grenzüberschreitung in irgendeine Richtung. Keine Charter-Änderung abgeleitet.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**Memory-Kandidat** (repo: `iil-klickdummy`, Datei `handover-stale-vor-merge-gate-overdue.md`):

```markdown
---
name: handover-stale-vor-merge-gate-overdue
description: Grüner, selbst-autorisierter Handover-Korrektur-PR blieb 2 Tage unmerged, main zeigte weiter falschen Merge-Status — 5. Instanz eines seit 2026-07-04 gate-pflichtigen, nie gebauten Gates
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-16-handover-stale-vor-merge-5th
---

Vor Beginn neuer Arbeit an einem Repo mit AGENT_HANDOVER.md: prüfen, ob ein eigener,
CI-grüner PR gegen diese Datei bereits offen ist — falls ja, zuerst mergen, nicht liegen
lassen. **Warum:** `handover-stale-vor-merge` ist seit `session-retro-2026-07-04-platform-f5e1d`
gate-pflichtig (×4 dokumentiert: f5e1d, 16fd96, 7f7fbd, d2522c) und laut
`session-retro-2026-07-11-platform-d2522c-incr` bis heute ohne systemisches Gate — dieser
Fund (`session-retro-2026-07-16-iil-klickdummy-d80d23`, PR iilgmbh/iil-klickdummy#180) ist die
5. Instanz. **How to apply:** bei `/session-start` oder vor `/session-ende` explizit
`gh pr list --author @me --search "AGENT_HANDOVER"` (oder Datei-Pfad-Filter) gegenchecken.
Siehe [[prod-deploy-preflight-before-merge-approval]] für das Schwester-Muster
`scope-checkpoint-not-durably-recorded` (gleiche Kategorie: bekannt, wiederholt, nie gegatet).
```

**ADR-Kandidat:** keiner — dies ist ein Prozess-/Tooling-Gate (Session-Start-Skill-Erweiterung
oder leichter CI-Check „AGENT_HANDOVER.md-PR älter als 24h + grün + author=self"), keine
Architekturentscheidung. Empfehlung: Gate-Issue in `platform` (analog zur `#1080`-Familie
bestehender Gate-Issues), nicht ADR.

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | PR #180 mergen (Handover-Korrektur, CI grün) | iil-klickdummy | https://github.com/iilgmbh/iil-klickdummy/pull/180 | 🟢 offen | Freigabe, dann merge ich |
| 2 | Gate-Issue „Handover-PR-Preflight" anlegen (5. Instanz `handover-stale-vor-merge`, bislang ungegatet) | platform | file:///tmp/claude-1000/-home-devuser-github-iil-klickdummy/23a3935e-193c-4329-bfaa-25fc05b54ad6/scratchpad/platform-retro-wt/docs/retros/session-retro-2026-07-16-iil-klickdummy-d80d23.md | 🔵 ich kann | Issue-Text aus §6 ableiten |
| 3 | Memory-Kandidat `handover-stale-vor-merge-gate-overdue` verankern | iil-klickdummy | n/a (Memory-Datei) | 🟢 dein Zug | Freigabe zum Schreiben in Memory-Dir |

## 8. Nicht verifiziert (Restlücken)

- Ob Issue #176 (Rollout-Queue) auf `main` aktuell den gleichen veralteten Merge-Stand zeigt wie in PR #180 beschrieben ("8/13 gemergt, 4 CI-blockiert, 2 zurückgestellt" vs. was `main` aktuell zeigt) wurde **nicht** einzeln nachgezogen — billigster Check: `gh issue view 176 --repo iilgmbh/iil-klickdummy` gegen den PR-#180-Diff vergleichen. Nicht als eigener Befund geführt, da vermutlich derselbe Root Cause (Befund #1) und kein zusätzlicher Beleg gezogen wurde.
- Kein Phase-5-Meta-Review durchgeführt (nur `full`/`deep`-Pflicht, hier `lean`).
