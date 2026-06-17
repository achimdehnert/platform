---
id: ADR-249
title: "Telefon-/Sprachagent als eigenständiges iilgmbh-Produkt: Swappable-Ports-Architektur + Souveränitäts-Profil, MVP mPA, erster regulierter Pilot meiki-hub"
status: proposed
date: 2026-06-17
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh, meiki-lra]
domains: [product, architecture, llm, rag, voice, data-sovereignty, cross-repo]
supersedes: []
amends: []
depends_on: [ADR-171, ADR-172]
related: [ADR-171, ADR-172]
tags: [voice-agent, telefonagent, mpa, rag, freshness, swappable-runtime, data-sovereignty, multi-tenant, product]
scope:
  include_paths:
    - "docs/adr/ADR-249-*"
---

# ADR-249 — Telefon-/Sprachagent als eigenständiges Produkt mit Swappable-Ports-Architektur

> Cross-Repo-Referenzen auf MEiKI-ADRs sind als `meiki:ADR-NNN` notiert (eigenes
> Repo `meiki-lra/meiki-hub`), Platform-ADRs ohne Präfix.

## 1. Kontext

Für das Landratsamt Günzburg ist ein **Telefon-Sprachagent** gewünscht, der Bürgern
Auskunft gibt (Vermittlung, FAQ, Datenaufnahme). Referenz-Anforderungsliste: das
Webinar-Produkt **samwin AI Agents**. Dessen Architektur setzt laut eigenen Slides auf
die **OpenAI Realtime API (GPT-4o)** — eine US-Cloud-Inferenz. Das kollidiert frontal mit
der dokumentierten MEiKI-Leitplanke (`meiki:ADR-004`):

> „Datenhaltung in Deutschland, kein Training auf Bürgerdaten, keine Übermittlung an
> Dritte … schließt Cloud-LLM-Dienste außerhalb der EU aus … Kein OpenAI / Anthropic /
> Mistral-Cloud-API."

Bei einem Sprachagenten wird der **Audio-Stream des Bürgers** (= personenbezogene Daten)
verarbeitet. Eine fest verdrahtete Cloud-Realtime-Pipeline ist damit für GZ unzulässig.
samwin ist deshalb als **Fachkonzept-Referenz** brauchbar, als **Produkt** aber nicht
beschaffbar, solange die Inferenz nicht garantiert EU/on-prem läuft.

Gleichzeitig ist der Agent von Natur aus **horizontal/mandantenfähig** (samwin verkauft
ihn an Stadtverwaltung, LKW-Waage u. a.). Ihn in das LRA-Vertikal-Repo `meiki-hub` zu
bauen, würde ein Produkt an einen Projektkontext koppeln.

## 2. Entscheidung

Wir bauen einen **eigenständigen Telefon-/Sprachagenten als Produkt** mit folgender
Festlegung:

### 2.1 Heimat & Schnitt
- **Code-Owner-Org/Repo: `iilgmbh`** (neues Produkt-Repo). `meiki-hub` ist **nicht**
  Code-Owner, sondern **erster regulierter Pilot-Tenant**.
- Begründung Org-Wahl: horizontales, mandantenfähiges Produkt → gehört nicht in ein
  Domänen-/Vertikal-Hub (vgl. Policy `platform-agents.md`: Domänen-Hubs hosten nur
  Business-Logik ihrer Domäne).

### 2.2 Architektur-Rückgrat: drei austauschbare Ports hinter einem Souveränitäts-Profil

| Port | Verantwortung | Naht |
|---|---|---|
| **LLM-Runtime** | Sprachverständnis/-generierung, Tool-Calls | OpenAI-kompatible API-Grenze (`meiki:ADR-004`: „LLM muss austauschbar bleiben") |
| **Knowledge/Retriever** | RAG über Wissensquelle(n) | Retriever-Interface (`ingest()` / `query()→chunks`), pgvector als Default-Adapter |
| **Voice (ASR/TTS)** | Sprache↔Text am Rand | Edge-Adapter (STT davor, TTS dahinter) |

Pro Mandant schaltet ein **`tenant_profile.sovereignty ∈ {open, strict}`**, welche
Adapter erlaubt sind. `strict` (z. B. GZ) erzwingt lokale Inferenz/Embedding/Voice;
`open` (z. B. mPA) erlaubt Cloud-Adapter. **Dieser Profil-Schalter macht den Übergang
mPA→meiki zum Config-Swap statt Rewrite** — genau das, was samwin strukturell nicht kann.

Zwei Verschärfungen aus dem externen Review (2026-06-17):
- **Profil = Policy, nicht nur Adapter-Allowlist** (REC-6): `tenant_profile` regelt **testbar**
  auch erlaubte **Datenflüsse, Logging/Telemetrie, Prompt-/Audio-Persistenz, Caching,
  Retention, Export**. Sonst umgeht ein Cloud-Logging-/Telemetrie-Pfad die Adapter-Grenze,
  obwohl der LLM-Adapter „lokal" ist.
- **LLM-Port = Capability-Contract, nicht nur HTTP-Form** (REC-1): „OpenAI-kompatibel" muss
  **Tool-Calls, Streaming, JSON-Schema-Verhalten, Fehlerklassen, Timeouts/Retries** pro
  Adapter normieren — sonst leakt Adapter-Sonderverhalten in den Core (Scheinsicherheit der Naht).

### 2.3 Modalität: Voice **und/oder** Text
Der **Agent-Core ist modalitäts-agnostisch** (operiert auf Text + Tool-Calls). **Voice ist
ein Edge-Adapter** (STT→Core→TTS), Telefonie = derselbe Voice-Adapter + Transport
(SIP/Inbound). Folge: Text-Pfad zuerst lieferbar, Voice-Naht aber von Anfang an vorhanden;
der Telefon-Pilot ist kein Core-Rewrite.

### 2.4 Wissens-Frische als Eigenschaft der Quelle (zwei Profile)
„Veraltete Info" sind **zwei** verschiedene Probleme mit fast gegensätzlicher Lösung. Der
Retriever-Port trägt pro Quelle eine **Frische-Strategie**:

| Profil | `live-mutable` | `immutable-temporal` |
|---|---|---|
| Beispiel | E-Mail, OneDrive-Ordner (mPA) | Gesetze, AVOs, Ausführungsbestimmungen (MEiKI) |
| „Veraltet" = | Index hinkt nach (Datei geändert/gelöscht/verschoben) | aktuelle Fassung für Frage zu Stichtag in der Vergangenheit |
| Lösung | Inhalt aktiv **entfernen**: Change-Detection + Lösch-**Tombstones** + Re-Embed | Inhalt **nie** entfernen: immutabel + `as_of_date` + Gültigkeitsintervalle |
| Realisierung | MS Graph **Delta-Query** (OneDrive + Outlook) | `meiki:ADR-006` (Temporal RAG, Accepted) |

`live-mutable` muss löschen können, `immutable-temporal` darf nie löschen — deshalb sind es
getrennte Profile, kein gemeinsamer Mechanismus. Für Rechts-/Normfragen ist **`as_of_date`
Pflicht** (kein impliziter „aktueller Stand") und beide Profile bleiben **technisch getrennt**
— eigene Adapter, Tests, Frische-Metriken (Review REC-10, gegen falsche Stichtagsantworten).

### 2.5 Staging
1. **MVP „mPA" (myPersonalAssistant)** unter `iilgmbh` — `sovereignty: open`, Quellen
   E-Mail + OneDrive (`live-mutable`), Cloud-Adapter erlaubt, eigene Daten des Betreibers
   (kein Bürger-Risiko). Beweist Engine + Frische-Naht billig.
2. **meiki-hub-Pilot** — `sovereignty: strict`, on-prem LLM/Embedding/Voice, Quellen
   Bürger-FAQ/Telefonbuch (`live-mutable`) + Rechts-Corpus (`immutable-temporal` via
   ADR-006).

### 2.6 SSoT / keine Doppelstruktur: bestehende Wissensquelle bevorzugt
Betreibt ein Tenant bereits eine eigene **Wissensquelle samt Chatbot** (z. B. ein on-prem
DMS-gestütztes System), baut der Knowledge-Port **keinen parallelen Store**, sondern bindet
die bestehende Quelle an — eine zu pflegende Wahrheit, immer gleicher Stand (Org-Policy
SSoT). Bevorzugte Adapter-Varianten, Reihenfolge nach SSoT-Treue:

| Variante | Mechanik | SSoT |
|---|---|---|
| (a) **Föderieren** | Agent ruft den bestehenden Chatbot/Antwort-Service als **Tool** auf | ✅ 0 Kopie |
| (b) **Read-through** | Agent liest die **Informationsquelle** read-only, eigenes Retrieval | ✅ solange kein gespiegelter Index entsteht |
| (c) Kopie/Sync in eigenen Store | periodischer Voll-/Delta-Import | ❌ erzeugt genau die Doppelstruktur — nur Fallback, wenn (a)/(b) technisch unmöglich |

Quelle der Anforderung: Stakeholder-Mail (Daniel, 2026-06-17) zum Pilot-Tenant.

**Konkrete Realisierung Pilot-Tenant (verifiziert, Telefonauskunft Daniel 2026-06-17):**
OCOS stellt **separate Wissensdatenbank-Produkte** bereit, die über eine **REST-Schnittstelle
abgefragt** werden können. → Knowledge-Port-Adapter = **OCOS-REST-Retriever** (Read-through,
Variante b): der Agent fragt die bestehende OCOS-Wissensdatenbank zur Laufzeit ab, **kein
eigener gespiegelter Index** für diese Quelle. Folgen, die noch zu klären sind (Adapter-Detail,
kein Blocker): ob OCOS selbst rankt/semantisch sucht (dann braucht diese Quelle **kein**
eigenes Embedding → G-2 entfällt für sie) oder Rohtreffer liefert; Auth/Format der REST-API;
Antwortlatenz pro Hop (relevant für das <400 ms-Voice-Ziel, ggf. Caching heißer Anfragen);
ob OCOS Quellennachweise/Provenance mitliefert (Pflicht für Bürger-Auskunft).

**Verschärfungen aus Review (2026-06-17):**
- **Resilienz statt harter Kopplung** (REC-4): Timeout/Fallback/Circuit-Breaker, damit die
  Verfügbarkeit des Sprachagenten nicht 1:1 an die Wissensquelle hängt. Ein **begrenzter
  TTL-Cache** ist erlaubt, gilt aber **nicht** als Wahrheitsstand (kein verdeckter Schatten-Index).
- **Provenance = harter Adaptervertrag** (REC-5): jede Bürgerauskunft trägt Quelle/Stand/
  Dokument — oder es gibt eine **definierte Nichtbeantwortung/Eskalation** statt Rateantwort.
- **Variante (b) ist vorläufig** (REC-12): Read-through ist gewählt, vor endgültiger
  Festlegung aber in einem kurzen Spike gegen Föderation (a) zu messen (Latenz, Provenance,
  SSoT-Treue, Antwortqualität).

### 2.7 Agent-Core-Invarianten (Review REC-8)
Der Core garantiert **tenant-unabhängig** (das macht die samwin-„Restriktionen" explizit):
- **Antwort nur aus freigegebenen Quellen**; **Nichtwissen statt Halluzination** (lieber
  „weiß ich nicht / ich verbinde weiter" als geraten).
- **Tool-Call-Allowlist** + validierte Befehle; **Eskalation/Weiterleitung an Mensch** als
  erstklassiger Pfad — inkl. **Human-in-the-Loop-Modus** für `strict`-Piloten (Agent nimmt
  auf / schlägt vor / eskaliert statt vollautonom; Review Out-of-the-Box, senkt Haftungs-/
  Halluzinations-/Consent-Risiko).
- **PII-Minimierung**; mandantenspezifische System-Prompts.

## 3. Gates (verbindliche Vorbedingungen / Risiken)

| # | Gate | Begründung |
|---|---|---|
| G-1 | **Runtime-Adapter-Naht ab Commit 1** | Ohne sie wird mPA→meiki ein Rewrite (samwins Fehler) |
| G-2 | **Embedding-Modell = Deploy-Zeit-Entscheidung pro Index, nicht hot-swap** | `meiki:ADR-004`: Modellwechsel macht alle pgvector-Vektoren ungültig |
| G-3 | **`strict`-Tenant: Embedding + LLM + Voice lokal** | Souveränität; kein Cloud-Embedding/-ASR für Bürgerdaten |
| G-4 | **Telefon-Voice (full-duplex, Barge-in, <400 ms) = separater Härtungsschritt** | ChatGPT-Voice ist turn-based; telefon-taugliche Latenz ist nicht „mit dem MVP erledigt" |
| G-5 | **mPA-MVP zieht OAuth/MS-Graph + echte PII** | Der „einfache" MVP wird weniger einfach; vertretbar nur, weil eigene Daten |
| G-6 | **On-prem Voice-Runtime (Hardware) ist Langläufer** | `meiki:ADR-004` GPU-Beschaffung A2-Gate, `implementation_status: none` |
| G-7 | **Bürger-Telefonie-Compliance-Flow** (Review REC-7) | Nicht nur „Hinweis": Begrüßung + KI-Kennzeichnung, **Consent/kein Consent**, Recording-Policy, Löschfristen, **Weiterleitung an Mensch**, Auditspur — produktprägende Flow-Entscheidungen |
| G-8 | **Integrationstiefe der bestehenden Wissensquelle (§2.6)** | ✅ **verifiziert** (Tel. Daniel 2026-06-17): OCOS bietet separate, **REST-abfragbare** Wissensdatenbanken → Read-through-Adapter (Variante b). Rest-Offen ist nur Adapter-Detail (Ranking/Auth/Latenz/Provenance), kein Architektur-Blocker |
| G-9 | **Ende-zu-Ende-Latenzbudget Telefonie** (Review REC-3) | <400 ms als Härtungsziel **mit Messmethode**; Budget über SIP-Transport + ASR + Core + Retrieval-REST-Hop + LLM + TTS + Streaming/Barge-in zerlegen |
| G-10 | **strict-Readiness-Gate** (Review REC-2) | GPU-Beschaffung + lokale LLM/ASR/TTS-Kandidaten + Offline-Betrieb + Deployment-Nachweis + Mindestqualität; Modell-/Runtime-Kandidaten aus `meiki:ADR-004` referenzieren (**nicht** duplizieren) |
| G-11 | **Tenant-Erweiterungspunkte statt Core-Sonderlogik** (Review REC-11) | Mandanten-Anpassungen leben in Profilen/Adaptern — verhindert, dass der erste strict-Tenant faktischer Architektur-Owner wird |

**Right-Sizing der Frische:** Die **Naht** (Frische-Strategie-Property) muss ab v0 da sein,
die **Raffinesse** gestaffelt — v0 mPA: nächtlicher Voll-Resync (Frische 24 h für eigene
Notizen ok); v1: Graph-Delta + Lösch-Tombstones. Nicht die volle Temporal+Delta-Maschinerie
am Tag 1.

## 4. Betrachtete Alternativen

- **samwin als Produkt beschaffen** — scheitert an fest verdrahtetem OpenAI-Realtime für
  `strict`-Tenants; nur heilbar mit vertraglich/technisch garantierter EU-/on-prem-Inferenz
  (offen, beim Vertrieb schriftlich abzufragen). Als **Referenz** behalten.
- **In `meiki-hub` bauen** — schnellster Start, koppelt aber das Produkt an den
  LRA-Vertikal-Kontext; spätere Herauslösung teuer. Verworfen.
- **Direkt mit dem GZ-Piloten starten („härtester Kunde zuerst")** — gute Forcing
  Function, aber Hardware-/DSFA-/AI-Act-Last blockiert frühes Engine-Feedback. Synthese:
  Engine im einfachen Kontext (mPA) bauen, **mit der Naht des harten Kontexts** (G-1/G-3).
- **Souveräne EU-/on-prem-Voice-Plattform unter dem Voice-Port** (Review Out-of-the-Box) —
  Telefonie/SIP/Barge-in/Monitoring zukaufen, LLM- + Knowledge-Port souverän selbst behalten;
  als **Benchmark/Beschleuniger** der Voice-Härtung (G-4/G-6) prüfen, nicht als Primärentscheidung.
- **Appliance/Box-Deployment für strict-Tenants** — Zielbild bei mehreren strict-Tenants
  (zertifizierte Modell-/Voice-/Observability-Komponenten); nicht MVP-relevant.

## 5. Konsequenzen

**Positiv:** ein Produkt-Skelett für viele Mandanten; mPA liefert frühes, billiges
Engine-Feedback; Souveränität ist Architektur-Constraint ab Tag 1 statt Nachrüstung;
MEiKI-Temporal-RAG (ADR-006) wird als Knowledge-Profil wiederverwendet.

**Trade-offs / offen:** Voice-Runtime on-prem ist Langläufer (G-6); telefon-taugliche
Latenz separater Schritt (G-4); mPA-Auth/PII-Aufwand (G-5); samwin-Referenz vs.
Eigenbau-Entscheidung endgültig zu bestätigen.

## 6. Nächste Schritte

1. `/konzept` mPA-MVP (T1/T2) im neuen `iilgmbh`-Repo — ein Voice-Slice, swappable Runtime.
2. `/onboard-repo` Produkt-Repo unter `iilgmbh`.
3. meiki-hub als `strict`-Pilot-Tenant anbinden (Profil aus `meiki:ADR-004` + `meiki:ADR-006`).
4. **OCOS-REST-Adapter-Detail** (§2.6/G-8 — Schnittstelle ✅ verifiziert): Ranking/Auth/Format,
   Antwortlatenz pro Hop (<400 ms-Ziel), Provenance/Quellennachweis abklopfen.
5. DSFA-Bedarf Sprachverarbeitung mit Datenschutz GZ prüfen.
6. **Voice-Spike** mit realer Telefonie-Härte (Barge-in, Stille, Dialekt, schlechte
   Verbindung, Abbruch, DTMF, Weitervermittlung) — Review REC-9.
7. **Spike Read-through (b) vs. Föderation (a)** der bestehenden Wissensquelle — Review REC-12.

---
*Verschärft nach externem Review (`adr-handoff-extern`, 2026-06-17): RECs 1–12 + Out-of-the-Box
geprüft und — soweit `[valid]` — als Entscheidungs-Verschärfung, Gate (G-9..G-11) oder Spike
verankert. Step-5-Tag-Tabelle siehe Session-Log.*

## 7. Referenzen
- `meiki:ADR-004` — LLM-Runtime/Modellauswahl (Souveränitäts-Leitplanke, Embedding-Risiko)
- `meiki:ADR-006` — Temporal RAG Pilot (immutable-temporal-Profil)
- `ADR-171` / `ADR-172` — Temporal RAG Infrastructure / rag-mcp Server (Platform)
- Policy `platform-agents.md` — Heimat-Wahl horizontaler vs. Domänen-Code
- Referenz-Anforderungsliste: samwin AI Agents (Webinar-Slides)
