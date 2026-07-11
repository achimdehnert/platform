---
id: ADR-272
title: "Anchor the adaptive text-improvement feedback loop in iil-promptfw"
status: proposed
decision_date: 2026-07-11
deciders:
  - "Achim Dehnert"
consulted: []
informed: []
domains:
  - shared-packages
  - llm
  - prompt-management
tags: [promptfw, aifw, feedback-loop, hitl, writing-hub, risk-hub, adaptive]
related:
  - "ADR-146"
  - "ADR-188"
  - "ADR-259"
---

<!--
  ADR-TEMPLATE v2.0 (2026-02-21)
  Basis: MADR 4.0 + Platform-Governance (ADR-021, ADR-046, ADR-056, ADR-059)
  Struktur gemäß ADR-271 (MADR-4.0-Scaffold, englische Überschriften)
-->

# ADR-272: Anchor the adaptive text-improvement feedback loop in `iil-promptfw`

## Metadaten

| Attribut          | Wert                                                                 |
|-------------------|----------------------------------------------------------------------|
| **Status**        | Proposed                                                             |
| **Scope**         | shared (Package-Evolution `iil-promptfw`, Konsumenten: writing-hub, risk-hub) |
| **Erstellt**      | 2026-07-11                                                           |
| **Autor**         | Achim Dehnert (Entscheid) / Claude (Ausarbeitung, Evidenz-Checks)    |
| **Reviewer**      | –                                                                    |
| **Supersedes**    | –                                                                    |
| **Superseded by** | –                                                                    |
| **Relates to**    | ADR-146 (Hub-Prompt-Management), ADR-188 (writing-hub HITL Vorschlag→Diff→Accept/Reject), ADR-259 (repo-scoped ADR-IDs, Kontext iil-adrfw) |

## Repo-Zugehörigkeit

| Repo           | Rolle    | Betroffene Pfade / Komponenten                                        |
|----------------|----------|------------------------------------------------------------------------|
| `iil-promptfw` | Primär   | neues Modul `feedback` (Schema + Präferenz-Store), Render-Hook in `renderer`/`stack`, `contrib.django`-Modelle |
| `aifw`         | Referenz | `LLMResult.call_id` (REC-10) als Join-Key Vorschlag↔Call↔Feedback — keine Änderung nötig, PR aifw#33 liefert das Feld |
| `writing-hub`  | Sekundär (Pilot) | Signal-Quellen: `LektoratIssue` (Beheben/Überspringen/Erledigt), `OutlineQualityRating`, ADR-188-HITL (`LectureProposal` Accept/Reject); Injection in bestehende promptfw-Aufrufe (10+ Services) |
| `risk-hub`     | Sekundär (2. Welle) | Ex-Schutz-Textgenerierung/-optimierung auf Basis mitgegebener Unterlagen: `src/explosionsschutz/doc_template_views.py`, `src/ai_analysis/{prompts,services}.py` |

---

## Decision Drivers

- **Rule of Two erfüllt — die Abstraktion ist nicht mehr spekulativ**: Zwei Domain-Hubs
  brauchen dieselbe Fähigkeit „Text erzeugen/optimieren, adaptiv an Nutzer-Feedback".
  writing-hub (Lektorat, Refine, HITL) und risk-hub (Ex-Schutz-Dokumente aus Unterlagen,
  verifiziert: `iil-promptfw>=0.8.0` in `pyproject.toml:46`, Nutzung in
  `explosionsschutz/doc_template_views.py`).
- **Die Feedback-Signale existieren bereits, werden aber nirgends ausgewertet**
  (verifiziert 2026-07-10/11 gegen writing-hub main):
  - `LektoratIssue.fix_text` + Beheben/Überspringen/Erledigt-Aktionen — erhoben, nicht ausgewertet
  - `OutlineQualityRating` — 1–5-Rating mit FK auf `OutlinePromptTemplate`-Version; der
    Docstring verspricht wörtlich einen „Prompt-Tuning-Feedback-Loop zu ermöglichen" —
    der Loop ist nicht geschlossen
  - ADR-188 B2 (writing-hub PR #146, gemergt 2026-07-07): HITL Vorschlag→Diff→Accept/Reject
    für Lectures — das sauberste Accept/Reject-Signal im Bestand
- **`iil-promptfw` v0.8.1 hat null Feedback-Konzept** (verifiziert per Modul-Scan
  2026-07-11: keine Treffer für feedback/rating/preference/accept in den Package-Quellen).
  Module: `concept_analysis, contrib, db_resolver, django_registry, exceptions,
  frontmatter, lektorat, parsing, planning, registry, renderer, schema, stack, writing`.
- **Der Join-Key ist frisch verfügbar**: aifw REC-10 (`LLMResult.call_id` = `AIUsageLog`-PK,
  aifw PR #33) macht Vorschlag ↔ LLM-Call ↔ Feedback erstmals verkettbar. risk-hub hat
  bereits einen aifw-Contract-Test (`src/tests/contracts/test_aifw_contract.py`).
- **Policy-Konformität**: Nach `platform-agents.md`-Entscheidungsbaum ist eine von zwei
  Domain-Hubs geteilte Business-Fähigkeit ein **platform package** — nicht dev-hub
  (kein Platform-Monitoring), nicht Duplikat je Hub.

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand

`iil-promptfw` (ADR-146) ist das geteilte Prompt-Management der Plattform: DB-backed,
versionierte Prompt-Stacks, von writing-hub in 10+ Services und von risk-hub für
Ex-Schutz-Dokumente und AI-Analysen konsumiert. Die Hubs erzeugen damit KI-Textvorschläge
(Lektorat-Korrekturen, Kapitel-Refines, Ex-Schutz-Dokumentabschnitte) und erheben
teilweise strukturiertes Nutzer-Feedback dazu (Accept/Reject/Skip/Rating).

Dieses Feedback versickert heute: Es wird gespeichert (writing-hub: drei Tabellen),
aber kein System liest es zurück. Jeder neue Vorschlag startet bei null — der Nutzer
lehnt dieselbe Art Korrektur zum zwanzigsten Mal ab, und der zwanzigste Prompt weiß
nichts davon. „Adaption" existiert nur statisch (Stilprofile im Style Lab,
Content-Type-Dispatch in `OutlinePromptTemplate`), nicht lernend.

### 1.2 Warum jetzt

Drei Dinge sind in derselben Woche zusammengekommen (Stand 2026-07-11):

1. ADR-188 B2 liefert das erste saubere Accept/Reject-Signal in Produktion (writing-hub).
2. aifw REC-10 liefert den `call_id`-Join-Key (PR #33).
3. Der risk-hub-Bedarf (Ex-Schutz-Texte aus Unterlagen optimieren) macht aus einem
   writing-hub-Feature eine geteilte Fähigkeit — und damit aus „wo bauen?" eine
   Architekturfrage, die vor dem ersten Code entschieden werden sollte, nicht danach.

Ohne Entscheidung passiert das Übliche: jeder Hub baut seine eigene Präferenz-Logik,
und in sechs Monaten existieren zwei inkompatible Feedback-Schemata.

---

## 2. Considered Options

### Option A: Adaptions-Loop als `iil-promptfw`-Modul (Feedback-Schema + Präferenz-Store + Render-Injection) ✅

Das Package bekommt drei kleine, generische Bausteine:

1. **Feedback-Schema** (`promptfw.feedback`): ein Ereignis
   `{scope, user, prompt_ref, call_id, verdict, category?, payload?}` —
   `verdict ∈ {accepted, rejected, skipped, rated}`. Django-Modell in `contrib.django`.
2. **Präferenz-Store**: aggregiertes Profil pro `(user, scope)` — z. B. „lehnt
   Passiv-Umformungen ab", „akzeptiert Terminologie-Fixes". Erste Version: einfache
   Aggregation (Zähler je Kategorie + jüngste N Ablehnungsgründe), **kein** ML.
3. **Render-Injection**: optionaler Hook im Renderer/Stack, der aus dem Profil einen
   Präferenz-Block generiert und in den System-/Kontext-Teil bestehender Prompts einfügt.

Die Hubs liefern nur: Signal-Adapter (bestehende Tabellen → Feedback-Events) und die
`scope`-Definition (writing-hub: Projekt/Autor; risk-hub: Anlage/Dokumenttyp).

- **Gut**: eine Implementierung, zwei Konsumenten; nutzt vorhandene Signale; kein
  Training/keine Modellkosten; `call_id`-Verkettung von Tag 1; Domain-Logik bleibt draußen.
- **Schlecht**: Package-API-Erweiterung (SemVer-Minor), Koordination über 3 Repos;
  Präferenz-Aggregation muss bewusst simpel starten, sonst Scope-Explosion.

### Option B: Je Hub eine eigene Adaptions-Schicht

- **Gut**: keine Cross-Repo-Koordination, jeder Hub maximal frei.
- **Schlecht**: verletzt Rule of Two bei bereits zwei bekannten Konsumenten; doppeltes
  Schema, doppelte Bugs; das writing-hub-HITL-Muster müsste für risk-hub ohnehin
  nachgebaut werden — nur eben als Kopie.

### Option C: Eigenständiger „Text-Verbesserer-Agent" in dev-hub

- **Gut**: zentrale Stelle, Dashboard-Anschluss.
- **Schlecht**: klarer Policy-Verstoß (`platform-agents.md`): dev-hub ist für
  Platform-Monitoring, nicht für Business-Fähigkeiten. Text-Verbesserung für Romane
  und Ex-Schutz-Dokumente ist Domain-Arbeit. Zusätzlich: ein Agent, der in fremde
  Hub-Daten schreibt, wäre genau das Cross-Repo-Write-Muster, das das Gate
  `autonomous-no-human-review` adressiert.

### Option D: Adaption in `aifw` statt `promptfw`

- **Gut**: aifw hat schon das Call-Log und (mit REC-10) die IDs.
- **Schlecht**: aifw ist Transport/Routing/Logging — es weiß nichts über Prompt-Semantik
  und soll das auch nicht (Schichtentrennung aus ADR-146). Präferenzen sind
  Prompt-Inhalt, nicht Call-Metadaten. aifw bleibt Referenz (Join-Key), nicht Ort.

### Option E: Direkt Prompt-/Modell-Auto-Tuning (Ratings → automatische Template-Iteration)

- **Gut**: maximaler Automatisierungsgrad.
- **Schlecht**: verfrüht — es gibt noch keine Baseline-Messung, ob simple
  Präferenz-Injection bereits reicht; teuer; und automatische Prompt-Mutation ohne
  Human-Review wäre ein neues Governance-Thema für sich. Kann später als Folge-ADR
  kommen, wenn Stufe-2-Daten (siehe Rollout) es rechtfertigen.

---

## 3. Decision Outcome

**Gewählt: Option A** — der adaptive Loop (Vorschlag → Feedback → Präferenz →
Prompt-Injection) wird als generisches Modul in `iil-promptfw` verankert; `aifw` liefert
per `call_id` die Verkettung; die Hubs liefern Signale, Scope und UI.

Bewusste Grenzen der Entscheidung:

- **Kein ML, kein Fine-Tuning, keine automatische Template-Mutation** in dieser Stufe —
  nur deterministische Aggregation + Kontext-Injection.
- **Kein Grounding/RAG im Package**: Das Einlesen mitgegebener Unterlagen (risk-hub)
  bleibt Domain-Pipeline im Hub. promptfw adaptiert *wie* formuliert wird, nicht
  *woraus* generiert wird.
- **Keine Cross-User-Aggregation** initial (ein Profil je `(user, scope)`) — vermeidet
  die Privacy-Diskussion, bis der Nutzen bewiesen ist.

### 3.1 Rollout in drei Stufen mit Beweis-Gate

1. **Stufe 1 — Package**: `promptfw.feedback` (Schema, Store, Injection-Hook) als
   SemVer-Minor (0.9.0), mit eigenen Tests, ohne Hub-Abhängigkeit.
2. **Stufe 2 — Pilot writing-hub**: ADR-188-Accept/Reject als erste Signal-Quelle
   (frischeste, sauberste Daten), Injection in den Lectures-/Lektorat-Pfad.
   **Gate: messbare Verbesserung der Akzeptanzquote** (siehe §8) — ohne Beweis kein
   weiterer Rollout.
3. **Stufe 3 — risk-hub/Ex-Schutz**: Signal-Adapter + HITL-UI nach ADR-188-Muster
   (im sicherheitsrelevanten Ex-Schutz-Kontext ist Accept/Reject ohnehin Pflicht,
   nicht Option).

---

## 4. Implementation Details

### 4.1 `iil-promptfw` (Stufe 1)

- `promptfw/feedback/schema.py`: `FeedbackEvent`-Dataclass + Verdict-Enum
- `promptfw/contrib/django/models.py`: `PromptFeedbackEvent`, `PromptPreferenceProfile`
  (JSON-Feld für Aggregat; `(user, scope)` unique)
- `promptfw/feedback/aggregate.py`: `update_profile(event) -> profile` — reine Funktion,
  Zähler je Kategorie + Ring-Puffer der letzten N Rejection-Begründungen
- Renderer-Hook: `render(..., preference_profile=None)` — erzeugt bei Übergabe einen
  klar abgegrenzten Block (`## Nutzer-Präferenzen` o. ä.) im System-Kontext
- Versionierung: 0.9.0; bestehende Aufrufer unverändert lauffähig (Hook ist opt-in)

### 4.2 writing-hub (Stufe 2, Pilot)

- Signal-Adapter: Django-Signal/Service-Aufruf an den drei bestehenden Stellen
  (ADR-188-Decision, `LektoratIssue`-Aktionen, `OutlineQualityRating.save`)
- Injection an den promptfw-Render-Stellen der betroffenen Services
- `call_id`-Durchreichung: setzt aifw PR #33 (REC-10) voraus — Merge dort ist
  Vorbedingung für die Verkettung, nicht für den Loop selbst

### 4.3 risk-hub (Stufe 3)

- Gleicher Adapter, Scope = (Anlage/Projekt, Dokumenttyp)
- HITL-Accept/Reject-UI nach ADR-188-Muster für Ex-Schutz-Textvorschläge

---

## 5. Rollout Tracking

| Stufe | Repo | Artefakt | Status |
|-------|------|----------|--------|
| 1 | iil-promptfw | `feedback`-Modul, 0.9.0 | offen |
| 2 | writing-hub | Signal-Adapter + Injection (Pilot Lectures/Lektorat) | offen |
| 2-Gate | writing-hub | Akzeptanzquote-Messung (Baseline vs. mit Injection) | offen |
| 3 | risk-hub | Ex-Schutz-Adapter + HITL-UI | offen (gated durch 2) |

---

## 6. Consequences

### 6.1 Good

- Vorhandene, heute versickernde Feedback-Daten werden erstmals genutzt
- Ein Schema statt (absehbar) zwei inkompatibler je Hub
- ADR-188-HITL-Muster wird Plattform-Muster statt writing-hub-Spezialität
- Vollständige Nachvollziehbarkeit Vorschlag→Call→Feedback über `call_id`

### 6.2 Bad

- Drei-Repo-Koordination für ein Feature (Package-Release + zwei Hub-Integrationen)
- Prompt-Verlängerung durch Präferenz-Block → marginal höhere Token-Kosten pro Call
- Präferenz-Profile sind nutzerbezogene Daten → Lösch-/Export-Pfad nötig (§7)

### 6.3 Nicht in Scope

- Grounding/RAG der Quell-Unterlagen (bleibt risk-hub-Domain-Pipeline)
- Automatisches Prompt-/Modell-Tuning (Option E — ggf. Folge-ADR nach Stufe-2-Daten)
- Cross-User-/Team-Präferenzen
- Ersatz der statischen Adaption (Style Lab, Content-Type-Dispatch bleiben unberührt)

---

## 7. Risks

| Risiko | Einschätzung | Gegenmaßnahme |
|--------|--------------|---------------|
| Feedback-Sparsity: zu wenige Events für sinnvolle Profile | mittel | Pilot auf dem Pfad mit dichtestem Signal (ADR-188 Lectures); Gate in §8 misst genau das |
| Präferenz-Drift: altes Feedback dominiert, Nutzer hat sich geändert | mittel | Ring-Puffer + Recency-Gewichtung von Anfang an im Aggregat |
| Prompt-Bloat: Präferenz-Block frisst Kontextfenster | niedrig | Harte Obergrenze (z. B. 10 Einträge) im Renderer-Hook |
| DSGVO: nutzerbezogene Verhaltensprofile | mittel | Profil hängt an `(user, scope)`, Kaskaden-Delete am User, Export als JSON trivial; keine Cross-User-Aggregation |
| Ex-Schutz-Fehladaption: Präferenz überschreibt Compliance-Anforderung | **hoch** | Injection in risk-hub nur in Stil-/Formulierungsebene, nie in fachliche Constraints; HITL-Pflicht bleibt davor; explizit in Stufe-3-Design zu verankern |
| Package-API-Bruch für Bestandsnutzer | niedrig | Hook strikt opt-in, 0.9.0 SemVer-Minor, Contract-Test in risk-hub existiert bereits als Vorbild |

---

## 8. Confirmation

Das ADR gilt als validiert, wenn:

1. `iil-promptfw` 0.9.0 released ist und alle Bestands-Aufrufer (writing-hub 10+
   Services, risk-hub) ohne Codeänderung grün bleiben (Contract-Tests)
2. In writing-hub ein vollständiger Loop in Produktion geschlossen ist:
   ein ADR-188-Reject erzeugt ein `PromptFeedbackEvent`, das Profil ändert sich,
   der nächste Vorschlag desselben Scopes enthält den Präferenz-Block
3. **Beweis-Gate für Stufe 3**: Akzeptanzquote der Vorschläge im Pilot-Pfad wird
   über ≥ 4 Wochen gemessen; Rollout nach risk-hub nur bei nachweisbarer Verbesserung
   gegenüber der Baseline (sonst: ADR-Review, ggf. Superseding)
4. Kill-Kriterium: Zeigt Stufe 2 bis **2026-10-31** keine messbare Verbesserung,
   wird das Modul auf „Feedback-Erfassung ohne Injection" zurückgeschnitten
   (Daten sammeln bleibt wertvoll, Adaption wird neu bewertet)

---

## Glossar

| Begriff | Bedeutung |
|---------|-----------|
| **HITL** | Human-in-the-Loop — KI-Vorschlag wird von einem Menschen geprüft (Accept/Reject), bevor er wirksam wird |
| **promptfw** | `iil-promptfw` — geteiltes Prompt-Management-Package der Plattform (ADR-146) |
| **aifw** | Geteiltes LLM-Routing-/Logging-Package; protokolliert jeden LLM-Call in `AIUsageLog` |
| **call_id** | Primärschlüssel des `AIUsageLog`-Eintrags eines LLM-Calls; seit REC-10 (aifw PR #33) am `LLMResult` verfügbar |
| **Ex-Schutz / ATEX** | Explosionsschutz — sicherheitsrelevante Arbeitsschutz-Domäne in risk-hub; Dokumente unterliegen fachlichen Pflichtinhalten |
| **Präferenz-Block** | Vom Profil generierter Prompt-Abschnitt („Nutzer lehnt X ab, bevorzugt Y"), der in den System-Kontext injiziert wird |
| **Rule of Two** | Heuristik: eine geteilte Abstraktion erst bauen, wenn mindestens zwei reale Konsumenten existieren |
| **Grounding / RAG** | Generierung auf Basis mitgelieferter Quelldokumente (Retrieval-Augmented Generation) |
| **SemVer-Minor** | Versionssprung, der Funktionen hinzufügt, ohne Bestehendes zu brechen (0.8.x → 0.9.0) |

---

## 9. More Information

- ADR-146 — Hub-Prompt-Management (Basis-Entscheidung für promptfw)
- ADR-188 (writing-hub) — HITL Vorschlag→Diff→Accept/Reject (Muster + erste Signal-Quelle)
- aifw PR #33 — REC-10 `LLMResult.call_id` (Join-Key; offen, Vorbedingung für Verkettung)
- writing-hub: `apps/projects/models.py` (`LektoratIssue`), `apps/outlines/models.py`
  (`OutlineQualityRating` mit Template-Versions-FK)
- risk-hub: `src/explosionsschutz/doc_template_views.py`, `src/ai_analysis/{prompts,services}.py`
- Policies: `platform-agents.md` (Entscheidungsbaum), `llm-routing.md` (Groq-first)

## 10. Changelog

| Datum | Änderung |
|-------|----------|
| 2026-07-11 | Initial (Proposed) — Ausarbeitung nach Owner-Freigabe („ja go"), Evidenz-Checks gegen writing-hub main, risk-hub main, iil-promptfw 0.8.1 |
