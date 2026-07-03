---
id: ADR-264
title: "Kanonische Deployment-Strategie (Staging→Prod-Promotion) + Supersession-Gate gegen Deploy-ADR-Sprawl"
status: proposed
date: 2026-07-03
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
supersedes: [ADR-021, ADR-075, ADR-120, ADR-156, ADR-210]
related: [ADR-157, ADR-164, ADR-166, ADR-193, ADR-198, ADR-209, ADR-212]
tags: [deployment, staging, prod, promotion-pipeline, ssot, supersession, rollback]
---

# ADR-264 — Kanonische Deployment-Strategie + Supersession-Gate

> Konzept-Basis: **KONZ-platform-011** (`docs/konzepte/`, T3, 3-Agenten-Adversariat).
> Dieses ADR operationalisiert dessen Empfehlung. Status `proposed` — die Supersession der
> unten gelisteten ADRs wird **bei Accept** wirksam (deren Status → `superseded_by: ADR-264`).

## Context and Problem Statement

Die Deployment-Strategie ist evolutionär akkretiert, nicht geplant — belegt:

- ~15 Deploy/Staging-Strategie-ADRs. **Zwei tragen „unified" im Titel, beide `accepted`,
  keiner supersedet den anderen**: ADR-021 (`unified-deployment-pattern`, 2026-02-10) und
  ADR-120 (`unified-deployment-pipeline`, 2026-03-11, `supersedes: []`). Zwei weitere stehen
  seit Monaten `proposed` (ADR-156 seit 2026-04-02, ADR-210 seit 2026-05-19).
- Der Deploy-Fluss ist **merge = Prod** (`on: push [main]`); Staging existiert (53
  `ports.yaml`-Einträge, `STAGING_*`-Secrets), ist aber **Parallelspur, kein Gate**.
- Das Monitoring (`prod-uptime-canary`) erkennt Ausfälle korrekt, aber der Loop ist **offen**
  (Detektion ohne erzwungene Remediation).

**Kernbefund (unabhängig von zwei Adversarial-Agenten bestätigt):** Der eigentliche Bug ist
das **leere `supersedes:`-Feld**, nicht die ADR-Anzahl. Ohne erzwungene Supersession ist jede
neue „Vereinheitlichung" nur Sprawl-Beitrag #N+1.

## Decision Drivers

1. **SSoT** — genau eine kanonische Deployment-ADR, prüfbar, gegen die neuer Code validiert.
2. **Zwangsentscheidung** — Alt-ADRs werden abgelöst, nicht danebengestellt.
3. **Prod-Sicherheit** — merge=Prod ist die teuerste latente Klasse (unverifizierte
   Prod-State-Änderung); ein Gate muss erzwingbar sein (GitHub Required-Check), nicht nur
   informativ.
4. **Deploy ≠ CI** — Deploy-Failures sind nicht idempotent/replaybar (DB-Migration, echte
   Nutzer); das `ci-green-program`-Muster (ADR-209) trägt nur **mit Rollback als Vorbedingung**.

## Decision

Drei **hart entkoppelte** Bausteine (kein Monolith):

### D1 — Supersession-Gate (der Durabilitäts-Scharnier)
- Dieses ADR supersedet die **fünf** echten Strategie-/Pipeline-ADRs **021/075/120/156/210**
  (`supersedes:` oben; Statusflip auf `superseded_by: ADR-264` **bei Accept**). **ADR-166**
  (`.ship.conf`-Format + `/livez/`) und **ADR-193** (laufende `DC-001…009`-Compliance-Checks in
  iil-codeguard) sind nach externem Review (AD-4) **komplementäre, weiterhin gültige** operative
  Substanz → `related:`, **nicht** abgelöst.
- **Supersession ist nicht nur Metadaten** (Verschärfung REC-1/REC-3): pro abgelöster ADR eine
  Ein-Satz-Begründung *übernommen / ersetzt / verworfen* + Zielabschnitt in ADR-264 oder Folge-ADR
  (Supersession-Matrix, **vor Accept** auszufüllen). Der CI-Check erzwingt nur die Nicht-Leerheit;
  die *semantische* Sauberkeit erzwingt die Matrix im Accept-Review.
- **`supersedes_waiver:` nur mit Pflichtfeldern** (REC-2): Owner · Ablaufdatum · Grundkategorie ·
  betroffene ADRs · Wiedervorlage-Issue. Waiver **ohne Ablaufdatum → blockiert** (sonst
  akkumulieren stille Ausnahmen, M28-3).
- Ein CI-Check (`tools/check_deploy_adr_supersession.py`, mit diesem ADR ausgeliefert) blockt
  künftig jedes **neue** Deployment-Strategie-ADR (ID ≥ 264) ohne nicht-leeres `supersedes:`
  bzw. ohne begründeten `supersedes_waiver:`. Grandfathering per Nummer; heutiger Baum grün.
  **Das ist der einzige Hebel, der Anlauf #7 strukturell von Anlauf #8 trennt** (Maintainer-
  Perspektive KONZ-011 §13). Grenze (AD-3): der Titel-Klassifikator fängt *ADR*-Sprawl, **nicht**
  Deploy-Änderungen an `*.yml` — dafür der separate Referenz-Lint (KONZ-011 REC-4).

### D2 — Promotion-Pipeline mit Required-Check + Rollback-Vorbedingung
- `merge → Staging` (auto), dann **gegatete Promotion `Staging → Prod`** als GitHub
  **Required-Status-Check** — nicht der bisherige `on: push [main]`-Direktschlag.
- **Rollback-Fähigkeit ist harte Vorbedingung** jedes Promotion-Gates (kein Gate ohne
  definierten Rückrollpfad). Die Selbstabschaltung (D3) zieht nur Standing-Automatik zurück,
  **nie** das Promotion-Gate selbst.
- Rollout: erst **ein** nicht-kundenkritischer Pilot grün, dann Fleet — kein Big-Bang.
- Hotfix/Incident-Deploys (`/hotfix`, `/incident`) unterliegen **demselben** Gate oder einer
  bewusst separaten, ebenso erzwungenen Eskalationsstufe — kein by-Konvention-Bypass.

**Verschärfungen aus externem Review (o3):**
- **Alte Prod-Pfade technisch stilllegen** (AC, REC-4/AD-5): sobald ein Repo auf die
  Promotion-Pipeline migriert ist, dürfen direkte `on: push [main]`-Deploys + alte Reusables
  dort **nicht mehr produktiv deployen** können (sonst ist das Required-Gate Theater). Analog
  Branch-Protection-Check-Namen konsistent halten (M28-4, koppelt an ADR-242).
- **Rollback operationalisieren** (REC-5/AD-6/M28-7): das ADR benennt konkret App-Version-Rollback,
  DB-Abwärtskompatibilität, Umgang mit *irreversiblen* Migrationen, Datenrestore, Background-Jobs,
  externe Side-Effects. **Vor Fleet-Rollout ≥1 dokumentierter Rollback-Drill im Pilot** (mit
  Migration oder bewusst begründetem migrationsfreien Testfall) — „Rollback vorhanden" ohne Übung
  zählt nicht (REC-6).
- **Break-Glass definiert** (REC-7/AD-7): für Hotfix/Incident — wer darf auslösen, welche Checks
  bleiben required, welche werden ersetzt, welche Audit-/Postmortem-Pflicht entsteht.

### D3 — Geschlossener Signal→Gate-Loop mit datiertem Exit
- `prod-uptime-canary` wird deterministisch (Label-Upsert + Close-when-green — siehe PR #877)
  und dient als Post-Promotion-Health-Check (ein Signal, zwei Zwecke, keine zweite Wahrheit).
- **Datiertes, gemessenes Exit-Kriterium** nach ADR-209-Vorbild (z. B. „≥90 % Repos auf
  Promotion-Pipeline UND alte Reusables 0 aktive Consumer über 30 Tage → Alt-Pfade löschen,
  Gate-Doku `retired`"), verankert mit **Wiedervorlage-Issue + Prüf-Owner** — nicht nur Prosa.

**Verschärfungen aus externem Review (o3):**
- **Canary als Betriebsregel, nicht nur Issue-Erzeuger** (REC-8/AD-8/M28-6): Post-Promotion-Health
  mit Timeout · Erfolgskriterium · Flapping-/Wartungsfenster-Regel · **Hold/Revert-Entscheidung**
  (Promotionsperre bei Rot). Der Label-Upsert + Close-when-green aus PR #877 ist die Basis, nicht
  das Ziel.
- **Exit misst Betriebsfähigkeit, nicht nur Konvergenz** (REC-12/AD-11): Kriterium zählt
  *erfolgreiche Promotions* + *getestete Rollbacks* + Incident-Verhalten nach Migration — nicht nur
  „Repo nutzt Pipeline". Deploy-Konvergenz ≠ Regelkonformität.
- **Alt-Reusables erst löschen, wenn auch selten-/Notfall-/archivierte Deploy-Pfade migriert sind**
  (REC-10/AD-10/M28-5): „0 aktive Consumer über 30 Tage" allein übersieht Disaster-Recovery- und
  Low-Frequency-Pfade → historische Wiederherstellbarkeit sichern, bevor gelöscht wird.

### D4 — Ownership (neu, REC-11/M28-2)
Benannter Owner für Gate-Logik, Branch-Protection-Konventionen/Check-Namen, Canary-Regeln und
Waiver-Audits über **≥2 Jahre** — inkl. Test-Suite + Änderungshistorie für die Gate-Skripte.
Ohne benannten Owner verrottet die Gate-Logik (Realbeleg: ADR-185 `proposed` liegengeblieben).

## Consequences

**Positiv:** eine prüfbare SSoT; merge≠Prod; erzwungene statt behauptete Konsolidierung;
selbst-schließender Monitoring-Loop; struktureller Schutz gegen künftigen Sprawl.
**Negativ / Kosten:** Übergangsphase mit koexistierenden Deploy-Pfaden (Alt-Reusables +
neues Gate) bis zum Cutover — deshalb der harte, datierte Exit in D3; Rollout-Aufwand
(Required-Check pro Repo). **Risiko** ohne D1-CI-Check: dieses ADR wird selbst Sprawl-Beitrag
#7 — daher ist der Check Teil der Definition-of-Done, nicht optional.

## Supersession-Notiz

Bis Accept bleiben die **fünf** gelisteten ADRs (021/075/120/156/210) `accepted`/`proposed`
gültig; erst mit Accept werden sie `superseded_by: ADR-264` gesetzt. `related:` verweist auf die
**komplementären, NICHT abgelösten** ADRs: 157/164/198/212 (Ports/Traefik/Edge), ADR-209
(Muster-Blaupause) sowie **166** (`.ship.conf`/`/livez/`) und **193** (`DC-*`-Compliance-Checks) —
letztere zwei nach externem Review (AD-4) aus `supersedes:` herausgenommen.

## Externe Zweitmeinung (openai/o3, 2026-07-03) — Audit + Verdikt

Anbieter-fremde Zweitrunde via `/adr-handoff-extern` (manueller Pfad; Orchestrator-`--auto` war
durch mcp-hub#128 blockiert). **Verdikt: überarbeiten** — Stoßrichtung richtig, aber zwei weiche
Stellen (semantisch belastbare Supersession statt Metadatenpflicht; operativ nachgewiesene
Rollback-/Gate-Erzwingung statt Pipeline-Absicht). Eingearbeitet in D1–D4 oben.

**Tag-Tabelle (Rückfluss-Gate, Step 5):**

| Befund/REC | Verdikt | Aktion in ADR-264 |
|---|---|---|
| AD-4 (166/193 lebende Substanz) | valid | **`supersedes:` 7→5**, 166/193 → `related:` |
| AD-1 / REC-1 (Metadaten-Bürokratie) | valid | D1: Supersession-Begründung je ADR (übernommen/ersetzt/verworfen) |
| AD-2 / M28-3 / REC-2 (Waiver-Schlupfloch) | valid | D1: Waiver-Pflichtfelder, ohne Ablaufdatum blockiert |
| REC-3 (Supersession-Matrix) | valid | D1: Matrix vor Accept |
| AD-3 (impliziter Klassifikator) | valid-partial | D1-Grenze benannt: Gate fängt ADR-Sprawl, nicht `*.yml` (→ KONZ-011 REC-4) |
| AD-5 / M28-4 / REC-4 (Prod-Pfade stilllegen) | valid | D2: AC „alte Pfade technisch tot" |
| AD-6 / M28-7 / REC-5+6 (Rollback operationalisieren + Drill) | valid | D2: konkrete Rollback-Dimensionen + Pilot-Drill |
| AD-7 / REC-7 (Break-Glass) | valid | D2: Break-Glass definiert |
| AD-8 / M28-6 / REC-8 (Canary Hold/Revert) | valid | D3: Canary als Betriebsregel mit Promotionsperre |
| AD-10 / M28-5 / REC-10 (seltene/Notfall-Pfade) | valid | D3: erst löschen nach Migration dieser Pfade |
| AD-11 / REC-12 (ci-green zu optimistisch) | valid | D3: Exit misst Promotions/Rollbacks, nicht nur Konvergenz |
| M28-2 / REC-11 (Ownership) | valid | **D4 neu**: benannter Owner ≥2 Jahre |
| AD-9 / REC-9 (Cutover-Aufwand) | valid | Rollout-Detail → 30/60/90 in KONZ-011 §13 (Build-Phase) |
| M28-1 (zu abstrakt) | valid-caution | Gegengewicht: D1–D4 sind konkrete AC, keine Prosa-SSoT |
| PRO-1…6 (Proponent) | valid-affirmation | keine Änderung — bestätigen die Stoßrichtung |
| OOTB-2 (zentraler Deploy-Service) | out-of-scope | vom Reviewer selbst verworfen (Overkill für ~50 Repos) |
| OOTB-3 (Progressive Delivery/Flags) | valid-ergänzend | als Option für riskante Migrationen in Build-Phase prüfen (nicht Ersatz) |
