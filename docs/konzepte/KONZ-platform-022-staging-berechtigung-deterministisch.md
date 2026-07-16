---
concept_id: KONZ-platform-022
title: "Staging-Berechtigung deterministisch — nur 'heavy active' Apps bekommen die mittlere Bühne"
pipeline_status: idea
tier: T2
owner: "Achim Dehnert"
spec_refs: []   # Betriebsmodell-/Infra-Konvention ohne ADR-211-Spec-Bezug; SSoT-Ziel ist registry/repos.yaml
adr_threshold: "kein eigener ADR — Konvention lebt als Registry-Schema-Feld + Messlauf; wird sie je CI-erzwungen (fail-closed Gate), dann Amendment an ADR-264 (KONZ-015-Achse)"
review_by: "2026-10-15"
kill_criteria: "Bis 2026-10-15: (a) Klassifizierungs-Regel + Messwerte als Feld in registry/repos.yaml verankert UND (b) mindestens ein Staging-Rückbau-Kandidat entschieden (abgebaut ODER dokumentiert behalten mit Grund) — sonst sunset; die Regel gilt dann als nicht gelebt und wird nicht weiter verfeinert."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: M1, source_path: "Migrations-Commits 90d je Repo: git log origin/main --since=2026-04-16 -- '*/migrations/*.py' nach fetch, 12 Repos", commit_or_pr: "Messlauf 2026-07-16, Werte in §Ledger", opened_in_session: true}
  - {claim_id: M2, source_path: "Deploy-Läufe/Fehlschläge 90d je Repo: gh api actions/workflows/deploy.yml/runs (total + status=failure)", commit_or_pr: "Messlauf 2026-07-16", opened_in_session: true}
  - {claim_id: M3, source_path: "Öffentliche Adressen: health_check_url aus deploy.yml (origin/main) je Repo", commit_or_pr: "Messlauf 2026-07-16", opened_in_session: true}
  - {claim_id: M4, source_path: "infra/host-maintenance/runner-nonprod-runbook.md §1 (Staging-Host-Containerliste: risk_hub_staging, cad_hub_staging_web, ttz/welten/writing-Stacks, u.a.)", commit_or_pr: "main", opened_in_session: true}
created: "2026-07-16"
---

# KONZ-platform-022 — Staging-Berechtigung deterministisch

> Herkunft: User-Direktive 2026-07-16 („wir benötigen nicht für alle Apps dev, staging und
> prod — nur ‚heavy active' rechtfertigen Staging; was heißt ‚heavy active' durch
> Determinismus und Evidence?"). Baustein des übergeordneten Betriebsmodells
> dev/staging/prod (Build-Plane-Säule: KONZ-platform-021; Registry-/Drift-Achse:
> KONZ-platform-015). **Tier T2** — neue org-weite Konvention (Auto-Eskalation
> Cross-Repo), aber reversibel, ohne neue Abhängigkeit, ohne neues Gate im ersten Schritt.

## Kernthese

Eine App bekommt eine Staging-Umgebung genau dann, wenn **beides** zutrifft — es gibt
etwas zu verlieren (echte Nutzer-/Kundendaten in Produktion) **und** ihre Auslieferungen
sind regelmäßig riskant (laufende Datenbank-Strukturänderungen) —, festgestellt nicht
per Bauchgefühl, sondern per aufgeschriebener Schwelle und quartalsweisem Messlauf,
dessen Ergebnis mit Messwert und Datum in `registry/repos.yaml` steht; fällt eine App
zwei Quartale unter die Schwelle, wird ihre Staging-Umgebung abgebaut, nicht geparkt.

## Annahmen-/Entscheidungs-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|-------------------------|--------|
| L1 | Auslieferungs-Häufigkeit trennt nicht: alle 12 Apps hatten 165–642 Pipeline-Läufe in 90 Tagen, weil jede Änderung am Hauptzweig (auch Doku) die Pipeline startet | Beobachtung | M2 | verifiziert |
| L2 | Datenbank-Strukturänderungen trennen sauber: risk-hub 39, trading-hub 22, writing-hub 15, dev-hub 12 Commits in 90 Tagen — alle übrigen 8 Apps: 0–4 | Beobachtung | M1 | verifiziert |
| L3 | Die Fehlschlag-Quote (60–90 % über die ganze Flotte) misst derzeit einen flottenweiten Defekt im Prüf-Vorspann der Pipeline (bekannt, getrackt als platform#1158), nicht app-spezifischen Schmerz — als Kriterium unbrauchbar, bis der Defekt behoben ist | Beobachtung + Interpretation | M2; Falsifikation: nach #1158-Fix Quoten erneut messen — trennen sie dann, wird das Kriterium aktiviert | verifiziert (Zahlen) / offen (Deutung) |
| L4 | Echte Produktionsdaten haben nur writing-hub, risk-hub und die Landratsamt-Anwendungen | Annahme (aus Memory 2026-06) | nicht in dieser Session gegen die Datenbanken geprüft — billigster Check: je App eine Zeilenzahl-Abfrage der Kern-Tabellen beim nächsten Wartungsfenster | offen (H) |
| L5 | Klassifizierungs-Regel: Staging nur bei (echte Daten/Nutzer) UND (≥8 Struktur-Änderungs-Commits pro Quartal). Schwellwert ist Setzung — Alternative: Median der Flotte ×3 | Entscheidung (D) | M1 + L4; Schwelle bewusst so gewählt, dass sie die beobachtete Lücke (4 vs. 0–4) mittig schneidet | vorgeschlagen |
| L6 | Ergebnis der ersten Klassifizierung: **risk-hub + writing-hub** staging-berechtigt; **trading-hub** Grenzfall (hohe Änderungsrate, aber Daten-Frage L4 offen — zudem fließt dort echtes Geld: Human-Entscheid); **dev-hub** kein Staging (hohe Änderungsrate, aber internes Werkzeug ohne Externe); übrige 8: dev + prod | Entscheidung (abgeleitet) | L2 + L4 + L5 | vorgeschlagen |
| L7 | Es existieren heute Staging-Container für Apps, die nach L5/L6 kein Staging rechtfertigen (mindestens cad-hub und weltenhub laut Staging-Host-Containerliste) — das sind die ersten Rückbau-Kandidaten | Beobachtung + Folgerung | M4; vor Rückbau je App live gegenprüfen (Containerliste ist Stand 2026-06-28) | teilverifiziert |
| L8 | Rückbau-Automatik: 2 Quartale unter Schwelle ⇒ Staging-Abbau als Pflicht-Folge, nicht als Option — sonst wiederholt sich die beobachtete Vermüllung (29 Container auf dem Staging-Rechner) | Entscheidung (D) | M4; Alternative: nur Warnung statt Abbau-Pflicht — verworfen, weil Warnungen hier nachweislich verhallen (KONZ-015-Befundlage: unverdrahtete Checks sind der Median) | vorgeschlagen |
| L9 | Die Einstufung wohnt in `registry/repos.yaml` (je System: `envs:`-Feld + `envs_evidence:` mit Messwerten und Datum) — dieselbe Datei, die KONZ-015 als normative Registry etabliert; keine neue Datei, keine zweite Wahrheit | Entscheidung | KONZ-015 §5.5 (Registry als SSoT-Ziel) | vorgeschlagen |

## MVC (kleinste sinnvolle Version)

1. **Schema-Erweiterung** `registry/repos.yaml`: je System `envs: [dev, prod]` oder
   `[dev, staging, prod]` plus `envs_evidence: {migrations_90d: <n>, real_data: ja|nein|offen, measured: <datum>}`.
   Erste Befüllung mit den Messwerten aus M1–M3 (§Ledger L2/L6).
2. **Messlauf dokumentiert** als `tools/staging_tier_check.py` ODER (noch kleiner) als
   dokumentierter Kommando-Block im Registry-Kopf — quartalsweise, Owner: Achim.
   **Ehrliche Grenze:** Bis ein Scheduled-Check das ausführt, ist das Review-Disziplin,
   kein Exit-Code (wire-before-extend, KONZ-015-Lehre — hier bewusst akzeptiert,
   weil die Konsequenz „Umgebung abbauen" ohnehin ein Mensch mit Wartungsfenster ist).
3. **Zwei Entscheidungen herbeiführen** (Human): trading-hub-Grenzfall (L6) und
   erster Rückbau-Kandidat (L7) — je als Issue mit Messwert-Zitat.

Bewusst NICHT drin: CI-Gate, das `envs:` erzwingt; Automatik, die Umgebungen abbaut;
Anfassen der Landratsamt-/Gov-Anwendungen (eigene Governance). **Rückbau des Konzepts:**
Feld + Kommandoblock löschen — nichts hängt davon ab.

## Kill-Gate + Threshold

Siehe Frontmatter `kill_criteria` (Stichtag 2026-10-15, zwei Bedingungen). Threshold:
Das Konzept bleibt unterhalb der ADR-Schwelle, solange es deklarativ bleibt (Feld +
Messlauf); erst ein **erzwingendes** Gate (Deploy blockiert ohne `envs:`-Eintrag) wäre
eine neue Boundary und liefe als Amendment an ADR-264 durch den Review.

| Kriterium | Status (offen/erfüllt/verworfen) | Beleg |
|---|---|---|
| (a) Regel + Messwerte in registry/repos.yaml verankert | offen | — |
| (b) ≥1 Rückbau-Kandidat entschieden (abgebaut oder begründet behalten) | offen | — |

## Befunde (inkl. Adversarial-Zeilen)

| ID | Rolle | Befund | Evidenz | Schwere |
|---|---|---|---|---|
| B1 | Steelman | Die Regel kodiert, was die Messung zeigt: Die Flotte hat real zwei Klassen (4 Apps mit laufenden Strukturänderungen vs. 8 nahezu statische) — Staging für alle wäre Versicherung für Häuser ohne Inventar | M1 (L2) | positiv |
| B2 | Steelman | Kein neues Statusmodell, keine neue Datei: Einstufung wohnt in der Registry, die KONZ-015 ohnehin zur einzigen Wahrheit macht | L9 | positiv |
| B3 | Diabolus | Kriterium „echte Daten" ist die tragende Säule und zugleich der schwächste Beleg (Memory-Stand, nicht gemessen, L4) — kippt L4, kippt die halbe Klassifizierung. Härtung: L4-Check ist Pflicht-Teil von MVC-Schritt 1, nicht Kür | L4 | hoch |
| B4 | Diabolus | Migrations-Zählung ist umgehbar (eine App kann Struktur riskant ändern, ohne Migrations-Dateien zu berühren — Roh-SQL, Daten-Backfills) und überzählbar (ein Merge-Commit mit 30 Migrationen = 1, 30 Einzel-Commits = 30). Härtung: bei Grenzfällen Dateien statt Commits zählen; Kriterium bleibt Indikator, nicht Beweis | M1-Methodik | mittel |
| B5 | Diabolus | „2 Quartale unter Schwelle ⇒ Abbau" ohne verdrahteten Zähler ist dieselbe Papier-Pflicht, die dieses Ökosystem schon mehrfach gebrochen hat — der Messlauf hat keinen Erzwingungsmoment (nur Kalender + Disziplin) | KONZ-015-Befundlage | hoch |
| B6 | Maintainer-2028 | Wahrscheinlichste Verrottung: Der quartalsweise Messlauf läuft zweimal, dann nie wieder; die `envs_evidence:`-Daten veralten still und 2028 zitiert jemand eine Messung von 2026 als Ist-Stand. Strukturelle Vorkehrung: `measured:`-Datum älter als 120 Tage ⇒ Eintrag gilt als „offen", nicht als letzter Wert (Regel im Registry-Kopf) | Präzedenz: github_repos.yaml, 3 Monate stale mit SSoT-Anspruch (KONZ-015 C5) | hoch |
| B7 | Alternative 1 | **Nur-Warnung statt Abbau-Pflicht** (Staging bleibt, wird aber als „unberechtigt" markiert): billiger, konfliktfrei — verworfen: markierte-aber-geduldete Zustände sind hier nachweislich Dauerzustände; genau die Vermüllung, die der User adressiert | M4 | — |
| B8 | Alternative 2 | **Staging on-demand statt Einstufung** (je PR/Release eine flüchtige Umgebung hochziehen, für niemanden dauerhaft): eleganter Endzustand, passt zur Service-Klassen-Idee — heute nicht umsetzbar ohne Provisioning-Automation; als Evolutionsziel notiert, ersetzt die Einstufung nicht | — | — |

## Changelog

- 2026-07-16: Initial (T2-Ledger). Messlauf über 12 Apps (M1–M3); Fehlschlag-Quote als
  Kriterium explizit zurückgestellt (L3), bis platform#1158 behoben ist.
