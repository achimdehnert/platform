---
id: ADR-211
title: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)
status: proposed
date: 2026-05-19
deciders: [achim]
consulted: [cascade-advocatus-diabolus]
informed: [all-repos]
domains: [ux, requirements, process, security, drift-prevention]
supersedes: []
amends: []
depends_on: [ADR-207]
tags: [klickdummy, mockup, requirements-spec, parity-test, prod-guard, convention]
scope:
  governed_artifacts:
    - "platform/.claude/policies/klickdummy.md (operative Regel, auto-injiziert)"
    - "meiki-hub:ADR-020 (Implementierung)"
    - "risk-hub:ADR-046 (Implementierung)"
    - "writing-hub:ADR-180 (Implementierung)"
    - "onboard-repo Skill — Adoptionspunkt"
---

# ADR-211: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)

- **Status:** proposed
- **Datum:** 2026-05-19
- **Entscheider:** Achim Dehnert · **Adversarial-Review:** cascade-advocatus-diabolus (eingearbeitet, Rev 2)
- **Verwandt:** ADR-207 (Cross-Repo-Ingest-/Doku-Konvention), risk-hub:ADR-046, writing-hub:ADR-180, meiki-hub:ADR-020

## Zusammenfassung

Mehrere Repos bauen „Klickdummies". Der naheliegende Rahmen — „jeder macht
weiter sein Ding, wir teilen Vokabular" — wäre **keine Entscheidung** (per
`adr-threshold.md` reichte dafür eine Konvention). Dieses ADR trifft stattdessen
drei harte, erzwingbare Entscheidungen, weil jede einen realen Schaden verhindert:

1. **Spec-zentriert statt Renderer-zentriert.** Das dauerhafte Artefakt ist die
   **Anforderungs-Spec**, nicht ihre Darstellung. Ein Klickdummy ist *ein
   Renderer* dieser Spec; ein Parity-Test ist das **Spec-Konformitäts-Gate**.
   Das löst die Scheindichotomie „Static vs. echte Templates" auf.
2. **Mock-Prototyp ≠ Demo-Render — mit hartem Prod-Guard.** Ein Demo-Render der
   *echten* App (`?demo=<state>`) ist eine **Prod-Sicherheitsfläche**, kein
   Mockup. Er ist verpflichtend env-gegated und per CI als in Prod
   nicht-erreichbar nachzuweisen.
3. **Parity-grün ist die Off-Ramp.** Sobald der Parity-Test für einen Screen
   grün ist, ist dessen statische Quelle **mechanisch zu entfernen**; Doppel­quelle
   über eine Release-Grenze hinaus ist CI-Verstoß. Das beendet das reale
   „Static-Reste bleiben ewig liegen"-Muster.

Implementierungs-Stack bleibt repo-lokal; die **Invarianten** unten sind
ansatz-offen (auch KI-generierte oder Design-Tool-Prototypen sind zulässig,
solange sie die Invarianten erfüllen).

## Kontext

Belegte Ist-Lage (2026-05-19): meiki-hub (manifest-getriebener Single-File-Mock,
CI-Invariante), writing-hub (`?demo=`-Render echter Django-Templates +
Parity-Test, ADR-180), risk-hub (Spec-Driven UI Convention, bewusst repo-lokal,
ADR-046 Rev 2). Drei Formen, kein gemeinsamer „fertig"-Begriff, kein
Off-Ramp-Trigger. Die Mehrdeutigkeit von „klickdummy"/„ADR-180" über
Repo-Grenzen verursachte in dieser Session eine konkrete Fehlzuordnung —
**dieses ADR ist die Drift-Lehre daraus** (Episode `2026-05-19-klickdummy-adr180-collision`;
zusätzlich als Memory + Policy zu verankern, nicht nur hier erzählt).

> **Warum überhaupt ein ADR (Selbsttest gegen `adr-threshold.md`):** Es kehrt
> den Status quo *repo-autonomer Klickdummy-Proliferation* um, adressiert eine
> **Sicherheitsfläche** (Demo-Render in Prod) und ist cross-cutting über ≥ 3
> Repos. Damit erfüllt es drei der Pflicht-Kriterien — es ist eine Entscheidung,
> keine Ergänzung.

## Entscheidung — vier Invarianten (ansatz-offen)

Jeder Klickdummy in jedem Repo, unabhängig vom Stack:

| # | Invariante | Erzwingung |
|---|---|---|
| **I1 Spec-first** | Es existiert ein versioniertes **Anforderungs-/Spec-Artefakt** (Manifest, UI-Spec, Anforderungsliste). Der Klickdummy *rendert* es, ist nicht selbst die Quelle. | repo-lokaler CI-Check „Spec == Render" (meiki: Manifest==Nav; writing-hub: Parity-Test; risk-hub: Spec-Driven) |
| **I2 Prod-Sicherheit** | **Mock-Prototyp**: keine Echtdaten/-Auth, Systemgrenzen als Target-Mock sichtbar. **Demo-Render**: env-gegated, CI weist Nicht-Erreichbarkeit in Prod nach. | CI-Assertion je Repo; Prod-Smoke „`?demo=` → 404/disabled" |
| **I3 Lebenszyklus mit Off-Ramp** | Existiert ein Zielsystem: Parity-grün ⇒ statische Quelle des Screens entfernt; keine Doppelquelle über eine Release-Grenze. Ohne Zielsystem: Endet beim dokumentierten Fachabteilungs-Review. | CI-Verstoß bei Dual-Source; Review-Gate-Doku |
| **I4 Namensraum** | Repo-lokales Klickdummy-ADR trägt reserviertes Titel-Präfix; Cross-Repo-Referenzen **nur** qualifiziert als `repo:ADR-NNN`. | Lint im onboard-repo-/ADR-Check |

**Auswahlhilfe (illustrativ, nicht abschließend):** Konzept-/Vergabephase ohne
Backend → Mock-Prototyp (Bsp. meiki-hub ADR-020). App-Repo mit Zielsystem →
Demo-Render echter Templates + Parity (Bsp. writing-hub ADR-180). UI-Spec als
primäres Artefakt → Spec-Driven (Bsp. risk-hub ADR-046). Andere Ansätze
(KI-generiert, Figma-as-Spec) sind zulässig, sofern I1–I4 erfüllt sind.

### Was repo-lokal bleibt

Tech-Stack, Schema, UI-Bausteine, Teststack. risk-hub ADR-046 behält seine
bewusste Repo-Lokalität; dieses ADR ersetzt **keine** Implementierungs-ADR,
sondern fordert nur deren Konformitätserklärung zu I1–I4.

## Enforcement-Pfad (sonst inert)

Ein ungelesenes ADR ändert nichts. Wirksamkeit über die *bestehende*
Plattform-Maschinerie:

1. **Rationale:** dieses ADR.
2. **Operative Regel:** `~/.claude/policies/klickdummy.md` (Trigger:
   „klickdummy", „mockup", „parity") — wird wie `adr-threshold.md` jede Session
   auto-injiziert. *(Anlage über `claude-policy`-CLI aus orchestrator-fähiger
   Session — Folge-Schritt, hier nicht ausführbar.)*
3. **Adoptionspunkt:** `onboard-repo`-Skill-Checkliste prüft I1–I4 + ADR-Header.
4. **Verifikation:** Registry/CI-Assertion — Repo mit `klickdummy/`-Pfad ⇒
   konformes Klickdummy-ADR mit `conforms_to: ADR-211`.

## Konsequenzen

**Positiv:** Spec-first beendet Renderer-Wildwuchs; Off-Ramp verhindert
Static-Leichen; Demo-Render-Prod-Guard schließt eine echte Sicherheitslücke;
Enforcement nutzt vorhandene Policy-Auto-Injektion statt neuer Bürokratie.
**Negativ:** Repos brauchen einen Spec==Render-CI-Check (Aufwand einmalig);
Policy-Datei + Registry-Assertion sind Folgeaufwand.
**Neutral:** Bestehende Klickdummies funktional unverändert; nur Einordnung +
Off-Ramp-Pflicht neu.

## Confirmation (checkbar, nicht Selbstauskunft)

- CI-Assertion: jedes Repo mit `klickdummy/`-Pfad hat ein ADR mit
  `conforms_to: ADR-211` und benennt seinen I1-Spec==Render-Check.
- Prod-Smoke je Demo-Render-Repo: `?demo=<state>` ist in Prod nicht erreichbar.
- Dual-Source-Check: kein Screen mit gleichzeitig statischer Quelle und grünem
  Parity-Test über eine Release-Grenze.
- `~/.claude/policies/klickdummy.md` existiert und ist auto-injiziert.
- Adversarial-Review (cascade-advocatus-diabolus) ohne offenen Konflikt mit
  ADR-046/ADR-180 — eingearbeitet in Rev 2 (dieses Dokument).

## Glossar (lokal)

| Begriff | Definition |
|---|---|
| **Anforderungs-Spec** | Versioniertes Quell-Artefakt der Anforderung (Manifest/UI-Spec/Liste) — das dauerhafte Gut |
| **Klickdummy** | Oberbegriff für einen *Renderer* der Spec zur frühen Validierung |
| **Mock-Prototyp** | Separater Wegwerf-Renderer ohne Backend (Systemgrenzen als Target-Mock) |
| **Demo-Render** | Env-gegateter Zustand der *echten* App (`?demo=<state>`) — Prod-Sicherheitsfläche |
| **Parity-Test** | Test, der Renderer-Zustände gegen die echte Implementierung auf Äquivalenz prüft — das Konformitäts-Gate **und** die Off-Ramp |
| **Off-Ramp** | Parity-grün ⇒ mechanische Entfernung der statischen Quelle dieses Screens |

## Bezug

- ADR-207 — Cross-Repo-Ingest-/Doku-Konvention (Schwestermuster)
- risk-hub:ADR-046 · writing-hub:ADR-180 · meiki-hub:ADR-020 (Implementierungen, I1–I4-konform zu erklären)
- Folge: `~/.claude/policies/klickdummy.md` anlegen (claude-policy-CLI); Drift-Memory `2026-05-19-klickdummy-adr180-collision`
- Policy `adr-threshold.md` (Selbsttest oben)
