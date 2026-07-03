---
id: ADR-264
title: "Kanonische Deployment-Strategie (Staging→Prod-Promotion) + Supersession-Gate gegen Deploy-ADR-Sprawl"
status: proposed
date: 2026-07-03
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
supersedes: [ADR-021, ADR-075, ADR-120, ADR-156, ADR-166, ADR-193, ADR-210]
related: [ADR-157, ADR-164, ADR-198, ADR-209, ADR-212]
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
- Dieses ADR supersedet ADR-021/075/120/156/166/193/210 (`supersedes:` oben; Statusflip der
  sieben auf `superseded_by: ADR-264` **bei Accept**).
- Ein CI-Check (`tools/check_deploy_adr_supersession.py`, mit diesem ADR ausgeliefert) blockt
  künftig jedes **neue** Deployment-Strategie-ADR (ID ≥ 264) ohne nicht-leeres `supersedes:`
  bzw. ohne begründeten `supersedes_waiver:`. Grandfathering per Nummer; heutiger Baum grün.
  **Das ist der einzige Hebel, der Anlauf #7 strukturell von Anlauf #8 trennt** (Maintainer-
  Perspektive KONZ-011 §13).

### D2 — Promotion-Pipeline mit Required-Check + Rollback-Vorbedingung
- `merge → Staging` (auto), dann **gegatete Promotion `Staging → Prod`** als GitHub
  **Required-Status-Check** — nicht der bisherige `on: push [main]`-Direktschlag.
- **Rollback-Fähigkeit ist harte Vorbedingung** jedes Promotion-Gates (kein Gate ohne
  definierten Rückrollpfad). Die Selbstabschaltung (D3) zieht nur Standing-Automatik zurück,
  **nie** das Promotion-Gate selbst.
- Rollout: erst **ein** nicht-kundenkritischer Pilot grün, dann Fleet — kein Big-Bang.
- Hotfix/Incident-Deploys (`/hotfix`, `/incident`) unterliegen **demselben** Gate oder einer
  bewusst separaten, ebenso erzwungenen Eskalationsstufe — kein by-Konvention-Bypass.

### D3 — Geschlossener Signal→Gate-Loop mit datiertem Exit
- `prod-uptime-canary` wird deterministisch (Label-Upsert + Close-when-green — siehe PR #877)
  und dient als Post-Promotion-Health-Check (ein Signal, zwei Zwecke, keine zweite Wahrheit).
- **Datiertes, gemessenes Exit-Kriterium** nach ADR-209-Vorbild (z. B. „≥90 % Repos auf
  Promotion-Pipeline UND alte Reusables 0 aktive Consumer über 30 Tage → Alt-Pfade löschen,
  Gate-Doku `retired`"), verankert mit **Wiedervorlage-Issue + Prüf-Owner** — nicht nur Prosa.

## Consequences

**Positiv:** eine prüfbare SSoT; merge≠Prod; erzwungene statt behauptete Konsolidierung;
selbst-schließender Monitoring-Loop; struktureller Schutz gegen künftigen Sprawl.
**Negativ / Kosten:** Übergangsphase mit koexistierenden Deploy-Pfaden (Alt-Reusables +
neues Gate) bis zum Cutover — deshalb der harte, datierte Exit in D3; Rollout-Aufwand
(Required-Check pro Repo). **Risiko** ohne D1-CI-Check: dieses ADR wird selbst Sprawl-Beitrag
#7 — daher ist der Check Teil der Definition-of-Done, nicht optional.

## Supersession-Notiz

Bis Accept bleiben die sieben gelisteten ADRs `accepted`/`proposed` gültig; erst mit Accept
dieses ADR werden sie `superseded_by: ADR-264` gesetzt. `related:` verweist auf die
**komplementären** Infra-ADRs (157/164/198/212 = Ports/Traefik/Edge) und ADR-209 (Muster-
Blaupause), die **nicht** abgelöst werden.
