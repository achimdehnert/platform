---
id: ADR-276
title: "Cross-Repo-Dokumenten-Klassifikation & Routing — selbstlernender Platform Agent in dev-hub, Geschwister-Architektur zum mPA/Voice-Agent"
status: proposed
decision_date: 2026-07-14
revision: 2   # 2026-07-14: zwei externe adversariale Reviews (beide „überarbeiten") eingearbeitet, s. §Externes Sparring
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
supersedes: []
related: [ADR-050, ADR-170, ADR-249, ADR-274]
tags: [dev-hub, dms-hub, risk-hub, iil-voice-agent, classification, routing, human-in-the-loop, feedback-loop, self-learning, sovereignty, aifw, platform-agent]
drift_check_paths:
  - "dev-hub/apps/"
  - "dms-hub/src/apps/scanner/models.py"
  - "risk-hub/src/documents/models.py"
  - "iil-voice-agent/docs/konzepte/KONZ-platform-006-mpa-mvp.md"
---

# ADR-276 — Cross-Repo-Dokumenten-Klassifikation & Routing (selbstlernend)

## Context and Problem Statement

Die Scan-Ingestion-Pipeline ist frisch produktiv: physische Scanner legen PDFs auf
einer Fritzbox-NAS-Share ab, ein Cron-Job auf dem Prod-Host synct sie nach
Paperless-ngx (docs.iil.pet), und `dms-hub` trackt jedes Dokument als
`ScanDocument` (`dms-hub/src/apps/scanner/models.py`) mit State-Machine
`INBOX → CLASSIFIED → FORWARDED → ARCHIVED → REJECTED` und Weiterleitung nach
d.velop (`scanner/services.py:281 forward_to_dvelop`).

**Klassifikation ist heute zu 100 % manuell:** Die Felder `document_category`,
`classification_confidence` und `classification_method` (AUTO/MANUAL) existieren
bereits im Modell, aber der einzige Schreiber ist `scanner/views.py:206
classify_view` — ein Mensch setzt die Kategorie im UI, hart mit
`classification_method="MANUAL"`, `confidence=1.0`. Der `AUTO`-Pfad ist
vorbereitet, aber nicht verdrahtet. Auf der NAS warten außerdem **~304 bereits
von Menschen in Ordner einsortierte Bestandsdokumente** auf den Sync — deren
Ordnerpfad ist ein (unscharfes) menschliches Label (s. Decision, Bootstrap).

**Sensibilitäts-Befund (Rev. 2, falsifiziert eine Annahme des Erstentwurfs):**
Der Backlog enthält nachweislich mindestens ein **echtes Mandanten-Dokument**
(`Rohstoffverwertung_Groeger_GmbH_Co._KG-nis2_assessment-20260710-4.pdf`,
gesichtet 2026-07-14 auf dem Prod-Host-Share `/mnt/fritz-nas-scans/scans/`;
vom Dev-Host aus nicht nachprüfbar — Share nur auf Prod gemountet). Gröger ist
ein realer Mandant (Org-Memory: Realdaten dürfen kontrollierte Kontexte nie
verlassen). „Eigene Betriebs-Scans = unkritisch" ist damit **widerlegt**:
Business-Scans tragen Dritt-/Mandanten-Daten. Konsequenz in §Souveränität.

Im Ökosystem existieren bereits **drei getrennte Klassifikations-/Analyse-Ansätze**,
keiner für den Scan-Eingang verdrahtet:

| Wo | Was | Grenze |
|---|---|---|
| `dms-hub/src/apps/benefits/classifier.py` | Keyword-Profil-Klassifikator via `ingest.classifier.ProfileClassifier` aus **iil-ingest** (ADR-170) | domänenspezifisch (Bürgergeld), nicht am Scanner-Inbox |
| `risk-hub/src/ai_analysis/` | LLM-Analyse via **iil-aifw** (`llm_client.py`: `aifw.service.sync_completion`, Action-Codes) | analysiert *strukturierte Domänenobjekte*, keine eingehenden Dokumente |
| `dev-hub/apps/repo_health/llm.py` | aifw-Bridge-Muster für Platform Agents (Action-Code, manueller Fallback) | Repo-Gesundheit, kein Dokumentbezug |

risk-hub hat eine **eigene Dokument-Taxonomie und einen Upload-Pfad**:
`risk-hub/src/documents/models.py` definiert `Document.Category` (brandschutz,
explosionsschutz, gefaehrdungsbeurteilung, sdb, betriebsanweisung, pruefbericht, …),
`documents/services.py:52 upload_document` schreibt nach S3. **Lücke (verifiziert):**
die ninja-API (`documents/api.py`) ist read-only — kein maschineller Import von
außen möglich, nur UI-Upload (`views.py:57/103`).

### Der Bezugspunkt „Voice Agent / mPA" — definiert

**mPA = myPersonalAssistant**, erster MVP des Produkts `iil-voice-agent`
(`iil-voice-agent/docs/konzepte/KONZ-platform-006-mpa-mvp.md`; Architektur-SSoT
platform:ADR-249): modalitäts-agnostischer Agent-Core hinter drei austauschbaren
Ports (LLM/Knowledge/Voice), gesteuert von `tenant_profile.sovereignty ∈ {open, strict}`.
Zwei dort entschiedene Muster sind hier direkt einschlägig:

1. **Vorschlags-Disziplin des Mail-Agenten** (`KONZ-iil-voice-agent-003`, Stufe 2):
   das LLM **schlägt vor und bestätigt nie sich selbst**; ausgeführt wird nur
   deterministischer Code aus git-versionierten Regeln; `plan → menschliches
   Go → apply` (Ledger L5/L6/L8). Strukturell dieselbe Schleife wie hier.
2. **Souveränitäts-Gate** (`iil-voice-agent/docs/adr/ADR-003`): Profilprüfung über
   *alle* egress-fähigen Adapter (inkl. **Embedding**), `is_cloud` host-abgeleitet,
   **fail-closed**; lokales Embedding (FastEmbed, PR #54) besteht das strict-Gate.

**Das Problem:** Ein Scan, der strukturell in eine Fach-App gehört (GefBU →
risk-hub), bleibt im generischen dms-hub/d.velop-Pfad hängen. Niemand schlägt vor,
*wohin* ein Dokument gehört; keine Korrektur wird als Lernsignal genutzt; und die
Schleifen-Muster aus dem Voice-Agent-Strang würden ein zweites Mal, inkompatibel,
erfunden.

## Decision Drivers

1. **Policy `platform-agents.md`:** Cross-cutting-Agents leben in
   `dev-hub/apps/<agent_name>/` — nicht in einem Domain-Hub.
2. **Keine Klassifikator-Vervielfältigung** (heute schon drei Ansätze).
3. **Hub-Souveränität:** Fach-Apps nur über deren API/Services befüllen.
4. **Selbstlernend ab Zeile 1, aber belegt:** Feedback braucht vom ersten
   Datensatz an einen Konsumenten — und die Lernwirkung einen Messbeweis, bevor
   „lernend" behauptet wird.
5. **Ein kohärentes Lern-Muster mit dem mPA-Strang**, keine zwei Feedback-Silos.
6. **Souveränität sitzt im INHALT, nicht in der Quelle** (Rev. 2, härtester
   Review-Befund, durch den Gröger-Fund belegt): eine „eigene" Quelle kann
   Dritt-/Mandanten-Daten tragen. Kein Roh-OCR an ein Cloud-LLM, bevor ein
   Mensch oder ein Pre-Gate den Inhalt eingestuft hat — fail-closed.
7. **Revisionssichere, idempotente Wahrheit über Systemgrenzen:** Vorschlag,
   Korrektur und Import müssen über dms-hub/dev-hub/Ziel-Hub rekonstruierbar
   und duplikatfrei sein (Rev. 2).
8. **LLM-Routing-Policy** (`llm-routing.md`): Free-Tier zuerst; via aifw-Action-Codes.

## Considered Options

### Option A — Zentraler, selbstlernender Platform Agent in `dev-hub/apps/` (gewählt)

Neuer Agent `dev-hub/apps/doc_router/` nach dem `repo_health`-Bauplan
(services/tasks/llm.py-aifw-Bridge/Models), mit deterministischer Kaskade vor dem
LLM, pull-basierter Feedback-Ableitung und Retrieval-gestützter Klassifikation.

- **Pro:** Ein Klassifikator, eine Feedback-Basis, eine Ziel-Registry; folgt der
  Policy; Lern-Mechanik teilt das Muster des Mail-Agenten.
- **Contra:** Neue Service-Grenze + Auth; risk-hub braucht vorab Write-Endpoint.

### Option B — Klassifikator je Repo (verworfen)

Beantwortet „gehört das in eine *andere* App?" strukturell nicht; Feedback
fragmentiert; Taxonomien divergieren (heute schon: `ScanDocument.document_category`
Freitext vs. risk-hub `Document.Category`-Choices).

### Option C — dms-hub als zentraler Router (verworfen)

Exakt das Anti-Pattern aus `platform-agents.md`; dms-hub würde zum heimlichen
Orchestrator mit Ziel-App-Wissen über fremde Domänen.

### Option D — Vollautomatik ohne Human-Correction (verworfen als Startpunkt)

Ohne Korrektur-Schritt keine gelabelten Daten. Stattdessen: **verdiente
Automatik** je Kategorie, gated auf gemessene Qualität (s. Decision).

### Option E — Push-Feedback: dms-hub schreibt Korrekturen nach dev-hub (geprüft, verworfen)

**Refutiert:** Der Agent kennt seinen eigenen Vorschlag (er hat ihn als
unveränderliches Proposal persistiert, s. Decision) und pollt den Quell-Hub
ohnehin — Feedback ist **pull-basiert ableitbar** (finaler Wert minus Vorschlag).
dms-hub braucht null Feedback-Code. dev-hubs `OutboxMessage`
(`dev-hub/apps/core/models.py:114`, ADR-050 §6.5) dient den *Import-Kommandos*,
nicht dem Feedback — und ersetzt dort keine Idempotenz (s. Decision, Import).

### Option F — Gemeinsame Runtime mit iil-voice-agent (geprüft, verworfen)

iil-voice-agent ist ein eigenständiges *Produkt* (Port-Architektur, kein Django),
doc_router ein interner Platform Agent (Django, aifw). Erzwungene gemeinsame
Runtime überbaut beide. Gewählt: **Geschwister auf gemeinsamem Lern-Substrat**
mit benanntem Konvergenzpunkt (s. Decision).

### Weitere geprüfte Ansätze (aus externem Sparring, Rev. 2)

- **Paperless-nativer Lern-Klassifikator** (R1-OOTB-2, teilweise übernommen):
  Paperless-ngx lernt selbst document_types/Tags. Als Voll-Ersatz verworfen — er
  kennt weder Routing-Ziele noch fremde Taxonomien. Übernommen als Argument,
  **die LLM-Fläche klein zu halten**: seine Signale speisen Stufe 0 (s. u.).
- **Weak Supervision / Labeling Functions** (R1-OOTB-3, dokumentiert-verworfen):
  Overbuild bei dieser Datenmenge; die deterministische Kaskade deckt den
  nützlichen Kern (regelbasierte Labels) ohne Framework ab.
- **Externes Document-AI-Produkt** (R2-OOTB-4, dokumentiert-verworfen):
  Souveränitäts-/Egress-Konflikt (Driver 6) und dritter Klassifikations-Silo.

## Decision Outcome

**Gewählt: Option A** mit den in Rev. 2 eingearbeiteten Verschärfungen. Neuer
Agent `dev-hub/apps/doc_router/` (Arbeitstitel), aifw-Bridge mit **manuellem
Fallback** (Wording-Fix R2-AD-14: ohne aifw bleibt der Eingang manuell — der
heutige Zustand; die *Egress-Autorisierung* dagegen ist ausnahmslos
**fail-closed**, s. §Souveränität — zwei verschiedene Achsen).

### Kern-Schleife: deterministisch → classify → shadow/review → route → feedback

**Stufe 0 — Deterministische Kaskade zuerst** (R1-OOTB-1 + R2-OOTB-1, von beiden
Reviews unabhängig erhoben): Versionierte, git-geführte Regeln entscheiden vor
jedem LLM-Call — Mapping-Tabelle, `paperless_correspondent`,
`paperless_document_type`/`paperless_tags` (Paperless bringt eigenes ML-Tagging
mit). Nur der **unknown-Bucket** geht ans LLM. Das LLM muss die deterministische
Baseline in der Backlog-Messung **messbar schlagen**, sonst bleibt es bei Regeln
(dasselbe Regel-zuerst-Prinzip wie beim Mail-Agenten, KONZ-003 L5).

**Stufe 1 — Classify (LLM, nur unknown-Bucket), zweistufige Ontologie**
(R2-AD-5/REC-5): Der Erstentwurf vermischte Dokumentklasse, Zielsystem und
Ziel-Taxonomie in einem Label-Raum. Jetzt getrennt:

- Der Agent entscheidet nur die **plattform-kanonische Routing-Klasse** — klein
  und stabil, z. B. `ARCHIVE | RISK_DOCUMENT | UNKNOWN` (erweiterbar je neuem
  Ziel-Hub).
- Die **zielsystemspezifische Fach-Kategorie** (risk-hub `Document.Category`,
  d.velop-Kategorie) löst ein **versionierter Ziel-Adapter** in einem zweiten
  Schritt auf. Registry-Einträge sind versioniert und stehen in
  `drift_check_paths` statt als stille Kopie (R2-AD-6); eine formale
  Contract-Schnittstelle für Kategorien wird erst beim **zweiten** Ziel-Hub
  gebaut (right-sized).
- Cold-Start: geschlossener Klassen-Raum + Paperless-Prior — dessen Treffsicherheit
  wird in der Backlog-Messung **separat mitgemessen**, nicht unterstellt (R1-AD-8).

**Stufe 1b — Unveränderliches Proposal-Artefakt** (R2-AD-1/2/16, R1-AD-4):
*Bevor* etwas nach dms-hub zurückgeschrieben wird, persistiert der Agent ein
revisionssicheres `ClassificationProposal`: Fingerprint + Quell-Revision (Re-OCR
erzeugt neue Revision → neues Proposal, keine Überschreibung), Routing-Klasse,
Konfidenz, `prompt_version`, `registry_version`, Few-Shot-Set-Referenz,
`model_ref` — damit ist jede Entscheidung reproduzierbar (Repro-Protokoll,
R2-M28-5). **DB-Eindeutigkeit:** `unique(source_repo, source_document_id,
source_revision, proposal_version)`. Erst dann wird der Vorschlag als
`classification_method="AUTO"` + echter Konfidenz nach dms-hub gespiegelt;
Status bleibt `INBOX`.

**Stufe 2 — Shadow-Fenster, dann Human-correct** (R1-AD-2/M28-1, R2-AD-9/M28-7,
R2-OOTB-2): „Akzeptiert" ist nicht automatisch Wahrheit — ein vorbelegter
Vorschlag wird auch aus Bequemlichkeit durchgewinkt (Rubber-Stamp).

- **Blind-Eval-Fenster zuerst:** Vorschläge werden anfangs nur persistiert,
  **nicht** im UI angezeigt; der Mensch klassifiziert unabhängig wie heute.
  Übereinstimmung = belastbares Label.
- Erst danach UI-Vorbelegung im bestehenden `classify_view` (kein neues UI).
  Accepts werden nach Herkunft getrennt gespeichert (`blind` vs. `prefilled`)
  — nur blinde und stichproben-geprüfte Accepts gelten als belastbar.
- **Dauer-Stichprobe nach Aktivierung:** randomisiert wird der Vorschlag
  ausgeblendet; die Stichprobe misst fortlaufend die echte Güte-ohne-Vorbelegung.
- Disziplin wie beim Mail-Agenten: die KI bestätigt nie sich selbst (KONZ-003 L8).

**Stufe 3 — Route/Import: Anforderungen, kein Design** (R1-AD-3, R2-AD-3/4/15):

- **v0-Scope ehrlich: Vorschlag only, kein Import.** Routing ist ein eigener
  Aktivierungsschritt mit formalen Vorbedingungen:
  1. **risk-hub Write-Endpoint** hinter `upload_document`
     (`documents/services.py:52`) — Owner: **Achim Dehnert**, Zieltermin **vor
     dem Review-Gate 2026-10-31** (Terminvorschlag, vom User zu bestätigen).
     Ohne Owner+Termin ist der Kern-Nutzen unbegrenzt blockiert — deshalb hier
     benannt, nicht im PR versteckt.
  2. **Tenant-Auflösung ist Zulässigkeits-Vorbedingung**, kein Detail: kein
     Import ohne eindeutig bestimmten `tenant_id` (R2-AD-15).
  3. **Idempotenz-Pflicht:** Outbox liefert at-least-once, verhindert also
     Doppelimporte gerade *nicht* — jedes Import-Kommando trägt einen
     Idempotency-Key (Fingerprint + Proposal-ID), der Ziel-Endpoint
     **dedupliziert**; ein Reconciliation-Zustandsmodell hält dms-hub-Status,
     Outbox und Ziel-Hub konsistent (keine „drei Wahrheiten", R2-M28-1).
     Detail-Design bleibt im Import-PR (Abgrenzung).
- Ohne Ziel-App: heutiger `forward_to_dvelop`-Pfad in dms-hub, unverändert.
- **Kein direkter DB-Zugriff von dev-hub in fremde Hubs — ausnahmslos.**

**Stufe 4 — Feedback-derive (pull, Option E):** Der Agent diff't beim nächsten
Poll den finalen Wert gegen sein Proposal und persistiert:

```python
class ClassificationFeedback(models.Model):
    proposal = models.ForeignKey("ClassificationProposal", on_delete=models.PROTECT)
    # Entscheidungs-Kern (substrat-fähig, modalitäts-agnostisch):
    origin = models.CharField(max_length=10)         # live | backlog | shadow | sample
    accept_mode = models.CharField(max_length=10)    # blind | prefilled
    corrected_class = models.CharField(max_length=50, blank=True)   # leer = akzeptiert
    corrected_target = models.CharField(max_length=50, blank=True)
    corrected_by = models.CharField(max_length=100)  # Personendatum → Retention s. u.
    created_at = models.DateTimeField(auto_now_add=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    # dokumentspezifische Felder (Fingerprint, Quelle, Profil) leben im Proposal —
    # Entscheidungs-Kern und Dokument-Kontext bewusst getrennt (R2-M28-3).
```

**Retention/Löschung/Audit** (R1-AD-9, R2-M28-4): `corrected_by` ist ein
Personendatum, Fingerprint+Vorschlag+Korrektur sind ein Schattenarchiv über
Dokumentinhalte. Festgelegt: Feedback-Zeilen sind über den Fingerprint löschbar
(Löschpfad Pflicht), `corrected_by` wird nach einer Frist pseudonymisiert
(Fristlänge: User-Entscheid, Open Question), Zugriffe auf den Feedback-Store
laufen über dev-hubs bestehendes `AuditEvent` (`apps/core/models.py:86`).

### Selbstlern-Mechanik: Retrieval statt Retraining — mit Beweispflicht

Der Konsument des Feedbacks ist der Klassifikations-Prompt selbst, ab Zeile 1 —
aber die Lernwirkung wird **bewiesen, nicht behauptet** (R1-AD-6, R2-AD-12):

- **v0 (MVP):** Few-Shot-Injection aus Feedback-Zeilen. Auswahl **k-divers und
  bounded** (je Klasse begrenzt, Tokenbudget hart, nicht „die jüngsten" —
  Recency-Bias/Promptwachstum). **A/B-Beweis vor dem „lernend"-Claim:** auf dem
  Backlog-Holdout Few-Shot-Prompt gegen Klassen-Raum-only messen; kein
  signifikanter Gewinn → v0 bleibt aus, Kaskade+Zero-Shot genügen.
- **Profil-Partitionierung (harte Regel, R1-AD-7):** Prompts an Cloud-LLMs ziehen
  ausschließlich Beispiele aus `open`-ratifizierten Zeilen; als `strict`
  eingestufte Zeilen erscheinen nie in Cloud-Kontexten — auch nicht als Beispiel.
- **Metriken statt Akzeptanzquote allein** (R2-AD-7/8): Die Akzeptanzquote misst
  Nicht-Korrigieren, nicht Richtigkeit. Automatik-Gates rechnen auf
  **Confusion-Matrix, Precision/Recall und Abstain-Rate je Routing-Klasse** aus
  belastbaren Labels (blind/sample), mit **Mindestfallzahl je Klasse**.
  LLM-„Konfidenz" ist unkalibriert — sie dient nur zur Ordnung und für
  Abstain-Schwellen, nie als Wahrscheinlichkeit.
- **Review-Gate:** 200 **Live**-Zeilen (origin=`live`; Backlog-Zeilen zählen
  nicht, R1-AD-10) oder 2026-10-31, was zuerst eintritt — Agent liefert den
  Metriken-Report, der User entscheidet über v1/Einstellung.
- **v0→v1 messbar** (R2-M28-8): v1 (Corrections-as-Few-Shot-Retrieval — lokale
  FastEmbed-Embeddings, exakt der Adapter, der im voice-agent das strict-Gate
  besteht, ADR-003/PR #54 — über den Orchestrator-pgvector) startet erst, wenn
  (a) die Live-Precision je Klasse über zwei aufeinanderfolgende 50er-Fenster um
  <2 pp steigt, obwohl der Feedback-Pool wächst, ODER (b) die k-diverse Auswahl
  das Tokenbudget reißt. **Vorbedingung v1:** eigener, isolierter
  pgvector-Namespace für doc_router (R1-M28-4) — keine Vermischung mit
  Klickdummy-/Orchestrator-Kollektionen.
- **Verdiente Automatik:** Auto-Route (AUTO → `CLASSIFIED` ohne Review) je
  Klasse erst, wenn die o. g. Metriken über N belastbaren Fällen eine Schwelle
  halten UND die Dauer-Stichprobe aktiv ist. Schwelle/N: User-Entscheid nach
  erstem Report.

### Bootstrap: der 304-Dokumente-Backlog — nüchtern eingesetzt

Der Backlog ist ein gelabelter Startdatensatz, aber (R2-AD-11) **Ordnerpfade sind
Ablagekonvention, nicht Klassen-Wahrheit** — die Baseline wird explizit als
„historisch/optimistisch" geführt, nicht als Prod-Accuracy verkauft (R1-AD-5).

- **Stratifizierter Holdout** (R1/R2): ein je Klasse geschichteter Teil wird
  ausschließlich zum Messen benutzt und **nie** in den Few-Shot-Pool gelegt —
  sonst misst die Eval das Auswendiglernen.
- Gemessen werden getrennt: deterministische Kaskade, Paperless-Prior,
  Zero-Shot-LLM, Few-Shot-LLM (A/B) — erst diese Messung rechtfertigt, welche
  Stufen live gehen.
- Backlog-Zeilen tragen `origin="backlog"` und zählen nicht ins Review-Gate.
- Vorbedingung bleibt das Taxonomie-Mapping Ordner→Routing-Klasse (User,
  Open Question 2). **Achtung Souveränität:** der Backlog enthält
  Mandanten-Dokumente (Gröger-Fund) — die Bootstrap-Messung selbst unterliegt
  dem Pre-Gate der nächsten Sektion.

### Souveränität: Inhalt schlägt Quelle — fail-closed (Rev. 2, umentschieden)

Der Erstentwurf profilierte je *Quelle* und erklärte den Scan-Eingang zu `open`.
**Das ist durch den Gröger-Fund falsifiziert** — die Quelle „eigener Scanner"
sagt nichts über den Inhalt; 2000 Zeichen Roh-OCR wären an ein Cloud-LLM
gegangen, bevor je ein Mensch den Inhalt gesehen hat (R1-AD-1, R2-AD-13).
Neu entschieden:

1. **Default = strict.** Jede Quelle und jedes Dokument gilt als
   Dritt-/Mandanten-Daten-haltig, bis das Gegenteil festgestellt ist —
   fail-closed, dieselbe Richtung wie voice-agent ADR-003 (`is_cloud`-Default
   CLOUD, unbekannt = abgelehnt).
2. **Zwei zulässige Wege zum LLM-Call:**
   - **Lokale Inferenz** — existiert in der Org bereits (Ollama-lokal trägt
     u. a. den `/adr-challenger`-Review-Fluss); Stufe-0-Kaskade + lokales Modell
     für den unknown-Bucket ist der souveräne Default-Pfad; oder
   - **Content-Pre-Gate vor Cloud:** eine PII-/Mandanten-Erkennung (bzw.
     Redaktion) stuft das Einzeldokument ein; nur als unkritisch eingestufte
     Inhalte dürfen an Cloud-LLMs (aifw/Groq). Toolwahl: eigener PR (Abgrenzung).
3. **`open` je Quelle ist eine explizite Owner-Ratifikation, kein Default** —
   dokumentiert im Registry-Eintrag. Für den dms-hub-Scan-Eingang: **Ratifikation
   durch Owner ausstehend** (und nach Aktenlage nicht pauschal erteilbar,
   s. Gröger).
4. **Embedding fällt unter dasselbe Gate** (Lücke 1 aus ADR-003 nicht
   wiederholen): v1-Embeddings sind lokal (FastEmbed); die Partitionierungsregel
   des Few-Shot-Pools (s. o.) gilt zusätzlich.
5. **Wording:** die aifw-Bridge ist „manueller Fallback" (Verfügbarkeits-Achse);
   die Egress-Autorisierung ist ausnahmslos fail-closed (Souveränitäts-Achse) —
   der frühere „fail-open"-Begriff wird nicht mehr verwendet (R2-AD-14).

### Verhältnis zu mPA/Voice-Agent: Geschwister auf gemeinsamem Lern-Substrat

**Entschieden:** doc_router und mPA sind **Geschwister, keine gemeinsame Runtime**
(Option F verworfen). Geteilt wird das Muster, nicht der Prozess:

| Geteilt | Quelle des Musters |
|---|---|
| Schleifen-Form: KI schlägt vor, bestätigt nie sich selbst, Mensch entscheidet, Ausführung deterministisch | Mail-Agent Stufe 2, KONZ-003 L5/L6/L8 |
| Souveränitäts-Gate inkl. Embedding, fail-closed, Inhalt vor Quelle | voice-agent ADR-003 + dieses ADR §Souveränität |
| Lokales Embedding (FastEmbed) + pgvector als Retrieval-Substrat | ADR-003 PR #54; Orchestrator-pgvector |
| LLM-Zugang über Action-Codes / Routing-Policy | aifw; `llm-routing.md` |

Das Substrat-Schema (Proposal + Feedback, `schema_version` + `origin`) ist
versioniert dokumentiert (R1-M28-2, light). **Konvergenzpunkt
(Zweiter-Konsument-Regel):** Sobald Mail-Agent Stufe 3 oder mPA Korrektur-Capture
braucht, wird das Substrat in ein gemeinsames Schema/Package extrahiert — dann,
und erst dann, mit Contract-Test. Bis dahin dev-hub-lokal, kein spekulatives
Shared-Package.

## Consequences

**Positiv:** Ein Ort für Klassifikation, Routing-Registry und Feedback; Feedback
hat ab Zeile 1 einen Konsumenten und die Lernwirkung eine Beweispflicht (A/B);
Baseline existiert vor dem ersten Live-Vorschlag; dms-hub braucht für Feedback
null Änderungen; Souveränität ist fail-closed ab Commit 1 statt Nachrüstung;
jede Entscheidung ist über das Proposal-Artefakt reproduzierbar.

**Betriebs-Klarstellung** (R2-M28-6, teils Missverständnis des Reviews): der
d.velop-Fluss läuft vollständig **in dms-hub** weiter — fällt dev-hub aus, ist
der Zustand exakt der heutige manuelle Betrieb, kein Dokumentverlust. Valid
bleibt der Restpunkt: der Agent exponiert minimale Health-/Reconciliation-Metriken
(Backlog-Tiefe, Proposal-Alter, Import-Queue-Zustand).

**Negativ / Risiko:**

- **v0 liefert bewusst weniger als die Vision:** Vorschlag only — der Import
  hängt an der terminierten risk-hub-Vorbedingung (Owner: Achim, Ziel
  2026-10-31); ohne sie bleibt der Kern-Nutzen Teilmenge.
- **Kein Celery-Verlass in risk-hub** (`.delay()` läuft in Prod nie — bekannte
  Drift-Lektion): Import synchron oder via Outbox-Publisher.
- **Konfidenz-Semantik in dms-hub:** heute `MANUAL`+`1.0`; UI/Filter mit
  impliziter `confidence==1.0`-Annahme vor Rollout prüfen.
- **Souveränitäts-Kosten:** lokaler Inferenz-Pfad bzw. Pre-Gate kostet Qualität
  oder Latenz gegenüber „einfach Cloud" — bewusst in Kauf genommen (Driver 6).
- **Backlog-Label-Qualität:** Ordnerpfade ≈ Konvention; Baseline nur so gut wie
  das Mapping.
- Neue Auth-Beziehung dev-hub↔dms-hub↔risk-hub — Security-Config-Gate.

**Geprüft und verworfen (für künftige Challenger):** Push-Feedback/Quell-Outbox
(→ Pull-Ableitung, Option E); Fine-Tuning/Retraining-Pipeline (→ Retrieval, erst
bei nachgewiesener Sättigung neu bewerten); gemeinsame Runtime mit
iil-voice-agent (Option F); Weak Supervision; externes Document-AI-Produkt.

## Externes Sparring (Audit, 2026-07-14)

Zwei externe adversariale Reviews (Provider vom User nachzutragen), beide Verdikt
**„überarbeiten"**; Volltexte + ID-Mapping:
`~/shared/adr-handoff-ADR-276-2026-07-14-response.md`. Konsolidiert:

| # | Thema | Verdikt | Änderung |
|---|---|---|---|
| 1 | Inhalts-PII vs Quell-Profil | valid (härtester Befund, Gröger-belegt) | §Souveränität umentschieden: Default strict, Pre-Gate/lokal, Owner-Ratifikation |
| 2 | Rubber-Stamp-Accepts | valid | Blind-Fenster, accept_mode, Dauer-Stichprobe, Mindestfallzahl |
| 3 | risk-hub-Vorbedingung owner-los | valid | Owner+Termin benannt; v0 = Vorschlag only; Tenant = Zulässigkeit |
| 4 | Proposal-Unveränderlichkeit/Unique | valid | ClassificationProposal + Revisionen + Unique-Constraint |
| 5 | Import-Idempotenz/Reconciliation | valid, right-sized | Als benannte Anforderung; Design im Import-PR |
| 6 | Zweistufige Ontologie | valid | Routing-Klasse kanonisch klein; Fach-Kategorie via versionierten Adapter |
| 7 | Registry-Drift | valid, light | Versionierte Einträge + drift_check; Contract erst beim 2. Ziel |
| 8 | Konfidenz unkalibriert | valid | Gates auf Confusion/Precision/Recall/Abstain; confidence nur ordinal |
| 9 | Backlog Holdout/Gate/Optimismus | valid | Stratifizierter Holdout; origin-Feld; Gate zählt nur live; Label „historisch" |
| 10 | Few-Shot unbelegt/Auswahl/Repro | valid | A/B-Pflicht; k-divers + Tokenbudget; Repro via Proposal |
| 11 | Profil-Partitionierung Pool | valid | Harte Regel: open-Prompts nur open-Beispiele |
| 12 | Paperless-Prior ungemessen | valid, mittel | In Bootstrap-Messung aufgenommen |
| 13 | corrected_by PII/Retention | valid | Retention-/Lösch-/Audit-Absatz |
| 14 | „fail-open"-Wording | valid | „manueller Fallback"; Egress ausnahmslos fail-closed |
| 15 | Konvergenz ohne Zahn | valid, light | Schema versioniert + origin; Contract-Test beim 2. Konsumenten |
| 16 | pgvector-Namespace | valid | v1-Vorbedingung |
| 17 | Deterministische Kaskade zuerst | valid (beide Reviews) | Stufe 0; LLM nur unknown-Bucket; muss Baseline schlagen |
| 18 | Shadow Mode | valid, teilweise | In Thema 2 integriert (Blind-Fenster) |
| 19 | Paperless-nativer Klassifikator | teilweise valid | Als „LLM-Fläche klein halten" dokumentiert |
| 20 | Weak Supervision | dokumentiert-verworfen | 1 Satz in Considered Options |
| 21 | Externes Document-AI-Produkt | dokumentiert-verworfen | 1 Satz in Considered Options (Souveränität) |
| 22 | dev-hub-Kritikalität | teilweise missversteht-Kontext | Klargestellt (d.velop läuft in dms-hub); Rest: Health-Metriken-Zeile |
| 23 | Feedback generisch vs spezifisch | valid, light | Entscheidungs-Kern vs Dokument-Felder getrennt (Proposal/Feedback) |
| 24 | v0→v1 unscharf | valid | Messbare Kriterien (<2 pp/2×50er-Fenster ODER Tokenbudget) |

## Open Questions / bewusst aufgeschoben

1. **Owner-Ratifikation Quellprofil (nur User):** Bleibt der Scan-Eingang strict
   (lokaler Pfad) oder wird ein Content-Pre-Gate gebaut, das Cloud-Calls je
   Dokument freigibt? `open` pauschal ist nach dem Gröger-Fund nicht erteilbar.
2. **Backlog-Taxonomie (nur User):** Mapping NAS-Ordner → Routing-Klassen; ohne
   das keine Baseline-Messung.
3. **Retention-Frist** für `corrected_by`-Pseudonymisierung (User).
4. **Schwelle/N für verdiente Automatik:** User-Entscheid nach erstem
   Metriken-Report.
5. **risk-hub Write-Endpoint:** Zieltermin 2026-10-31 bestätigen (User) —
   Design/PR im risk-hub.
6. **Provider-Namen** der zwei externen Reviews im Frontmatter nachtragen (User).
7. **Konvergenz mit mPA/Mail-Agent:** ausgelöst durch Zweiter-Konsument-Regel.
8. **Agent-Name:** `doc_router` ist Arbeitstitel.

## Abgrenzung

Dieses ADR entscheidet **Ort (dev-hub/apps/), Schnittstellen-Prinzip (Hub-APIs
wrappen, keine DB-Reach-Ins), die Schleifen-Form (deterministische Kaskade →
LLM-Vorschlag → Blind/Review → Proposal-Artefakt → Pull-Feedback →
Retrieval-Lernen mit Beweispflicht), die Souveränitäts-Regel (Inhalt vor Quelle,
fail-closed) und das Geschwister-Verhältnis zum mPA-Strang.** Kein
Implementierungsplan. In eigene PRs/Konzepte verschoben: Prompt-Design,
Registry-/Adapter-Format, Polling-Mechanik, risk-hub-Write-API inkl.
Tenant-Auflösung, Import-State-Machine/Reconciliation-Design, Wahl des
PII-Pre-Gate-Tools, Kategorien-Contract beim zweiten Ziel-Hub, Backlog-Import.
Der d.velop-Pfad und die Paperless-Ingestion werden nicht angefasst; am
iil-voice-agent-Repo ändert dieses ADR nichts.
