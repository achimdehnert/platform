---
status: accepted
decision_date: 2026-06-12
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-068, ADR-095, ADR-243]
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
| **Relates to** | ADR-095 (Quality-Level-Routing — wird erweitert, nicht ersetzt), ADR-068 (Adaptive Model Routing), ADR-243 (corefw-Fehlerkategorien als Failover-Vorbedingung) |

---

## 1. Kontext

### 1.1 Ausgangslage

Die Org-Policy `~/.claude/policies/llm-routing.md` („Groq free-tier first, paid only with
justification") ist **Text, nicht Code**. In aifw — der Primär-LLM-Integration aller Hubs
(bfagent, authoringfw, odoo-hub, writing-hub) — sieht die Realität so aus (verifiziert
2026-06-12):

- Routing = deterministischer DB-Lookup: `AIActionType.default_model` + **ein**
  `fallback_model` (`service.py:196-254`, `_lookup_cascade()`). **Wichtig:** dieser
  Lookup ist kein Unfall, sondern die bewusst reviewte ADR-095-Mechanik (Quality-Level
  1–9 → Modell, Rev-1 „B-02: deterministic lookup"). Was *fehlt*, ist die
  **Kosten-Dimension orthogonal dazu** — dieser ADR erweitert ADR-095, er repariert es nicht.
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

### 1.4 Entscheidungstreiber

- **Konvention→Konstruktion** (ADR-242-Lehre): eine Policy, die nur als Markdown existiert,
  driftet — die Kosten-Evidenz ($1.577/48 h) ist der gemessene Drift.
- **Quota-Resilienz:** Provider-Erschöpfung muss ein Routing-Ereignis sein, kein Admin-Einsatz.
- **Auditierbarkeit:** „Warum lief das auf paid?" muss eine Query sein (policy_id +
  escalation_reason im UsageLog).
- **Orthogonalität zu ADR-095:** Qualität (welches Modell genügt?) und Kosten (welcher
  Provider zuerst?) sind getrennte Achsen — heute ist nur die erste modelliert.
- **Keine neue Infrastruktur:** Library-Lösung statt Gateway-Singleton (2-Personen-Org).

---

## 2. Entscheidung

aifw bekommt eine **deklarative Provider-Policy-Engine**:

1. **Datenmodell:** `LLMProvider` erhält `cost_tier ∈ {free, subsidized, paid, premium}`,
   `priority: int` und `api_key_env: str` (Name der Env-Variable — ersetzt das hartkodierte
   Key-Mapping in `service.py:411-419`, das als deprecated Fallback bestehen bleibt).
   Neues Modell `ProviderPolicy`: geordnete Kette von `(provider, model, bedingungen)`-
   Schritten je `action_code`-Klasse, versioniert, mit `requires_justification: bool` für
   paid-Stufen. Alle Migrationen sind **expand-only** (nullable Felder + neue Tabelle,
   kein DROP/RENAME — Expand-Contract-konform).
2. **Routing-Semantik:** `completion()` löst über die Policy-Kette auf — **innerhalb der
   von ADR-095 bestimmten Qualitätsstufe** (die Kette enthält nur Schritte, deren Modell
   das geforderte `quality_level` erfüllt; s. §2.1). Schritt N+1 wird nur betreten bei
   Fehlerkategorie `TRANSIENT`/`QUOTA_LIMIT` (corefw, ADR-243) oder explizitem
   Quality-Override; `CONFIGURATION`/`AUTHORIZATION` failt sofort (kein
   Kosten-Eskalations-Bug durch Fehlkonfiguration).
3. **Org-Default als Code:** eine versionierte Default-Policy `org-groq-first-v1`
   (free → subsidized → paid) wird mit ausgeliefert; Abweichung pro Action erfordert eine
   eigene Policy mit `justification`-Feld. **Justification ist statisch, nicht
   call-zeitlich:** sie lebt im Policy-Eintrag selbst (warum existiert diese paid-Stufe),
   wird beim Policy-Laden validiert — eine paid-Stufe ohne `justification` ist eine
   ungültige Policy (Lade-Fehler, kein Laufzeit-Gate). Policy-Änderung = PR auf das
   Fixture = reviewbare Begründung. Damit ist die llm-routing.md-Regel erzwungen statt
   erinnert.
4. **Audit:** `AIUsageLog.metadata` erhält `policy_id`, `policy_step`, `escalation_reason`.
   Damit ist „wie oft sind wir auf paid eskaliert und warum" eine Query, kein Forensik-Projekt.

**Nicht in Scope:** Session-Level-Routing von Claude Code (bleibt `session-routing.md`,
Mensch-Entscheidung); Modell-Qualitäts-Benchmarking; ein zentraler Proxy.

### 2.1 Koexistenz mit ADR-095 (Quality-Level-Routing) und ADR-068

Nach dem Vorbild der Koexistenz-Regel in ADR-095 §2 (zu ADR-068):

| ADR | beantwortet | Achse |
|---|---|---|
| ADR-068 | „welcher Agent-Tier für diesen Task?" | Workflow |
| ADR-095 | „welches Modell genügt dieser Qualitätserwartung?" | Qualität (`quality_level` 1–9) |
| **ADR-245** | „welcher Provider in welcher **Kosten-Reihenfolge** innerhalb dieser Qualitätsstufe — und wohin bei Quota/Transient?" | Kosten + Resilienz |

Die Policy-Kette wird **nach** der ADR-095-Qualitätsauflösung ausgewertet: ADR-095 bestimmt
die Menge zulässiger Modelle, ADR-245 ordnet sie nach `cost_tier`/`priority` und liefert
das Failover. Kein Schritt der Kette darf die Qualitätsstufe unterschreiten (R-2). Die
ADR-095-Mechanik (deterministischer Lookup, `TierQualityMapping`, Redis-Cache) bleibt
unverändert — ADR-245 ist eine additive Dimension, keine Ablösung.

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
  `api_key_env`, `ProviderPolicy` — expand-only), Default-Policy `org-groq-first-v1` als
  Fixture, Degenerat-Kompatibilität (bestehende default/fallback-Paare werden automatisch
  als 2-Schritt-Policy interpretiert).
- **Phase 2:** Routing-Auflösung in `completion()`/`sync_completion()` inkl.
  Kategorien-gesteuertem Failover; Audit-Felder in `AIUsageLog.metadata`; Tests mit
  simulierten Quota-Fehlern.
- **Phase 3 (Pilot):** bfagent + ein writing-hub-Action-Code auf explizite Policies;
  2-Wochen-Auswertung `escalation_reason`-Verteilung.
- **Phase 4:** aifw-minor-Release; Policy-Review-Konvention (Policy-Fixture-Änderung = PR
  mit Begründung) in CORE_CONTEXT der Consumer.

### 5.1 Phasen-Tracking

| Phase | Inhalt | Status |
|---|---|---|
| 1 | Datenmodell (`cost_tier`/`priority`/`api_key_env`/`ProviderPolicy`) + Default-Fixture | ⬜ (wartet auf ADR-243 Ph. 2) |
| 2 | Routing-Auflösung + Failover + Audit-Felder | ⬜ |
| 3 | Pilot bfagent + writing-hub, 2-Wochen-Auswertung | ⬜ |
| 4 | Release + Policy-Review-Konvention | ⬜ |

> ⬜ → 🔶 → ✅ je Phasen-PR — ADR-138-Evidence-Träger.

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

### 7.4 Offene Punkte (deferred, nicht Accept-blockierend)
- **Per-Tenant-Policies:** `ProviderPolicy` ist in diesem ADR **global je
  action_code-Klasse**. Ein Tenant-Override (z. B. Kunde zahlt Premium-Provider) ist
  vorbereitet (Policy-Auflösung ist ein Lookup, der um `tenant_id` erweiterbar ist),
  wird aber erst bei konkretem Kundenbedarf entschieden — dann als Amendment mit
  Billing-Anbindung (ADR-062-Kontext), nicht vorauseilend.

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

## 9. Glossar

| Begriff | Bedeutung |
|---|---|
| **cost_tier** | Kosten-Klasse eines Providers (free/subsidized/paid/premium) — die Achse, entlang derer die Kette eskaliert. |
| **Degenerat-Fall** | Der einfachste gültige Spezialfall: ein bestehendes default/fallback-Modell-Paar wird automatisch als 2-Schritt-Kette interpretiert — Bestands-Configs funktionieren unverändert. |
| **Eskalation** | Übergang zum nächsten (teureren) Ketten-Schritt — nur bei transienten/Quota-Fehlern, mit protokolliertem Grund. |
| **Failover** | Automatisches Ausweichen auf den nächsten Provider, wenn der aktuelle nicht antworten kann. |
| **Fixture** | Versionierte Daten-Datei, die mit dem Code ausgeliefert und per PR geändert wird — hier: die Default-Policy. |
| **Policy-Kette** | Geordnete Liste von (Provider, Modell)-Schritten, die ein Call der Reihe nach durchlaufen darf. |
| **Quality-Level** | Qualitätserwartung 1–9 des Consumers (ADR-095) — bestimmt, welche Modelle überhaupt zulässig sind, bevor die Kosten-Reihenfolge greift. |
| **Quota** | Vom Provider gedeckeltes Nutzungskontingent (z. B. Groq free-tier); Erschöpfung ist ein transientes Routing-Ereignis. |
| **UsageLog** | aifw-Tabelle, die jeden LLM-Call protokolliert — erhält policy_id/policy_step/escalation_reason als Audit-Spuren. |

---

## 10. Referenzen

- `~/.claude/policies/llm-routing.md` + `policies/session-routing.md` (Kosten-Evidenz
  $1.577/48 h).
- aifw-Code-Evidenz: `src/aifw/models.py:35-52`, `src/aifw/service.py:196-254` + `411-419`.
- ADR-243 (corefw-Fehlerkategorien), ADR-242 (Konvention→Konstruktion-Muster).

---

## 11. Changelog

- **2026-06-21 (Accepted):** Status `proposed → accepted`. Sequenziert nach ADR-243 (im selben
  Zug accepted) — die Policy-Engine ist zugleich der lebende Konsument, der ADR-243s observe/
  provenance-Hälfte aus ihrem Reife-Gate hebt. Review-Changes (3.7/5) eingearbeitet, §7.4
  deferred. Kill-Kriterium bleibt: Phase 2 bis 2026-10-31 in einem aifw-Release, sonst Re-Eval.
- **2026-06-12 (Review-Fixup):** `/adr-review`-Findings eingearbeitet (Score 3.7/5, „Accept
  with changes"): **§2.1 Koexistenz mit ADR-095/068** (kritischer Fund — Policy wählt
  *innerhalb* der Qualitätsstufe; Status-quo-Rahmung korrigiert: ADR-095 wird erweitert,
  nicht repariert); Justification statisch im Policy-Eintrag (Lade-Validierung, kein
  Laufzeit-Gate); `api_key_env`-Feld ersetzt hartkodiertes Key-Mapping; Migrationen
  expand-only zugesagt; §7.4 Per-Tenant-Policies explizit deferred; §1.4
  Entscheidungstreiber, §5.1 Phasen-Tracking, §9 Glossar; `related:` + ADR-068/095.
  Status unverändert Proposed.
- **2026-06-12:** Initial (Proposed). Aus der Tier-4/5-Analyse; sequenziert nach ADR-243.
