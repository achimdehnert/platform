---
status: proposed
date: 2026-06-12
decision-makers: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-243]
implementation_status: none
last_reviewed: 2026-06-12
staleness_months: 6
tags: [llm-routing, aifw, cost-governance, provider-policy, failover, groq-first]
---

# ADR-245: LLM-Routing-Policy als Code — Provider-Policy-Engine in iil-aifw (free-tier-first mit Auto-Failover)

> **Nummern-Hinweis:** 245 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert zur
> Merge-Zeit (ADR-228).

| Attribut       | Wert                                              |
|----------------|----------------------------------------------------|
| **Status**     | Proposed                                          |
| **Scope**      | platform (org-weite Routing-Konvention) · Implementierung in `aifw` |
| **Repo**       | platform (Entscheidung) · aifw (Code)             |
| **Erstellt**   | 2026-06-12                                        |
| **Autor**      | Achim Dehnert                                     |
| **Reviewer**   | –                                                 |
| **Supersedes** | –                                                 |
| **Relates to** | ADR-243 (corefw-Fehlerkategorien als Failover-Vorbedingung) |

---

## 1. Kontext

### 1.1 Ausgangslage

Die Org-Policy `~/.claude/policies/llm-routing.md` („Groq free-tier first, paid only with
justification") ist **Text, nicht Code**. In aifw — der Primär-LLM-Integration aller Hubs
(bfagent, authoringfw, odoo-hub, writing-hub) — sieht die Realität so aus (verifiziert
2026-06-12):

- Routing = statische DB-Config: `AIActionType.default_model` + **ein** `fallback_model`
  (`service.py:196-254`, `_lookup_cascade()` ist reiner DB-Lookup).
- `LLMProvider` (`models.py:35-52`) kennt weder `priority` noch `cost_tier` — die Kette
  „erst frei, dann bezahlt" ist nicht modellierbar.
- API-Key-Auflösung hat ein hartkodiertes Fallback-Mapping nur für anthropic/openai/google
  (`service.py:411-419`).
- Erschöpfte Groq-Quota ⇒ manueller Admin-Eingriff (Modell in DB umschalten).

Die Kosten-Evidenz, warum ungelenktes Routing teuer ist, liegt vor: 2026-05-12/13 liefen
$1.577 in 48 h über ein Top-Tier-Modell für überwiegend Tier-3-Arbeit (llm_calls-Tabelle,
dokumentiert in `policies/session-routing.md`).

### 1.2 Problem / Lücken

1. **Policy nicht durchsetzbar:** „free-tier first" kann heute weder erzwungen noch gemessen
   werden — es gibt kein Datenmodell dafür.
2. **Kein automatischer Failover entlang der Kosten-Achse:** ein Quota-Fehler eskaliert zum
   Menschen statt zur nächsten Stufe der Kette.
3. **Keine Auditierbarkeit:** `AIUsageLog` hält fest *was* lief, aber nicht *warum* (welcher
   Policy-Schritt, welche Begründung für paid).

### 1.3 Constraints

- Bestehende Consumer dürfen nicht brechen: `default_model`/`fallback_model` müssen als
  Degenerat-Fall (Kette der Länge 2) weiterfunktionieren.
- Failover braucht saubere Fehlerkategorien (transient/quota vs. config) — Vorbedingung
  **ADR-243** `corefw.errors`.
- Kein externes Gateway als Pflicht-Infrastruktur (Singleton-Risiko, vgl. mcp-hub-Singleton-
  Lehren); die Engine lebt in der Library.

---

## 2. Entscheidung

aifw bekommt eine **deklarative Provider-Policy-Engine**:

1. **Datenmodell:** `LLMProvider` erhält `cost_tier ∈ {free, subsidized, paid, premium}` und
   `priority: int`. Neues Modell `ProviderPolicy`: geordnete Kette von
   `(provider, model, bedingungen)`-Schritten je `action_code`-Klasse, versioniert, mit
   `requires_justification: bool` für paid-Stufen.
2. **Routing-Semantik:** `completion()` löst über die Policy-Kette auf — Schritt N+1 wird
   nur betreten bei Fehlerkategorie `TRANSIENT`/`QUOTA_LIMIT` (corefw, ADR-243) oder
   explizitem Quality-Override; `CONFIGURATION`/`AUTHORIZATION` failt sofort (kein
   Kosten-Eskalations-Bug durch Fehlkonfiguration).
3. **Org-Default als Code:** eine versionierte Default-Policy `org-groq-first-v1`
   (free → subsidized → paid) wird mit ausgeliefert; Abweichung pro Action erfordert eine
   eigene Policy mit `justification`-Feld — damit ist die llm-routing.md-Regel erzwungen
   statt erinnert.
4. **Audit:** `AIUsageLog.metadata` erhält `policy_id`, `policy_step`, `escalation_reason`.
   Damit ist „wie oft sind wir auf paid eskaliert und warum" eine Query, kein Forensik-Projekt.

**Nicht in Scope:** Session-Level-Routing von Claude Code (bleibt `session-routing.md`,
Mensch-Entscheidung); Modell-Qualitäts-Benchmarking; ein zentraler Proxy.

---

## 3. Betrachtete Alternativen

| # | Alternative | Verworfen, weil |
|---|---|---|
| A | **Status quo** (DB-Paar default/fallback + Policy als Text) | Policy nachweislich nicht gelebt (Kosten-Evidenz); Quota-Failover bleibt manuell |
| B | **LiteLLM-Router/`fallback_models` direkt nutzen** | deckt Failover, aber nicht cost_tier-Semantik, Justification-Zwang und Audit-Felder; Policy läge dann in LiteLLM-Config statt im auditierbaren Datenmodell — als *Ausführungs-Backend* der Kette aber weiter nutzbar |
| C | **Externes LLM-Gateway (litellm-proxy o. ä.)** | neuer Infrastruktur-Singleton + Betriebslast für 2-Personen-Org; Library-Ansatz erreicht dasselbe ohne neuen Prozess |
| D | **Policy nur im Orchestrator-MCP** | erreicht nur Agent-Flows; Hubs callen aifw direkt — die Engine muss dort sitzen, wo alle Calls durchlaufen |

---

## 4. Begründung im Detail

- **Regeln, die nur in Markdown existieren, driften** — dieselbe Lehre wie ADR-242
  (no-bypass als Konvention → trading-hub#13). Die Routing-Policy bekommt denselben Schritt:
  von Dokument zu Konstruktion.
- **Fehlerkategorien-Kopplung an ADR-243 ist bewusst:** ohne `QUOTA_LIMIT` als typisierte
  Kategorie müsste die Engine Provider-Fehlertexte parsen — fragil und providerspezifisch.
- **Deklarativ + versioniert** macht Policy-Änderungen reviewbar (PR auf Policy-Fixture)
  statt DB-Hand-Edits.

---

## 5. Implementation Plan

- **Phase 1 (nach ADR-243 Phase 2):** Datenmodell-Migration (`cost_tier`, `priority`,
  `ProviderPolicy`), Default-Policy `org-groq-first-v1` als Fixture, Degenerat-Kompatibilität
  (bestehende default/fallback-Paare werden automatisch als 2-Schritt-Policy interpretiert).
- **Phase 2:** Routing-Auflösung in `completion()`/`sync_completion()` inkl.
  Kategorien-gesteuertem Failover; Audit-Felder in `AIUsageLog.metadata`; Tests mit
  simulierten Quota-Fehlern.
- **Phase 3 (Pilot):** bfagent + ein writing-hub-Action-Code auf explizite Policies;
  2-Wochen-Auswertung `escalation_reason`-Verteilung.
- **Phase 4:** aifw-minor-Release; Policy-Review-Konvention (Policy-Fixture-Änderung = PR
  mit Begründung) in CORE_CONTEXT der Consumer.

---

## 6. Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R-1 | Failover-Loop bei systematischem Fehler | Kette ist endlich + `CONFIGURATION` failt sofort; max-1-Durchlauf der Kette pro Call |
| R-2 | Qualitäts-Regression durch free-first | `quality_level`-Routing (aifw 0.6+) bleibt orthogonal: Policy wählt innerhalb der zulässigen Qualitätsstufe |
| R-3 | Migration bricht bestehende Action-Configs | Degenerat-Fall ist der Default; keine Pflicht-Migration der Bestands-Configs |
| R-4 | Audit-Metadata bläht UsageLog | nur 3 Schlüssel im bestehenden JSON-Feld, keine Schema-Migration |

---

## 7. Konsequenzen

### 7.1 Positiv
- „Groq free-tier first" ist erzwungen, gemessen und auditierbar.
- Quota-Erschöpfung wird ein Routing-Ereignis statt eines Admin-Einsatzes.
- Paid-Eskalationen tragen ihre Begründung im Log — Kosten-Reviews werden Queries.

### 7.2 Trade-offs
- aifw-Komplexität steigt (ein Modell, eine Auflösungsschicht mehr).
- Harte Abhängigkeit von ADR-243-Fehlerkategorien (bewusste Sequenzierung).

### 7.3 Nicht in Scope
- Claude-Code-Session-Modellwahl; Prompt-/Quality-Tuning; Provider-Onboarding.

---

## 8. Validation Criteria

- Ein simulierter Groq-`QUOTA_LIMIT` führt im Test ohne Mensch zur nächsten Policy-Stufe;
  ein `CONFIGURATION`-Fehler eskaliert **nicht**.
- Jeder Call mit `cost_tier != free` hat `policy_id` + `escalation_reason` im UsageLog.
- Pilot-Auswertung (Phase 3) zeigt ≥95 % der Calls auf free-tier ohne Qualitäts-Regression
  in den Action-Metriken — sonst Policy-Schwellen nachziehen statt Engine verwerfen.
- Kill-Kriterium: Ist Phase 2 bis **2026-10-31** nicht in einem aifw-Release, wird der ADR
  deprecated (Policy bleibt dann ausdrücklich Text + Mensch).

---

## 9. Referenzen

- `~/.claude/policies/llm-routing.md` + `policies/session-routing.md` (Kosten-Evidenz
  $1.577/48 h).
- aifw-Code-Evidenz: `src/aifw/models.py:35-52`, `src/aifw/service.py:196-254` + `411-419`.
- ADR-243 (corefw-Fehlerkategorien), ADR-242 (Konvention→Konstruktion-Muster).

---

## 10. Changelog

- **2026-06-12:** Initial (Proposed). Aus der Tier-4/5-Analyse; sequenziert nach ADR-243.
