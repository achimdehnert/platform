---
id: ADR-248
title: "COMPOSE_PROJECT_NAME pro Hub fixieren + --remove-orphans scopen (Multi-Hub-Host)"
status: proposed
date: 2026-06-17
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh, meiki-lra, ttz-lif]
domains: [infra, deploy, docker, cross-repo]
supersedes: []
amends: []
depends_on: [ADR-156]
related: [ADR-156, ADR-157]
tags: [docker, compose, deploy, multi-hub, orphan-removal, infra]
scope:
  include_paths:
    - "docs/adr/ADR-248-*"
---

# ADR-248 — COMPOSE_PROJECT_NAME pro Hub fixieren + `--remove-orphans` scopen (Multi-Hub-Host)

## 1. Kontext

Auf dem Prod-Host laufen **mehrere Hubs** als getrennte Docker-Compose-Projekte auf
**einer** Engine. Docker leitet den Projektnamen (`COMPOSE_PROJECT_NAME`) sonst aus dem
Arbeitsverzeichnis ab — auf einem Multi-Hub-Host eine **Identitäts-Kollision**.

Beleg aus der Praxis (session-retro 2026-06-15/16):
- Der risk-hub-Deploy loggte wiederholt
  `⚠️ COMPOSE_PROJECT_NAME mismatch — running='137-hub' expected='risk-hub'`.
- `risk_hub_web` (Prod) verschwand **zweimal an einem Tag** ohne Docker-lifecycle-Event;
  die Root-Cause war ein Workflow auf dem Prod-Host-Runner mit einem ungescopten
  `docker rm -f` per `--filter publish=8090`, das den Prod-Container traf
  (`project_prod_web_outage_2026-06-15`).
- Dieselbe `137-hub`-Kollision ist über **zwei** Drift-Memories belegt
  (`project_prod_web_outage_2026-06-15`, plus die COMPOSE-Pin-Mitigation in `.env`).

`--remove-orphans` und ad-hoc `docker compose` ohne festen Projektnamen sind auf einem
Multi-Hub-Host die wahrscheinlichste Quelle für **Cross-Projekt-Orphan-Removal**.

## 2. Entscheidung

**Pro Hub einen festen, eindeutigen `COMPOSE_PROJECT_NAME`** + gescopte Removal-Operationen,
plattformweit verbindlich:

1. **`COMPOSE_PROJECT_NAME=<hub>`** in `/opt/<hub>/.env` UND in allen Deploy-Skripten
   pinnen (defense-in-depth: Skripte pinnen es bereits; `.env` schließt die ad-hoc-Lücke).
2. **`--remove-orphans` nur projekt-scoped** verwenden — nie global/ohne `-p <hub>`.
3. **Keine port-gefilterten `docker rm -f`** auf einem geteilten Host für Container, deren
   Port mit einem anderen Hub kollidieren kann; CI/Workflows auf dem Prod-Host-Runner
   verwenden hub-eigene Host-Ports (Beleg-Fix: risk-hub Staging-Gate `:8090`→`:8190`, #207).
4. **CI-Lint/Guard:** ein Deploy-Config-Lint prüft, dass jedes Hub-Compose einen expliziten
   Projektnamen setzt und kein ungescoptes `--remove-orphans`/port-`rm -f` enthält.

## 3. Betrachtete Alternativen

- **Ein Hub pro Host** — sauberste Isolation, aber teuer/unwirtschaftlich für die
  Hub-Flotte; verworfen.
- **Nur Watchdog (reaktiv)** — der risk-hub-Web-Watchdog heilt das Symptom, nicht die
  Ursache; bleibt als Defense-in-Depth, ersetzt aber das Pinnen nicht.
- **Status quo (impliziter Projektname)** — die belegte Ursache der Outage; verworfen.

## 4. Begründung im Detail

Die Kollision ist **strukturell** (Multi-Hub-Host) und **wiederkehrend** (zwei Memories) —
das macht sie laut session-retro-Längsschnitt zum **Gate-Kandidaten**, nicht zum N-ten
Notizzettel. Ein expliziter Projektname + gescopte Removal entfernt die Klasse von Fehlern,
nicht nur den Einzelfall.

## 5. Implementation Plan

- Bestand: risk-hub `.env` pinnt `COMPOSE_PROJECT_NAME=risk-hub` bereits (Mitigation
  2026-06-15); Staging-Gate-Port entkollidiert (#207).
- Rollout: gleiche Pin in `/opt/<hub>/.env` für alle Hubs auf dem Multi-Hub-Host.
- Guard: Deploy-Config-Lint-Regel ergänzen (explizit gesetzter Projektname; kein
  ungescoptes `--remove-orphans` / port-`rm -f`).

## 6. Risiken

- Ein bestehender Hub ohne Pin kann beim Umstellen kurz „verwaiste" Container hinterlassen
  (alter impliziter vs. neuer expliziter Name) — einmalig manuell bereinigen.

## 7. Konsequenzen

- (+) Cross-Projekt-Orphan-Removal als Outage-Klasse eliminiert.
- (+) Deploy-Logs eindeutig pro Hub.
- (−) Jeder Hub trägt eine zusätzliche `.env`-Zeile + Lint-Konformität.

## 8. Validation Criteria

- Kein `COMPOSE_PROJECT_NAME mismatch`-Warning mehr in Deploy-Logs.
- Deploy-Config-Lint schlägt fehl bei fehlendem Projektnamen oder ungescoptem Removal.
- Kein erneutes unerklärtes Verschwinden eines Prod-Web-Containers.

## 9. Glossar

- **Orphan** — Container eines Compose-Projekts, der nicht mehr im aktuellen Compose-File
  steht; `--remove-orphans` löscht ihn — projektweit, bei Namenskollision projektübergreifend.

## 10. Referenzen

- ADR-156 (Deploy-Infra), ADR-157 (Staging).
- risk-hub #207 (Staging-Gate-Port-Entkollision).
- Memories: `project_prod_web_outage_2026-06-15`, `feedback_risk_hub_deploy_pipeline`.

## 11. Changelog

- 2026-06-17: Initial (proposed) — aus session-retro 2026-06-17 (Längsschnitt:
  `137-hub`-COMPOSE-Kollision über 2 Memories belegt → Gate-Kandidat).
