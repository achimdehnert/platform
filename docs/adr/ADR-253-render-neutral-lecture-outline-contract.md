---
id: ADR-253
title: "Render-neutraler Lehr-Outline-Vertrag → editierbares .pptx + live-präsentierbares Web-Deck (Renderer per Gate-1-Bake-off)"
status: proposed
date: 2026-06-19
deciders: [Achim Dehnert]
consulted: [Claude Code, externes LLM-Review #1 (Vertrag/Governance/Security), externes LLM-Review #2 (Renderer-Fakten/Reframe, teils verifiziert)]
informed: [iilgmbh, achimdehnert]
domains: [teaching, slides, authoring, architecture, governance]
supersedes: []
amends: []
depends_on: [ADR-140]
related: [ADR-121, ADR-139, ADR-211]
tags: [lecture, outline, ssot, render-neutral, web-deck, slidev, revealjs, pptx, learn-hub, contract, gate, presenter]
scope:
  include_paths:
    - "docs/adr/ADR-253-*"
---

# ADR-253 — Render-neutraler Lehr-Outline-Vertrag → editierbares .pptx + live-präsentierbares Web-Deck

> **Rev 2 (2026-06-19):** Nach zwei externen Zweitmeinungen überarbeitet (Befund-Tagging als
> Nachweis in `~/shared/adr-handoff-ADR-253-2026-06-19.md`). Kernänderungen: (a) **semantisches**
> Risiko wird jetzt zuerst gegated, nicht nur das operative; (b) Renderer-Wahl ist **Gate-1-Bake-off**
> (Slidev vs. Node-freies reveal.js-aus-Python), nicht Vorab-Setzung; (c) **Live-Präsentation
> (Presenter-Modus)** als Erstklasse-Ziel; (d) Web-Deck-Build (kein Chromium) von PDF-Export
> (Chromium) getrennt; (e) Cross-Repo-Schutz (`schema_version` + Contract-Tests) **jetzt**, weil
> Slidev/reveal bereits der **zweite Consumer** ist.

> **Cross-Repo-Hinweis:** Governance-Ebene (`platform`). Render-Logik liegt in **pptx-hub**
> (dortiges ADR-003, repo-lokal — nicht das `platform`-ADR-003) und perspektivisch **learn-hub**
> (ADR-140). `writing-hub` ist hier ausschließlich **Abgrenzung**, kein Consumer.

## 1. Kontext und Problemstellung

### 1.1 Ausgangslage
Es existiert ein bereits render-neutraler Vertrag für Folieninhalte: das Schema
`creation/schema/v1` der App **pptx-hub**. Es beschreibt ein Deck rein strukturell
(`deck_title`, `slides[]` mit `intent ∈ {title, agenda, content, kpi, closing}`, `bullets`,
`notes`, `chart`) — ohne Annahme über das Ausgabeformat. Daran hängt heute **ein** Renderer:
`render_outline_to_pptx()` → editierbares `.pptx` mit Design-Vererbung aus einer vorhandenen
PowerPoint-Vorlage des Mandanten.

**Ziel dieses ADR (präzisiert):** Lehrende sollen denselben Lehrinhalt **auch live im Browser
präsentieren** können (technische Vorlesung, code-/diagrammlastig) — mit **Presenter-Modus**
(Sprechnotizen + Nächste-Folie-Vorschau + Timer), Schritt-für-Schritt-Einblenden, Code-Highlight
und Einbettung ins LMS **learn-hub** (ADR-140). Slidev (sli.dev) war der auslösende Fund;
**reveal.js** ist ein ernsthafter, Node-freier Gegenkandidat.

### 1.2 Problem / Lücken
| Lücke | Konsequenz ohne Entscheidung |
|---|---|
| **Schema v1 ist PowerPoint-geboren & bullet-zentriert** | Genau die Web-Lehr-Features (Code+Zeilen-Highlight+Steps, Diagramme, LaTeX, 2-spaltig Code+Erklärung, Presenter-Notes) haben **keine** Erstklasse-Repräsentation. Ein Gate, das das nicht stresst, besteht **trivial und baut trotzdem das Falsche**. |
| Slidev breit als „Tool für teaching/writing/etc." adoptiert | Tool-Proliferation: ein Folien-Tool wird Prosa (writing-hub) / LMS (learn-hub) aufgezwungen — falsche Artefakt-Einheit |
| Zweiter Renderer ohne abgesicherten Vertrag | Slidev/reveal ist **mit diesem ADR der zweite Consumer**; ohne `schema_version` + Contract-Tests bricht jede Format-Änderung still einen Renderer (Cross-Repo-Koordinationstanz) |
| „Node-Toolchain" und „headless Chromium" verschmolzen | Fehl-Gating: der **Web-Deck-Build braucht kein Chromium**; nur der PDF-Export tut es. Falsche Kostenmodellierung |
| Render-Trigger-Seam undefiniert | **Stale-Deck-Bugklasse**: Dozent ändert Outline, eingebettetes Deck zeigt bis zum manuellen Re-Run alten Stand |

### 1.3 Constraints
- Slidev/Marp/reveal erzeugen **kein editierbares `.pptx`** und konsumieren **keine** vorhandene
  PowerPoint-Vorlage. *(verifiziert: Slidev/Marp-`export` erzeugt ein **bildbasiertes** .pptx,
  eine Folie = ein Bild, nicht selektierbar.)* → ersetzt pptx-hub **nicht**.
- pptx-hub = Python/Django; Slidev = Node/Vue/Vite; reveal.js = client-seitig, aus Python/Jinja2
  **ohne** Node erzeugbar.
- learn-hub (ADR-140) bleibt LMS (Kurse, Enrollment, Tracking) — ein Renderer liefert **Folien**,
  keine Kursverwaltung.
- Org `achimdehnert`, keine Mandanten-/Citizen-Daten, keine Souveränitäts-Auflagen. Slidev/reveal: MIT.

## 2. Entscheidung

1. **Ein render-neutraler Lehr-Outline-Vertrag (LO) als Single Source of Truth.** Erweiterung des
   pptx-hub-Schemas v1. **Vorbedingung (neu):** vor jeder Renderer-Arbeit ein
   **Capability-Check** — der Vertrag muss die ausdrucks-kritische Lehr-Semantik tragen
   (Code+Highlight+Steps, Diagramm, Math, 2-spaltig, **Presenter-Notes**). Trägt er sie nicht,
   wird **zuerst der Vertrag erweitert** (oder der Renderer ist falsch) — nicht in `bullets`/`notes`
   hineingepresst.

2. **Renderer sind Consumer über einen Adapter (Transform-Pipeline), kein symmetrischer Fan-out.**
   Ehrliche Naht: `LO → Adapter → Zielformat → Renderer`.
   - **pptx-hub** → editierbares `.pptx` (bestehend, Design-Vererbung)
   - **Web-Deck-Renderer** → live-präsentierbares Deck (neu) — **welcher**, entscheidet der
     **Gate-1-Bake-off** (Slidev vs. reveal.js-aus-Python, Marp optional), nicht dieses ADR vorab.
   - **learn-hub** → bettet das Web-Deck ein (kein eigener Renderer)

3. **Scope scharf auf technische Lehr-Folien + Live-Web-Präsentation.** Operationalisiert:
   - **Unterstützt:** Titel/Agenda/Content/KPI/Closing, Code-Folie (Highlight+Steps), Diagramm
     (Mermaid o. ä.), Math (LaTeX), 2-spaltig Code+Erklärung, Speaker-Notes/Presenter-Modus.
   - **Nicht unterstützt (bewusst):** Prosa-/Buch-Authoring (→ writing-hub), Kursverwaltung/
     Quizze/Tracking (→ learn-hub als LMS), beliebige interaktive Web-Apps in Folien.

4. **Node-Toolchain auf den Build-Schritt isoliert; Web-Deck und PDF getrennt.**
   - Web-Deck wird **einmal gebaut** (Slidev `build` / reveal aus Python = **kein Chromium**) und
     als **statische Seite** ausgeliefert; **zur Vortragszeit läuft kein Node/Chromium** — der
     Presenter-Modus ist client-seitig in der gebauten Seite enthalten.
   - **PDF/Handout** ist ein **separates, eigenständig gegatetes** Deliverable (nur dafür fällt
     headless Chromium an). Für Live-Präsentation **YAGNI** bis Nachfrage belegt.

5. **Cross-Repo-Schutz JETZT, Package-Extraktion später.** Korrektur des Trigger-Denkfehlers:
   Der Schutz darf **nicht** auf einen „zweiten Producer" warten — der **zweite Consumer ist
   bereits da**. Daher **sofort**: `schema_version`-Feld + **Cross-Repo-Golden-Fixture-Contract-Tests**
   als Kompatibilitätswächter. Die **Extraktion** in ein `iil-*fw`-Package bleibt aufgeschoben,
   bis realer Bedarf besteht (ADR-121-Präzedenz: Story-Outline bewusst getrennt).

6. **Vertrags-Form: leichtgewichtig.** Wahrheit ist das **Python-Domänenmodell** + `schema_version`
   + Golden-Fixture-Contract-Tests. **Kein** eingefrorenes, publiziertes JSON-Wire-Schema mit
   SemVer-Apparat — es gibt **keine externen Consumer**; das wäre Overkill und erzwänge einen
   Kleinster-gemeinsamer-Nenner-Kompromiss über zwei Render-Paradigmen (Placeholder vs. Markdown/
   Komponente). Eine **Renderer-Capability-Matrix** (Feld/Feature × {pptx, web-deck} =
   nativ/approximiert/ignoriert/unsupported) hält den Kern neutral.

## 3. Gates (vor jeder Stack-Investition, Kill-Kriterien explizit)

- **Gate 0 — Do-Nothing-Baseline.** Kosten des *Nicht-Bauens* beziffern (vorhandenes `.pptx`/PDF
  einbetten/abspielen). Der Web-Deck-Nutzen (Live-Presenter, Code-Highlight) muss diese Baseline
  für die **reale Vorlesungs-Frequenz** schlagen. **Kill:** schlägt er sie nicht → nicht bauen.
- **Gate 1 — Renderer-Bake-off (rein Python/Build, kein Vortrags-Runtime).** Slidev vs.
  reveal.js-aus-Python (Marp optional) auf **einer Fixture-Matrix** mit den ausdrucks-kritischen
  Folientypen aus §2.1 + **Presenter-Modus**. Bewertung: (i) trägt der **LO-Vertrag** die Semantik
  verlustfrei? (ii) **Live-Presenter-Erlebnis** (Notes/Vorschau/Timer/Steps/Annotation), (iii)
  Node-Last. **„Verlustfrei" = semantische Vollständigkeit im Ziel**, NICHT Pixel-Layout, KEIN
  Roundtrip Renderer→LO. **Kill:** lässt sich ein Pflicht-Folientyp nicht im LO ausdrücken → Vertrag
  ist PowerPoint-förmig, **erst erweitern**; nimmt reveal.js-aus-Python die Feature-Hürde, **dominiert
  es Slidev auf der ADR-eigenen „Node-minimieren"-Achse** und Gate 2 entfällt weitgehend.
- **Gate 2 — nur PDF/Chromium-Export (falls überhaupt gewollt).** Erst nach belegter PDF-Nachfrage.
  Kriterien inkl. **Supply-Chain**: Lockfile, `npm audit`/CVE-Prozess, Base-Image-Owner,
  Update-Rhythmus, Build-Reproduzierbarkeit, Image-/Buildzeit-Cap, ADR-021-Compose-Konformität.
  **Kill:** Betriebsaufwand trägt den PDF-Nutzen nicht.

## 4. Betrachtete Alternativen

| Option | Bewertung |
|---|---|
| Slidev als **Ersatz** für pptx-hub | ❌ kein editierbares `.pptx`, keine Template-Vererbung |
| Slidev als **Autoren-Plattform** (teaching+writing+etc.) | ❌ Kategorie-Fehler; verdrängt writing-hub/learn-hub semantisch |
| **reveal.js aus Python (Jinja2)** → statisches HTML | ✅ **Gate-1-Hauptkandidat**: null Node, Live-Presenter (Speaker-View), Code via Shiki/highlight, Mermaid/KaTeX-Plugins; erfüllt „Node minimieren" strikt besser; Komfort/Politur etwas mehr Eigenbau |
| **Slidev** → Web-Deck | ✅ **Gate-1-Favorit für Live-Erlebnis**: stärkster Presenter-Modus, Code-Steps, Annotation; Node-Last nur **beim Build**, nicht zur Vortragszeit |
| **Marp** | ➖ leichter, HTML-Export Chromium-frei, aber schwacher Presenter-Modus → für **Live** wohl unterlegen; als billiger Dritter im Bake-off zulässig |
| **Quarto** (Pandoc → reveal/Beamer/PPTX) | ➖ als **reiner** Renderer denkbar, aber eigenes Quell-Format `.qmd` → SSoT-Konflikt wenn als Autoren-Tool; schwergewichtiger als nötig — verworfen als Autoren-Tool |
| Eigenes Zweitformat für den Web-Renderer | ❌ zerstört SSoT |
| LO sofort als geteiltes Package extrahieren | ❌ verfrüht (Extraktion); **aber** Schutz (Version+Tests) ist NICHT verfrüht → §2.5 |
| **Domänenmodell-als-Wahrheit + Per-Target-Adapter + Golden-Contract-Tests** (Gegenmodell zu §2.1) | ✅ **gewählt als Vertrags-Form** (§2.6) — vermeidet eingefrorenes Wire-Schema-Freeze und LCD-Kompromiss |

## 5. Konsequenzen

### Positiv
- Ein Lehrinhalt → editierbares `.pptx` **und** live-präsentierbares Web-Deck ohne Doppelpflege.
- Web-Deck zur **Vortragszeit ohne Node/Chromium** (einmal gebaut, statisch ausgeliefert).
- Renderer-Wahl ist **belegt** (Bake-off), nicht gesetzt; semantisches Risiko **vorab** gegated.
- Cross-Repo-Konsum **abgesichert** (Version + Contract-Tests), bevor er weh tut.

### Trade-offs
- Zwei Render-Paradigmen (pptx-Placeholder vs. Web-Markdown/Komponente) → **Capability-Matrix**
  nötig, damit der Kern render-neutral bleibt (kein Einsickern renderer-spezifischer Hints).
- `kpi/chart`: Chartdaten bleiben **semantisch im LO**; renderer-spezifische Charts sind nur
  Consumer, **nie** zweite Datenquelle.
- Build-Schritt (Node oder Python) muss betrieben werden; **Render-Job-Kontrakt** (Trigger,
  Status, Idempotenz, Retry, Artefakt-Ablage, Cleanup, Metriken, **Staleness-Garantie**) ist zu
  spezifizieren — sonst Stale-Deck-Bugs.
- **Security:** Outlines sind teils LLM-/nutzer-generiert → Regel nötig, welche Markdown-/HTML-/
  Komponenten-Features erlaubt sind (raw-HTML/Script-Verbot, Sanitization) bevor live im Browser
  ausgespielt wird.

### Nicht in Scope
- `writing-hub` (Prosa/Buch). Ersatz/Umbau des LMS `learn-hub`. **Package-Extraktion** des LO.
- **learn-hub-Embed-Detail** (Auth, Tenant-Isolation, iframe/CSP, Asset-URLs, Cache, Lifecycle):
  Naht hier nur **benannt**, Ausspezifikation in einem **learn-hub-Folge-ADR** (Cross-Repo-Scope).

## 6. Validation Criteria
- Gate 0: Do-Nothing-Kosten beziffert; Web-Deck-Nutzen schlägt sie für reale Frequenz.
- Gate 1: LO-Capability-Check bestanden (alle Pflicht-Folientypen + Presenter-Notes verlustfrei);
  Bake-off entscheidet Renderer auf Live-Erlebnis + Node-Last; Fixture-Matrix grün.
- LO trägt `schema_version`; Cross-Repo-Golden-Contract-Tests laufen in CI beider Repos.
- Renderer-Capability-Matrix dokumentiert; Artefakt-Policy (LO = Quelle; .md/web/pdf/pptx =
  wegwerfbare Build-Artefakte) festgehalten.
- Gate 2 nur falls PDF gewollt: Supply-Chain-Kriterien + Determinismus/Fonts/Notes erfüllt.

## 7. Glossar
| Abkürzung | Bedeutung |
|-----------|-----------|
| **ADR** | Architecture Decision Record |
| **LO** | Lecture/Lehr-Outline — der render-neutrale Inhalts-Vertrag dieses ADR |
| **SSoT** | Single Source of Truth — eine maßgebliche Quelle |
| **LMS** | Learning Management System (hier: learn-hub) — Kursverwaltung/Tracking |
| **Presenter-Modus** | Vortragenden-Ansicht: Sprechnotizen + Nächste-Folie-Vorschau + Timer, getrennt von der Publikums-Ansicht |
| **Slidev** | sli.dev — Vue/Node-Framework, Markdown → Web-Präsentation/PDF |
| **reveal.js** | client-seitiges HTML-Präsentations-Framework, aus Python/Jinja2 ohne Node erzeugbar |
| **Marp** | Markdown-Präsentations-Tool (HTML-Export browser-frei) |
| **Bake-off** | direkter Vergleich mehrerer Kandidaten auf identischer Testgrundlage, Entscheidung = Ergebnis |
| **YAGNI** | „You Aren't Gonna Need It" — nicht bauen, bis Bedarf belegt ist |
| **Capability-Matrix** | Tabelle Feature × Renderer: nativ/approximiert/ignoriert/unsupported |
| **Build- vs. Vortragszeit** | einmaliger Erzeugungsschritt vs. Moment des Live-Vortrags (letzterer ohne Toolchain) |

## 8. Referenzen
- pptx-hub **ADR-003** (repo-lokal) — Slide Generation Pipeline / render-neutrales Outline-Schema v1
- platform **ADR-140** — learn-hub (LMS, Embed-Target)
- platform **ADR-139** — iil-learnfw (Shared Learning Platform Package)
- platform **ADR-121** — iil-outlinefw (Story-Outline-Framework — Domänen-Abgrenzung)
- platform **ADR-211** — Klickdummy-/Gate-Muster (Right-Sizing)
- Externe Reviews + Befund-Tagging (Nachweis): `~/shared/adr-handoff-ADR-253-2026-06-19.md`
- sli.dev · revealjs.com · marp.app — Renderer-Dokumentation

## 9. Changelog
- **2026-06-19 (Rev 1)** — Entwurf erstellt (proposed).
- **2026-06-19 (Rev 2)** — Nach zwei externen Zweitmeinungen überarbeitet: semantisches Risiko
  vorab gegated (LO-Capability-Check); Renderer-Wahl als Gate-1-Bake-off (Slidev vs. reveal.js-aus-
  Python); Live-Präsentation/Presenter-Modus als Erstklasse-Ziel; Web-Deck-Build (kein Chromium)
  von PDF-Export (Chromium) getrennt; Cross-Repo-Schutz (`schema_version` + Contract-Tests) sofort
  (zweiter Consumer bereits da); Vertrags-Form leichtgewichtig (Domänenmodell + Golden-Tests);
  Gate 0 Do-Nothing-Baseline; Security-/Render-Job-/Staleness-/Capability-Matrix-Konsequenzen ergänzt.
