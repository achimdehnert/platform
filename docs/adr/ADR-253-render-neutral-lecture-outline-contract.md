---
id: ADR-253
title: "Web-Präsentationen: Slidev als primäres Autoren-Tool (Glanzstücke) + Lehr-Outline-Vertrag als Gerüst-Generator (Bulk) — Zwei-Schienen-Strategie"
status: proposed
date: 2026-06-19
deciders: [Achim Dehnert]
consulted: ["Claude Code", "externes LLM-Review #1 (Vertrag/Governance/Security)", "externes LLM-Review #2 (Renderer-Fakten/Reframe, teils verifiziert)"]
informed: [iilgmbh, achimdehnert]
domains: [teaching, slides, presentations, authoring, architecture, governance]
supersedes: []
amends: []
depends_on: [ADR-140]
related: [ADR-121, ADR-139, ADR-211, ADR-254]
tags: [presentations, slidev, lecture, outline, scaffold, two-track, webinar, learn-hub, contract, presenter, ownership-transfer]
scope:
  include_paths:
    - "docs/adr/ADR-253-*"
---

# ADR-253 — Web-Präsentationen: Slidev-Autoren-Tool + Lehr-Outline-Gerüst (Zwei Schienen)

> **Rev 3 (2026-06-19) — Reframe nach Ziel-Klärung.** Ziel ist **perfekte Web-Präsentationen**
> für Vorträge, Lehr-Module und Webinare — nicht nur automatische Massen-Decks. Erkenntnis: ein
> generiertes Deck aus einem Inhalts-Vertrag erreicht nur den **kleinsten gemeinsamen Nenner**
> (~20–30 % von Slidevs Spektrum); „perfekt" entsteht aus dem **Autoren-Handwerk** (Vue-Komponenten,
> Animationen, Live-Code, Transitions), das ein Datenmodell nicht trägt. Daher **zwei Schienen**:
> Slidev wird **primäres Web-Autoren-Tool** (Glanzstücke), der LO-Vertrag ein **optionaler
> Gerüst-Generator** (Bulk), dessen Ausgabe **in Slidev veredelt** wird.
>
> Vorgeschichte: Rev 1 Entwurf · Rev 2 nach zwei externen Reviews (Gate-Logik, Bake-off,
> Presenter-Modus). Befund-Tagging: `~/shared/adr-handoff-ADR-253-2026-06-19.md`.
> Gate-1-Capability-Check ausgeführt 2026-06-19 → **Kill-Kriterium ausgelöst** (s. §6).

> **Cross-Repo:** Governance (`platform`). Renderer/Vertrag in **pptx-hub** (dortiges ADR-003).
> Embed in **learn-hub** (ADR-140 / Naht: **ADR-254**). `writing-hub` = Abgrenzung, kein Consumer.

## 1. Kontext und Problemstellung

### 1.1 Ausgangslage & Ziel
Bestehend: pptx-hubs render-neutrales Outline-Schema v1 → ein Renderer (`render_outline_to_pptx`)
→ editierbares `.pptx` mit Mandanten-Template-Vererbung.

**Ziel (geklärt):** Es sollen **perfekte Web-Präsentationen** für **Vorträge, Lehr-Module und
Webinare** erstellbar sein — live im Browser präsentierbar (Presenter-Modus), code-/diagrammlastig,
in learn-hub einbettbar. **Slidev** bietet genau dieses Spektrum.

### 1.2 Die zentrale Erkenntnis (warum nicht „nur Vertrag")
„Ein Inhalt → viele Formate" (Vertrag → pptx + Web) optimiert **Masse/Konsistenz**, **deckelt** die
Web-Präsentation aber auf das, was ein JSON-Vertrag beschreiben kann:

| Slidev-Fähigkeit | aus Vertrag generierbar? |
|---|---|
| Struktur, Bullets, Code, Diagramm, Math, Speaker-Notes | ✅ ~20–30 % (Vertragsteil) |
| Custom Vue-Komponenten, Layouts, Themes | ⚠️ nur uniform |
| `v-click`/Motion/Transitions, Live-Code (Monaco/Twoslash), Zeichnen, Kamera, interaktive Embeds | ❌ ~70 % — **Autoren-Handwerk, kein Datenmodell** |

→ Generiert wird **„gut & konsistent"**, nie **„perfekt & maßgeschneidert"**. Das sind **zwei
verschiedene Produkte**, die unterschiedliche Werkzeuge brauchen.

### 1.3 Constraints
- Slidev erzeugt **kein editierbares `.pptx`** und konsumiert **keine** PowerPoint-Vorlage
  *(`export` liefert bildbasiertes .pptx)* → ersetzt pptx-hub **nicht**.
- Slidev = Node/Vue; lebt als **Autoren-/Build-Werkzeug** (Dev-Tooling + CI-Build), **nicht** als
  Django-Runtime-Abhängigkeit. Vortragszeit: statische Seite, kein Node/Chromium.
- learn-hub (ADR-140) bleibt LMS; ein Deck wird **eingebettet** (ADR-254-Naht), nicht im LMS gerendert.
- Org `achimdehnert`, keine Mandanten-/Souveränitätsauflagen. Slidev MIT.

## 2. Entscheidung — Zwei Schienen

### Schiene 1 — Slidev als primäres Web-Autoren-Tool (Glanzstücke)
1. **Slidev wird adoptiert** als das Werkzeug für perfekte Vorträge/Webinare/Vorzeige-Module —
   **volles Spektrum**, direkt in Slidev (Markdown + Vue) autorenseitig gepflegt.
2. **Minimale Plattform-Investition:** ein geteiltes **iil/meiki/ttz-Theme**, eine **Repo-/Ordner-
   Konvention** für Decks, ein **statisches Build+Deploy-Ziel** (in learn-hub einbettbar via ADR-254).
   *(Placement-Frage — eigenes `decks`-Repo vs. Ordner — ist Folge-Entscheidung, s. §5.3.)*
3. Für Schiene-1-Decks ist die **Slidev-Datei die Single Source of Truth**. Keine pptx-Ableitung
   erzwungen (optional via `export` als bildbasiertes Handout).

### Schiene 2 — Lehr-Outline-Vertrag als Gerüst-Generator (Bulk)
4. Der **LO-Vertrag** (Erweiterung pptx-hub-Schema, **Schema v2** nötig — s. §6) generiert aus
   strukturiertem Inhalt ein **Slidev-Markdown-Gerüst** (Struktur, Inhalt, Code/Diagramm/Math,
   Speaker-Notes). Dasselbe LO speist weiter **pptx-hub → editierbares .pptx**.
5. Das Gerüst ist ein **Startpunkt, kein Endartefakt** — ein Mensch **veredelt** es in Slidev
   (Schiene 1). Damit konvergieren beide Schienen im selben Werkzeug.

### Querschnitt — Ownership & SSoT (der ehrliche Kern)
6. **Ownership-Transfer-Point:** Ein LO-generiertes Deck gehört dem LO **nur bis zur ersten
   Veredelung**. Ab dem ersten menschlichen Slidev-Edit ist die **Slidev-Datei die Wahrheit**;
   das LO wird **historischer Seed**. **Re-Generieren aus dem LO verwirft die Politur.**
   - Konsequenz: **Kein Roundtrip** Slidev→LO. „Detached"-Decks werden **explizit markiert**;
     Re-Generierung nur für **nie veredelte** Gerüste.
7. **Renderer-Wahl ist entschieden:** Slidev (nicht der frühere Bake-off). Begründung: das
   Spektrum *ist* der Zweck. **reveal.js-aus-Python** wird **dokumentierte Fallback-Option** —
   nur falls je ein **rein-generierter, nie-veredelter, Node-freier** Bulk-Bedarf entsteht
   (dann ist Slidevs Autoren-Spektrum irrelevant und Null-Node sticht).
8. **Cross-Repo-Schutz für den LO (Schiene 2) sofort:** `schema_version` + Golden-Fixture-
   Contract-Tests (LO ist mit Schiene 2 ein zweiter Consumer). Vertrags-Form **leichtgewichtig**
   (Python-Domänenmodell + Tests, kein eingefrorenes Wire-Schema; keine externen Consumer).
   Package-**Extraktion** aufgeschoben.

## 3. Was das ändert vs. Rev 2
- „Slidev = nur Renderer, keine Autoren-Plattform" ist **aufgehoben** → Slidev = primäres Autoren-Tool.
- Der **Bake-off** (Gate 1) entfällt als Renderer-Entscheidung; Slidev ist gesetzt, reveal.js = Fallback.
- **Schema v2** ist nur noch für **Schiene 2 (Gerüst)** kritisch, **nicht** für Glanzstücke → repriorisiert.
- Neuer Kern: **Zwei-Schienen + Ownership-Transfer**.

## 4. Gates (Right-Sizing)
- **Schiene 1 ist kaum gegatet** — es ist Tool-Adoption: Slidev + Theme + Deploy. Risiko niedrig,
  reversibel (Decks sind statische Artefakte). Erstes Glanzstück-Deck = der Proof.
- **Gate 0 (Schiene 2) — Do-Nothing-Baseline:** lohnt der Gerüst-Generator vs. „Deck direkt in
  Slidev von Hand"? Nur bauen, wenn Bulk-Volumen die Generator-Pflege trägt.
- **Gate 1 (Schiene 2) — LO-Capability:** ✅ **ausgeführt** (§6) → Schema v2 erforderlich, bevor
  der Gerüst-Generator gebaut wird.
- **Gate 2 — PDF/Chromium (optional):** nur falls PDF-Handout gewünscht; Supply-Chain-Kriterien
  (Lockfile, CVE, Base-Image-Owner, Reproduzierbarkeit, Image/Build-Cap, ADR-021).

## 5. Konsequenzen

### 5.1 Positiv
- Perfekte Web-Präsentationen **sofort** möglich (Schiene 1, minimale Plattform-Arbeit).
- Bulk/Konsistenz bleibt erreichbar (Schiene 2) — und mündet im selben Tool (veredelbar).
- Node nur als **Autoren-/Build-Tool**, nicht als Server-Runtime; Vortragszeit statisch.

### 5.2 Risiken / Trade-offs
- **Detach-Risiko (Haupt-Trade-off):** nach Veredelung kein Re-Generieren aus LO → zwei Quellen,
  wenn „detached" nicht sauber markiert wird. Mitigation: explizites Detach-Flag + Konvention.
- Schema v2 = echte Schema-Arbeit (Schiene 2) mit Renderer-Folgewirkung.
- **Security:** LLM-/nutzergenerierte Gerüst-Inhalte → Sanitization-Regel (kein raw-`<script>`),
  greift bei Einbettung (ADR-254 CSP).
- Theme-/Deck-Pflege (Schiene 1) ist Autoren-Aufwand, kein Generator-Aufwand.

### 5.3 Nicht in Scope / Folge-Entscheidungen
- **Placement Schiene 1** (eigenes `decks`-Repo vs. Ordner in dev-hub/learn-hub) → Folge-Entscheidung
  (Policy „wo soll das leben" konsultieren).
- learn-hub-Embed-Detail → **ADR-254**.
- `writing-hub` (Prosa); Ersatz/Umbau des LMS; Package-Extraktion des LO.

## 6. Gate-1-Capability-Check — Evidenz (ausgeführt 2026-06-19)
Probe gegen den realen `validate_outline` (pptx-hub, `extra="forbid"`). Positiv-Kontrolle
(title/bullets/notes, kpi+chart) validiert; **0/5** Web-Lehr-Folientypen ausdrückbar:

| Typ | v1 | Grund |
|---|---|---|
| Code (Highlight+Steps) | ❌ | `code` extra_forbidden |
| `intent:"code"` | ❌ | intent literal_error |
| Diagramm (Mermaid) | ❌ | `diagram` extra_forbidden |
| Math (LaTeX) | ❌ | `math` extra_forbidden |
| 2-spaltig Code+Erklärung | ❌ | `columns` extra_forbidden |
| Step-Reveal | ❌ | `reveal` extra_forbidden |
| Presenter-Notes | ✅ | `notes` vorhanden |

→ Vertrag ist PowerPoint-förmig; **Schema v2** (additive optionale Blöcke `code/diagram/math/
columns/reveal`, `$schema_version:"2"`, v1 bleibt gültig) ist Voraussetzung für **Schiene 2**.

## 7. Betrachtete Alternativen
| Option | Bewertung |
|---|---|
| A: Nur Vertrag-first (generiert, Slidev=dumb) | ❌ deckelt Web-Decks auf LCD — verfehlt „perfekt" |
| B: Nur Slidev-Authoring | ✅ perfekte Decks, aber keine Bulk-/pptx-Wiederverwendung |
| **C (gewählt): Beides — Slidev-Authoring + LO-Gerüst** | ✅ Glanzstücke sofort + Bulk-Pfad; Preis = Detach-Risiko (§5.2) |
| Slidev als pptx-Ersatz | ❌ kein editierbares .pptx |
| reveal.js-aus-Python als Primär-Tool | ❌ verfehlt das Slidev-Spektrum; nur Fallback (§2.7) |
| Quarto/Marp als Autoren-Tool | ❌ eigenes Quellformat / schwächerer Presenter → SSoT-Konflikt |

## 8. Validation Criteria
- Schiene 1: erstes Glanzstück-Deck live präsentiert + in learn-hub eingebettet (ADR-254).
- Schiene 2: Schema v2 trägt alle 5 Folientypen verlustfrei; LO→Slidev-Gerüst erzeugt; `schema_version`
  + Cross-Repo-Contract-Tests grün; Detach-Flag-Konvention dokumentiert.
- Artefakt-Policy: pro Deck eindeutig, ob LO-Seed (regenerierbar) oder detached (Slidev = Wahrheit).

## 9. Glossar
| Begriff | Bedeutung |
|---|---|
| **LO** | Lecture/Lehr-Outline — strukturierter Inhalts-Vertrag (Gerüst-Quelle, Schiene 2) |
| **Schiene 1 / 2** | Glanzstück-Authoring in Slidev / Bulk-Gerüst-Generierung aus dem LO |
| **Gerüst (Scaffold)** | generierter Startpunkt eines Decks, der in Slidev veredelt wird |
| **Ownership-Transfer-Point** | Moment der ersten Veredelung — ab da ist die Slidev-Datei die Wahrheit |
| **Detached** | Deck, das nach Veredelung nicht mehr aus dem LO regenerierbar ist |
| **Presenter-Modus** | Vortragenden-Ansicht (Notizen + Vorschau + Timer) getrennt vom Publikum |
| **SSoT** | Single Source of Truth |
| **Slidev / reveal.js** | sli.dev (Vue/Node, volles Spektrum) / client-seitiges HTML-Framework (Fallback) |

## 10. Referenzen
- pptx-hub **ADR-003** (repo-lokal) — Outline-Schema v1 / Slide-Pipeline
- platform **ADR-254** — learn-hub Web-Deck-Embed-Naht (gilt für beide Schienen)
- platform **ADR-140** — learn-hub · **ADR-139** — iil-learnfw · **ADR-121** — iil-outlinefw (Abgrenzung)
- platform **ADR-211** — Gate-/Right-Sizing-Muster
- Externe Reviews + Tagging: `~/shared/adr-handoff-ADR-253-2026-06-19.md`
- sli.dev · revealjs.com

## 11. Changelog
- **2026-06-19 (Rev 1)** — Entwurf (proposed).
- **2026-06-19 (Rev 2)** — Nach zwei externen Reviews: semantisches Risiko vorab gegated; Bake-off;
  Presenter-Modus; build≠export; Cross-Repo-Schutz sofort; leichtgewichtige Vertrags-Form.
- **2026-06-19 (Rev 3)** — Ziel-Reframe „perfekte Web-Präsentationen": **Zwei-Schienen-Strategie**
  (Slidev primäres Autoren-Tool + LO als Gerüst-Generator), Slidev adoptiert (Bake-off→Fallback),
  **Ownership-Transfer-Point** + Detach-Risiko verankert, Schema v2 auf Schiene 2 repriorisiert,
  Gate-1-Capability-Check-Evidenz (0/5) eingearbeitet.
