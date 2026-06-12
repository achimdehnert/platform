---
status: proposed
date: 2026-06-12
decision-makers: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-209, ADR-234, ADR-242]
implementation_status: none
last_reviewed: 2026-06-12
staleness_months: 6
tags: [governance, rule-lifecycle, adrfw, codeguard, reflex, severity, suppression, compliance-gate]
---

# ADR-244: Geschlossener Regel-Lebenszyklus — eine Severity-/Suppression-Sprache und ein Compliance-Gate über alle Check-Systeme

> **Nummern-Hinweis:** 244 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert zur
> Merge-Zeit (ADR-228).

| Attribut       | Wert                                              |
|----------------|----------------------------------------------------|
| **Status**     | Proposed                                          |
| **Scope**      | platform (org-weit: iil-adrfw, iil-codeguard, iil-reflex, platform/tools) |
| **Repo**       | platform                                          |
| **Erstellt**   | 2026-06-12                                        |
| **Autor**      | Achim Dehnert                                     |
| **Reviewer**   | –                                                 |
| **Supersedes** | –                                                 |
| **Relates to** | ADR-209 (CI-Green-Governance), ADR-234 (Invariante statt Task), ADR-242 (Branch-Protection) |

---

## 1. Kontext

### 1.1 Ausgangslage

Drei Regel-Systeme prüfen heute drei Domänen — ohne gemeinsame Sprache (Analyse 2026-06-12):

| System | Domäne | Regelbestand | Severity | Suppression |
|---|---|---|---|---|
| `iil-reflex` (quality.py) | UC-Qualität (semantisch) | 11 Regex-Kriterien C-01..C-11 | keine Ordnung | keine |
| `iil-codeguard` (checkers/) | Code (syntaktisch, AST/HTML/YAML) | 35+ Rules SL/HX/DC/DF/NX | `Severity.order()` | geplant „Phase 3 future" |
| `platform/tools/repo_health_check.py` | Repo-Struktur | Profil-Checks | eigene | `# noqa: AP-xxx` (in `check_htmx_patterns.py`) |

Dazu der entscheidende Befund: Die Org-Disziplin **„neue Rules starten als SUGGEST, gegen ≥5
echte Repos validiert, 0 False Positives, deterministisch ohne LLM"** existiert nur als
Memory/Konvention. `iil-adrfw/schemas/adr_rules.schema.json` — das Schema, das genau diesen
Lifecycle tragen könnte — liegt **ungenutzt** im Repo. Und: `adr_audit`/`staleness`/`freshness`
*finden* Probleme, aber nichts *erzwingt* Remediation (kein Compliance-Gate, keine
Drift-Notification) — derselbe „Detektor ohne Aktor"-Befund, den ADR-234 für CI-Zustände
behoben hat, besteht für die Regel-Ebene fort.

### 1.2 Problem / Lücken

1. **Regel-Einführung ist ungovernt:** Ob eine neue Rule die SUGGEST→ENFORCE-Schwelle
   (≥5 Repos, 0 FP) je erfüllt hat, ist nicht maschinenlesbar — und damit nicht prüfbar.
2. **Drei Suppression-Dialekte** (`# noqa: AP-xxx`, geplantes `# codeguard: disable=`,
   nichts bei reflex) → Entwickler lernen pro Tool neu; Cross-Tool-Reports können
   Unterdrückungen nicht einheitlich ausweisen.
3. **Audit ohne Loop:** adrfw-Findings (stale ADRs, broken refs, deadline überschritten)
   versanden, wenn die Session sie nicht zufällig sieht.

### 1.3 Constraints

- **Kein Mega-Linter:** Die drei Systeme prüfen verschiedene Domänen mit verschiedenen
  Mechaniken (Regex/AST/Filesystem) — die Engines bleiben getrennt.
- **Enforcement folgt Reife** (ADR-234/242-Muster): ein Compliance-Gate startet als
  Dry-Run/Report, nie als Flotten-Blocker.
- Deterministisch, kein LLM in Gating-Pfaden (Repo-Health-Disziplin).

---

## 2. Entscheidung

Wir schließen den Regel-Lebenszyklus mit drei Bausteinen — **gemeinsame Sprache, getrennte
Engines**:

1. **G1 — Rule-Lifecycle maschinenlesbar in iil-adrfw:** `adr_rules.schema.json` wird
   aktiviert und erweitert um `lifecycle ∈ {suggest, enforce, deprecated}`,
   `validated_repos: []` (≥5 für enforce), `false_positives: int` (0 für enforce),
   `engine ∈ {reflex, codeguard, repo-health}`, `severity`. Jede Rule der drei Systeme
   bekommt einen Eintrag; adrfw wird der **Katalog**, die Engines bleiben die **Ausführung**.
   Ein adrfw-Auditor `rule_lifecycle` failt, wenn eine Engine eine Rule enforced, deren
   Katalog-Eintrag die Schwelle nicht belegt.
2. **G2 — eine Severity-Skala + ein Suppression-Marker org-weit:**
   Severity `{CRITICAL, ERROR, WARNING, INFO}` mit definierter Ordnung (Quelle: corefw oder
   adrfw, eine Implementierung). Suppression einheitlich
   **`# iil: disable=<RULE-ID> [reason=…]`** in allen drei Engines; Alt-Dialekte
   (`# noqa: AP-xxx`) bleiben ein Deprecation-Fenster lang gültig. Jeder Report weist
   Suppressions mit Grund aus (keine stillen Ausnahmen).
3. **G3 — `adr_compliance_gate` (Dry-Run-first):** neues adrfw-CLI/MCP-Tool, das pro Repo
   prüft: keine `broken_refs`, keine überschrittenen `implementation_done_when`-Deadlines,
   keine enforce-Rules ohne Lifecycle-Beleg. Stufe 1 = wöchentlicher Report (Issue/Memory),
   Stufe 2 = informational CI-Check, Stufe 3 (gated, eigenes Amendment) = required-Check
   nach ADR-242-Mechanik. Drift-Notification läuft über den bestehenden
   Recurring-Errors-/Memory-Pfad (ADR-154), kein neuer Kanal.

---

## 3. Betrachtete Alternativen

| # | Alternative | Verworfen, weil |
|---|---|---|
| A | **Status quo** (Konvention im Memory) | nicht prüfbar; Suppression-Dialekte wachsen weiter; Audit-Findings versanden — exakt der offene Regelkreis, den ADR-234 auf CI-Ebene geschlossen hat |
| B | **Ein Mega-Linter** (alle Rules in codeguard) | Domänen-Mismatch: UC-Qualität (Regex über Markdown) und Repo-Struktur passen nicht in eine AST-Engine; Single-Tool-Risiko |
| C | **Katalog in platform/registry statt adrfw** | adrfw hat Schema, Auditor-Framework und MCP-Anbindung bereits; eine zweite Katalog-Mechanik wäre neue Dual-SSoT |
| D | **Sofort hartes CI-Gate** | verletzt „Enforcement folgt Reife"; würde bei heutigem Findings-Bestand Repos einfrieren (Goodhart-Druck, vgl. ADR-242 §Kontext 4) |

---

## 4. Begründung im Detail

- **Selbe Krankheit, selbes Heilmittel:** ADR-234 hat „Detektor ohne Aktor" für CI-Zustände
  beendet (Invariante statt Reparatur-Task). Dieser ADR wendet das Muster auf die
  Regel-Ebene an — inklusive der Reife-Vorbedingung (Lifecycle-Beleg statt Dekret).
- **Katalog ≠ Engine** ist die kleinste Schnittstelle, die Konsistenz erzwingt, ohne die
  drei bewährten Engines anzufassen.
- **Suppression mit Pflicht-Grund** macht False-Positive-Druck sichtbar statt unsichtbar —
  die FP-Zählung aus G1 speist sich direkt daraus.

---

## 5. Implementation Plan

- **Phase 1:** `adr_rules.schema.json` erweitern + Bestands-Inventur: alle ~50 Rules der
  drei Engines als Katalog-Einträge mit ehrlichem `lifecycle` (Bestand ohne Beleg = `suggest`).
- **Phase 2:** Suppression-Marker `# iil: disable=` in codeguard (vor dessen Rollout —
  blockiert sonst 7 Consumer-CIs) und reflex implementieren; `check_htmx_patterns.py` auf
  den Marker umstellen (Alias-Fenster für `# noqa: AP-xxx`).
- **Phase 3:** `adr_compliance_gate` Stufe 1 (Report) + `rule_lifecycle`-Auditor; 4 Wochen
  Beobachtung der FP-/Findings-Raten.
- **Phase 4 (gated):** Stufe 2 informational CI; Stufe-3-Entscheidung als Amendment mit
  ADR-242-Frische-Logik.

---

## 6. Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R-1 | Katalog driftet von Engines weg | `rule_lifecycle`-Auditor vergleicht Katalog ↔ Engine-Registries maschinell (beide sind Code/Config, deterministisch lesbar) |
| R-2 | Suppression wird Schlupfloch | Pflicht-`reason`, Report-Ausweis, FP-Zählung; Budget-Idee aus ADR-234-Waiver-Semantik übernehmbar |
| R-3 | Gate erzeugt Issue-Spam | Stufe 1 aggregiert wöchentlich, dedupliziert über entry_key (Muster ADR-154 Recurring-Errors) |
| R-4 | Drei-Engine-Umbau parallel zu Rollouts | Phase 2 priorisiert codeguard (dessen Rollout wartet ohnehin auf Suppression) |

---

## 7. Konsequenzen

### 7.1 Positiv
- Die SUGGEST-Disziplin wird prüfbar statt erinnerbar; Regel-Qualität bekommt einen Beleg-Pfad.
- Ein Suppression-Dialekt, ein Severity-Vokabular → Cross-Tool-Reports werden aggregierbar.
- adrfw-Findings münden in einen definierten Loop statt in Session-Zufall.

### 7.2 Trade-offs
- Initiale Inventur-Arbeit (~50 Rules katalogisieren).
- adrfw bekommt eine zusätzliche Rolle (Katalog) — mehr Verantwortung auf einem Paket.

### 7.3 Nicht in Scope
- Zusammenlegung der Engines; neue Rules selbst; LLM-gestützte Checks.
- Stufe-3-Enforcement (eigenes, gated Amendment).

---

## 8. Validation Criteria

- Jede in einer Engine als enforce laufende Rule hat einen Katalog-Eintrag mit
  `validated_repos ≥ 5` und `false_positives == 0` — maschinell geprüft, Verstoß = Audit-Fail.
- `grep -rn "iil: disable="` ist der **einzige** aktive Suppression-Dialekt nach Ablauf des
  Alias-Fensters (Stichtag im Phase-2-PR fixiert).
- Der wöchentliche Compliance-Report existiert 4 Wochen in Folge mit abnehmender oder
  begründet konstanter Findings-Zahl.
- Kill-Kriterium: Ist G1-Katalog bis **2026-10-01** nicht mit den Engines abgeglichen,
  fällt der ADR auf Detect-only zurück (Report bleibt, Gate-Ambition entfällt).

---

## 9. Referenzen

- Codebase-Analyse 2026-06-12: Engine-/Severity-/Suppression-Inventur (Pfade in §1.1).
- `iil-adrfw/schemas/adr_rules.schema.json` (vorhanden, ungenutzt).
- ADR-234 (Invariante-statt-Task-Muster), ADR-242 (Enforcement folgt Frische),
  ADR-154 (Memory/Recurring-Errors-Pfad).

---

## 10. Changelog

- **2026-06-12:** Initial (Proposed). Aus der Tier-4/5-Analyse; Befund „Detektor ohne
  Aktor auf Regel-Ebene" + ungenutztes Rules-Schema.
