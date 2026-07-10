---
id: ADR-271
title: "Adopt MADR 4.0 section structure for the /adr skill scaffold"
status: accepted
decision_date: 2026-07-10
deciders:
  - "Achim Dehnert"
consulted: []
informed: []
domains:
  - governance
  - documentation
  - adr-process
tags: [adr, governance, madr, tooling, fleet-audit]
related:
  - "ADR-021"
  - "ADR-046"
  - "ADR-056"
  - "ADR-059"
---

<!--
  ADR-TEMPLATE v2.0 (2026-02-21)
  Basis: MADR 4.0 + Platform-Governance (ADR-021, ADR-046, ADR-056, ADR-059)
  Strategie: techdocs-first, dev-hub-sync, Drift-Detector-kompatibel
-->

# ADR-271: Adopt MADR 4.0 section structure for the `/adr` skill scaffold

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Accepted                                                             |
| **Scope**       | platform (Governance/Tooling)                                       |
| **Erstellt**    | 2026-07-10                                                           |
| **Autor**       | Achim Dehnert (Entscheid) / Claude Sonnet 5 (Ausarbeitung, Fleet-Audit) |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | – (kein früheres ADR definiert den Skill-Scaffold explizit)          |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-021 (Unified Deployment Pattern), ADR-046 (Docs Hygiene), ADR-056 (Deployment Pre-Flight & Pipeline Hardening — Nachfolger von ADR-054), ADR-059 (ADR Drift Detector) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                          |
|----------------|------------|-----------------------------------------------------------|
| `platform`     | Primär     | `.windsurf/workflows/adr.md` (Step 4), `docs/templates/adr-template.md` |
| *alle ADR-tragenden Repos* | Sekundär | `.windsurf/workflows/adr.md` (via `cc-skill-dist`-Verteilung; betrifft jede künftige `/adr`-Ausführung, 34 Repos aktuell) |
| `iil-adrfw`    | Referenz   | `schemas/adr_frontmatter.schema.json` (unverändert — reine Body-Struktur-Frage, kein Frontmatter-Feld) |

---

## Decision Drivers

- **Selbstwiderspruch entdeckt, nicht konstruiert**: Der Fleet-Audit vom 2026-07-10 (`docs/adr/reviews/ADR-FLEET-AUDIT-2026-07-10.md`) fand, dass `platform` zwei nie abgeglichene, gleichzeitig gültige Struktur-Vorgaben für ADR-Bodies führt — `docs/templates/adr-template.md` (erklärt sich selbst als „Basis: MADR 4.0") und `.windsurf/workflows/adr.md` Step 4 (deutsches, nicht-MADR-benanntes 11-Abschnitt-Gerüst). Beide sind offiziell, keine ist als veraltet markiert.
- **Bereits mehrheitlich MADR-Vokabular im Bestand**: Über 692 ADRs/34 Repos zählt die MADR-Familie (Template + reines MADR-Englisch) 196 Dateien gegen 341 Skill-Gerüst-Dateien — kein Fremdkörper, sondern die knapp unterlegene, aber real gelebte Alternative. Selbst innerhalb von `platform` ist der Bestand fast hälftig gespalten (80 vs. 58 von 217).
- **Der Skill ist der Multiplikator**: `/adr` feuert bei jeder Neuanlage repo-übergreifend. Jede Session, die zufällig zuerst den Skill statt das Template liest (oder umgekehrt), erzeugt eine andere Struktur — nicht-deterministisch, ohne dass irgendjemand das entschieden hätte.
- **Governance-Aufwand ohne Nutzen**: Solange beide Quellen widersprüchlich sind, kann keine der beiden als „die" Konvention kommuniziert werden — jede Einführungs-Doku, jedes Onboarding muss beide kennen.

---

## 1. Context and Problem Statement

`platform` betreibt zwei parallele Quellen für die Body-Struktur neuer ADRs: die Template-Datei (MADR-4.0-Vokabular, numeriert, mit `Considered Options`/`Decision Outcome`/`Consequences`/`More Information`) und den `/adr`-Skill (deutsches 11-Abschnitt-Gerüst: Kontext/Entscheidung/Betrachtete Alternativen/Begründung im Detail/Implementation Plan/Risiken/Konsequenzen/Validation Criteria/Glossar/Referenzen/Changelog). Kein Dokument erklärt eine der beiden Strukturen für veraltet; keines verweist auf das andere.

### 1.1 Ist-Zustand

Body-Struktur-Klassifikation über 692 ADRs/34 Repos (H2-Überschriften-Scan, Fleet-Audit 2026-07-10):

| Familie | Dateien | Anteil |
|---|---|---|
| Skill-Gerüst (aktiv per `/adr`) | 341 | 49 % |
| Template-Gerüst + reines MADR-Englisch | 196 | 28 % |
| sonstige/gemischt/keine H2 | 155 | 22 % |

Kein Werkzeug prüft Body-Struktur (verifiziert: `iil-adrfw validate` ist Frontmatter-only; `platform`-CI ruft nur Validator/Staleness/Nummern-Guards; `adr_audit.py` prüft nur Nummernkonflikte). Die Divergenz ist damit unsichtbar, bis man sie wie hier explizit misst.

### 1.2 Warum jetzt

Der Fleet-Audit deckte den Widerspruch als Nebenbefund einer Struktur-Konformitäts-Analyse auf (Auftrag: „Vereinheitlichungen auf MADR sinnvoll?"). Je länger beide Quellen unentschieden nebeneinanderstehen, desto teurer wird die spätere Vereinheitlichung (mehr Bestand, mehr Gewöhnung an eine der beiden Formen).

---

## 2. Considered Options

### Option A: Skill-Scaffold auf Template-Struktur (MADR 4.0 + Platform-Erweiterungen) umstellen ✅

**Pros:**
- Das Template ist das einzige der beiden Artefakte mit Bezug auf einen **externen Standard** und wurde als legitimes MADR-4.0-Superset verifiziert (alle drei MADR-Pflichtabschnitte — Context and Problem Statement, Considered Options, Decision Outcome — enthalten; Abgleich gegen <https://adr.github.io/madr/> am 2026-07-10).
- Die MADR-Familie ist mit 196 von 692 Dateien die zweitstärkste gelebte Form und wächst organisch auch außerhalb von platform — kein Fremdkörper.
- Externes, dokumentiertes Vokabular — neue Mitarbeitende/Modelle kennen es ggf. bereits; Anschlussfähigkeit an Community-Tooling.

**Cons:**
- 341 bestehende ADRs bleiben strukturell „alt" — gemildert durch bewussten Verzicht auf retroaktive Umformatierung (§6.3).

### Option B: Template auf Skill-Struktur umstellen (deutsches 11-Abschnitt-Gerüst kanonisieren)

**Pros:**
- Skill-Gerüst ist im Bestand knapp häufiger (341 vs. 196).
- Kein Vokabular-Wechsel für die Mehrheit der Autoren.

**Cons:**
- Kanonisiert eine Eigennomenklatur ohne externen Standard — jede Doku, jedes Onboarding, jedes Tooling muss sie von Grund auf selbst erklären.
- Erforderte den Umbau des Templates gegen dessen expliziten Selbstbezug („Basis: MADR 4.0") — machbar, aber ohne inhaltlichen Gewinn. → **Abgelehnt weil:** bei fast gleichstarkem Bestand (341 vs. 196) gibt Anschlussfähigkeit + verifizierte Superset-Eigenschaft des Templates den Ausschlag — **nicht** ein früherer Beschluss (siehe §3, Einordnung: einen expliziten Body-Struktur-Beschluss gab es bislang nicht).

### Option C: Status quo — beide Quellen bleiben bestehen, keine Entscheidung

**Pros:**
- Kein Migrationsaufwand.

**Cons:**
- Der gemessene Selbstwiderspruch bleibt aktiv; jede neue ADR-Struktur bleibt vom Zufall abhängig, welche Quelle die Session zuerst liest. → **Abgelehnt weil:** das ist der dokumentierte Ist-Zustand, kein Lösungsvorschlag — Nichtstun war der Zustand, den der Fleet-Audit als Befund gemeldet hat.

---

## 3. Decision Outcome

**Gewählte Option: Option A — Skill-Scaffold auf Template-Struktur (MADR 4.0 + Platform-Erweiterungen) umstellen**

Der Skill-Scaffold in `.windsurf/workflows/adr.md` Step 4 wird durch einen Verweis auf `docs/templates/adr-template.md` als alleinige Struktur-SSOT ersetzt. Die Platform-Erweiterungen, die kein MADR-Bestandteil sind, aber begründet sind, bleiben erhalten: **Glossar** (wird ins Template gehoben, §4.2 — nicht mehr skill-seitig eingefügt), **Implementation Details**, **Migration Tracking**, **Risks**. Betroffen sind ausschließlich **neu erstellte** ADRs ab Merge dieses ADRs — keine rückwirkende Umformatierung (§6.3).

### 3.1 Einordnung: erste explizite Body-Struktur-Entscheidung (v1.1-Korrektur)

Die v1.0-Fassung rahmte dieses ADR als „Vollzug einer bereits getroffenen Entscheidung". Die Nachprüfung (2026-07-10) ergab: Das Template entstand als **Arbeitspaket von ADR-059** (Migration-Tracking, abgeschlossen 2026-02-21), aber ADR-059 verwendet „MADR-konform" ausschließlich für die **Status-State-Machine** (`draft → proposed → …`), nicht für die Body-Struktur; der Kopfkommentar „Basis: MADR 4.0" ist eine Selbstauskunft des Templates ohne eigenen Beschluss. Der Skill wiederum ist über ADR-229/230 (accepted) verteilungs-gedeckt — ebenfalls ohne Struktur-Beschluss. **Dieses ADR ist damit die erste explizite Entscheidung über die ADR-Body-Struktur der Plattform**, kein Vollzug. Die Options-Bewertung (§2) wurde entsprechend korrigiert: Option B verliert aus inhaltlichen Gründen, nicht wegen eines (nicht existenten) Präzedenz-Beschlusses.

### 3.2 Sprachentscheidung: englische Überschriften fleet-weit (Owner-Entscheid 2026-07-10)

Die Struktur-Umstellung ist zugleich eine **Sprachentscheidung**, die v1.0 nicht benannt hatte: Das Skill-Gerüst ist deutsch, MADR-Vokabular englisch — und die Skill-Gerüst-Repos mit den höchsten Anteilen sind genau die mit Behörden-Stakeholdern (`meiki-hub` 29/36, `risk-hub` 26/35, `ausschreibungs-hub` 9/9). Entschieden wird:

- **Abschnitts-Überschriften: kanonisch Englisch, fleet-weit** (MADR-Vokabular unverändert übernehmen; keine Zwei-Klassen-Struktur je Repo — eine Struktur-SSOT bleibt eine).
- **Prosa-Sprache bleibt frei** — Deutsch ist und bleibt in LRA-/Behörden-Repos üblich und erwünscht; die Entscheidung betrifft ausschließlich das Struktur-Vokabular (H2-Ebene).
- **Abfederung für Nicht-IT-Leser:** Glossar-Pflicht bleibt (und wandert ins Template, §4.2); die Glossar-Kandidatenliste wird um die MADR-Überschriften selbst ergänzt (ein Nicht-IT-Leser, der „Decision Outcome" nicht einordnen kann, findet es im Glossar).
- **Rückfalloption dokumentiert:** Zeigt sich dokumentierter Stakeholder-Widerstand (≥ 2 konkrete Fälle), ist eine deterministische DE-Überschriften-Mapping-Tabelle im Template als Amendment nachrüstbar — ohne die Struktur-SSOT zu brechen (Risiko-Tabelle §7).

---

## 4. Implementation Details

### 4.1 `.windsurf/workflows/adr.md` Step 4

Der Abschnitt „Pflicht-Metadaten-Template" + „Pflicht-Abschnitte (Reihenfolge einhalten)" (aktuell: Metadaten-Tabelle mit `Status/Scope/Repo/Erstellt/Autor/Reviewer/Supersedes/Relates to` + 11-Punkte-Liste `1. Kontext … 11. Changelog`) wird ersetzt durch:

```
### Pflicht-Struktur (SSOT: docs/templates/adr-template.md)

Datei-Inhalt = Kopie von docs/templates/adr-template.md, Platzhalter ausgefüllt.
NICHT die Struktur neu erfinden oder aus dem Gedächtnis rekonstruieren.

Pflicht-Abschnitte (siehe Template): Metadaten, Repo-Zugehörigkeit, Decision
Drivers, §1 Context and Problem Statement, §2 Considered Options, §3 Decision
Outcome, §4 Implementation Details, §6 Consequences, §8 Confirmation.
Optional (nur wenn zutreffend): §5 Migration Tracking (nur bei Transitions),
§7 Risks, §9 More Information, §10 Changelog.

Glossar: siehe Template (§Glossar) — Pflicht-Trigger und Kandidatenliste
stehen DORT, nicht hier. Der Skill fügt nichts ein, was das Template
nicht kennt.
```

**v1.1-Korrektur:** Die v1.0-Fassung wies den Skill an, einen Glossar-Abschnitt einzufügen, den das Template nicht kennt — das hätte den Ursprungsfehler (Skill weiß etwas, das die SSOT nicht weiß) eine Ebene tiefer reproduziert. Stattdessen wandert das Glossar ins Template (§4.2); der Skill referenziert nur.

### 4.2 `docs/templates/adr-template.md`

Zwei Ergänzungen (v1.1 — die v1.0-Aussage „kein struktureller Change nötig" ist damit überholt):

1. **Glossar-Abschnitt** (zwischen §8 Confirmation und §9 More Information): als optionaler Abschnitt mit dokumentiertem Pflicht-Trigger („Pflicht, sobald Fachbegriffe/Abkürzungen für Nicht-IT-Leser vorkommen") + der bisherigen Kandidatenliste aus dem Skill (ADR, KI, ML, LLM, HITL, OCR, API, DSGVO, DMS, QR, HMAC, CI/CD …), **ergänzt um die MADR-Überschriften selbst** (Context and Problem Statement, Considered Options, Decision Outcome, Confirmation — wegen §3.2 Sprachentscheidung).
2. **Sprachregel-Hinweis** im Kopfkommentar: Abschnitts-Überschriften kanonisch Englisch (fleet-weit, §3.2), Prosa-Sprache frei.

### 4.3 `cc-skill-dist`-Verteilung

Der geänderte Skill propagiert über den bestehenden `cc-skill-dist`-Mechanismus (siehe `MANAGED-BY`-Footer in `.windsurf/workflows/adr.md`) automatisch an alle konsumierenden Repos — kein manueller Rollout je Repo nötig.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `platform` (`docs/templates/adr-template.md`) | 1 — Glossar-Abschnitt + Sprachregel ins Template (§4.2) | ✅ Abgeschlossen | 2026-07-10 | Template v2.1, inkl. F-4-Fix (ADR-054→056) |
| `platform` (`.windsurf/workflows/adr.md`) | 2 — Skill-Scaffold umstellen (§4.1) | ✅ Abgeschlossen | 2026-07-10 | Step 4 verweist auf Template-SSOT |
| `platform` (`cc-skill-dist`) | 3 — Verteilung an konsumierende Repos | ⬜ Ausstehend | – | automatisch, kein Extra-Schritt |
| Struktur-Lint (F-3, Fleet-Audit-Backlog) | 4 — Enforcement, nur neue ADRs | ⬜ Ausstehend | – | separater Folge-PR, WARN nicht BLOCK |

---

## 6. Consequences

### 6.1 Good

- Eine Struktur-SSOT statt zweier widersprüchlicher — jede Session liest dieselbe Quelle, unabhängig davon, ob sie zuerst Template oder Skill sieht.
- Erste explizite Body-Struktur-Entscheidung überhaupt (§3.1) — der bisherige Zustand war unentschieden, nicht anders entschieden.
- Externes, dokumentiertes Vokabular (MADR) statt Eigenerfindung — Anschlussfähigkeit für neue Mitarbeitende/Modelle.

### 6.2 Bad

- Übergangszeit: bis Struktur-Lint (F-3) existiert, ist die neue Struktur nicht technisch erzwungen — reines Konventions-Vertrauen (wie bisher schon bei beiden Alt-Strukturen).
- 341 bestehende Skill-Gerüst-ADRs bleiben strukturell uneinheitlich zu neuen ADRs — akzeptiert, siehe 6.3.
- **Englische Überschriften sind für Behörden-/Nicht-IT-Leser (`meiki-lra`, `ttz-lif`) eine Lesbarkeits-Regression** — bewusst akzeptiert (Owner-Entscheid §3.2), abgefedert durch freie Prosa-Sprache + Glossar-Pflicht inkl. der MADR-Begriffe selbst; Rückfalloption (DE-Mapping-Tabelle) dokumentiert.

### 6.3 Nicht in Scope

- **Keine retroaktive Umformatierung** der 692 bestehenden ADR-Bodies. Kosten hoch, Nutzen ~null — akzeptierte historische Entscheidungen werden durch Überschriften-Kosmetik nicht besser, und die ADR-Praxis rät explizit von nachträglichem Umschreiben ab.
- Struktur-Lint/Enforcement (F-3) ist ein separater Folge-PR, kein Bestandteil dieses ADRs.
- Frontmatter-Schema (`iil-adrfw`) ist unberührt — reine Body-Struktur-Frage.

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Skill-Kopie driftet erneut vom Template ab (wie beim ursprünglichen Befund) | Mittel | Mittel | Quartals-Abgleichspunkt analog Wargame-WG-16-Muster; F-3-Lint macht Drift sichtbar statt nur SSOT-Verweis |
| Glossar-Pflicht geht beim Umbau verloren (LRA-Anforderung) | Niedrig | Hoch (Compliance-relevant für `meiki-lra`) | Explizit in §4.1 als eigener Pflicht-Absatz reformuliert, nicht nur implizit übernommen |
| Struktur-Wechsel ohne Enforcement wird ignoriert (Autoren nutzen weiter alte Gewohnheit) | Mittel | Niedrig | F-3-Struktur-Lint als Folge-Maßnahme vorgemerkt (Migration Tracking Phase 4) |
| EN-Überschriften senken Akzeptanz bei Behörden-Stakeholdern (meiki-lra/ttz-lif — 29/36 bzw. dominant deutsche Bestände) | Mittel | Mittel | Prosa bleibt deutsch; Glossar erklärt die MADR-Begriffe; bei ≥ 2 dokumentierten Widerstands-Fällen: DE-Mapping-Tabelle als Amendment (§3.2 Rückfalloption) |

---

## 8. Confirmation

1. **Stichprobe der nächsten 5 neu erstellten ADRs**: manuell gegen Template-Struktur geprüft (H2-Überschriften-Abgleich) — im Rahmen des nächsten Fleet-Audits.
2. **F-3-Struktur-Lint** (sobald gebaut): automatischer WARN-Check neuer ADRs gegen die kanonische Abschnittsliste.
3. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: 6 Monate (Governance-Entscheidungen altern schneller als technische).

---

## Glossar

| Abkürzung | Bedeutung |
|-----------|-----------|
| **ADR** | Architecture Decision Record — dokumentierte Architektur-Entscheidung |
| **MADR** | Markdown Architectural Decision Records — offener, versionierter Community-Standard für ADR-Struktur |
| **SSOT** | Single Source of Truth — die eine maßgebliche Quelle für eine Information |
| **Fleet-Audit** | Cross-Repo-Analyse aller ADR-tragenden Repos (hier: `docs/adr/reviews/ADR-FLEET-AUDIT-2026-07-10.md`) |

---

## 9. More Information

- Fleet-Audit-Report (Grundlage dieses ADRs): `docs/adr/reviews/ADR-FLEET-AUDIT-2026-07-10.md` (PR #1040)
- MADR-Projekt: <https://adr.github.io/madr/>
- ADR-021: Unified Deployment Pattern — Teil der Template-Governance-Basis
- ADR-046: Docs Hygiene — Teil der Template-Governance-Basis
- ADR-056: Deployment Pre-Flight & Pipeline Hardening — Nachfolger von ADR-054, Template-Zitat korrigiert (Fleet-Audit F-4)
- ADR-059: ADR Drift Detector — prüft dieses ADR auf Staleness

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-10 | Achim Dehnert | Accepted (PR-#1042-Approve nach v1.1-Amendment) |
| 2026-07-10 | Achim Dehnert / Claude Fable 5 | v1.1 (Amendment nach adversarialem Review, vor Merge): §3.1 Einordnung korrigiert („Vollzug"-Framing war falsch — ADR-059 entschied MADR nur für die Status-State-Machine; dies ist die erste explizite Body-Struktur-Entscheidung), §3.2 Sprachentscheidung EN fleet-weit (Owner-Entscheid) inkl. LRA-Abfederung + Rückfalloption, §4.1/4.2 Glossar ins Template gehoben (Skill-Einfügung hätte die Divergenz reproduziert), §2 Option-A/B-Begründungen ehrlich neu gefasst, §6.2/§7 um Sprach-Regression ergänzt |
| 2026-07-10 | Achim Dehnert / Claude Sonnet 5 | Initial: Status Proposed, aus Fleet-Audit F-1 |

---

<!--
  GOVERNANCE-HINWEISE (werden nicht in dev-hub angezeigt):

  Drift-Detector-Felder (ADR-059):
  - staleness_months: 6
  - drift_check_paths:
      - platform/.windsurf/workflows/adr.md
      - platform/docs/templates/adr-template.md
  - supersedes_check: true

  Review-Checkliste: /docs/templates/adr-review-checklist.md
  Template-Version: 2.0 (2026-02-21)
-->
