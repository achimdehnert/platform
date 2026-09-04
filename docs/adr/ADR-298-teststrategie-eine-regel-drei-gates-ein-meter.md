---
status: proposed
decision_date: 2026-08-29
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: [ADR-057, ADR-058, ADR-155, ADR-184]
amends: [ADR-100, ADR-179]
related: [ADR-074, ADR-108, ADR-174, ADR-233]
implementation_status: in_progress
last_reviewed: 2026-08-29
staleness_months: 6
tags: [testing, ci, shared-ci, coverage, iil-testkit, governance]
---

# ADR-298: Teststrategie der Flotte — eine Regel, drei Gates, ein Meter

> **Status `proposed`:** Entwurf aus Auftrag [platform#2428](https://github.com/achimdehnert/platform/issues/2428)
> (Kriterium 3). Accept ist Owner-Entscheidung; erst dann wechseln die vier
> ersetzten ADRs auf `superseded`.

## Kontext

Die Plattform hat acht `accepted` Test-ADRs (057, 058, 074, 100, 108, 155, 179, 184)
und **kein einziges Gate, das eines davon durchsetzt**. Gemessen am 2026-08-29:

| Befund | Beleg |
|---|---|
| Der shared-ci-Job „Coverage Gate (≥N %)" konnte nie rot werden: `coverage combine` auf XML-Dateien liefert „No data to report", der `\|\| echo`-Zweig schluckt jeden Ausgang | `shared-ci/.github/workflows/_ci-python.yml:522` (v1.1.11), writing-hub-Run 27814891601 |
| Contract-Job wertet „keine Tests gesammelt" (exit 5) grün — bewusst so (platform#846), aber unsichtbar | `_ci-python.yml:571` |
| Testpyramide 40/45/10/5 (ADR-057 §2.4) und 28-Arten-Taxonomie (ADR-058) werden nirgends gemessen; Compliance „manuell via grep" | ADR-058 Z. 65–71 |
| Vier Contract-Techniken parallel: Schemathesis/WSGI (057), Schemathesis+responses+jsonschema (058), `inspect.signature`-Asserts (155), `ContractVerifier` (184) — kein Vorrang | ADR-184 Z. 20 nennt 155 „Vorstufe", 155 bleibt `accepted` |
| Drei Namen für das Test-Settings-Modul: `config/settings/test.py` (057, shared-ci-Default) vs. `config/settings/testing.py` (179) | `_ci-python.yml:35` |
| ADR-100 pinnt `>=0.1.0,<0.2.0`; Flottenkonvention ist `>=0.5.3,<1`; PyPI steht bei 0.6.1; **1 von 16** gepinnten Repos ist auf 0.6 | `docs/conventions/fw-dependency-ranges.md:11`, Fleet-Test-Meter |
| Browser-Tests sind in 057/058 abgelehnt — und laufen als `/ux-review`, `/kd-review`, `iil_testkit.oberflaeche` 0.6.0 (platform#2326, KONZ-051) ohne ADR | KONZ-platform-051 |
| Flotte (74 Repos): 62 mit Tests, Coverage-Schwellen 10–85 ohne Norm, 6 Repos mit Tests ohne CI-Testjob, zwei inkompatible Marker-Schemata (Testtyp vs. Requirement-ID) | `docs/audits/fleet-test-meter-2026-08-29.md` |

Das Problem ist nicht zu wenig Strategie, sondern zu viel unwirksame. ADR-Text und
CI-Realität sind seit Februar auseinandergelaufen; jede weitere Strategieseite
vergrößert die Lücke (🌀 „gebaut ≠ feuert").

## Entscheidung

**Subtraktiv:** Es gilt nur, was ein Gate prüft. Alles andere wird gestrichen oder
zur Empfehlung herabgestuft.

### Eine Regel

Ein Repo ist **getestet im Sinne der Plattform**, wenn alle fünf Punkte zutreffen:

| # | Regel | Prüfer |
|---|---|---|
| R1 | CI hat einen Testjob, der bei Fehlschlag rot wird (`_ci-python.yml` oder eigener pytest-Job) | Meter B1 |
| R2 | **Coverage-Ratchet:** `coverage_threshold` = gemessener Ist-Wert (ganze Prozent, abgerundet), darf nur steigen; Senkung braucht ein Issue | Gate G1 |
| R3 | Marker-Schema: genau `unit \| integration \| contract \| e2e \| slow` als Testart-Marker; Requirement-/Traceability-IDs im eigenen Namensraum `req_<id>` (z. B. `req_f1`), nie als nackte Kurz-IDs | Meter (Spalte Marker) |
| R4 | `iil-testkit>=0.6.0,<1` (Band `<1`, Minor frei — ADR-100 §Pin-Strategie damit ersetzt) | Meter B2 |
| R5 | PostgreSQL-only, Settings-Modul `config.settings.test` (ADR-179 bleibt; sein Modulname `testing.py` wird auf den shared-ci-Default `test.py` angepasst) | shared-ci-Default |

Empfohlen, nicht gegated: `test_should_*`-Naming (testkit-Plugin im Modus `warn`, wie
seit 0.5.2 praktiziert), factory_boy-Factories aus `iil_testkit`, Schemathesis für
Repos mit OpenAPI-Schema.

### Drei Gates

| Gate | Wo | Wirkung |
|---|---|---|
| **G1 Coverage-Ratchet** | `shared-ci/_ci-python.yml`, Job `coverage-report` ([iilgmbh/shared-ci#61](https://github.com/iilgmbh/shared-ci/pull/61)) | Zeilen-Union aus Unit- und Integration-XML; **keine Daten = rot**, Ist < Schwelle = rot; Ist-Wert im `::notice`, damit der Ratchet-Wert ablesbar ist |
| **G2 Kein Test ohne Leser** | `platform/tools/fleet_test_meter.py`, Befund B1 | Repo mit ≥1 Testdatei ohne CI-Testjob ist eine Verletzung, außer es steht mit Grund + Issue in `governance/tests/fleet-test-exceptions.json` |
| **G3 Pin-Konvergenz** | Meter, Befund B2 | Jeder testkit-Pin unter `>=0.6.0` ist eine Verletzung |

Der Contract-Job bleibt bei exit 5 grün (Repos ohne Contract-Tests sollen nicht
deswegen rot werden), aber der Meter zeigt je Repo die Anzahl `@pytest.mark.contract`
— „0" ist sichtbar, nicht versteckt.

### Ein Meter

`python3 tools/fleet_test_meter.py --report docs/audits/fleet-test-meter-<datum>.md`
([platform#2431](https://github.com/achimdehnert/platform/pull/2431)). Zwei Läufe sind
byte-identisch; Exit 1 bei ≥1 Verletzung. Das Audit-Dokument ist die einzige
Tracking-Tabelle — die eingefrorenen Migrationstabellen in ADR-057 §3, ADR-058, ADR-184
§5 und ADR-179 entfallen.

### Was entfällt (und warum)

| Bisher | Neu | Grund |
|---|---|---|
| Pyramide 40/45/10/5 | gestrichen | nie gemessen, kein Prüfer |
| 28 Testarten in 4 Dimensionen, Pflicht-Mindestsets | 5 Marker | Compliance war „grep von Hand" |
| Coverage-Stufenplan 30→50→70→80 % | Ratchet ab Ist | Stufenplan stand seit 02/2026 auf „🔴 Not started"; Ist-Werte reichen von 14 % bis >80 % |
| Contract-Testing als Drei-Schichten-Pflicht (184) und `inspect`-Asserts (155) | optional; `iil_testkit.contract` bleibt verfügbar | 13/13 Migrationszeilen offen seit 04/2026; 2 von 74 Repos haben Contract-Tests |
| Browser-Automation „abgelehnt" | vierte Schicht **Begehbarkeit**: `iil_testkit.oberflaeche`-Klassen-Gates als Unit-Tests + `/ux-review` als Prüfweg (KONZ-051) | ist Praxis, war nur nicht beschlossen |
| ADR-100 Pin `<0.2.0`, Naming-Modus `error` | `>=0.6.0,<1`, `warn` | ADR beschreibt einen Zustand, den kein Repo hat |

### Auflösung der elf Widersprüche des Scans

| # | Widerspruch | Auflösung |
|---|---|---|
| 1 | ADR-155 und ADR-184 beide `accepted` | beide `superseded` durch dieses ADR |
| 2 | `test.py` vs. `testing.py` | `config.settings.test` (shared-ci-Default); ADR-179 amended |
| 3 | vier Contract-Techniken | keine Pflicht; `iil_testkit.contract` empfohlen, Schemathesis wo OpenAPI |
| 4 | Celery-Payload-Contracts doppelt | fällt mit 3 |
| 5 | ADR-057 „Phase 2 complete" vs. „🔴" | Tabellen entfallen; Meter ist Tracking |
| 6 | Stufenplan 70 vs. Default 80 | Ratchet; kein Zielwert |
| 7 | Playwright abgelehnt vs. betrieben | Schicht Begehbarkeit |
| 8 | ADR-100-Pin vs. Flotte | R4 |
| 9 | Naming `error` vs. `warn` | `warn` festgeschrieben |
| 10 | ADR-074 Tenancy-Gate fehlt in shared-ci | unverändert offen — **Folge-Issue**, nicht Teil dieses ADR (Out of Scope in #2428) |
| 11 | Guardian-Job nur bei `run_contract_tests` | bleibt so; Guardian ist keine Testregel |

## Konsequenzen

- **Rollout des Gates G1 macht Repos rot**, deren Ist unter ihrer gesetzten Schwelle
  (Default 80) liegt. Deshalb ist der shared-ci-Tag-Release **Owner-Wort** und pro
  Consumer ein Ratchet-Wert zu setzen (Ist steht im Notice des Pilot-Laufs). Rollout in
  Staffeln, nicht als Welle (🌀 `mass_bump_wave_stagger_preflight`).
- Vier ADRs werden bei Accept `superseded`, zwei amended; INDEX regeneriert.
- Der Meter ist zunächst **nicht** in CI verdrahtet (kein Kriterium in #2428).
  Ob er als wöchentlicher Workflow läuft, entscheidet der Owner beim Accept.
- Repos ohne Tests (12 von 74) sind **keine** Verletzung — dieses ADR erzwingt keine
  Tests, es erzwingt, dass vorhandene Tests gelesen werden und Coverage nicht sinkt.

## Confirmation

| K | Kriterium (aus #2428) | Nachweis |
|---|---|---|
| K1 | Meter reproduzierbar | zwei Läufe byte-identisch, `docs/audits/fleet-test-meter-2026-08-29.md` |
| K2 | Gate feuert | Pilot writing-hub#855: Schwelle 99 → rot, Schwelle = Ist → grün |
| K3 | dieses ADR `proposed` | dieser PR |
| K4 | 6 Repos ohne Leser: Job oder begründete Ausnahme | Meter B1 = 0 |
| K5 | 15 Pins auf `>=0.6.0,<1` | Meter B2 = 0 (bfagent frozen, ausgenommen) |

Review-Termin: `last_reviewed` + 6 Monate. Kill-Kriterium: Meter zeigt nach 6 Monaten
mehr Verletzungen als beim Start (21) → das ADR hat nichts bewirkt und wird
`deprecated`, nicht erweitert.

## Alternativen

| Option | Verworfen weil |
|---|---|
| A. Alles behalten, Doku nachführen | die Lücke entstand *mit* gepflegter Doku; Text ohne Prüfer driftet erneut |
| B. Hartes 80-%-Gate flottenweit | ≥20 Repos sofort rot, Reaktion wäre `skip_tests`/Schwelle senken — das Gate wäre am ersten Tag umgangen |
| C. Ratchet ab Ist (gewählt) | kein Repo wird schlechter, jedes Repo hat einen prüfbaren Wert; Fortschritt ist optional, Rückschritt ist rot |
| D. Meter als CI-Gate in jedem Repo | doppelt shared-ci; ein Flotten-Meter reicht, solange jemand ihn liest (KONZ-050 Blindstellen) |

## Changelog

- 2026-08-29: Entwurf (`proposed`) aus platform#2428, Grundlage Doku-Scan + Fleet-Test-Meter.
