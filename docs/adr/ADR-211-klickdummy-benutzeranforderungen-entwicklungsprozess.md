---
id: ADR-211
title: Klickdummy — Benutzeranforderungs-Erfassung und Entwicklungsprozess (Cross-Repo-Rahmen)
status: proposed
date: 2026-05-19
deciders: [achim]
consulted: [cascade-advocatus-diabolus]
informed: [all-repos]
domains: [ux, requirements, process, drift-prevention]
supersedes: []
amends: []
depends_on: [ADR-207]
tags: [klickdummy, mockup, requirements, parity-test, ux, convention]
scope:
  include_paths:
    - "*/docs/adr/ADR-*klickdummy*.md"
    - "*/klickdummy/**"
    - "*/docs/01-architektur/mockups/**"
---

# ADR-211: Klickdummy — Benutzeranforderungs-Erfassung und Entwicklungsprozess (Cross-Repo-Rahmen)

- **Status:** proposed
- **Datum:** 2026-05-19
- **Entscheider:** Achim Dehnert
- **Verwandt:** ADR-207 (Cross-Repo-Ingest-/Doku-Konvention — Schwester­muster), risk-hub:ADR-046 (Spec-Driven UI Convention, repo-lokal — Implementierung), writing-hub:ADR-180 (Lectures-Wizard / Static→Echt-Migration — Implementierung), meiki-hub:ADR-020 (Manifest-Klickdummy-Konvention — Implementierung)

## Zusammenfassung

Mehrere Repos bauen „Klickdummies" — interaktive Mockups zur **frühen
Erfassung und Validierung von Benutzeranforderungen** vor der Implementierung.
Die Ansätze sind heute **divergent und ohne gemeinsames Vokabular**: meiki-hub
nutzt einen manifest-getriebenen Single-File-Static-Mockup mit CI-Invariante,
writing-hub server-gerenderte echte Templates mit Parity-Test und einem
„Static → echt → entfernen"-Lebenszyklus, risk-hub eine bewusst repo-lokale
Spec-Driven-UI-Convention. Diese Divergenz hat bereits zu einer
Cross-Repo-Fehlzuordnung geführt (gleiche Begriffe „ADR-180"/„klickdummy"
meinen je Repo Verschiedenes). Dieses ADR setzt einen **Cross-Repo-Rahmen**:
Zweck, sanktionierte Ansätze samt **Auswahlmatrix**, verbindlicher
**Lebenszyklus** und gemeinsame **Qualitäts-Gates** — *ohne* eine konkrete
Implementierung vorzuschreiben. Die repo-lokalen ADRs bleiben die
Implementierungen und behalten ihre Autonomie.

## Kontext und Problemstellung

Belegte Ist-Lage (2026-05-19):

| Repo | Ansatz | Eigenes ADR |
|---|---|---|
| **meiki-hub** | Manifest-getriebener Single-File-Static-Mockup; SSoT `module-manifest.json`; CI-Invariante (Entitlement/RBAC); Target-Mock für Systemgrenzen; frozen Reference-States | ADR-020 (mit diesem ADR neu) |
| **writing-hub** | Server-gerenderte **echte Django-Templates**; `?demo=<state>` (nur non-prod); **Parity-Test** Klickdummy↔Template; Lebenszyklus „Static entfernen, sobald echt" | ADR-180 |
| **risk-hub** | `klickdummy/verify_dummy.py`; **Spec-Driven UI Convention** + optionaler Visual-Regression-Layer; bewusst **repo-lokal** | ADR-046 (Rev 2) |

Drei Repos, drei Formen, kein gemeinsamer Begriff von „fertig" und kein
geteilter Übergangs-Playbook. Künftig werden weitere Repos Klickdummies
brauchen (u. a. risk-hub „Redesign UX"). **ADR-pflichtig** nach
`adr-threshold.md`: cross-cutting über mehrere Repos **und** nicht-trivialer,
wiederkehrender Trade-off (Static-Mockup vs. Echt-Template-Parity), der für
künftige Challenger festzuhalten ist.

> **Schon einmal verbrannt:** Die Mehrdeutigkeit von „ADR-180" und „klickdummy"
> über Repo-Grenzen hinweg verursachte eine konkrete Fehlzuordnung. Dieses ADR
> ist die Drift-Lehre daraus — gemeinsames Vokabular statt Re-Derivation.

## Betrachtete Optionen

1. **Prozess-/Rahmen-ADR (gewählt):** standardisiert Zweck, Ansatz-Auswahl,
   Lebenszyklus und Gates; Implementierung bleibt repo-lokal.
2. **Rahmen + Default-Stack je Projekttyp:** wie 1, zusätzlich verbindlicher
   Default — stärkere Steuerung, höheres Kollisionsrisiko mit Repo-ADRs.
3. **Voller Implementierungs-Standard:** ein Framework/Schema für alle Repos —
   maximale Konsistenz, kollidiert frontal mit writing-hub (echte Templates ≠
   Single-File-Static) und mit der bewussten Repo-Lokalität von risk-hub
   ADR-046; degeneriert mit genug Ausnahmen ohnehin zu Option 1.

## Entscheidung

**Option 1 — Prozess-/Rahmen-ADR — mit integrierter Auswahlmatrix** (das
wertvolle Element aus Option 2, ohne dessen Steuerungs-Overreach). Option 3
wird verworfen (Konflikt mit ADR-046/ADR-180).

### Was dieses ADR plattformweit regelt

**1. Zweck (verbindlich):** Ein Klickdummy ist ein Werkzeug zur **frühen
Erfassung, Visualisierung und Validierung von Benutzeranforderungen** mit der
Fachseite — *kein* Produktionscode und *kein* Designsystem-Ersatz. Er macht
Anforderungen und Systemgrenzen vor der Implementierung diskutierbar.

**2. Auswahlmatrix — welcher Ansatz wann:**

| Kriterium | Static-Mockup (manifest-/datei-getrieben) | Echt-Template + Parity |
|---|---|---|
| Phase | Konzept-/Workshop-Phase, Vergabe/Vorprojekt | App-Repo mit Zielsystem in Entwicklung |
| Backend vorhanden? | nein / irrelevant | ja (Templates wandern in die App) |
| Zielartefakt | wegwerfbares Kommunikationsmittel | Migrationspfad in Produktion |
| Pflicht-Gate | CI-Konsistenz-Invariante | **Parity-Test** Klickdummy↔Template |
| Repo-Beispiel | meiki-hub (ADR-020) | writing-hub (ADR-180) |
| Spec-zentriert (UI-Spec als Artefakt) | optional | risk-hub (ADR-046) |

**3. Lebenszyklus (verbindlich, sobald ein Zielsystem existiert):**
`Klickdummy → Fachabteilungs-Review (dokumentiert) → echte Templates →
Parity-Test sichert Äquivalenz → Static-Reste entfernen`. Ein Static-Klickdummy
ohne Zielsystem (reine Konzeptphase) endet beim Review; er wird **nicht**
unbegrenzt parallel zur App gepflegt.

**4. Qualitäts-Gates (plattformweit, repo-unabhängig):**
- **Keine Echtdaten, keine echte Authentisierung** — Systemgrenzen als
  Target-Mock sichtbar (Absprung benannt, nicht toter Link).
- **CI-Invariante** je Klickdummy (Konsistenz dessen, was der Dummy behauptet —
  z. B. Manifest==Nav bzw. Parity Dummy==Template).
- **Frozen Reference-States** explizit kennzeichnen (eingefrorener Vergleichs­stand).
- **Auditpflicht-Hinweis**: jede simulierte Aktion, die real auditpflichtig
  wäre, ist im Dummy als Mock markiert.
- **Reviewfähigkeit**: Anforderungs-Herkunft (Workshop/Fachabteilung) ist
  verlinkt; Klickdummy referenziert das zugehörige Anforderungs-/Scope-Dokument.

### Was dieses ADR **nicht** regelt (bleibt repo-lokal)

Konkreter Tech-Stack, Template-/Manifest-Schema, UI-Bausteine, Teststack. Die
repo-lokalen ADRs (meiki-hub ADR-020, risk-hub ADR-046, writing-hub ADR-180)
bleiben die maßgeblichen **Implementierungen** und behalten Autonomie; sie
deklarieren lediglich ihre Konformität zu Zweck/Lebenszyklus/Gates dieses
Rahmens. Dieses ADR **ersetzt sie nicht** und hebt insbesondere die bewusste
Repo-Lokalität von risk-hub ADR-046 nicht auf.

## Konsequenzen

**Positiv**
- Gemeinsames Vokabular und „fertig"-Begriff über Repos → Drift-/Kollisions­schutz.
- Static→Echt-Migration ist ein vorab entschiedenes Playbook statt pro Repo neu verhandelt.
- Neue Repos bekommen Zweck + Gates + Auswahlhilfe von der Stange (Onboarding).

**Negativ / Kosten**
- Reduziert *Implementierungs*-Divergenz nicht (kein geteiltes Framework/CI erzwungen).
- Zusätzliche Konformitäts-Deklaration in repo-lokalen ADRs nötig.

**Neutral**
- Bestehende Klickdummies bleiben funktional unverändert; nur ADR-Einordnung wird ergänzt.

## Confirmation

- Jedes Repo mit Klickdummy hat ein repo-lokales ADR, das Konformität zu
  Zweck/Lebenszyklus/Gates dieses Rahmens erklärt (meiki-hub ADR-020,
  risk-hub ADR-046, writing-hub ADR-180 referenzieren ADR-211).
- Kein Klickdummy mit Zielsystem wird dauerhaft parallel zur App gepflegt
  (Lebenszyklus-Check im jeweiligen Repo-CI/Review).
- Adversarial-Review (cascade-advocatus-diabolus) bestätigt keinen Konflikt
  mit ADR-046/ADR-180.

## Glossar (lokal)

| Begriff | Definition |
|---|---|
| **Klickdummy** | Interaktives Mockup zur frühen Anforderungs-Erfassung/-Validierung; kein Produktionscode |
| **Static-Mockup** | Klickdummy ohne Backend (datei-/manifest-getrieben, ggf. Single-File) |
| **Echt-Template-Klickdummy** | Klickdummy über die *echten* Templates des Zielsystems (z. B. `?demo=<state>` nur non-prod) |
| **Parity-Test** | Automatischer Test, der Klickdummy-Zustände gegen die echten Templates auf Äquivalenz prüft |
| **Frozen Reference-State** | Eingefrorener Vergleichsstand eines Klickdummys |
| **Target-Mock** | Sichtbar gemachte Systemgrenze (benannter Absprung statt totem Link) |

## Bezug

- ADR-207 — Cross-Repo-Ingest-/Doku-Konvention (Schwestermuster, Platform)
- risk-hub:ADR-046 — Spec-Driven UI Convention (Implementierung, repo-lokal)
- writing-hub:ADR-180 — Lectures-Wizard, Static→Echt-Migration (Implementierung)
- meiki-hub:ADR-020 — Manifest-Klickdummy-Konvention (Implementierung)
- Policy `adr-threshold.md` (Cross-cutting + nicht-trivialer Trade-off → ADR-pflichtig)
