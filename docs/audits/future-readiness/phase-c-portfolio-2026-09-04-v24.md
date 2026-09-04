# Future-Readiness Phase C — Portfolio-Auswertung (2026-09-04)

Quelle: `tools/future_readiness_portfolio.py dev-hub docs/audits/future-readiness/2026-09-04` über die je Repo abgelegten Ergebnisdateien des Phase-C-Laufs (dev-hub, privat). Auftrag [platform#2737](https://github.com/achimdehnert/platform/issues/2737).

Diese Datei enthält nur Aggregate, Repo-Namen und Readiness-Bänder — keine Personendaten, keine Secrets, keine Einstellungswerte einzelner privater Repos (platform ist öffentlich; Regel 11* der Regelbilanz).

**Rubrik 2.4** (37a Dimensions-Schwelle >=3 answered ODER >=50 %, #2805) · **Neulauf 2026-09-04** (vollständige Wiederholung von Phase C 2026-09-03 über dieselben 56 Repos) · Werkzeugstand: platform `origin/main` @ `b7ed5a2b` (nach Merge #2803 + #2805). Die v2.3-Datei `phase-c-portfolio-2026-09-04.md` (Zahlen aus dem Lauf 2026-09-03) bleibt unverändert stehen.

## Grundmenge

| Kennzahl | Wert |
|---|---|
| Ergebnisdateien gewertet | 56 |
| ältere Läufe desselben Repos verdrängt | 0 |
| Nicht-Ergebnisse übersprungen | 0 |
| davon mit Feld `readiness` | 56 |
| ohne Feld `readiness` | 0 |

## Verteilung Readiness

| Kennzahl | Wert |
|---|---|
| Minimum | 14 |
| Q1 (25 %) | 43 |
| Median | 53 |
| Q3 (75 %) | 56.2 |
| Maximum | 74 |

Quantile mit linearer Interpolation (Position = p·(n−1) auf der sortierten Liste, wie `statistics.quantiles(..., method="inclusive")`); bei geradem n ist der Median das Mittel der beiden mittleren Werte.

## Repos nach Readiness-Band

| Band | Repos | Namen |
|---|---|---|
| 0-24 | 4 | achimdehnert/ci-sichtbarkeit-probe, achimdehnert/ci-sichtbarkeit-probe-caller, achimdehnert/decks-hub, achimdehnert/molkerei-landing |
| 25-49 | 20 | achimdehnert/apo-hub, achimdehnert/design-hub, achimdehnert/doc-hub, achimdehnert/gaeb-toolkit, achimdehnert/ifc-mcp, achimdehnert/iil-codeguard, achimdehnert/iil-demo-fixture, achimdehnert/iil-enrichment, achimdehnert/iil-ingest, achimdehnert/infra-deploy, achimdehnert/lastwar-alliance-ops, achimdehnert/lastwar-bot, achimdehnert/manuskripte, achimdehnert/music-lab, achimdehnert/news-hub, achimdehnert/robo-lab, achimdehnert/schutztat-reporting, achimdehnert/shared-ci, meiki-lra/meiki-hub, ttz-lif/ttz-hub |
| 50-69 | 29 | achimdehnert/137-hub, achimdehnert/aifw, achimdehnert/authoringfw, achimdehnert/bahn-hub, achimdehnert/billing-hub, achimdehnert/cad-hub, achimdehnert/coach-hub, achimdehnert/dms-hub, achimdehnert/iil-adrfw, achimdehnert/iil-django-commons, achimdehnert/iil-reflex, achimdehnert/iil-testkit, achimdehnert/illustration-hub, achimdehnert/learn-hub, achimdehnert/learnfw, achimdehnert/mcp-hub, achimdehnert/nl2cad, achimdehnert/odoo-hub, achimdehnert/outlinefw, achimdehnert/pptx-hub, achimdehnert/promptfw, achimdehnert/researchfw, achimdehnert/trading-hub, achimdehnert/travel-beat, achimdehnert/weltenfw, achimdehnert/weltenhub, iilgmbh/risk-hub, meiki-lra/frist-hub, meiki-lra/meiki-dms |
| 70-84 | 3 | achimdehnert/dev-hub, achimdehnert/platform, achimdehnert/writing-hub |
| 85-100 | 0 | — |

## Klassen und Archetypen

| readiness_class | Repos |
|---|---|
| insufficient-evidence | 56 |

| Archetyp | Repos |
|---|---|
| django-app | 20 |
| python-package | 15 |
| other | 15 |
| ci-workflow | 5 |
| docs | 1 |

## Findings

| Kennzahl | Wert |
|---|---|
| Findings gesamt | 944 |
| davon P1 | 53 |
| davon P2 | 746 |
| davon P3 | 145 |
| Repos mit mindestens einem P1 | 34 |

### P1-Findings nach Dimension (Top 10)

| # | Dimension | P1-Findings | Repos |
|---|---|---|---|
| 1 | D06 | 45 | 33 |
| 2 | D05 | 8 | 8 |

### Häufigste Finding-Schlüssel (Top 5)

Schlüssel normalisiert als `question_id` + `finding_type` (im `locator` mit `|` getrennt, in der Tabelle wegen der Pipe als `·`) — der repo-unabhängige Teil des `locator`; der volle `key` trägt zusätzlich Org/Repo und den Locator-Hash und ist damit je Repo einmalig.

| # | Schlüssel | Repos | Findings |
|---|---|---|---|
| 1 | D02.2 · lockfile | 55 | 55 |
| 2 | D05.1 · required-checks | 55 | 55 |
| 3 | D05.2 · review-pflicht | 55 | 55 |
| 4 | D04.5 · typen-in-ci | 53 | 53 |
| 5 | D06.3 · dependabot-alerts | 53 | 53 |

## Feldabdeckung über die Berichte

| Feld | Berichte mit Feld | ohne Feld |
|---|---|---|
| readiness | 56 | 0 |
| evidence_coverage | 56 | 0 |
| readiness_class | 56 | 0 |
| archetype | 56 | 0 |
| findings | 56 | 0 |
| scores | 56 | 0 |
| controls | 56 | 0 |
| rubric_version | 56 | 0 |
| depth | 56 | 0 |
| calculation | 56 | 0 |

## Anmerkungen

- Neulauf 2026-09-04, Rubrik v2.4 (37a Dimensions-Schwelle, D02.1-Fix), 56 Repos, 0 Fehlschlaege.

