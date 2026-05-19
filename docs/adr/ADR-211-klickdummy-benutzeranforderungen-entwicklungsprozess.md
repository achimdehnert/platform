---
id: ADR-211
title: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)
status: proposed
date: 2026-05-19
deciders: [achim]
informed: [all-repos]
review_history:
  - 2026-05-19: Rev 1 — initial proposal
  - 2026-05-19: Rev 2 — adversarial review feedback integrated (commit bf7c4d6)
  - 2026-05-19: Rev 3 — second adversarial pass: enforcement-path moved into repo, I1/Confirmation executable, Mock→Impl transition specified
domains: [ux, requirements, process, security, drift-prevention]
supersedes: []
amends: []
depends_on: [ADR-207]
tags: [klickdummy, mockup, requirements-spec, parity-test, prod-guard, convention]
scope:
  governed_artifacts:
    - "platform/policies/klickdummy.md (operative Regel, im Repo versioniert, auto-injiziert)"
    - "meiki-hub:ADR-020 (Implementierung)"
    - "risk-hub:ADR-046 (Implementierung)"
    - "writing-hub:ADR-180 (Implementierung)"
    - "onboard-repo Skill — Adoptionspunkt"
---

# ADR-211: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)

- **Status:** proposed
- **Datum:** 2026-05-19
- **Entscheider:** Achim Dehnert
- **Verwandt:** ADR-207 (Cross-Repo-Ingest-/Doku-Konvention), risk-hub:ADR-046, writing-hub:ADR-180, meiki-hub:ADR-020
- **Adversarial reviews:** zwei Cascade-Paßagen (2026-05-19), siehe Frontmatter `review_history` und Followup-Issues `adr-211-followup`

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
| **I1 Spec-first** | Es existiert ein **maschinenlesbares**, versioniertes Anforderungs-/Spec-Artefakt (YAML/JSON/strukturiertes Frontmatter). Der Klickdummy *rendert* es, ist nicht selbst die Quelle. Bullet-Listen in Markdown zählen nicht. | Repo-Conformance-Test mit Exit-Code: `make klickdummy-i1` — parst Spec, rendert, diff/assert. Konformitäts-Erklärung wird via CI verifiziert, nicht als Frontmatter-Behauptung akzeptiert. |
| **I2 Prod-Sicherheit** | **Mock-Prototyp**: keine Echtdaten/-Auth, Systemgrenzen als Target-Mock sichtbar. **Demo-Render**: env-gegated, CI weist Nicht-Erreichbarkeit in Prod nach. | CI-Assertion je Repo; Prod-Smoke „`?demo=` → 404/disabled" |
| **I3 Lebenszyklus mit Off-Ramp** | Phase A — *ohne Zielsystem*: Klickdummy endet beim dokumentierten Fachabteilungs-Review. "Ende" = ADR-Status → `superseded` oder `accepted-frozen`, Spec versioniert eingefroren, Klickdummy-Pfad nach `klickdummy/archive/`. Phase B — *Transition zu Zielsystem*: Sobald **der erste Screen** der Spec eine Implementierungs-Route bekommt (Django-View / API-Endpoint), startet I3-Pflicht je Screen. Phase C — *mit Zielsystem*: Parity-grün pro Screen ⇒ statische Quelle dieses Screens entfernt; keine Doppelquelle über eine Release-Grenze. | `make klickdummy-i3` — listet Spec-Screens, listet implementierte Routes, listet statische Renders; assert: für jeden Screen mit Implementierungs-Route + grünem Parity-Test ist die statische Quelle abwesend. Release-Grenze = jedes deploy auf staging oder prod (Tag oder Container-Push). |
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

Ein ungelesenes ADR ändert nichts. Wirksamkeit ausschließlich über
**im Repo versionierte** Artefakte (kein User-Home, kein Single-Laptop):

1. **Rationale:** dieses ADR.
2. **Operative Regel:** `platform/policies/klickdummy.md` — im Plattform-Repo
   versioniert, plattform-gemeinsam, von **jedem** Onboarding-Pfad lesbar.
   Auto-Injektion via Cascade/Claude-Policy-Loader liest aus dieser Datei,
   nicht aus `~/.claude/`. Die User-Home-Variante ist explizit deprecated
   (siehe Followup-Issue `adr-211-followup` SF1).
3. **Adoptionspunkt:** `onboard-repo`-Skill-Checkliste prüft I1–I4 +
   ADR-Header + Existenz von `make klickdummy-{i1,i2,i3,i4}` Targets.
4. **Verifikation:** plattformweiter CI-Check `platform/scripts/checks/klickdummy_registry.sh`:
   - listet alle Repos mit `klickdummy/`-Pfad aus `registry/repos.yaml`
   - assert: jedes hat ein ADR mit `conforms_to: ADR-211`
   - assert: jedes hat `make klickdummy-i1`-Target, der mit Exit 0 endet
   Exit-Code != 0 ⇒ Plattform-CI rot.

## Konsequenzen

**Positiv:** Spec-first beendet Renderer-Wildwuchs; Off-Ramp verhindert
Static-Leichen; Demo-Render-Prod-Guard schließt eine echte Sicherheitslücke;
Enforcement nutzt vorhandene Policy-Auto-Injektion statt neuer Bürokratie.
**Negativ:** Repos brauchen einen Spec==Render-CI-Check (Aufwand einmalig);
Policy-Datei + Registry-Assertion sind Folgeaufwand.
**Neutral:** Bestehende Klickdummies funktional unverändert; nur Einordnung +
Off-Ramp-Pflicht neu.

## Confirmation (executable, nicht Selbstauskunft)

Jeder Punkt unten ist ein konkreter Befehl mit Exit-Code:

```bash
# C1 Registry-Konformität
platform/scripts/checks/klickdummy_registry.sh
# exit 0 ⇒ alle Repos mit `klickdummy/`-Pfad haben ADR mit `conforms_to: ADR-211`

# C2 I1 Spec==Render je Repo
make -C <repo> klickdummy-i1

# C3 I2 Prod-Guard je Demo-Render-Repo
curl -fsS "https://<repo>.iil.pet/?demo=foo" | grep -q 'demo mode' && exit 1 || exit 0
# zusätzlich: Middleware-Unit-Test, der `?demo` in PROD strippt, exit 0

# C4 I3 Dual-Source bei jedem Deploy-Tag
make -C <repo> klickdummy-i3

# C5 I4 Cross-Repo-Referenz-Format
platform/scripts/checks/adr_cross_repo_refs.sh
# parst alle ADRs, assert: cross-repo-refs matchen `^[a-z][a-z0-9-]+:ADR-\d{3}$`

# C6 Policy existiert plattform-versioniert
test -f platform/policies/klickdummy.md && exit 0 || exit 1
```

Adversarial-Review-Historie: siehe Frontmatter `review_history`. "Kein
offener Konflikt" ist **nicht** Confirmation-Kriterium — zukünftige Reviews
produzieren Followup-Issues, dieses ADR wird nur geändert, wenn ein
Issue Rev-pflichtig ist.

## Glossar (lokal)

| Begriff | Definition |
|---|---|
| **Anforderungs-Spec** | Versioniertes, **maschinenlesbares** Quell-Artefakt der Anforderung (Manifest/UI-Spec in YAML/JSON/strukturiertem Frontmatter) — das dauerhafte Gut. Markdown-Bullets zählen nicht. |
| **Klickdummy** | Oberbegriff für einen *Renderer* der Spec zur frühen Validierung |
| **Mock-Prototyp** | Separater Wegwerf-Renderer ohne Backend (Systemgrenzen als Target-Mock) |
| **Demo-Render** | Env-gegateter Zustand der *echten* App (`?demo=<state>`) — Prod-Sicherheitsfläche |
| **Parity-Test** | Test, der Renderer-Zustände gegen die echte Implementierung auf Äquivalenz prüft — das Konformitäts-Gate **und** die Off-Ramp |
| **Off-Ramp** | Parity-grün ⇒ mechanische Entfernung der statischen Quelle dieses Screens |

## Bezug

- ADR-207 — Cross-Repo-Ingest-/Doku-Konvention (Schwestermuster)
- risk-hub:ADR-046 · writing-hub:ADR-180 · meiki-hub:ADR-020 (Implementierungen, I1–I4-konform zu erklären)
- Folge: `platform/policies/klickdummy.md` anlegen (im Repo, nicht in `~/.claude/`); Policy-Loader auf Repo-Pfad umstellen; Drift-Memory `2026-05-19-klickdummy-adr180-collision` als Issue belegen
- Policy `adr-threshold.md` (Selbsttest oben)
