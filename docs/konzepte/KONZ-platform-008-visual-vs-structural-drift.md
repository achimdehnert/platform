---
concept_id: KONZ-platform-008
title: Visual- vs. Structural-Drift-Detection für Klickdummy-basiertes Screen-Testing
pipeline_status: idea
tier: T3
owner: achim.dehnert
spec_refs: [risk-hub:klickdummy-spec-sds-verwalten]   # empirischer Anker (Rev 21); decks-hub/pptx-hub haben noch keine Spec
adr_threshold: Amendment an ADR-211 (opt-in Visual-Report-Capability, Muster Rev 12/16/18) — eigener ADR nur falls jemals Gate-Pflicht
review_by: 2026-09-20        # created + 90 d
kill_criteria: "risk-hub-Pilot: wenn `text`-Asserts + die 6 Prosa→Executable-Checks die Template-/Feld-Genauigkeit NICHT ausdrücken können (DSL-Lücke ohne tragfähige F17-Erweiterung) → Strang stoppen. (Visual-Schiene bereits verworfen: Decider 2026-06-22 — Pixelgetreue nicht nötig.)"
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: platform/docs/adr/ADR-211-klickdummy-benutzeranforderungen-entwicklungsprozess.md, commit_or_pr: "grep visual|pixel|screenshot|baseline = 0 Treffer", opened_in_session: true}
  - {claim_id: C2, source_path: platform/docs/adr/ADR-211-...md (Rev 21, Zeile 954), commit_or_pr: "iil-klickdummy #67", opened_in_session: true}
  - {claim_id: C3, source_path: platform/docs/adr/ADR-211-...md (Zeilen 74/482/989/994/1000), commit_or_pr: "#255 dormant", opened_in_session: true}
  - {claim_id: C4, source_path: pptx-hub/project-facts.md, commit_or_pr: "2026-06-15", opened_in_session: true}
  - {claim_id: C5, source_path: platform/docs/adr/ADR-211-...md (Zeile 755), commit_or_pr: "Rev 16", opened_in_session: true}
created: 2026-06-22
---

# KONZ-platform-008 — Visual- vs. Structural-Drift-Detection

## 0 Decider-Steuerung 2026-06-22 (überschreibt Empfehlung)

Der Decider hat den Rahmen geschärft: **„Pixelgetreue nicht notwendig — wichtig ist Template- und
Feld-Genauigkeit"** + **risk-hub ist der Pilot** (wird ohnehin gerade getestet). Das ist eine
**strukturelle** Anforderung → die Visual-Schiene (Optionen B/C) entfällt für das eigentliche Ziel.

**Folge:** Der Strang **deflationiert von T3 auf eine ADR-211-Adoptions-Aufgabe** (kein neuer
ADR/keine neue Dependency/keine Render-Boundary) — Fortsetzung des Executable-Parity-Rollouts
(F19) mit risk-hub als 2. bewiesenem Konsumenten. Verifizierte Ausgangslage (Session-Reads):
- Assert-DSL kann genau 5 Verben (`gen_e2e.py:105–114`): visible/text/clickable/url/count. **`text`
  = Feldwert-Genauigkeit.**
- risk-hubs 3 Live-Asserts nutzen nur visible/count/clickable — **`text` (Feldwert) noch nicht
  genutzt**; 6/9 `parity_acceptance` sind Prosa ohne `assert` (F19-Skip-Debt).

**Neue Arbeitslinie (statt Option C):** (1) `text`-Asserts für Feldwerte ergänzen; (2) die 6
Prosa-Checks ausführbar machen; (3) offene F17-Frage am Pilot klären — reichen 5 Verben für
„Feld-/Template-Genauigkeit" oder braucht es Schärfe (exakt-vs-enthält, Containment „Feld in
richtiger Sektion/Platzhalter")? PPTX-Template-Genauigkeit (pptx-hub) ist ein *separater*
struktureller Pfad (python-pptx Layout/Platzhalter), nicht dieser HTML-Generator.

**Visual-Schiene: geparkt** — nur falls je decks-hubs *ästhetische* Oberfläche selbst zum Thema
wird (eigene Entscheidung, nicht dieses Ziel). Abschnitte 4–11 unten bleiben als Beleg, warum
Visual für das Template-/Feld-Ziel das falsche Werkzeug ist.

### 0.1 Konvention: Assert-Schichtung für „Template-/Feld-Genauigkeit"

Verifizierte DSL-Semantik (`iil-klickdummy/gen_e2e.py:105–119`): `visible` → `to_be_visible()`;
`text` → `to_contain_text(exp)` (**Substring**, kein Exact-Match); `count` → `to_have_count(n)`
(exakt, datengetrieben).

**Regel — zwei Schichten, nicht entweder-oder:**

| Schicht | Verb | Zweck | Datenabhängig? | Wann |
|---|---|---|---|---|
| **1 — Präsenz-genau** | `visible` (je Soll-Feld) | „richtiges Template rendert richtige Felder" | **nein** — kein Seed, robust gg. Testdaten | **immer zuerst, flächig** — fängt Template-/Fehlfeld-Drift sofort |
| **2 — Wert-genau** | `text` / `count` | „richtiger Wert im richtigen Feld" | **ja** — braucht deterministischen Seed (`seed_<app>`) | **gezielt** auf High-Stakes-Felder (Zone, CAS, rechtlich relevant) |

**AI-Freitext-Regel:** Bei LLM-generierten Feldern (z. B. Ex-Schutzdokument `ex_doc_prefill` /
`ai/prompts`) ist Voll-Wert-Pinning spröde (Output nicht-deterministisch). Dort **nur** `visible`
(Präsenz) **oder** ein gepinnter deterministischer Anker via `to_contain_text` (z. B. „Zone 21",
CAS-Nummer) — **kein** Assert auf den ganzen generierten Text. Exakt-Wert-Asserts (`text`/`count`)
bleiben den **deterministischen** Mappings vorbehalten (Formular-Eingabe→Anzeige, regelbasierte
Berechnung, strukturiertes Prefill).

**Begründung:** robustes Netz sofort (Schicht 1, demo-tauglich, kein Seed-Aufwand), Seed-/
Wartungskosten nur dort investiert, wo Feld-Genauigkeit real schadensrelevant ist (Schicht 2).
Offen bleibt F17 (Granularität exakt-vs-enthält-vs-Containment „Feld in richtiger Sektion") — am
risk-hub-Pilot zu entscheiden, ob die 3 Verben reichen oder ein Containment-Verb nötig wird.

### 0.2 F17-Befund am Pilot (risk-hub `/sds/review/`, 2026-06-23 — beantwortet)

Pilot-Increment ausgeführt (risk-hub PR #270): zwei Schicht-2-`text`-Asserts am bereits
parity-grünen Manual-Review-Screen, plus eine spalten-gescopte Zelle
`data-testid="sds-review-cell-manufacturer"`. Render-Layer-Test grün (Testid + Feldwert in
derselben Zelle), `gen-e2e` drift-clean.

**Befund: kein neuer Containment-Verb nötig.** „Wert in der richtigen Spalte" wird durch
**Cell-Level-`data-testid`** + bestehendes `to_contain_text` (Substring) gelöst — die Granularität
sitzt im **Selektor-Kontrakt** (Zelle statt Zeile/Container), nicht in der DSL. Die 5 Verben
reichen.

**Echte Restgrenze (verschoben, nicht DSL):** *zeilenspezifische* Wert-Pinnung. Der Generator
emittiert `text` nur als `.first` — bei `-created_at`-Sortierung ist ein `.first`-Cell-Assert auf
einen zeilen-variablen Wert ordnungs-fragil. Auflösung **ohne** DSL-Erweiterung:
1. **spalten-konstante Werte** value-exact pinnen (z. B. Hersteller „ProofCo" in allen Seed-Zeilen) —
   `.first` ist dann ordnungs-unabhängig;
2. **zeilen-variable Werte** queue-weit als Präsenz prüfen (Produkt „Aceton" irgendwo in der Queue);
3. exakte Zeile×Spalte erst, wenn ein Screen es real braucht → dann **dokumentierter
   Ordnungs-Kontrakt in der Spec** (nicht ein neuer Verb). Bis dahin offen lassen (YAGNI).

**Konsequenz für F17:** als *für den Pilot gelöst* markieren; Containment-Verb-Idee verworfen.
Nächster Schritt der Adoptions-Linie bleibt §0 Punkt (2): die **6 Prosa-`parity_acceptance`**
(Screens 1–5) ausführbar machen — das braucht zuerst echte App-Routen + Cell-Testid-Kontrakte +
Seeds je Screen (größerer Lift als dieser Increment), kein DSL-Problem.

### 0.3 §0-Punkt-(2)-Befund: nicht jede `parity_acceptance` ist render-parity-ausdrückbar (2026-06-23)

Increment-2 ausgeführt (risk-hub PR #272 — gemergt; #271 war der gestapelte Vorläufer, von GitHub
auto-geschlossen, als #270 + dessen Base-Branch gemergt wurden): die 6 Prosa-Checks der Screens 1–5
angegangen. Ergebnis ist **8 ausführbar / 3 kategorisiert**, **nicht** „6/6 grün" — und das ist der
*richtige* Endzustand. Drei Checks gehören in **andere Test-Schichten** als die Playwright-Parität:

| Klasse | Check | Warum nicht Render-Parität | Echte Heimat |
|---|---|---|---|
| **parametrisierte Route** | detail.bestand (`/sds/revision/<int:pk>/`) | pk nicht-deterministisch → Generator-Skip `parametrised_route`; `page.goto` würde 404 raten | seed-fixiertes `route_example` (Schicht-2-Folge) |
| **HTMX-Interaktion** | update.bestand (diff/adopt/defer in `#diff-container`) | kein Page-Load, braucht Klick-Interaktion | Service-Unit-Tests |
| **Backend-Cron** | frist.job (`sds_check_deadlines`) | gar kein Render | Management-Command-Test |

Die 3 ausführbaren (bibliothek/upload/frist.dashboard) sind **Schicht-1-Präsenz-Asserts** auf
immer-rendernde Anker (KPI-Kacheln, Upload-Formular, Revisions-Zähler) → seed-unabhängig, robust.

**Lehre (deckt sich mit dem Anti-Theater-Kern des Konzepts):** „alle Prosa-Checks ausführbar machen"
ist das **falsche** Ziel — richtig ist, jeden Check der **billigsten ausdrucksstarken Schicht**
zuzuordnen und den Rest als **kategorisierten** (nicht stillen) Skip zu dokumentieren. Der Generator
unterstützt das bereits (`parametrised_route` / `login_required_no_auth` / `no_assert`); die Spec
sollte den Blocker im `check`-Text benennen, damit Skip-Debt sichtbar und begründet bleibt.

## 1 Executive Summary (historisch — vor Decider-Steuerung §0)

**Entscheidung stand an:** Reicht die bestehende **strukturelle** Klickdummy-Parität
(ADR-211, `data-testid` · visible/text/clickable/url/count) als „Drift ausschließen", oder
braucht es zusätzlich eine **visuelle** Regression-Schiene (Pixel/Layout, Playwright
`toHaveScreenshot`)?

**Ursprüngliche Empfehlung (durch §0 überholt): Option C — gezielter Hybrid.** Nicht structural-only,
nicht breiter Visual-als-Gate. Sondern:
- **Strukturell bleibt das Gate überall** — ADR-211 unverändert.
- **Visual NUR für HTML-Render-Oberflächen** (decks-hub Slidev zuerst), **NUR als
  nicht-blockierender Report** (Diff-Galerie im PR), **NUR im container-gepinnten Render-Env**.
- **PPTX bekommt strukturelle OOXML-/Shape-Geometrie-Assertions** (python-pptx-Objektebene),
  **kein Pixel** — weil LibreOffice→PNG die falsche Render-Engine misst (Kunde nutzt PowerPoint).

## 2 Scope & Evidenzbasis

Cross-Repo-Plattform-Testing-Strategie → **T3** (nicht verhandelbar: Cross-Repo + potenzielle
neue Dependency = Baseline-Storage + gepinntes Render-Image + neue CI-Boundary).

Geöffnete Quellen (E1/E2, in Session): ADR-211 (89 KB, gegrept + relevante Revs gelesen),
`pptx-hub/project-facts.md`, risk-hub-Klickdummy-Instanz-Listing, iil-klickdummy-Generator-/
Schema-Listing. Adversariat: 3 unabhängige Agenten (Steelman / Advocatus Diabolus /
Maintainer-2028), blind zueinander.

## 3 Infrastruktur-Fit (verifiziert)

- **C1** — ADR-211 enthält **null** Pixel-/Screenshot-/Visual-Automatisierung (`grep` = 0). Es ist
  bewusst zu 100 % strukturell. (E1/E2)
- **C5** — Zeile 755: „Ein KD validiert per Definition nur Layout/Flow" — aber als **menschlicher
  Review am Mockup**, nicht automatisch. Die optische Bewertung ist im Prozess schon vorgesehen,
  nur eben manuell. (E1)
- **C2** — Strukturelle Parität ist real bewiesen: risk-hub `/sds/review/` 3/3 grün gegen live
  Django-App, rot bei Selektor-Divergenz (Rev 21). (E1)
- **C3** — Offene Schwächen, die Visual verschärfen würde: F17 (assert-DSL-Lifecycle), F18
  (Selector-Fragilität, Locator-Registry bewusst zurückgestellt wg. Doppelquell-Risiko), F19
  (Skip-Debt cross-repo), F11 (Prod-Guard dormant). Cross-Repo-Adoption der *strukturellen*
  Schiene war monatelang „0 reale Renderer #2". (E1)
- **C4** — pptx-hub: Django 5.2, erzeugt `.pptx`, prezimo.com. Das Liefergut ist eine **binäre
  OOXML-Datei**, kein DOM. (E2)

**Kern-Asymmetrie (alle drei Agenten einig):** ADR-211 deckt **interaktive UI** (Formulare,
Queues, Navigation) gut ab und **render-zentrierte Deliverables** (Slidev-Decks, PPTX-Slides)
**konzeptionell gar nicht** — dort gibt es keine semantischen Selektoren, das Layout *ist* das
Produkt.

## 4 Steelman (stärkster Fall FÜR Visual)

Strukturelle Asserts sind blind für alles *zwischen* den Selektoren: CSS-Token-Bruch aus
design-hub (Button `visible`+`clickable`, aber weiß auf weiß), z-index-Überlappung (DOM grün,
Klick trifft falsch), abgeschnittener Text (`toHaveText` matcht vollen DOM-String, User sieht
„Antrag genehmi…"), Flex-`order`-Vertauschung (DOM-Reihenfolge bleibt). Bei **render-zentrierten
Deliverables** ist Visual die *einzige* automatisierbare Schiene — `data-testid` auf Slidev-Folien
zu erzwingen wäre Test-Theater. Flakiness ist mit container-gepinntem Rendering + `maxDiffPixelRatio`
+ Masking + Baseline-Governance-PR beherrschbar (Standard, keine Forschung).

## 5 Konzeptdefinition (Option C, präzise)

| Oberfläche | Beispiel | Schiene | Modus |
|---|---|---|---|
| Interaktive UI | risk-hub `/sds/review/`, writing-hub | **strukturell** (ADR-211) | **Gate** (unverändert) |
| HTML-Render-Deliverable | decks-hub Slidev | **+ visuell** (`toHaveScreenshot`, gepinnt, maskiert) | **nicht-blockierender Report** |
| Binär-Render-Deliverable | pptx-hub `.pptx` | **strukturell auf OOXML/Shape-Geometrie** (python-pptx) | **Gate** — kein Pixel |

Begründung der Asymmetrie: HTML rendert Playwright deterministisch (Einzeiler, eigene Engine =
Auslieferungs-Engine). PPTX rendert nur via LibreOffice→PNG — eine Engine, die der Kunde **nie
sieht** (PowerPoint). Strukturelle XML-Assertions prüfen das *tatsächliche* Artefakt.

## 6 Adversariale Analyse — Konfliktmatrix (Pflicht T3)

| # | Streitpunkt | Steelman | Advocatus Diabolus | Maintainer-2028 | Auflösung |
|---|---|---|---|---|---|
| K1 | Fängt Visual Bugs, die strukturell nicht fängt? | Ja, viele Szenarien | Marginal — A11y-Tree/DOM-Snapshot deckt 80 % | Ja, aber empirisch **~2 netto** in 2 J. | **Existenz ja, Magnitude klein** → rechtfertigt schmalen Scope, kein breites Gate |
| K2 | Gate oder Report? | (impliziert Gate per Baseline-PR) | Gate → Bulk-Accept → Theater | **Report, nie Required-Check** | **Report gewinnt** — neutralisiert Theater-Kritik, hält die 2 echten Treffer |
| K3 | PPTX visuell? | Phase 2 via LibreOffice | Falsche Engine (≠PowerPoint) | 2× grün-aber-Kunde-Ticket → zurückgebaut | **Diabolus/Maintainer gewinnen** → PPTX strukturell |
| K4 | Flakiness lösbar? | Ja, Container-Pinning | Threshold-Hochdrehen = blind | Pinning senkt Frequenz, heilt Bulk-Accept **nicht** | Pinning **notwendig, nicht hinreichend** → darum Report statt Gate |
| K5 | Doppelquelle? | (nicht adressiert) | Baseline-PNG vs. Spec, niemand schlichtet deterministisch | Baseline-Rot = Default-Endzustand | Real → Report-Modus entschärft (PNG gatet nichts, Spec bleibt SSoT) |

**Einziger nicht-aufgelöster Dissens:** K1-Magnitude — lohnen sich ~2 echte Treffer/2 J.? Das ist
die Rest-Wette, die der Pilot beantwortet (Kill-Gate).

## 7 Deep-Dive: warum PPTX die Schiene wechselt

Ein `.pptx` ist binäres OOXML. „Visual-Regression" erzwingt Slide→PNG via LibreOffice headless.
LibreOffice substituiert Fonts (Calibri→Carlito), bricht Zeilen und SmartArt anders als
PowerPoint. Ergebnis (Maintainer, plausibles Muster): grüner Pixel-Diff bei kaputter
PowerPoint-Folie. Die strukturelle Alternative — Assertions auf Platzhalter-Typ, Text, Shape-Count,
Geometrie (python-pptx, exakt ADR-211-Geist) — prüft das *ausgelieferte* Artefakt deterministisch.
Echte PPTX-Visual-Parität bräuchte einen **Windows/PowerPoint-Renderer in CI** — unverhältnismäßig.

## 8 Alternativen

- **A — structural-only:** verworfen. Konzediert die render-Deliverable-Lücke (K1-Existenz von
  keinem bestritten); decks-hub-z-index-Bruch bliebe unsichtbar.
- **B — Visual breit als Gate:** verworfen. Diabolus+Maintainer: Bulk-Accept-Reflex, Baseline-Rot,
  Repo-Bloat/LFS, verschärft F18/F19, Render-Boundary in jedem Repo.
- **C — gezielter Hybrid (Report-only, HTML-Surface, PPTX-strukturell):** empfohlen.

## 9 Out-of-the-Box

Billigere 80-%-Schienen, die einen Teil des Visual-Werts *ohne* Pixel liefern und Option C
ergänzen (nicht ersetzen): **Accessibility-Tree-Snapshot** (OS-/Font-invariant, text-diffbar, fängt
Struktur-/Reihenfolge-Drift), **computed-style-Assertion** auf Schlüssel-Tokens (fängt
design-hub-Theme-Bruch ohne Pixel), und der **bereits vorgesehene manuelle Klickdummy-Review**
(Zeile 755) gezielt als Ästhetik-Gate statt 200 PNGs blind durchwinken.

## 10 Befunde

| ID | Befund | Evidenz |
|---|---|---|
| B1 | ADR-211 ist bewusst 100 % strukturell, Visual fehlt vollständig | E1/E2 (C1) |
| B2 | Render-Deliverables (Slidev/PPTX) sind strukturell nicht abdeckbar — reale Lücke | E1 + Agenten-Konsens |
| B3 | PPTX-Pixel misst LibreOffice ≠ Kunde-PowerPoint → falsches Surrogat | Diabolus+Maintainer (D/H) |
| B4 | Visual-als-Gate erzeugt Bulk-Accept-Theater + Baseline-Rot | Diabolus+Maintainer (H, empirisches Muster) |
| B5 | Plattform-Adoption der *strukturellen* Schiene ist bereits zäh (Rev 20: „0 Renderer #2") | E1 (C3) |

## 11 Top-5-Risiken

1. **Report wird ignoriert** (kein Gate → niemand schaut) → R-Gegenzug: Diff-Galerie als
   PR-Kommentar mit ein-Klick-Sichtung, nicht als verstecktes Artefakt.
2. **Scope-Creep zum Gate** (jemand macht den Report „mal eben" required) → ADR-211-Amendment
   schreibt Report-only fest; Eskalation zu Gate = neuer Threshold-Check.
3. **Container-Pin verrottet** (Chromium/Font-Bump) → Render-Image versioniert + Bump
   maschinen-getriggert, nicht kalendergetrieben.
4. **PPTX-OOXML-Assertions unterschätzt** (auch das ist Arbeit) → bewusst auf wenige
   Layout-tragende Shapes pro Master begrenzen.
5. **F18/F19 verschärft** falls doch breit ausgerollt → Pilot-Gate vor jedem zweiten Konsumenten.

## 12 Empfehlungen (konkret, verifizierbar)

- **REC-1:** decks-hub-Pilot: ein Slidev-Deck (Title + 1 Content-Folie), `toHaveScreenshot` im
  gepinnten Render-Container, Masking dynamischer Regionen, Output als **PR-Diff-Galerie
  (non-blocking)**.
- **REC-2:** Erfolgskriterium hart: ein injizierter design-hub-Token-Drift (Brand-Farbe/Logo-Pos)
  wird vom Visual-Report rot, während ein paralleler `data-testid`-Assert grün bleibt — der
  reproduzierbare Beweis der Lücke.
- **REC-3:** pptx-hub bekommt **keine** Pixel-Schiene, sondern python-pptx-Assertions auf
  Platzhalter-Typ/Text/Shape-Count/Geometrie (eigenes, kleines Konzept falls grün).
- **REC-4:** Bei Pilot-Erfolg → **Amendment an ADR-211** (opt-in §Visual-Report-Capability, Muster
  Rev 18), nicht eigener ADR; Report-only nicht-status-gatend ins Scoreboard.

## 13 Entscheidung + Kill-Gate + 30/60/90

**Vorzulegende Wahl an den Decider:** A (structural-only) · B (Visual breit als Gate) ·
**C (gezielter Hybrid — empfohlen)**.

**Kill-Gate (messbar):** siehe Frontmatter `kill_criteria`. Exception-Budget: **bis 2026-09-20**
(= `review_by`); ohne grünen Pilot bis dahin → `pipeline_status: sunset`, structural-only bleibt.

- **30 Tage:** decks-hub-Pilot gebaut, gepinntes Render-Image, REC-2-Beweislauf gefahren.
- **60 Tage:** Pilot-Bilanz (echte Treffer vs. False-Positives) + Entscheidung Amendment ja/nein.
- **90 Tage:** Bei grün → ADR-211-Amendment + pptx-hub-OOXML-Assertion-Konzept; bei rot → sunset.

> **Ehrliche Enforcement-Grenze:** Dieses Doc *schreibt* `review_by`/`kill_criteria`, *erzwingt*
> sie nicht — solange kein Lifecycle-Gate sie liest, ist die Kontrolle Review-Gate, kein Exit-Code.
