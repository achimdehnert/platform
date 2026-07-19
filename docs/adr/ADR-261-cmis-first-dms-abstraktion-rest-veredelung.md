---
status: proposed
decision_date: 2026-06-29
revision: 2
deciders: [Achim Dehnert]
scope: platform
implementation_status: none
related: [meiki:ADR-001, meiki:ADR-002, meiki:ADR-003, meiki:ADR-015]
supersedes: []
---

# ADR-261: CMIS-first DMS-Abstraktion mit optionaler native-REST-Veredelung

> **Kurz:** Für das Mehr-LRA-Produkt (mehrere Landratsämter, heterogene DMS — Günzburg=d.velop,
> Traunstein=enaio, künftige Kreise) wird **CMIS** als **portable Basisschicht** der DMS-Integration
> festgelegt (CRUD, Suche, eAkte, Dokument-Ingest). Native Hersteller-REST-APIs (z. B. d.velop
> DMSApp-REST mit Webhooks/Events) sind eine **optionale additive Veredelungsschicht pro Hersteller**,
> wo installiert (KI-/Echtzeit-Features). Das **kehrt die Reihenfolge** aus `meiki:ADR-001` Variante A
> um: nicht REST-first + CMIS parallel, sondern **CMIS-first + REST additiv**. Dieser ADR entscheidet
> das **produktweite Muster**; `meiki:ADR-001/003` bleiben die LRA-lokalen Ausprägungen.

## Status

`proposed` — wartet auf Entscheidung. Ausgelöst durch die verifizierte Rückmeldung LRA Günzburg
(2026-06-29: **CMIS vorhanden**) und die strategische Festlegung, mittelfristig **mehrere
Landratsämter** auf heterogenen DMS zu bedienen.

## 1 · Kontext

### 1.1 Ausgangslage

- **Heterogene DMS-Landschaft, schon heute belegt:** LRA Günzburg = **d.velop documents** (CMIS-Connector,
  `meiki:ADR-001`); LRA Traunstein = **enaio®** (CMIS-Modul `repositorymanager-cmis`, `meiki:ADR-003`).
  Das Produkt muss perspektivisch über **N Landratsämter** mit **verschiedenen DMS-Herstellern** laufen.
- **`meiki:ADR-001` (Variante A „Hybrid")** entschied bisher **REST-first** (native DMSApp-REST bevorzugt)
  **+ CMIS parallel** dort, wo DokuFIS-Konformität nötig ist — eine **Günzburg-lokale** Optik.
- **Verifizierter Auslöser (LRA GZ, 2026-06-29):** Die native **REST-API ist on-prem (noch) nicht
  installiert**, **CMIS ist vorhanden**. Der REST-first-Ansatz hätte die Migration an einen
  herstellerseitigen Installations-Termin gekettet; CMIS löst diese Abhängigkeit auf.

### 1.2 Problem / Lücken

- **Single-Vendor-Kopplung:** Eine REST-first-Integration bindet pro Hersteller eine eigene native API —
  über N LRAs = N Integrationen, schlechte Amortisation, je Kreis erneuter Termin-/Lizenzpfad.
- **Migrations-Geiselhaft:** REST-first macht jede On-Prem-Anbindung von der herstellerseitigen
  REST-Installation abhängig (GZ: heute nicht vorhanden) — Termin liegt außerhalb unserer Kontrolle.
- **Vergaberecht:** Kommunale Ausschreibungen referenzieren **DIN SPEC 32791 (DokuFIS)** / CMIS als
  standardkonformen Integrationsweg; eine proprietär-REST-zentrierte Architektur ist schwächer
  positioniert.

### 1.3 Constraints

- **Fähigkeits-Delta CMIS:** CMIS (OASIS, final 2013, nicht weiterentwickelt) bietet **keine** Webhooks/
  Events, nur Polling → für **KI-/Echtzeit-Features** funktional schwächer (vgl. Bewertungsmatrix
  `meiki:ADR-001`). KI-Features dürfen daher **nicht** allein auf CMIS gebaut werden.
- **„Uniform CMIS" ist Teil-Mythos:** Hersteller implementieren CMIS mit Eigenheiten (Property-Mapping,
  Query-Dialekt-Abdeckung, Custom-Types, Performance/Schema-Konflikte). Das enaio-Bestandsinterview
  flaggt CMIS-Performance/Schema-Risiken ausdrücklich.
- **Einmaliger Build-Aufwand:** Ein CMIS-Adapter ist echte Entwicklung (Auth, Dokumentmodell-/
  Property-Mapping, CMIS-QL-Suche) — relativiert die „Migration = nur Konfiguration"-Botschaft, ist
  aber einmalig und über LRAs wiederverwendbar.

## 2 · Entscheidung

1. **CMIS ist die kanonische, herstellerneutrale Basisschicht** der DMS-Integration für das Mehr-LRA-
   Produkt: Dokument-Ingest/-Lesen, Eigenschaften, Suche, eAkte-Anbindung laufen über CMIS
   (OASIS CMIS 1.1, DIN SPEC 32791/DokuFIS).
2. **Native Hersteller-REST-APIs sind eine optionale additive Veredelungsschicht** pro Hersteller —
   genutzt **nur** dort, wo installiert, **ausschließlich** für Fähigkeiten, die CMIS strukturell nicht
   liefert (Webhooks/Events/Echtzeit/KI-Trigger). Die Basisfunktion bleibt **immer** CMIS-fähig.
3. **Architektur-Form:** **CMIS-Kern + Hersteller-Profil je DMS** (Mapping/Query-Eigenheiten),
   nicht „ein CMIS für alle unberührt". Erstes Profil: **d.velop**; zweites: **enaio**. Ein Profil ist
   **bewusst kein „dünner" Pauschalbegriff**, sondern hat einen definierten Umfang (§5, REC-2).
4. **Capability-Modell statt Protokoll-first (REC-1, OOTB-1):** Verbindlich ist eine **Capability-Matrix**
   (`DocumentRead/Write`, `CaseFileSearch`, `MetadataUpdate`, `EventReceived`, `AITrigger`, …) mit drei
   Zusage-Klassen je Capability: **(a) garantiert über CMIS**, **(b) CMIS-möglich, standortabhängig zu
   verifizieren**, **(c) nur mit nativer REST-Veredelung zugesagt**. CMIS/REST sind **Provider je
   Capability**, nicht die Architektursprache. Diese Matrix ist Entscheidungsbestandteil, nicht
   Implementierungs-Kür.
5. **Interne REST-Fassade = stabile interne Produkt-API (REC-3):** UI, KI-Komponenten und Fachlogik
   sprechen **ausschließlich** gegen die interne Fassade (`meiki:ADR-015`); CMIS und native Hersteller-REST
   liegen als **austauschbare Provider/Adapter darunter**. Kein direkter Leak von CMIS-/Vendor-Konzepten
   in die oberen Schichten.
6. **Reihenfolge-Reframe:** Dieser ADR kehrt die Hybrid-Reihenfolge aus `meiki:ADR-001` Variante A um
   (CMIS-first statt REST-first). `meiki:ADR-001/003` werden auf diesen ADR verlinkt und als
   LRA-lokale Ausprägungen geführt.

## 3 · Betrachtete Alternativen

| Alternative | Inhalt | Bewertung |
|---|---|---|
| **A0 — REST-first je Hersteller** (Status quo `meiki:ADR-001`) | native API bevorzugt, CMIS nur DokuFIS | **verworfen** für Produktebene — N Integrationen, Migrations-Geiselhaft, schwache Amortisation |
| **A1 — CMIS-only** | ausschließlich CMIS, keine native API | **verworfen** — opfert KI/Echtzeit (kein Webhook/Event); MEiKI-Differenzierung verloren |
| **A2 (gewählt) — CMIS-first Basis + REST-Veredelung** | CMIS portabel als Kern, native REST additiv wo vorhanden | **gewählt** — Portabilität + Amortisation, KI-Features erhalten, vergabekonform |
| **A3 — Eigene Abstraktions-API über beide** | proprietäre Fassade, intern Adapter je DMS | **in A2 integriert** (REC-3): die interne REST-Fassade `meiki:ADR-015` IST diese stabile API, CMIS/REST als Provider darunter — keine *zusätzliche* neue Vertrags-API |
| **A4 — Kauf statt Bau** (REC-10, OOTB-2) | bestehendes DMS-Integrations-Gateway / iPaaS-Middleware (kapselt CMIS, Hersteller-Adapter, Mapping, Events) | **geprüft, vorerst vertagt** — On-Prem-Behördenbetrieb, Datensouveränität, Vergabe, Lizenzkosten und Vendor-Lock-in wiegen schwerer als die Bauersparnis; bei wachsender Hersteller-Zahl erneut bewerten |

## 4 · Begründung im Detail

- **Amortisation:** Ein CMIS-Kern bedient d.velop (GZ) **und** enaio (TS) — beide CMIS-fähig belegt —
  und jede künftige Kommune auf Alfresco/Nuxeo/OpenText/SharePoint. Marginale Integrationskosten pro
  LRA sinken auf das dünne Hersteller-Profil.
- **De-Risking des kritischen Pfads:** Mit vorhandenem CMIS (GZ verifiziert) hängt die On-Prem-Migration
  **nicht** mehr an einer herstellerseitigen REST-Installation. Der pfadkritische Schritt wandert von
  „d.velop installiert REST" (außerhalb unserer Kontrolle) zu „HNU baut CMIS-Adapter" (steuerbar).
- **Vergabe-/Politik-Konformität (qualifiziert, REC-8):** CMIS ist **anschlussfähig an / standardkonform
  mit** DIN SPEC 32791 (DokuFIS) und damit ausschreibungsfreundlich. **Nicht verifiziert** (offener Punkt):
  ob typische kommunale Ausschreibungen CMIS nur als *Kompatibilität* fordern, es *empfehlen* oder als
  Basis *erzwingen* — billigster Check: ein bis zwei reale LRA-Leistungsverzeichnisse prüfen. Bis dahin
  **keine** „erzwingt"-Behauptung.
- **Fähigkeitserhalt:** Die REST-Veredelungsschicht hält die KI-/Event-Features dort verfügbar, wo der
  Hersteller eine native API bereitstellt — kein Funktionsverlust gegenüber `meiki:ADR-001`.

## 5 · Implementation Plan

1. **Capability-Matrix erstellen** (REC-1): Produkt-Capabilities × Zusage-Klasse (a/b/c, §2.4) — der
   verbindliche Vertrag, gegen den Profile, Tests und Produktkommunikation laufen.
2. **CMIS-Kern-Adapter** (vendor-neutral): Auth, Repository-/Dokumentmodell, Property-Mapping-Abstraktion,
   CMIS-QL-Suche, Ingest/Read. Referenz-Stack z. B. Apache Chemistry. Spricht **nur** gegen die interne
   Fassade (`meiki:ADR-015`), nicht direkt in obere Schichten (§2.5).
3. **Hersteller-Profil — definierter Umfang statt „dünn" (REC-2):** Jedes Profil deklariert explizit:
   Property-/Metadaten-Mapping, unterstützte Query-Fähigkeiten, Rechte-/Akten-Konventionen,
   Performance-Parameter und **bekannte Nicht-Ziele**. Erstes Profil **d.velop** (GZ-Pilot): Binding/Version
   bestätigen (AtomPub/Browser, 1.1), Property-Konvention abbilden (z. B. „3"=Name, „5"=Aktenzeichen aus
   KONZ-meiki-003), Dienstaccount.
4. **Standort-Readiness-Check vor jeder Zusage (REC-4):** verbindliche Checkliste — CMIS aktiviert,
   Version/Binding bestätigt, Lizenzstatus geklärt, Dienstaccount verfügbar, synthetische Testdaten möglich,
   **Mindestperformance gemessen**. „CMIS vorhanden" (formal) zählt erst nach diesem Check als
   anschlussfähig (AD-1).
5. **CMIS-Konformitäts-/Regressions-Test-Suite als Entscheidungsbestandteil (REC-5):** automatisiert je
   DMS-Version/Standort; grün = Voraussetzung für Onboarding, nicht bloße Implementierungsabsicht
   (vgl. Org-Lehre „strukturelle Invariante braucht CI-Gate").
6. **Verifikation** gegen das GZ-On-Prem-**Testsystem** mit **synthetischen** Daten (Datensparsamkeit,
   vgl. `meiki:KONZ-meiki-003/ADR-039`).
7. **Zweites Hersteller-Profil enaio (TS) VOR dem produktiven Rollout (REC-7):** der Portabilitäts­anspruch
   gilt erst als belegt, wenn ein zweiter Hersteller über denselben Kern läuft — **Exit-Kriterium für
   „Plattformmuster bestätigt"**, nicht Nacharbeit.
8. **Optionale REST-Veredelung** je Hersteller später, wo native API installiert (GZ: wenn REST kommt).
9. `meiki:ADR-001/003` mit Verweis auf diesen ADR und Reihenfolge-Reframe aktualisieren.

## 6 · Risiken

| Risiko | Schwere | Gegenmaßnahme |
|---|---|---|
| **CMIS formal vorhanden ≠ funktional nutzbar** (AD-1) — kann performant/organisatorisch genauso blocken wie fehlendes REST | hoch | Standort-Readiness-Check inkl. **gemessener Mindestperformance** vor Zusage (§5.4); Exit-Pfad bei schwacher CMIS-Realität (Fallback REST/manuell) |
| **Profile wachsen zu mittelgroßen Adaptern** (AD-2, M28-2) — „dünn" trügt | hoch | Profil-Umfang + Nicht-Ziele explizit deklariert (§5.3); Governance-Review gegen Profil-Wildwuchs |
| **Onboarding wird manuelle Integrationsdiagnose** statt wiederholbarem Prozess (M28-3) | hoch | automatisierte Konformitäts-/Regressions-Suite als Onboarding-Gate (§5.5) |
| CMIS-Fähigkeits-Delta (kein Webhook/Event) → KI-Features eingeschränkt; **Polling** statt Events nötig (AD-7) | hoch | REST-Veredelung Pflichtschicht für KI/Echtzeit; CMIS-only-Standorte erhalten laut Capability-Klasse (b/c) **degradierte Echtzeit** (Polling) — konkrete Polling-Parameter = Impl-Detail (§7.3) |
| **„Optionale" REST-Veredelung wird faktische Pflicht** (M28-4), wenn KI kommerziell zentral → Rückfall in REST-first-Druck | mittel | Capability-Matrix macht die Abhängigkeit explizit; Produktkommunikation §7 trennt Basis- von KI-Zusagen |
| Build-Aufwand relativiert „Migration=Konfiguration" | mittel | einmalig + wiederverwendbar kommunizieren; Trennung Build (einmal) vs. Anbindung (Konfig je LRA) |
| Annahme „CMIS überall aktiv" falsch bei künftigem LRA (AD-6) | mittel | Standort-Readiness-Check **vor** Zusage (§5.4; Lehre GZ: cheapest check zuerst) |

## 7 · Konsequenzen

### 7.1 Positiv
- Eine Integration über mehrere LRAs/DMS; bessere Amortisation und Wiederverwendung.
- On-Prem-Migration nicht mehr von Hersteller-REST-Installationsterminen abhängig.
- Vergabe-/DokuFIS-konforme Positionierung.

### 7.2 Trade-offs
- Einmaliger CMIS-Adapter-Bauaufwand bei HNU; je DMS ein Hersteller-Profil.
- KI-/Echtzeit-Features benötigen zusätzlich die REST-Veredelung (zwei Schichten statt einer).

### 7.3 Produktkommunikation (verbindlich, REC-9)
- **Basisfunktionen** (Capability-Klasse a) dürfen als **CMIS-fähig/standortunabhängig** beworben werden.
- **KI-/Echtzeit-Funktionen** (Klasse c) werden **nur bei vorhandener nativer REST-/Event-Schicht**
  zugesagt — nie pauschal. Klasse-b-Funktionen nur mit Standort-Vorbehalt.
- Diese Trennung ist die kommerzielle Spiegelung der Capability-Matrix (§2.4) und verhindert Over-Selling.

### 7.4 Nicht in Scope
- Konkrete CMIS-Library-Wahl/Implementierungsdetails (Folge-Konzept/Repo-ADR).
- **Konkrete Polling-Parameter** (Frequenz, Backoff, Änderungsdetektion, Latenzbudget) = Implementierungs-
  Detail des CMIS-only-Pfads (REC-6 scoped) — die *Architektur-Konsequenz* (degradierte Echtzeit, Klasse b/c)
  steht in §6.
- LRA-spezifische Schema-/Kategorie-Definitionen (bleiben LRA-lokal, z. B. GZ-Spezifikationsblatt).
- Produktinternes Dokument-Arbeitsrepository als Architektur-Basis (OOTB-3) — **abgelehnt**: zweite
  Wahrheit neben dem Stammdaten-Master (`meiki:ADR-028`/SSoT-Disziplin); nur enge synthetische
  Test-Caches sind erlaubt.
- Realdaten-Zugriff (gegated; Pilot bleibt synthetik-only).

## 8 · Validation Criteria

- **Capability-Matrix** existiert, jede Produkt-Capability ist Klasse a/b/c zugeordnet (REC-1).
- **Konformitäts-/Regressions-Suite** ist grün gegen das d.velop-Profil und Onboarding-Gate (REC-5).
- **Standort-Readiness-Check** für GZ bestanden, inkl. gemessener Mindestperformance (REC-4).
- CMIS-Kern-Adapter liest/schreibt synthetische Dokumente gegen das GZ-Testsystem (d.velop-Profil) — E2E grün.
- **Zweiter Hersteller (enaio) läuft über denselben Kern** mit deklariertem Profil — Portabilität belegt,
  **bevor** „Plattformmuster bestätigt" erklärt wird (REC-7).
- Obere Schichten (UI/KI/Fachlogik) sprechen nur gegen die interne Fassade — kein CMIS-/Vendor-Leak (REC-3).
- KI-/Event-Feature läuft über die REST-Veredelung dort, wo native API vorhanden — ohne Bruch der CMIS-Basis.

## 9 · Glossar

| Abkürzung | Bedeutung |
|---|---|
| **ADR** | Architecture Decision Record — dokumentierte Architekturentscheidung |
| **CMIS** | Content Management Interoperability Services — herstellerneutraler OASIS-Standard für DMS-Zugriff |
| **DMS** | Dokumentenmanagement-System (z. B. d.velop, enaio) |
| **DokuFIS / DIN SPEC 32791** | Deutsche Spezifikation für standardkonforme DMS-Schnittstellen in Kommunen |
| **REST-API** | Native HTTP-Schnittstelle eines Herstellers (hier inkl. Webhooks/Events) |
| **Webhook / Event** | Server-Push bei Änderungen (Echtzeit) — von CMIS nicht geboten, nur Polling |
| **eAkte** | Elektronische Akte |
| **KI** | Künstliche Intelligenz (hier: Posteingangs-Klassifikation, Chatbot, HITL) |
| **LRA** | Landratsamt |
| **PoC** | Proof of Concept |
| **Property „3"/„5"** | d.velop-Eigenschaftskonvention im Projekt: Feld 3 = Name, Feld 5 = Aktenzeichen |

## 10 · Referenzen

- `meiki:ADR-001` — CMIS vs. REST (Günzburg) — Reihenfolge-Reframe durch diesen ADR
- `meiki:ADR-002` — d.velop Betriebsmodell (On-Prem)
- `meiki:ADR-003` — enaio Schnittstellenarchitektur (Traunstein)
- `meiki:ADR-015` — REST-Fassade / Integrationsstrategie
- `meiki:KONZ-meiki-003` / `meiki:ADR-039` — DMS-als-Personenquelle, Synthetik-Testharness
- `meiki-hub:docs/02-prozesshandbuch/pilotierung/m0-onprem-migration-rueckmeldung-guenzburg-dvelop.md` — Auslöser-Rückmeldung (CMIS vorhanden, 2026-06-29)

## 11 · Changelog

- **2026-06-29 (Rev 1):** Erstellt. Ausgelöst durch verifizierte GZ-Rückmeldung (CMIS vorhanden) +
  Mehr-LRA-Strategie. Status `proposed`.
- **2026-06-29 (Rev 2):** Externe Zweitmeinung (`/adr-handoff-extern`, anonymisiert/Cross-Provider)
  eingearbeitet — Rückfluss-Gate (Befund-IDs):
  - `[valid]` → eingearbeitet: REC-1 Capability-Matrix (§2.4, §5.1), REC-2 Profil-Umfang+Nicht-Ziele (§5.3),
    REC-3 interne Fassade als Produkt-API / A3 integriert (§2.5, §3), REC-4 Standort-Readiness-Check (§5.4),
    REC-5 Konformitäts-Suite als Gate (§5.5), REC-7 zweiter Hersteller vor Rollout (§5.7), REC-9
    Produktkommunikations-Regel (§7.3), REC-10 Kauf-statt-Bau A4 (§3); AD-1/AD-2/AD-6/M28-2/M28-3/M28-4
    in Risiken (§6) verschärft.
  - `[valid-scoped]` → REC-6 (AD-7): Polling-*Konsequenz* in §6 aufgenommen, konkrete Parameter als
    Impl-Detail nach §7.4 (nicht ADR-Flughöhe).
  - `[valid, als Qualifizierung]` → REC-8 (AD-5): Vergabe-Argument auf „anschlussfähig/standardkonform"
    abgeschwächt + „erzwingt?" als offener, zu verifizierender Punkt markiert (keine unbelegte Behauptung).
  - `[out-of-scope]` → OOTB-3 (produktinternes Dok-Repo als Basis): abgelehnt — zweite Wahrheit neben
    `meiki:ADR-028`/SSoT; nur synthetische Test-Caches erlaubt (§7.4).
  - PRO-1..5 bestätigen den Steelman (keine Änderung). Briefing+Antwort: `~/shared/adr-handoff-ADR-259-sanitized-2026-06-29*.md`.
