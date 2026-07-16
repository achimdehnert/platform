---
id: ADR-275
title: "Registry-SSoT-Konsolidierung — canonical.yaml als einzige Quelle, github_repos.yaml stilllegen"
status: accepted
decision_date: 2026-07-14
implemented: 2026-07-14
implementation_status: implemented
implementation_evidence:
  - "P0 Archiv-Lifecycle-View + gen_archived (additiv): PR #1137"
  - "P0.5+P1 sovereign hubs + sync-workflows.sh auf Flat-View: PR #1139"
  - "P2 runner-health.yml via registry_api: PR #1140"
  - "P3 sync-drift-meter (Kommentar-Fix; war Nicht-Consumer): PR #1142"
  - "P4 validate_repos.py auf canonical.yaml: PR #1144"
  - "P5 github_repos.yaml → registry/_ARCHIVED/ (direkter Move, s. Umsetzung): PR #1145"
  - "Hygiene (bfagent/doc-hub/ifc-mcp/schutztat-reporting): PR #1146, Issue #1143"
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
supersedes: []
related: [ADR-022, ADR-157, ADR-234]
tags: [registry, ssot, drift-prevention, ci, generated, governance]
ai_sparring_by:
  - tool: other
    date: 2026-07-14
    role: adversarial-review
    summary: "ollama-local: dolphin3 + qwen2.5:7b (lokale 7B-Klasse, kein Egress); Befunde AD-1/AD-4 dennoch repo-verifiziert."
drift_check_paths:
  - "registry/canonical.yaml"
  - "registry/_ARCHIVED/github_repos.yaml"
  - "registry/repos.yaml"
---

# ADR-275 — Registry-SSoT-Konsolidierung

## Context and Problem Statement

Zwei Repo-Registries beanspruchten „Single Source of Truth" und wurden **beide von aktiver
CI gelesen**:

| Datei | Anspruch | Realität | Schutz |
|---|---|---|---|
| `registry/canonical.yaml` → `repos.yaml` | kanonisch (ADR-234 P0) | generiert, 53 aktive Repos, reiches Schema | CI-Drift-Gate `registry-consistency.yml` |
| `registry/github_repos.yaml` | SSoT für Cascade/port_audit/onboard-repo/deploy-check | manuell, Snapshot 2026-04-03, 113 Einträge (68 Archiv) | keins |

4 aktive Konsumenten von `github_repos.yaml` (verifiziert 2026-07-14): `sync-workflows.sh`,
`runner-health.yml`, `sync-drift-meter.yml`, `validate_repos.py`. **Kernbefund:** manche
Workflows entschieden gegen die frische Quelle, andere gegen einen 3,5 Monate alten
Snapshot — stille Fehlfunktion durch Datenalter war der Schaden, nicht die Existenz zweier
Dateien (bereits als „bekannt" notiert, nie aufgelöst — KONZ-platform-015).

## Decision Drivers

1. Genau eine SSoT, prüfbar
2. Kein stiller Datenzerfall — Gate statt manueller Disziplin
3. Reversibel & inkrementell — jeder Consumer einzeln migrierbar
4. Coverage-Ehrlichkeit — Lücken vor Stilllegung schließen, nicht danach

## Coverage-Delta (verifiziert 2026-07-14, nicht geschätzt)

`canonical.yaml` (53 Repos) deckt `github`/`deployed`/`type`/`deploy`/`staging` ab.
`github_repos.yaml`-Unikate, vor Stilllegung zu schließen:

| Lücke | Betroffener Consumer |
|---|---|
| 68 Archiv-Repos (Snapshot) | `validate_repos.py` |
| `django-lms-lite` (fehlte in canonical) | coach-hub-Dep |
| Sektions-Gruppierung (`django_apps`/`frameworks`) | `sync-workflows.sh`, `runner-health.yml` |

## Considered Options

- **A (gewählt) — canonical.yaml als alleinige SSoT.** 4 Consumer migrieren,
  `github_repos.yaml` stilllegen. Pro: ein Anspruch, ein Gate, Datenalter strukturell
  unmöglich. Contra: 4 Migrationen + Lückenschluss.
- **B — github_repos.yaml aus canonical.yaml generieren.** Pro: kein Consumer-Change.
  Contra: zementiert zwei Schemata dauerhaft.
- **C — Status quo + Waiver.** Verworfen: genau das ist seit 2026-04 passiert, Snapshot
  altert weiter.

## Decision Outcome

**Option A**, in reversiblen Phasen, jede mit eigenem Gate. B taugt als *befristeter
Migrations-Adapter* (externes Sparring OOB-1), nicht als Endzustand.

**Vorab-Klärungen (vor den Phasen entschieden, nicht im PR versteckt):**
- Consumer-Vertrag = View `repos.yaml`, **nicht** `canonical.yaml` direkt — ADR-234 §11.1
  Reader-Baseline entsprechend erweitert (sonst reißt die Migration ein bestehendes Gate).
- Archiv-Modell = `lifecycle: archived` in `canonical.yaml` + gefilterte View
  `archived-repos.yaml` — Archivieren ist ein Feld-Flip, kein Datei-Umzug.

## Umsetzung — abgeschlossen 2026-07-14 (alle Phasen auf main, verifiziert)

| Phase | Plan | PR | Abweichung |
|---|---|---|---|
| P0 | Archiv-Lifecycle-View + `gen_archived` (additiv) | #1137 | Die „68 Archive" waren 96 % Fiktion (GitHub-live verifiziert: 0 real archiviert, 65 gelöscht, 3 fehlklassifiziert-aktiv). P0 importiert nur die 3 echten (`adr-doctor`, `bfagent`, `testkit`) |
| P0.5+P1 | sovereign hubs + `sync-workflows.sh` → Flat-View | #1139 | Identitäts-Gate als Drei-Teil-Vertrag (unverändert / Soll-Delta / keine Zusatz-Abweichung) statt naivem „Ausgabe unverändert" |
| P2 | `runner-health.yml` → `registry_api` | #1140 | — |
| P3 | `sync-drift-meter.yml` | #1142 | War kein echter Consumer — las nie `github_repos.yaml` direkt, nur ein seit P1 veralteter Kommentar; reiner Doku-Fix |
| P4 | `validate_repos.py` → `canonical.yaml` | #1144 | — |
| P5 | `github_repos.yaml` → `registry/_ARCHIVED/` | #1145 | Direkter `git mv` statt geplantem Rollback-Fenster — alle 4 Consumer bereits grün verifiziert, Fenster-Zweck gegenstandslos |
| Hygiene | bfagent/doc-hub/ifc-mcp/schutztat-reporting | #1146 (Issue #1143) | — |

**Enforcement:** `check_registry_view_readers.py` grep-Guard gegen neue direkte
`github_repos.yaml`-Leser. Grenze: fängt keine dynamischen Pfade/externe Repos — vor P5
zusätzlich org-weite Code-Suche + Dry-Runs aller Consumer durchgeführt.

**Rest-/Folgearbeit:** `validate_repos --github` meldet 3 vorbestehende,
un-katalogisierte Repos (`design-hub`, `iil-demo-fixture`, `molkerei-landing`) —
dokumentiert in #1143, kein neuer Gap, außerhalb Scope. `ifc-mcp`/`schutztat-reporting`
additiv-neutral aufgenommen, Domain-Promotion optional später.

## Consequences

**Positiv:** Eine autoritative Registry für Repo-Identität/Typ/Deploy/Lifecycle — bewusst
nicht „genau eine SSoT": die ADR-021-§2.9-Port-Teilkopie besteht separat fort.

**Wichtig:** „generiert + driftgeprüft" ≠ „fachlich aktuell". Das Drift-Gate beweist nur
`View == canonical`, nicht Übereinstimmung mit dem realen GitHub-Bestand — das leistet
`reconcile_registry_live.py`.

**Offen (Kipp-Punkt):** 4 direkte YAML-Leser können künftig erneut divergieren — eine
gemeinsame Query-Schicht wird ab dem 5. Consumer oder erneuter Filter-Drift fällig
(bewusst nicht jetzt gebaut, YAGNI bei 4 Consumern).

**Risiko:** 6 PRs statt 1; jeder Consumer-PR brauchte einen echten Vorher/Nachher-Diff-Beleg,
nicht nur „CI grün".

**Nicht verifiziert:** ob `sync-drift-meter.yml`/`validate_repos.py` weitere
`github_repos.yaml`-Felder über die belegten hinaus lasen — nur per `grep` geprüft, nicht
per Tool-Ausführung im Vorher/Nachher.

## Abgrenzung

Nur die Registry-Doppelquelle. Die ADR-021-§2.9-Port-Tabelle ist eine separate, verwandte
Teilkopie (~24 vs. 53 Einträge) — eigener, kleinerer Folge-PR.

## Externes Sparring (2026-07-14)

Zwei adversariale Zweitmeinungen aus lokalen Ollama-Modellen (`dolphin3`, `qwen2.5:7b`,
souveränitäts-sicher, kein Egress). Kein 7B-Modell hat per se Autorität — Wert entstand
durch den Verifikations-Filter: tragende Befunde (AD-3, AD-4) wurden vor Übernahme gegen
das reale Repo geprüft und bestätigten sich. Hohe Valid-Quote ist ehrlicher Befund, kein
Gummistempel: ADR-275 war ein `proposed`-Entwurf mit bewusst offenen Punkten.

| ID | Verdikt | Aktion |
|---|---|---|
| PRO-1…PRO-5 | valid | Zustimmung, keine Änderung nötig |
| AD-1 / REC-1 | valid (verifiziert-logisch) | Identitäts-Gate → Drei-Teil-Vertrag (P1–P4), der zentrale Fix |
| AD-2 / REC-2, M28-1 | valid | Archiv-Modell entschieden: `lifecycle: archived` + gefilterte View |
| AD-3 / REC-3 | valid (repo-verifiziert) | Consequences trennt „View==canonical"-Gate von GitHub-Reconciliation |
| AD-4 / REC-4 | valid (repo-verifiziert) | Consumer-Vertrag = `repos.yaml`; Reader-Baseline-Kollision adressiert |
| AD-5 / REC-5 | valid | P0/P4-Ordering bereinigt |
| AD-6 / REC-6, M28-4 | valid | grep-Guard-Grenzen benannt; org-weite Suche + Dry-Runs vor P5 verpflichtend |
| AD-7 / REC-7 | valid | Typ→Sektion als totale Abbildung (P1-Anforderung) |
| AD-8 / REC-3 | valid (repo-verifiziert) | Archive gegen aktuelles GitHub reconciliiert statt Snapshot blind kopiert |
| AD-9 / REC-9 | valid | Voll-Diff aller Views + Consumer-Ausgaben als P0-Gate |
| M28-2 / REC-8 | valid | P5-Rollback-Fenster-Konzept (real: direkter Move, s. Abweichung oben) |
| M28-3 / OOB-2 | valid (Folge-Schritt) | Query-Schicht als benannter Kipp-Punkt, kein Blocker |
| M28-5 / REC-10 | valid | „genau eine SSoT" → „eine autoritative Registry für die hier behandelten Felder" |
| OOB-1 | valid (übernommen) | B als befristeter Migrations-Adapter, Endzustand bleibt A |
| OOB-3 | valid-Kern | GitHub als Reconciliation-Quelle, nicht als Archiv-Speicherort |
