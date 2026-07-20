---
id: ADR-225
title: "genesor-Ingest-Architektur: reproduzierbarer main-basierter Ingest statt Working-Tree-Scan"
status: accepted
decision_date: 2026-05-29
deciders: [Achim Dehnert]
consulted: []
informed: [iilgmbh, meiki-lra, bahn-sqf, ttz-lif]
domains: [klickdummy, genesor, ingest, ci]
supersedes: []
amends: []
depends_on: []
related: [ADR-211, ADR-213, ADR-216]
tags: [klickdummy, genesor, ingest, cross-repo, ci]
scope:
  include_paths:
    - "docs/adr/ADR-225-*"
---

# ADR-225 — genesor-Ingest-Architektur: reproduzierbarer main-basierter Ingest statt Working-Tree-Scan

| Attribut       | Wert                                             |
|----------------|--------------------------------------------------|
| **Status**     | Accepted                                         |
| **Scope**      | platform (cross-cutting: alle KD-Repos)          |
| **Repo**       | platform                                         |
| **Erstellt**   | 2026-05-29                                       |
| **Autor**      | Achim Dehnert                                    |
| **Reviewer**   | –                                                |
| **Supersedes** | –                                                |
| **Relates to** | ADR-211 (Klickdummy-Prozess), ADR-216 (Hosting iil.pet), ADR-213 (Cross-Repo-Ref-Format) |

## 1. Kontext

### 1.1 Ausgangslage

`genesor` ist die kanonische Cross-Repo-Klickdummy-Übersicht (ADR-216, gehostet auf
`iil.pet/genesor/`; ein zusätzliches stale Snapshot läuft auf `88.99.38.75:8765`).
Der Generator (`iil_klickdummy.lineage`, console_script `klickdummy-genesor`) erzeugt
die Übersicht durch **Glob-Scan des Working-Trees** unter `~/github` auf einem
Dev-Host: `~/github/<repo>/klickdummy/*/screens-spec.yaml` (+ meiki-mockups-Pfad).

### 1.2 Problem / Lücken

Vorfall 2026-05-29: Der neue `design-hub`-Klickdummy fehlte in genesor. Drei Ursachen:

1. **Working-Tree-Abhängigkeit (Konstruktionsfehler):** Was genesor sieht, hängt davon
   ab, welche Branches gerade auf *einem* Host ausgecheckt sind. Ein Durchlauf am
   2026-05-29 ergab, dass ein Regen aus dem aktuellen Tree-Zustand inkonsistent ist und
   ein **main-basierter** Regen **11 bestehende KDs verlieren würde** (meiki-hub:
   buergerportal/post-routing/uvg/wohngeld/asyl; ausschreibungs-hub:
   document-intelligence/vergabe/submission-phasen) — weil deren Specs **nicht auf
   `origin/main`**, sondern auf Feature-Branches liegen.
2. **Kein reproduzierbarer Generierungs-Pfad:** Vendoring (`iil-pet-portal/kd/<repo>/`)
   und `--vendored-repos` wurden über mehrere **manuelle** Läufe aufgebaut; es gibt kein
   wiederverwendbares Skript, das den vollständigen Stand erzeugt.
3. **Status im falschen Speicher:** „visual accepted / real implemented" wird in
   generiertem HTML/lokalem JSON gehalten — geht bei jedem Regen verloren.

### 1.3 Constraints

- genesor muss **alle** Hub-Repos abdecken (Org-übergreifend: iilgmbh, bahn-sqf,
  achimdehnert, meiki-lra). Eine GitHub-Action *eines* Repos kann das nicht (kein
  All-Repo-Checkout) — ADR-216.
- Sperrvermerk-Repos (bahn-sqf/pg-hub) nur mit ausdrücklicher Genehmigung
  ([[pg-hub-db-mandat]]); kein Bulk-Vendoring.
- Fremde Working-Trees dürfen **nicht** angefasst werden (laufende Arbeit, ungesicherte
  Änderungen — am 2026-05-29 hatten writing-hub 50, sqf-hub 29 dirty files).

## 2. Entscheidung

1. **genesor wird reproduzierbar aus dem veröffentlichten Stand (`main`) jedes Repos
   ingestiert** — nicht aus dem zufälligen Working-Tree eines Hosts. Mechanik:
   ephemere **git-worktrees am `origin/main`-Ref** (read-only, kein Working-Tree wird
   berührt; nachweislich am 2026-05-29 erprobt) in einem Temp-Scan-Root; Generator mit
   `--repos-root <temp>`. Mittelfristig CI-/manifest-fähig.
2. **Contract „KD-Specs leben auf `main`":** Ein Klickdummy gilt erst als
   *veröffentlicht* (und erscheint in der kanonischen genesor), wenn seine
   `screens-spec.yaml` auf dem `main` seines Repos liegt. Feature-Branch-KDs sind WIP
   und nicht kanonisch.
3. **Status ist Spec-Eigentum, genesor ist nur View:** Lifecycle-Status
   (visual → accepted → implemented) lebt in der Spec (ADR-211 `off_ramp_status`,
   `acceptance.spec_signed`) bzw. in GitHub Projects (System-of-Record laut
   `genesor-sync/setup-project.sh`). genesor rendert ihn, speichert ihn nicht.
4. **Reproduzierbarer Regen wird als Skript codifiziert** (`iil-pet-portal/scripts/`),
   inkl. `--vendored-repos` + Vendoring, mit **Diff-Gate** gegen den committeten Stand
   vor jedem Deploy.
5. **Seed-vs-Live-Gate (Vorbedingung zur Veröffentlichung):** Ein KD darf erst auf
   `main` (und damit in genesor/`iil.pet`) veröffentlicht werden, wenn er **ausschließlich
   synthetische Daten** enthält — **keine realen Mandanten-/Bürgerdaten**. genesor ist
   über `iil.pet` (CF-Access) stakeholder-sichtbar; reale Daten dort verletzen die
   Daten-Souveränität ([[feedback-seed-vs-live-data]], 🌀 Vorfall „Realdaten in public
   risk-hub"). Dieses Gate ist Teil des „KD-auf-main"-Contracts (Punkt 2).

## 3. Betrachtete Alternativen

| Option | Bewertung |
|---|---|
| **Working-Tree-Scan beibehalten** (Status quo) | ❌ verworfen — driftet strukturell; „vollständig" ist Zufall des Checkout-Zustands; der heutige Vorfall wiederholt sich bei jedem neuen KD. |
| **Scan je Repo am beliebigen KD-Branch** | ❌ verworfen — ein Repo kann KDs über mehrere Branches verstreut haben (meiki: 1 auf main, Rest auf Branches); nicht in *einen* Repo-Dir konsolidierbar; nicht reproduzierbar. |
| **Pull via GitHub-API / Code-Search** (wie alt `discover-klickdummies.py`) | ⚠️ tragfähig als Zukunft (CI-only, kein lokaler Checkout) — aber Contents-API für ganze Mockup-Trees teuer; als Stufe 2 nach dem worktree-Ingest. |
| **worktree-Ingest am `main` (gewählt)** | ✅ kein Working-Tree-Risiko, reproduzierbar, lokal+CI-fähig, erzwingt den „KD-auf-main"-Contract. |

## 4. Begründung im Detail

Die Vision „genesor = Basis der Entwicklung (visual → accepted → implemented), alle
Repos, forward+backward" setzt **eine verlässliche, vollständige, reproduzierbare**
Datengrundlage voraus. Ein Host-Working-Tree-Scan kann das prinzipiell nicht leisten
(Beweis: Regressions-Diff 2026-05-29). `main` als Ingest-Quelle macht „veröffentlicht"
eindeutig und reproduzierbar und richtet sich an der bereits gelebten Konvention aus
(die meisten KDs sind auf main). forward/backward ist großteils schon in ADR-211
modelliert (`off_ramp_status` = forward; `spec_id`-Rücklink aus der echten App = backward) —
diese Felder werden genutzt, keine neue State-Maschine in genesor.

## 5. Implementation Plan

1. **Reproduzierbares Regen-Skript** (`iil-pet-portal/scripts/regen-genesor-main.sh`):
   enumeriert KD-Repos, legt worktrees am `origin/main` an (Repos ohne KD-auf-main →
   geloggt + übersprungen), generiert, vendored, **Diff-Gate**, räumt worktrees ab.
2. **Migration „KD → main"** (Vorbedingung für Vollständigkeit, je Repo-PR):
   meiki-hub (buergerportal/post/uvg/wohngeld/asyl), ausschreibungs-hub
   (document-intelligence/submission-phasen), risk-hub
   (`fix/klickdummy-i4-qualify-adr-refs`) → nach `main` mergen.
3. **Deploy** der vollständigen kanonischen genesor + `iil.pet/genesor/`-Verifikation;
   **erst dann** 8765 abschalten.
4. **Stufe 2 (deferred):** CI-/manifest-basierter Ingest (nightly, GH-API), damit kein
   Dev-Host mehr nötig ist.
5. `/klickdummy`-Skill um Hinweis „nach Merge auf main: genesor regenerieren" ergänzen.

## 6. Risiken

- **Migration unvollständig:** Solange KDs nicht auf main gemergt sind, bleibt genesor
  unvollständig — bewusst sichtbar statt durch Branch-Scan kaschiert.
- **Sperrvermerk:** bahn-sqf/pg-hub-Ingest nur mit Genehmigung; Skript muss eine
  Allowlist respektieren.
- **worktree-Leichen** bei Abbruch — Skript räumt im `trap` ab.

## 7. Konsequenzen

### 7.1 Positiv
- genesor wird **reproduzierbar** und **deterministisch** (gleicher main-Stand → gleiche Übersicht).
- Kein Risiko mehr für fremde Working-Trees; Drift strukturell ausgeschlossen.
- „KD-auf-main" macht Veröffentlichung explizit und CI-prüfbar.

### 7.2 Trade-offs
- KDs auf Feature-Branches erscheinen **nicht** mehr (bis gemergt) — gewollt, kann aber
  als „Verlust" wahrgenommen werden, bis die Migration läuft.
- Einmaliger Migrationsaufwand (mehrere Repo-PRs).

### 7.3 Nicht in Scope
- CI-/manifest-Ingest (Stufe 2, deferred).
- Acceptance-Workflow-Mechanik selbst (ADR-211).
- Hosting/CF-Access (ADR-216).

## 8. Validation Criteria

- `regen-genesor-main.sh` erzeugt aus `origin/main` aller KD-Repos eine genesor-Übersicht,
  die **alle auf main veröffentlichten** KDs (inkl. design-hub) enthält, ohne ein
  Working-Tree zu verändern.
- Diff-Gate verhindert Deploy bei unbeabsichtigtem KD-Verlust.
- Nach Migration: `iil.pet/genesor/` zeigt die vollständige Menge; 8765 kann abgeschaltet werden.

## 9. Glossar

| Abkürzung | Bedeutung |
|-----------|-----------|
| **genesor** | Cross-Repo-Klickdummy-Übersicht (Topologie/Lineage), kanonisch auf `iil.pet/genesor/` |
| **KD** | Klickdummy — Renderer einer maschinenlesbaren Anforderungs-Spec (ADR-211) |
| **Ingest** | Einlesen/Aggregieren der Quell-Specs zur Erzeugung der Übersicht |
| **Working-Tree** | der ausgecheckte Dateistand eines Git-Repos (branch-abhängig) |
| **git-worktree** | zusätzlicher, an einen Ref gebundener Arbeitsbaum desselben Repos, ohne den Haupt-Tree zu ändern |
| **off_ramp_status** | Lifecycle-Feld je Screen in der Spec (static → parity → real), ADR-211 |
| **CI** | Continuous Integration — automatisierte Pipeline |

## 10. Referenzen

- platform:ADR-211 — Klickdummy-Benutzeranforderungen/Entwicklungsprozess (Specs, Invarianten, off_ramp)
- platform:ADR-216 — Klickdummy-Hosting auf iil.pet
- platform:ADR-213 — Cross-Repo-ADR-Ref-Format
- Memory `genesor-iilpet-consolidation`, `design-hub-tenant-dashboard-kd`
- Vorfall + Durchlauf-Evidenz: 2026-05-29 (Regressions-Diff 11 KDs)

## 11. Changelog

- 2026-05-29: Initial (Proposed). Aus Vorfall „design-hub-KD fehlt in genesor" + Durchlauf-Evidenz abgeleitet.
- 2026-05-29: Seed-vs-Live-Gate (Entscheidung Pkt. 5) ergänzt — entdeckt bei Migrationsstart: risk-hubs KD-Branch enthält realen Mandanten „Gröger GmbH" (dutzende Treffer); Veröffentlichung nach genesor/iil.pet wäre Daten-Souveränitäts-Verstoß. Synthetische-Daten-Pflicht ist nun Teil des Contracts.
- 2026-06-16: **Accepted** (gemeinsam mit ADR-246). Stufe-1-Ingest in Betrieb (`regen-genesor-main.sh`; apo-hub:apocenna-portale verifiziert live auf iil.pet/genesor). Stufe 2 (dev-host-freier CI-Auto-Ingest) ausgestaltet in **ADR-246** (amends).
