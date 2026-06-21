---
status: accepted
date: 2026-06-12
decision-makers: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-209, ADR-234, ADR-239, ADR-240, ADR-242]
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
| **Relates to** | ADR-209 (CI-Green-Governance), ADR-234 (Invariante statt Task), ADR-239 (Guardian), ADR-240 (Repo-Health-Framework), ADR-242 (Branch-Protection) |

---

## 1. Kontext

### 1.1 Ausgangslage

Vier Regel-Systeme prüfen heute vier Domänen — ohne gemeinsame Sprache (Analyse 2026-06-12,
Guardian-Ergänzung nach Review):

| System | Domäne | Regelbestand | Severity | Suppression |
|---|---|---|---|---|
| `iil-reflex` (quality.py) | UC-Qualität (semantisch) | 11 Regex-Kriterien C-01..C-11 | keine Ordnung | keine |
| `iil-codeguard` (checkers/) | Code (syntaktisch, AST/HTML/YAML) | 35+ Rules SL/HX/DC/DF/NX | `Severity.order()` | geplant „Phase 3 future" |
| `platform/tools/repo_health_check.py` | Repo-Struktur | Profil-Checks | eigene | `# noqa: AP-xxx` (in `check_htmx_patterns.py`) |
| `platform/agents/guardian.py` (ADR-239) | PR-Diff vs. Architektur-Regeln | Regel-Set in Code, **required check** auf platform-PRs | keine Ordnung | keine |

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

- **Kein Mega-Linter:** Die vier Systeme prüfen verschiedene Domänen mit verschiedenen
  Mechaniken (Regex/AST/Filesystem) — die Engines bleiben getrennt.
- **Enforcement folgt Reife** (ADR-234/242-Muster): ein Compliance-Gate startet als
  Dry-Run/Report, nie als Flotten-Blocker.
- Deterministisch, kein LLM in Gating-Pfaden (Repo-Health-Disziplin).

### 1.4 Entscheidungstreiber

- **Prüfbarkeit statt Erinnerung:** Die SUGGEST→ENFORCE-Disziplin existiert nur als Memory —
  was nicht maschinenlesbar ist, wird nicht eingehalten (Befund: Konvention bereits 3 Dialekte).
- **Selbe Krankheit wie ADR-234:** Detektoren ohne Aktor — Audit-Findings versanden ohne Loop.
- **Aggregierbarkeit:** Cross-Tool-Reports brauchen ein Severity-Vokabular und einen
  Suppression-Ausweis, sonst bleibt jede Flotten-Aussage Handarbeit.
- **Rollout-Entsperrung:** codeguard wartet konkret auf Suppression (7 Consumer-CIs) — die
  Marker-Entscheidung ist der kritische Pfad.
- **Enforcement folgt Reife** (ADR-242-Muster): Gate als Dry-Run-Treppe, nie als Dekret.

---

## 2. Entscheidung

Wir schließen den Regel-Lebenszyklus mit drei Bausteinen — **gemeinsame Sprache, getrennte
Engines**:

1. **G1 — Rule-Lifecycle maschinenlesbar in iil-adrfw:** `adr_rules.schema.json` wird
   aktiviert und erweitert um `lifecycle ∈ {suggest, enforce, deprecated}`,
   `validated_repos: []` (≥5 für enforce), `false_positives: int` (0 für enforce),
   `engine ∈ {reflex, codeguard, repo-health, guardian}`, `severity`. Jede Rule der vier
   Systeme bekommt einen Eintrag; adrfw wird der **Katalog**, die Engines bleiben die
   **Ausführung**. Die Katalog-Datei lebt als **Package-Data in iil-adrfw** (via pip in
   jeder Consumer-CI verfügbar, versioniert mit dem Paket — bewusst **nicht** in
   platform/registry, s. Alternative C). Ein adrfw-Auditor `rule_lifecycle` failt, wenn
   eine Engine eine Rule enforced, deren Katalog-Eintrag die Schwelle nicht belegt.
   *Bestandsschutz Guardian:* dessen Rules laufen bereits als required check — sie werden
   mit `lifecycle: enforce` + `validated_repos: [platform]` inventarisiert und sind vom
   ≥5-Repo-Kriterium ausgenommen, solange ihr Scope platform-only bleibt (single-repo-Regel
   = single-repo-Beleg).
2. **G2 — eine Severity-Skala + ein Suppression-Marker org-weit:**
   Severity `{CRITICAL, ERROR, WARNING, INFO}` mit definierter Ordnung. **Heimat bedingt
   entschieden:** wird ADR-243 accepted, liefert `corefw.errors` die Enum (eine
   Runtime-Implementierung für alles); andernfalls iil-adrfw — kein „oder" zur Laufzeit,
   die Bedingung ist der ADR-243-Statuswechsel. Suppression einheitlich
   **`iil: disable=<RULE-ID> [reason=…]`** im Kommentar-Dialekt der jeweiligen Datei:

   | Dateityp | Marker-Syntax |
   |---|---|
   | Python / YAML / Dockerfile / Shell | `# iil: disable=SL-001 reason=…` |
   | HTML / Jinja-Templates | `<!-- iil: disable=HX-005 reason=… -->` |
   | Markdown (UC-Dateien, reflex) | `<!-- iil: disable=C-06 reason=… -->` |

   Alt-Dialekte (`# noqa: AP-xxx`) bleiben ein Deprecation-Fenster lang gültig. Jeder
   Report weist Suppressions mit Grund aus (keine stillen Ausnahmen).
3. **G3 — `adr_compliance_gate` (Dry-Run-first):** neues adrfw-CLI/MCP-Tool, das pro Repo
   prüft: keine `broken_refs`, keine überschrittenen `implementation_done_when`-Deadlines,
   keine enforce-Rules ohne Lifecycle-Beleg. Stufe 1 = wöchentlicher Report (Issue/Memory),
   Stufe 2 = informational CI-Check, Stufe 3 (gated, eigenes Amendment) = required-Check
   nach ADR-242-Mechanik. Drift-Notification läuft über den bestehenden
   Recurring-Errors-/Memory-Pfad (ADR-154), kein neuer Kanal.

### 2.1 Abgrenzung zu ADR-240 (Repo-Health-Framework) und ADR-239 (Guardian)

Beide ADRs berühren die Prüf-Domäne — die Grenzen sind komplementär, nicht konkurrierend:

- **ADR-240 = Laufzeit-Health:** Probes, Narration, einheitliches Datenmodell für *Zustände*
  (Git-State, HTTP-Endpoints, Modell-Drift, Cadence/Eskalation). **ADR-244 = statischer
  Regel-Lifecycle:** Governance darüber, *welche Checks mit welcher Reife enforced werden
  dürfen* (Severity/Suppression/Beleg). Schnittstelle: ADR-240-Probes, die deterministische
  Rules ausführen (z. B. `compliance-check.yml`), beziehen deren Enforce-Berechtigung aus dem
  G1-Katalog; ADR-244 definiert **keine** Probes, kein Health-Datenmodell, keine Cadence.
  Sollte ADR-240 accepted werden, konsumiert sein Framework den Katalog read-only — es
  entsteht keine zweite Lifecycle-Quelle.
- **ADR-239 (Guardian)** ist die vierte Engine (s. §1.1): seine Rules werden inventarisiert
  (Bestandsschutz s. G1), seine Ausführung (PR-Zeit, required check) bleibt unverändert.

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
  vier bewährten Engines anzufassen.
- **Suppression mit Pflicht-Grund** macht False-Positive-Druck sichtbar statt unsichtbar —
  die FP-Zählung aus G1 speist sich direkt daraus.

---

## 5. Implementation Plan

- **Phase 1:** `adr_rules.schema.json` erweitern + Bestands-Inventur: alle ~50+ Rules der
  vier Engines als Katalog-Einträge mit ehrlichem `lifecycle` (Bestand ohne Beleg =
  `suggest`; Guardian-Bestandsschutz s. G1).

### 5.1 Inventur-Tracking (Engine × Phase)

| Engine | Rules | Katalog (P1) | Marker (P2) | Gate-Report (P3) | Status |
|---|---|---|---|---|---|
| iil-codeguard | 35+ (SL/HX/DC/DF/NX) | ⬜ | ⬜ **prio** (Rollout wartet) | ⬜ | not started |
| iil-reflex | 11 (C-01..C-11) | ⬜ | ⬜ | ⬜ | not started |
| repo_health_check | Profil-Checks | ⬜ | ⬜ (`# noqa`-Alias) | ⬜ | not started |
| guardian (ADR-239) | Regel-Set in Code | ⬜ (Bestandsschutz) | n/a (PR-Kommentar) | ⬜ | not started |

> Tabelle wird je Phasen-PR aktualisiert (⬜ → 🔶 → ✅) — ADR-138-Evidence-Träger.
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

## 9. Glossar

| Begriff | Bedeutung |
|---|---|
| **Dry-Run** | Prüfung läuft und berichtet, blockiert aber nichts — Vorstufe vor scharfem Enforcement. |
| **Engine** | Das ausführende Prüf-System (reflex, codeguard, repo_health_check, guardian) — führt Rules aus, entscheidet aber nicht über deren Reife. |
| **Enforce / Suggest** | Lebenszyklus-Stufen einer Rule: `suggest` = berichtet nur; `enforce` = darf blockieren — erst nach Beleg (≥5 Repos, 0 False Positives). |
| **False Positive (FP)** | Fehlalarm: die Rule schlägt an, obwohl der Code/Inhalt korrekt ist. |
| **Katalog** | Die maschinenlesbare Liste aller Rules mit Lifecycle/Severity/Beleg — lebt als Package-Data in iil-adrfw; die eine Quelle der Regel-Reife. |
| **Lifecycle** | Der dokumentierte Reifegrad-Pfad einer Rule von Vorschlag bis Abschaltung (suggest → enforce → deprecated). |
| **Package-Data** | Daten-Dateien, die mit einem Python-Paket installiert werden — jede CI, die das Paket installiert, hat sie automatisch. |
| **Required Check** | CI-Prüfung, die grün sein muss, bevor ein Merge erlaubt ist (Branch-Protection, ADR-242). |
| **Severity** | Schweregrad eines Befunds (CRITICAL/ERROR/WARNING/INFO) mit definierter Ordnung für Schwellenwert-Filter. |
| **Suppression** | Dokumentierte, begründete Unterdrückung eines einzelnen Befunds direkt an der Fundstelle (`iil: disable=<RULE-ID> reason=…`). |

---

## 10. Referenzen

- Codebase-Analyse 2026-06-12: Engine-/Severity-/Suppression-Inventur (Pfade in §1.1).
- `iil-adrfw/schemas/adr_rules.schema.json` (vorhanden, ungenutzt).
- ADR-234 (Invariante-statt-Task-Muster), ADR-242 (Enforcement folgt Frische),
  ADR-154 (Memory/Recurring-Errors-Pfad).

---

## 11. Changelog

- **2026-06-21 (Accepted):** Status `proposed → accepted`. Die in §2 G2 als bedingt markierte
  Severity-Heimat ist aufgelöst — ADR-243 ist im selben Zug accepted, also liefert
  `corefw.errors` die kanonische Severity-Enum. Enforcement bleibt die Dry-Run-Treppe
  („Enforcement folgt Reife", ADR-242-Muster), kein Hart-Gate beim heutigen Findings-Bestand.
- **2026-06-12 (Review-Fixup):** `/adr-review`-Findings eingearbeitet (Score 3.8/5, „Accept
  with changes"): **§2.1 Abgrenzung zu ADR-240** (Laufzeit-Health vs. Regel-Lifecycle —
  kritischer Fund: proposed-Kollision) + **Guardian (ADR-239) als vierte Engine**
  inventarisiert (Bestandsschutz-Regel in G1); Severity-Heimat als bedingte Entscheidung
  (ADR-243-Status statt „oder"); Katalog-Ort = adrfw-Package-Data; Suppression-Marker-
  Dialekt-Tabelle (HTML/Markdown via `<!-- -->`); §1.4 Entscheidungstreiber, §5.1
  Inventur-Tracking, §9 Glossar. `related:` um ADR-239/240 erweitert. Status unverändert
  Proposed.
- **2026-06-12:** Initial (Proposed). Aus der Tier-4/5-Analyse; Befund „Detektor ohne
  Aktor auf Regel-Ebene" + ungenutztes Rules-Schema.
