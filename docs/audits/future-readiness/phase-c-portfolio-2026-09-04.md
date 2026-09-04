# Future-Readiness Phase C — Portfolio-Auswertung (2026-09-04)

Quelle: `tools/future_readiness_portfolio.py dev-hub:docs/audits/future-readiness/2026-09-03/repositories/ (origin/main @ b654e20)` über die je Repo abgelegten Ergebnisdateien des Phase-C-Laufs (dev-hub, privat). Auftrag [platform#2737](https://github.com/achimdehnert/platform/issues/2737).

Die Zahlen stammen aus dem Lauf vom 2026-09-03 unter **Rubrik 2.3**. Mit dem Owner-Wort vom
2026-09-04 senkt v2.4 die Schwelle, ab der eine Dimension in den Score eingeht, auf „≥ 3
beantwortete Fragen ODER ≥ 50 %" (Kandidat 37a); ein Neulauf über die 56 Repos folgt und wird
die Readiness-Werte hier verschieben. Bis dahin gilt diese Datei als Stand des v2.3-Laufs.

Diese Datei enthält nur Aggregate, Repo-Namen und Readiness-Bänder — keine Personendaten, keine Secrets, keine Einstellungswerte einzelner privater Repos (platform ist öffentlich; Regel 11* der Regelbilanz).

## Grundmenge

| Kennzahl | Wert |
|---|---|
| Ergebnisdateien gewertet | 56 |
| ältere Läufe desselben Repos verdrängt | 3 |
| Nicht-Ergebnisse übersprungen | 0 |
| davon mit Feld `readiness` | 56 |
| ohne Feld `readiness` | 0 |

## Verteilung Readiness

| Kennzahl | Wert |
|---|---|
| Minimum | 11 |
| Q1 (25 %) | 42.2 |
| Median | 52 |
| Q3 (75 %) | 56.2 |
| Maximum | 74 |

Quantile mit linearer Interpolation (Position = p·(n−1) auf der sortierten Liste, wie `statistics.quantiles(..., method="inclusive")`); bei geradem n ist der Median das Mittel der beiden mittleren Werte.

## Repos nach Readiness-Band

| Band | Repos | Namen |
|---|---|---|
| 0-24 | 4 | achimdehnert/ci-sichtbarkeit-probe, achimdehnert/ci-sichtbarkeit-probe-caller, achimdehnert/decks-hub, achimdehnert/molkerei-landing |
| 25-49 | 19 | achimdehnert/apo-hub, achimdehnert/bahn-hub, achimdehnert/cad-hub, achimdehnert/doc-hub, achimdehnert/ifc-mcp, achimdehnert/iil-codeguard, achimdehnert/iil-demo-fixture, achimdehnert/iil-enrichment, achimdehnert/iil-ingest, achimdehnert/infra-deploy, achimdehnert/lastwar-bot, achimdehnert/manuskripte, achimdehnert/music-lab, achimdehnert/news-hub, achimdehnert/robo-lab, achimdehnert/schutztat-reporting, achimdehnert/shared-ci, meiki-lra/meiki-hub, ttz-lif/ttz-hub |
| 50-69 | 29 | achimdehnert/137-hub, achimdehnert/aifw, achimdehnert/authoringfw, achimdehnert/billing-hub, achimdehnert/coach-hub, achimdehnert/design-hub, achimdehnert/dms-hub, achimdehnert/gaeb-toolkit, achimdehnert/iil-adrfw, achimdehnert/iil-django-commons, achimdehnert/iil-reflex, achimdehnert/iil-testkit, achimdehnert/illustration-hub, achimdehnert/lastwar-alliance-ops, achimdehnert/learn-hub, achimdehnert/learnfw, achimdehnert/nl2cad, achimdehnert/odoo-hub, achimdehnert/outlinefw, achimdehnert/pptx-hub, achimdehnert/promptfw, achimdehnert/researchfw, achimdehnert/trading-hub, achimdehnert/weltenfw, achimdehnert/weltenhub, achimdehnert/writing-hub, iilgmbh/risk-hub, meiki-lra/frist-hub, meiki-lra/meiki-dms |
| 70-84 | 4 | achimdehnert/dev-hub, achimdehnert/mcp-hub, achimdehnert/platform, achimdehnert/travel-beat |
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
| Findings gesamt | 970 |
| davon P1 | 53 |
| davon P2 | 773 |
| davon P3 | 144 |
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
| 4 | D08.4 · security-md | 55 | 55 |
| 5 | D11.2 · third-party-notices | 55 | 55 |

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

## Verdrängte Dateien

Von einer `*.phase-c.json` desselben Repos verdrängt (älterer Canary-Lauf): achimdehnert-aifw.json, achimdehnert-dev-hub.json, achimdehnert-platform.json

## Anmerkungen

- Für die drei Canary-Repos (aifw, dev-hub, platform) liegen zwei Ergebnisse nebeneinander: der Modell-Lauf in `<repo>.json` und der deterministische Phase-C-Lauf in `<repo>.phase-c.json`. Gewertet ist der Phase-C-Lauf; ohne diese Vorrangregel käme man auf 56 P1 in 36 Repos statt auf 53 in 34.
- Die Zwischenstands-Zusammenfassung im dev-hub nennt „53 P1 in 33 Repos", listet darunter aber 34 Repo-Namen, deren Zahlen sich zu 53 addieren. Gemessen sind es 34 Repos — die 33 im Fließtext sind ein Zählfehler dort, kein abweichendes Ergebnis.
- Alle 56 Repos liegen in `insufficient-evidence`: bei T1 ohne Flotten-Grep, CVE-Scan und Doku-Inhalten bleibt die Deckung unter der 0,80-Schwelle. Der Readiness-Wert ist damit ein Vergleichswert innerhalb des Laufs, keine Reifegrad-Aussage.

