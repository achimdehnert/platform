---
id: ADR-268
title: Projekt-Assurance-Tiers — Projektart × Reife-Phase als plattformweite Risiko-Achse (Cross-Repo)
status: accepted
date: 2026-07-09
deciders: [achim]
informed: [all-repos]
domains: [governance, process, security, deployment, drift-prevention]
supersedes: []
amends: []
depends_on: [KONZ-platform-009]
consumed_by: [ADR-267]
tags: [assurance-tier, project-class, lifecycle, risk-based, registry, fail-closed, sovereignty]
scope:
  include_paths:
    - "platform/infra/**"
    - "**/project-facts.md"
---

# ADR-268: Projekt-Assurance-Tiers — Projektart × Reife-Phase als plattformweite Risiko-Achse (Cross-Repo)

- **Status:** accepted *(2026-07-09, Owner-Entscheidung. Enforcement-Grenze: die Achse ist definiert; scharf wird sie erst mit dem Registry-`tier`-Feld + dessen CI-Check.)*
- **Datum:** 2026-07-09
- **Entscheider:** Achim Dehnert
- **Verwandt:** KONZ-platform-009 (registry-unified-ssot), ADR-211 (Klickdummy = nie Prod), ADR-267 (Review-Requirement — erster Konsument dieser Achse)

## Zusammenfassung

Governance-Strenge (Review-Pflicht, später auch CI-Härte, Coverage-Schwellen, Deploy-Gates,
Datenhandling) darf **nicht** für alle Repos gleich sein — ein privates Wegwerf-Repo braucht nicht
die Government-Strenge, und **kein** Projekt darf in der frühen Prototyp-Phase durch Prod-Rigidität
ausgebremst werden. Dieses ADR definiert **eine** wiederverwendbare Risiko-Achse aus **zwei
Dimensionen** und macht sie **verbindlich pro Repo** hinterlegbar.

## Kontext & Problem

- Eine „one-size-fits-all"-Policy ist entweder zu lasch (für Government/Tenant) oder bremst zu stark
  (für private/PoC/Prototypen).
- Der erste Konsument (ADR-267, Review-Requirement) braucht eine **verbindliche** Antwort auf
  „wie streng ist *dieses* Repo?" — und zwar so, dass jeder Mensch und jede Automation es über
  **einen** Lookup kennt.
- Strenge hängt nicht nur an der *Projektart*, sondern am **realen Exposure**: ein Government-
  Projekt als Klickdummy hat keine echten Daten und kein Prod (ADR-211: KD ist nie Prod).

## Entscheidung

**Zwei Achsen; die effektive Strenge ist `f(Projektart, Reife-Phase)`.**

### Achse 1 — Projektart (Ziel-Assurance / Decke)

Legt die **Ziel-Strenge in Prod** + die **harten Constraints** fest (Souveränität/DSGVO). Sechs
Klassen, T0–T5:

| Projektart | Tier | Ziel-Strenge in Prod | Harte Constraints (ab Prod/echte Daten) |
|---|---|---|---|
| **privat** | T0 | minimal | — |
| **Proof of Concept** | T1 | niedrig | — |
| **MVP** | T2 | mittel | intern |
| **Kundenindividuelles Produkt** | T3 | hoch | Kundendaten: kein externer Egress |
| **Tenant-fähiges Produkt** | T4 | sehr hoch | Mandantentrennung, DSGVO |
| **Produkt für Government** | T5 | maximal | ttz-lif-Souveränität: on-prem, kein Egress, Datenklassifikation |
| *(nicht deklariert)* | **→ T5** | maximal | **fail-closed** |

### Achse 2 — Reife-Phase (aktive Strenge)

Reuse des bestehenden Genesor-`pipeline_status` (kein neues Statusmodell): **idea → klickdummy →
pilot → prod → sunset**. Die Phase **deckelt**, wie viel der Ziel-Strenge *jetzt* aktiv ist.

### Aktivierungsschwelle (der Kern)

Die volle Projektart-Rigidität greift **erst ab Prod-Deploy ODER echten/sensiblen Daten**. Davor
ist die Strenge für **alle** Klassen gedeckelt:

| Phase | Aktive Strenge (jede Klasse) |
|---|---|
| **Klickdummy / Prototyp** (kein Prod, keine echten Daten; ADR-211 Prod-Guard) | ≈ T1: großzügige Positivliste (Docs + App-Code + nicht-Deploy-Config), Zweit-Review **nicht** erzwungen |
| **Pilot / Staging** (synthetische/begrenzte Daten) | mittel: inerte Docs + nicht-ausführende Assets; Zweit-Review empfohlen |
| **Prod / echte Daten** | **volle** Projektart-Rigidität + harte Constraints |

### Positivliste — konkret als *inert vs. ausführend* (nicht schwammig)

- **Immer review-frei** (alle Klassen/Phasen): reine Prosa — `*.md`-Text, `CHANGELOG.md`,
  `LICENSE`, `.txt`, Bild-Assets *innerhalb* `docs/`.
- **Nie review-frei** (hart, endungsunabhängig): alles, was CI/Build/Deploy **liest oder ausführt**
  — `.github/**`, `Dockerfile`, `*.yml/*.yaml/*.toml/*.json` mit Build-/CI-Bezug, Migrationen,
  jeglicher Code, Secrets/Deploy-Config.
- **Phasen-/Tier-abhängig dazwischen:** App-Quellcode + nicht-Deploy-Config sind **vor Prod**
  (bzw. in T0/T1) review-frei; ab Prod (T2+) nicht mehr.

### Zweit-Review (Vier-Augen)

Genau **ein** Hebel: **wann ist `wirdigital` (der zweite Mensch) Pflicht?** Es gibt **kein**
Freigabe-Board/Gremium. Skala: nie (T0) → optional (T1) → Prod-Deploys (T2/T3) → Prod **+**
Migration/Config (T4) → immer-in-Prod (T5). In der Klickdummy-Phase: nie erzwungen.

### Kill-Reaktion (immer repo-lokal)

Ein Fail-open (etwas fälschlich review-frei durchgelaufen) ist **immer** ein protokolliertes
Ereignis; die *Reaktion* skaliert im **Blast-Radius**, nie global:

| Tier | Reaktion | Aufhebung |
|---|---|---|
| T0/T1 | Fast-Path *dieses* Repos aus + Log/Notiz | geprüfter PR behebt Ursache + reaktiviert Fast-Path |
| T2/T3 | + Root-Cause-Pflicht | wie oben |
| T4 | + Incident + Policy-Review | + Incident-Close |
| T5 | + Incident + `wirdigital`-Sign-off | + Incident-Close mit Sign-off |

**Kein** automatischer klassen-/plattformweiter Freeze. Kein globaler Schalter — Aufheben ist
immer ein sichtbarer, geprüfter PR pro Repo.

## Verbindliche Hinterlegung (SSoT)

- Das Tier lebt als **`tier`-Feld** in der **bestehenden zentralen Repo-Registry** (KONZ-platform-009,
  registry-unified-ssot) — **keine** neue Parallel-Datei (SSoT-Disziplin).
- **CI erzwingt Vollständigkeit:** jedes Repo muss einen `tier` haben; fehlt er → CI rot **und**
  Behandlung als **T5** (fail-closed).
- **Repo = Projekt = ein Tier.** Ein Repo trägt genau einen Tier.
- **Änderung:** hoch stufen (strenger) jederzeit; **runter** stufen (Kontrollen lockern) nur als
  bewusste, geprüfte Entscheidung (PR + Review).

## Konsequenzen

**Positiv:** eine wiederverwendbare Risiko-Achse (Review heute; CI/Coverage/Deploy morgen); kein
Ausbremsen früher Phasen; fail-closed by default; Souveränität sauber an T3–T5 gekoppelt.
**Negativ:** die Registry muss gepflegt werden (CI erzwingt es); `f(Klasse, Phase)` ist eine
Matrix, kein Skalar — Konsumenten müssen beide Dimensionen lesen.

## Kill-Gate / Review

- **review_by:** 2026-10-09.
- **Kill:** Wenn nach einem Quartal die Tier-Matrix in der Praxis nur „alle = T5" oder „alle = T0"
  ergibt (die Differenzierung wird nicht genutzt), ist die Achse überflüssig → auf eine einfache
  „prod-vs-nonprod"-Binärregel zusammenfalten.

## Konsumenten

- **ADR-267** (Review-Requirement) ist der erste Konsument: Positivliste + `wirdigital`-Pflicht +
  Kill-Reaktion werden aus `f(Projektart, Phase)` dieses ADR bezogen.
- Künftig möglich (nicht Teil dieses ADR): CI-Härte, Coverage-Schwellen, Deploy-Gates,
  Datenhandling entlang derselben Achse.
