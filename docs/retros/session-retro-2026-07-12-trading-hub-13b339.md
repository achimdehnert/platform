---
retro_schema: 1
date: 2026-07-12
repo_scope: [trading-hub]
session_id: 13b339
footprint: deep
findings_total: 12
findings_survived: 7
refuted_rate: 0.42
phase3_refuted: 5
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [handover-stale-vor-merge, deploy-green-not-prod-healthy, prod-incident-no-tracking-artifact]
recurring_findings: [handover-stale-vor-merge, deploy-green-not-prod-healthy, prod-incident-no-tracking-artifact, fragile-anchor-config-edit, run-result-not-anchored, deferred-item-no-tracking-issue]
over_ask: 0
over_act: 2
footprint_reduction_reason: "keine — deep beibehalten: Prod-Schritte + Migration 0029 + realer Prod-Incident (Downscale-Kriterium b verletzt)"
---

# Session-Retro 2026-07-12 — trading-hub (Session 13b339)

Session-Inhalt (Artefakt-Grenze): Tiefenanalyse → PR-Kette #116–#122, #124 (8 Feature-PRs,
alle gemergt+deployed), #127 (Handover), #129 (Hotfix, OPEN), Prod-Ops (1d-Backfill,
`shadow_evidence`-Lauf, Beat-Diagnose). Fremd/parallel (out of scope): #126, #128, #130–#132.

## 1. Executive Summary

- 8/8 geplante Items als PRs geliefert, gemergt, deployed; Prod-Backfill + erste Kill-Gate-Auswertung real ausgeführt — Kernziel erreicht.
- **Aber:** #121 führte per fragilem Text-Anker-Insert einen Beat-Schedule-Bug ein → Prod-Beat-Crashloop inkl. Dead-Man-Switch, 5h18min unentdeckt, >16h unbehoben (Fix #129 wartet korrekt am Prod-Gate, hat aber **kein** Tracking-Artefakt außer sich selbst).
- Deploy-Gate misst nur Web-Liveness — drei „grüne" Deploys liefen über den kaputten Beat (auch fremde Sessions); „Deploy grün ≠ Prod gesund" ist der zentrale Gate-Kandidat.
- Das Prod-Auswertungsergebnis (INSUFFICIENT_EVIDENCE, 14/17 Tage leere Screener-Auswahl) ist in keinem dauerhaften Artefakt verankert — nur im Chat.
- Falsifikation arbeitete: 5/12 Befunde REFUTED (u.a. Batch-Merge-Kritik, gitignore-Vorfall als gelebte Selbstkorrektur, Lint-Nachschub ohne Schadmechanismus).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| A1 | Prod-Lauf-Ergebnis `shadow_evidence` (INSUFFICIENT_EVIDENCE, 14/17 leer, 2 Tage Ø +1,50%) in keinem Artefakt (Issue/Handover/Memory) | Prozesslücke | kritisch | SURVIVES | gh-Suche 0 Treffer; origin/main:AGENT_HANDOVER Prio 1 „offen"; pgvector-Summary deckt nur Build | run-result-not-anchored ×1 |
| A2 | Beat-Bug unverändert auf origin/main (settings.py:145); Fix #129 >12h CI-grün unmerged — Faktum bestätigt, Schuldzuweisung entkräftet (Merge = Prod-Gate, wartet korrekt auf Freigabe) | Prozesslücke | kritisch | SURVIVES | gh pr view 129 (OPEN, CLEAN, createdAt 20:18:17Z); origin/main-Grep | — |
| A4 | #120 „Bewusst NICHT drin": Fill-Latenz = aufgeschobene Arbeit ohne Tracking-Issue (Kontrast: #122→#123, #124→#125); Options-Paper-Punkt = finale Design-Entscheidung (ok) | Kommunikation | niedrig | SURVIVES | PR-Body #120; Issue-Suche 0 Treffer | deferred-item-no-tracking-issue ×1 |
| A5 | Handover (#127, 15:04Z) vor Incident-Sichtbarkeit gemergt; bis heute kein Incident-Nachtrag — Session IX liest sich als voller Erfolg | verfrühte Festlegung | mittel | SURVIVES | git log origin/main -- AGENT_HANDOVER.md (letzter Touch 4477f83); grep beat/129 leer | handover-stale-vor-merge ×3 (≥2 ⇒ GATE) |
| B1 | Beat-Crashloop-Root-Cause: anker-basierter Text-Insert schachtelte options-shadow-scan in options-auto-trade; kein Struktur-Test vor #129 (git log -S: einziger Treffer = Fix-Commit) | fehlende Validierung / Werkzeug | kritisch | SURVIVES | git show 7819d4f; git log --all -S CELERY_BEAT_SCHEDULE -- src/tests/ | fragile-anchor-config-edit ×1 |
| B3 | gitignore `data/` verschluckte quality.py still | Werkzeug | mittel | REFUTED | im selben PR binnen 1 min entdeckt+gefixt+Lesson dokumentiert — Selbstkorrektur, kein Muster | — |
| B4 | Lint-Nachschub-Commits = fehlender Pre-Commit-Gate | Prozesslücke | niedrig | REFUTED | gh pr view 117/119/120/121 --json commits: Muster nur in 2/4; grep ci.yml: kein Lint-Job; Push-Hook = main-tree-guard only | — |
| B5 | Merge 82c466a verpasste Chance, #121-Bug zu sehen | Prozesslücke | niedrig | REFUTED | git show 82c466a -- settings.py: einziger Hunk in TRADING_PAPER_*-Region; CELERY_BEAT-Block nicht im Diff | — |
| C1 | Batch-Merge (6 PRs/14s, 5 Deploys cancelled) versteckte den Bug | Prozesslücke | hoch | REFUTED | merge-base-Check: e9ea712 ∈ 2433c0b (Batch nie einzeln deployt, Fakt bestätigt); #129-Body zeigt präzise #121-Zuordnung ohne Bisect — Kausal-Mangel nicht belegt | — |
| C3 | Incident-Latenz 5h18min: Deploy-Gate prüft nur `livez` (kein Beat-Health); Dead-Man-Blindspot dokumentiert, ungedeckt; Latenz fiel in AKTIVE Sessionzeit (#128/#126 deployten drüber) | Prozesslücke / Monitoring | hoch | SURVIVES | run 29196973342 15:00:05Z vs. #129 20:18:17Z; deploy.yml Z.62; deadman.py-Docstring | deploy-green-not-prod-healthy ×1 |
| C4 | Kein Tracking-Artefakt außer offenem PR; Folge-Merges (#126, #131) deployten über kaputten Beat; #131 registriert sogar neuen Beat-Task, der nie läuft | Prozesslücke | kritisch | SURVIVES | merge-base-Check c11506a∉main; Issue-Suche leer; #131-Body ohne Beat/129-Bezug | prod-incident-no-tracking-artifact ×1 |
| C5 | settings.py-Parallel-Edit riskant (#120/#124-Kollision) | Prozesslücke | mittel | REFUTED | gh pr view --json files über #116–#124: nur #120/#121/#124 touchten settings.py; git branch --contains 82c466a: einziger Konflikt-Merge — erwartbare ADR-233-Reibung | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | 8/8 Items + Prod-Läufe geliefert, aber Incident eingeführt + Ergebnis nicht verankert (A1, B1) |
| architektur_design | 4 | fail-closed-Design testbelegt (Finder-Gegenprobe: test_should_report_insufficient_* in #116/#122), lib/-Boundary etabliert; kein Architektur-Survivor |
| code_konventionstreue | 4 | Konventionen eingehalten; B4/B5 refuted; kleiner Rest: Nachschub-Commits |
| risiko_debt | 2 | Prod-Beat >16h tot inkl. Dead-Man (C3/C4); kein Kapitalschaden (Strategien dormant) |
| prozess_effizienz | 3 | 8 PRs + Hotfix + Prod-Ops in einer Session; C1/C5 refuted; aber 5h-Latenz + Tracking-Lücken |
| entscheidungsqualitaet | 4 | Gates korrekt respektiert (A2-Steelman), Right-Sizing, saubere bewusste Auslassungen (außer A4) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, Beleg) | Soll | eliminiert |
|---|---|---|
| Prod-Report nur im Chat (A1-Belege) | Prod-Lauf-Ergebnis im SELBEN Turn als Issue-Kommentar/Handover-Nachtrag verankern (Tracking-Regel gilt auch für Run-Ergebnisse, nicht nur ausgelassene Arbeit) | A1 |
| Gate-blockierter Hotfix wartete stumm >12h (gh pr view 129) | Gate-blockierte Incident-Fixes aktiv eskalieren: Discord/PushNotification an den Menschen + Issue-Verweis, nicht nur Chat-Schlusszeile | A2 |
| Fill-Latenz als „nicht right-sized" ohne Issue (PR-Body #120) | „Bewusst NICHT drin" binär klassifizieren: finale Entscheidung (Begründung reicht) vs. aufgeschoben (Issue-Pflicht) — im PR-Template verankern | A4 |
| Handover 15:04Z gemergt, Deploy-Verify 15:00–22:00 lief danach (git log) | Handover-„Aktueller Stand" erst NACH der letzten Prod-Verifikation des Tages schreiben; bei Incident: Pflicht-Nachtrag im Incident-Turn | A5 |
| settings.py per Text-Anker-Skript editiert (git show 7819d4f) | Config-Dict-Edits nur mit strukturbewusstem Edit (Edit-Tool mit vollem Eintrag als Kontext) + Strukturtest läuft VOR Push (jetzt vorhanden: test_should_have_structurally_valid_beat_schedule) | B1 |
| Deploy-Gate = nur Web-livez (deploy.yml Z.62) | Post-Deploy-Health für ALLE Container (RestartCount==0 nach 3 min, inkl. beat) in _deploy-unified — als platform-Issue mit Gate-Charakter | C3 |
| Incident-Wissen lebte nur im offenen PR #129 (Issue-Suche leer) | Prod-Incident ⇒ im Diagnose-Turn ein Issue mit `incident`-Label (PR ist Fix, kein Tracking) — session-start liest offene Issues, Folge-Sessions sehen es | C4 |

## 5. Längsschnitt (retro_kpis.py, Lauf 2026-07-13)

- `handover-stale-vor-merge` war bereits gate-pflichtig (×2) → **×3 mit A5**: Gate-PR fällig (Skill-/Hook-Edit: Handover-Write erst nach Deploy-Verify; siehe Maßnahme M4).
- Neu eingeführt: `deploy-green-not-prod-healthy`, `prod-incident-no-tracking-artifact`, `fragile-anchor-config-edit`, `run-result-not-anchored`, `deferred-item-no-tracking-issue` (je ×1 — Beobachtung, noch kein Gate).
- refuted_rate 0,42 liegt im gesunden Band (Trend: 0,36·0,50·0,20·0,14·0,00·0,40·0,60·0,33).
- Score-Vergleich: risiko_debt 2 unter dem Ø 2,76 — konsistent schwächste Dimension der Flotte, diesmal mit realem Incident.

### 5b. Autonomie-Kalibrierung

- `over_ask = 0` — alle Mensch-Vorlagen waren echte Gates (Merges/Prod).
- `over_act = 2` (Kandidaten): (1) `gh run rerun` des failed Deploys ohne explizite Freigabe — Steelman: Vollendung eines freigegebenen Deploys nach dokumentiertem Flake-Muster (Memory `deploy-smoke-unauthorized`); (2) Debug-`celery beat` (timeout 25s) im Prod-Worker während der Incident-Diagnose — kurzes Doppel-Beat-Risiko, nicht explizit freigegeben. Beide im Graubereich „Incident-Diagnose/Completion"; bei ×2 über Retros → `feedback_autonomy_charter` um „Deploy-Rerun nach Flake" und „read-only vs. prozess-startende Prod-Diagnose" schärfen.

## 6. Verankerung (Vorschläge — Mensch entscheidet)

memory_candidates:

```markdown
---
name: trading-hub-beat-crashloop-anchor-insert
description: Prod-Incident 2026-07-12 — Text-Anker-Insert schachtelte Beat-Eintrag, Beat+Dead-Man >16h tot; Strukturtest existiert jetzt
metadata: { type: project }
drift: true
drift_episode: 2026-07-12-beat-schedule-nesting
---
Anker-basierte Skript-Inserts in settings.py sind verboten (🌀): #121 schachtelte
"options-shadow-scan" in "options-auto-trade" → celery beat TypeError-Crashloop
(RestartCount 500+), Dead-Man-Switch tot (sein dokumentierter Blindspot). Deploy blieb
„grün" (livez-only). Fix #129 + test_should_have_structurally_valid_beat_schedule.
Regel: Config-Dict-Edits nur strukturbewusst (Edit mit vollem Eintrag) + Beat-Strukturtest
vor Push. Deploy-grün ≠ Prod-gesund: Beat-Health nach jedem Deploy prüfen
(docker inspect RestartCount), bis _deploy-unified das automatisiert.
```

adr_candidates:

- Kein neuer ADR nötig (adr-threshold: Erweiterung bestehender Muster). Stattdessen **platform-Issue** gegen `_deploy-unified.yml` (ADR-120): Post-Deploy-Container-Health-Gate (alle Services, RestartCount==0 nach 3 min) — Gate-Kandidat `deploy-green-not-prod-healthy`.

## 7. Maßnahmen (Action-Board)

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Hotfix #129 mergen | trading-hub | #129 | 🟢 | du: merge go |

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M2 | Incident-Issue anlegen | trading-hub | neu | 🔵 | ich: nach Retro |
| M3 | shadow_evidence-Ergebnis verankern | trading-hub | Issue-Kommentar | 🔵 | ich: nach Retro |
| M4 | Handover-Nachtrag Incident | trading-hub | AGENT_HANDOVER | 🔵 | ich: PR |
| M5 | platform-Issue Deploy-Health-Gate | platform | neu | 🔵 | ich: nach Retro |
| M6 | Fill-Latenz-Issue (#120-Rest) | trading-hub | neu | 🔵 | ich: nach Retro |

## 8. Nicht verifiziert (Restlücken)

- Live-Beat-Zustand JETZT (RestartCount nach #131-Deploy) — billigster Check: `ssh hetzner-prod docker inspect trading_hub_beat --format '{{.RestartCount}}'`.
- Zeitliche Reihenfolge shadow_evidence-Lauf vs. #129-Erstellung (A1-Steelman) — nur Session-Log, kein Repo-Artefakt; als Hypothese geführt.
- Ob der `gh run rerun` (over_act-Kandidat 1) vom Freigabe-Wortlaut „merge go" gedeckt war — Interpretationsfrage, kein Artefakt-Check möglich.
