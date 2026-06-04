---
description: Geerdete, adversariale Session-Retrospektive — sammelt git/gh/CI als Ground Truth, urteilt in frischem Kontext (Richter≠Angeklagter), falsifiziert jeden Befund, schlägt kopierfertige Verankerung + Scorecard vor. Schreibt Report nach ~/shared/.
mode: write
---

# /session-retro — Geerdeter, adversarialer Session-Review

> **Zweck:** Eine zurückliegende Arbeitssession schonungslos reviewen — aber so, dass die
> vier Konstruktionsfehler des klassischen „Paste-Prompt-Retros" gelöst sind: Angeklagter≠
> Richter, Artefakt-Erdung statt Erinnerung, geschlossener Lessons-Loop, Falsifikation der
> eigenen Befunde.
>
> **Wann:** Nach größeren Umbau-/Architektur-Sessions; am Sitzungsende.
> **Wann NICHT:** Trivial-Edits (ein Tippfehler-Fix braucht keinen Retro) → höchstens `lean`.
> **Deterministische Engine (optional):** Für schwere Läufe den JS-Workflow
> `~/shared/session-retro.workflow.js` via Workflow-Tool starten (parallele Finder +
> pipeline-erzwungene Falsifikation). Dieser Command ist die portable Prosa-Variante mit
> identischer Methode.

## Eiserne Regeln — die 4 Fixes (nicht verhandelbar)

1. **Richter ≠ Angeklagter.** Urteile NIE aus deinem Session-Gedächtnis. Jeden Befund über
   einen **frischen Subagenten** (Agent-Tool) erzeugen, der nur die Artefakte sieht — nicht
   deine Erzählung. (Self-Review verbucht eigene Fehler als Erfolge.)
2. **Evidenz vor Behauptung.** Jeder Befund braucht einen harten Artefakt-Beleg
   (repo#PR, Commit-SHA, Datei:Zeile, CI-Run). Kein Beleg → kein Befund. „Eindruck" zählt nicht.
3. **Falsifikation.** Jeden Befund einem Widerlegungs-Pass aussetzen (Steelman der
   Original-Entscheidung). Nur Überlebende bleiben — sonst entsteht performative Kritik.
4. **Geschlossener Loop.** Lessons NICHT als Prosa versanden lassen → als **kopierfertige**
   Memory-/ADR-/CLAUDE.md-Vorschläge ausgeben. Verankerung entscheidet der Mensch.

## Phase 0 — Right-Sizing
Footprint messen (PRs / Repos / Prod-Schritte / Migrationen / ADRs). **lean** (≤2 PRs,
1 Repo, kein Prod/Migration/ADR) → 2 Dimensionen, knappe Scorecard. **full** → 3 Dimensionen
+ volle Scorecard.

## Phase 1 — Collect (Ground Truth, frischer Ermittler)
Ein Subagent sammelt **ausschließlich aus Artefakten** (kein Self-Report):
- `gh pr list --repo <owner>/<repo> --state all --search "updated:>=<datum>"` (+ `gh issue list`)
- `git -C ~/github/<repo> log --oneline --since=<…>` + `git diff --stat` wo sinnvoll
- CI/main-Status der betroffenen Repos (`gh run list --branch main`)

**Aktiv nach red_flags suchen, die ein Self-Review systematisch übersieht:**
OPEN-PR überholt von späterem MERGED-PR zum selben Issue (Duplikat/dangling) · mehrere PRs
„Closes" dasselbe Issue · rote Required-Gates auf offenen PRs · Migrations-Nummern-Kollision ·
Issue offen geblieben trotz gemergtem Fix.

> **Repos verbindlich halten:** vom Menschen genannte Repos sind in-scope — niemals als
> „separater Workstream" wegklassifizieren. Falls ein Transkript-Pfad gegeben ist, erdet er
> die Session-Grenze (gewinnt bei Konflikt gegen die Artefakt-Heuristik).

## Phase 2 — Find (frischer Kontext, je Dimension)
Je Dimension ein **eigener** Subagent (kennt die Session-Erzählung nicht), geerdet im Footprint:
- **Soll-Ist & Scope** — Ziel vs. real Geliefertes; Scope Creep; still Weggelassenes; Offenes,
  das das Ziel verfehlt.
- **Entscheidungen & Fehler** — tragfähig vs. fragwürdig; Anti-Patterns; Konventionsverstöße;
  neue Tech-Debt; verfrühte/zu enge Festlegungen.
- **Prozess & Kollaboration** — Rework, Duplikat-/dangling-PRs, rote Gates, unklare Steuerung,
  fehlende frühe Checks (Stand von main / parallele Arbeit nicht geprüft).

Je Befund: Schweregrad (kritisch/hoch/mittel/niedrig) + Root Cause (5-Why) + Kategorie
(Wissenslücke / Prozesslücke / Kommunikation / verfrühte Festlegung / fehlende Validierung / Werkzeug).

## Phase 3 — Verify (Falsifikation)
Pro Befund ein **Skeptiker-Subagent**: versuche zu WIDERLEGEN, prüfe den Beleg per gh/git nach.
Default „refuted" bei nicht-tragendem Beleg. Nur überlebende Befunde gehen in den Report.

## Phase 4 — Anchor (schließen + Längsschnitt)
- **Executive Summary** (max 5 Bullets).
- **Scorecard 1–5** je Dimension **mit Anker-Begründung** (Zahl aus den Befunden ableiten,
  nicht aus dem Bauch): Zielerreichung · Architektur/Design · Code & Konventionstreue ·
  Risiko-/Debt-Management · Prozess-Effizienz · Entscheidungsqualität.
- **Kopierfertige** `memory_candidates` + `adr_candidates` (du schreibst sie NICHT selbst).
- **Längsschnitt — der eigentliche Hebel:** gegen die bestehende Memory abgleichen
  (`<auto-memory>/MEMORY.md`). Ist ein Befund eine **Wiederholung** (gleiche Kategorie mehrfach
  in dieser Session ODER schon als Drift-Memory dokumentiert) → Kandidat für ein **HARTES GATE**
  (Hook / CI), nicht für den N-ten Notizzettel. Die Memory-Schicht hält offensichtlich nicht.
- **Top-3-Maßnahmen** für die nächste Sitzung (priorisiert, konkret, umsetzbar).
- Report schreiben nach `~/shared/session-retro-<datum>.md`.

## Anti-Patterns
- ❌ Aus dem eigenen Session-Kontext urteilen (in-context self-review).
- ❌ Befund ohne harten Artefakt-Beleg.
- ❌ Befunde nicht falsifizieren — performative Kritik durchlassen.
- ❌ Memory/ADR/CLAUDE.md selbst schreiben statt nur vorschlagen.
- ❌ Ein wiederkehrendes Muster als „noch ein Memo" abtun statt als Gate-Kandidat zu eskalieren.
- ❌ Vom Menschen genannte Repos als „separaten Workstream" aus dem Scope kippen.

## Changelog
- 2026-06-04: Initial. Aus einem Advocatus-Diabolus-Review des Paste-Prompt-Retros
  (`iil-prompts-retrospective`) hervorgegangen; die 4 Fixes + der Längsschnitt-Hebel sind die
  Lehren daraus. Deterministische Engine: `~/shared/session-retro.workflow.js`.
