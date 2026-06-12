---
status: proposed
date: 2026-06-12
decision-makers: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-131, ADR-226, ADR-234]
implementation_status: none
last_reviewed: 2026-06-12
staleness_months: 6
tags: [shared-library, frameworks, retry, error-handling, observability, cost-tracking, pypi]
---

# ADR-243: `iil-corefw` — Shared Runtime Core für die Framework-Flotte (Retry, Errors, Observability, Cost-Provenance)

> **Nummern-Hinweis:** 243 = nächste freie Nummer zum Draft-Zeitpunkt (`adr_next_number.py`,
> 2026-06-12); final allokiert zur Merge-Zeit (ADR-228).

| Attribut       | Wert                                              |
|----------------|----------------------------------------------------|
| **Status**     | Proposed                                          |
| **Scope**      | platform (org-weit: alle `iil-*`-Framework-Pakete) |
| **Repo**       | platform (Entscheidung) · neues Repo `corefw` (Implementierung) |
| **Erstellt**   | 2026-06-12                                        |
| **Autor**      | Achim Dehnert                                     |
| **Reviewer**   | –                                                 |
| **Supersedes** | –                                                 |
| **Relates to** | ADR-131 (django-commons), ADR-226 (\_ci-pypi), ADR-234 (iil-Cohort) |

---

## 1. Kontext

### 1.1 Ausgangslage

Die Framework-Flotte (17 PyPI-Pakete) hat Querschnitts-Logik unabhängig voneinander
implementiert. Codebase-Analyse 2026-06-12 (alle Pfade verifiziert):

1. **Retry-Konfiguration 4× identisch dupliziert:** `aifw/src/aifw/service.py:374-387`
   (tenacity, `wait_exponential(multiplier=1, min=1, max=10)`, `stop_after_attempt(3)`,
   `_TRANSIENT_ERRORS`) — byte-gleich erneut in `researchfw/iil_researchfw/search/brave.py:41-45`
   und `search/academic.py:87-90` (dort mehrfach).
2. **Drei inkompatible Exception-Hierarchien:** aifw (3 Exceptions, plain), promptfw
   (4, plain), researchfw (6, mit `service`/`status_code`-Attributen). Ein Consumer
   (bfagent, authoringfw) kann nicht generisch unterscheiden, ob ein Fehler transient,
   permanent oder ein Konfigurationsfehler ist.
3. **Observability nur in aifw:** `AIUsageLog` (21 Spalten inkl. `tenant_id`,
   `quality_level`) existiert nur dort. promptfw-Rendering und researchfw-Suchen sind
   für Kosten-/Latenz-Tracking unsichtbar.
4. **Cost-Attribution endet an der Paketgrenze:** `promptfw.RenderedPrompt`
   (`schema.py:71-82`) trägt keine `template_id`; `aifw.LLMResult`/`AIUsageLog` können
   Kosten daher nicht auf das verursachende Template zurückführen.

### 1.2 Problem / Lücken

- Jede Änderung an Retry-/Fehler-Semantik muss in N Paketen synchron nachgezogen werden —
  nachweislich passiert das nicht (die Duplikate sind bereits identisch *eingefroren*).
- Cross-Paket-Fragen („welches Template verursacht die höchsten Kosten?", „welcher Provider
  failt am häufigsten transient?") sind heute **prinzipiell** unbeantwortbar, nicht nur unbequem.
- Ohne gemeinsame Fehlerkategorien kann ADR-245 (Provider-Policy-Engine) Failover nicht
  sauber definieren („failover bei TRANSIENT/QUOTA, nie bei CONFIGURATION").

### 1.3 Constraints

- **Framework-frei:** researchfw ist pure-async ohne Django; aifw ist Django-gebunden.
  Der Core darf **keine** Django-Abhängigkeit haben (sonst unbrauchbar für researchfw).
- **Klein bleiben:** kein Sammelbecken (Lehre iil-django-commons: bewusst eng geschnittene
  Module). Theming, CLI-Helpers, YAML-Utils sind explizit **nicht** in Scope.
- Verteilung folgt ADR-234 P0.5a (iil-Cohort-Constraints) — ein zentrales Paket darf die
  Flotte nicht über Version-Skew brechen.

---

## 2. Entscheidung

Wir extrahieren einen **schlanken Shared Runtime Core `iil-corefw`** (neues Repo `corefw`,
PyPI `iil-corefw`) mit genau vier Bausteinen:

1. **`corefw.retry`** — die heute 4× duplizierte tenacity-Konfiguration als benannte,
   zentral versionierte Policies (`RetryPolicy.default()`, `RetryPolicy.api_call()`);
   Transient-Error-Mengen pro Provider-Typ konfigurierbar.
2. **`corefw.errors`** — Basishierarchie `IILError(Exception)` mit Pflichtfeldern
   `category ∈ {CONFIGURATION, TRANSIENT, PERMANENT, QUOTA_LIMIT, AUTHORIZATION}`,
   `retryable: bool`, `user_message: str | None`. Die Paket-Exceptions (aifw/promptfw/
   researchfw) erben davon; bestehende Klassen bleiben als Aliase erhalten (kein Breaking
   Change vor jeweiligem Major).
3. **`corefw.observe`** — `ObservableResult`-Protocol (`latency_ms`, `input_tokens`,
   `output_tokens`, `cost_estimate`, `provenance: dict`) + ein In-Process-Collector mit
   austauschbarem Sink (Django-ORM-Sink lebt in **aifw**, nicht im Core).
4. **`corefw.provenance`** — Durchreich-Kontrakt für Prompt-Herkunft: promptfw stempelt
   `template_id`/`template_version` in `RenderedPrompt`, aifw übernimmt sie in
   `LLMResult`/`AIUsageLog.metadata`. Damit wird Cost-Attribution bis zum Template möglich.

**Nicht in Scope:** LLM-Provider-Clients, Rate-Limiting (bleibt paket-spezifisch),
Caching (aifw-2-Layer ist Django-spezifisch, researchfw-TTLCache bleibt lokal), Theming.

---

## 3. Betrachtete Alternativen

| # | Alternative | Verworfen, weil |
|---|---|---|
| A | **Status quo** (Copy-Paste-Konvention) | Duplikate sind nachweislich eingefroren; Drift-Risiko bei jeder Sicherheits-/Verhaltensänderung; Cross-Paket-Telemetrie bleibt unmöglich |
| B | **aifw als Host des Cores** (researchfw/promptfw hängen von aifw ab) | aifw ist Django-gebunden — researchfw (pure async) müsste den Django-Stack transitiv ziehen; zudem invertierte Kopplung (Template-Engine hinge am LLM-Client) |
| C | **iil-django-commons erweitern** | gleiche Django-Kopplung wie B; commons ist bewusst Hub-Backend-Scope (Middleware, Health), nicht Framework-Runtime |
| D | **Großer Core** (inkl. YAML-Utils, CLI, Theming, HTTP-Client) | Sammelbecken-Antipattern; jede Erweiterung erhöht die Bruchfläche der zentralen Dependency; Theming gehört zu ADR-211-Klickdummy-Strecke |
| E | **Vendoring per Code-Generator** (Core-Code in Pakete kopieren, CI prüft Gleichheit) | löst Telemetrie/Provenance nicht (braucht geteilte Typen zur Laufzeit); CI-Gleichheits-Gate ist komplexer als ein normales Paket |

---

## 4. Begründung im Detail

- **Die Duplikation ist verifiziert, nicht vermutet** — identische tenacity-Parameter an
  4 Stellen sind der klassische Fall „beim nächsten Fix divergiert es still".
- **Fehlerkategorien sind die Vorbedingung für Policy-Routing** (ADR-245): Failover-Regeln
  brauchen maschinenlesbare Unterscheidung transient/quota/config. Das gehört in den Core,
  nicht in die Policy-Engine (sonst re-implementiert jeder Consumer das Mapping).
- **Sink-Trennung hält den Core framework-frei:** Das Observe-Protocol definiert *was*
  gemessen wird; *wohin* (Django-ORM, stdout, NDJSON) entscheidet der Consumer. aifw behält
  sein `AIUsageLog` als ein Sink — kein Migrationszwang.
- **Klein + 4 Bausteine = überschaubare Bruchfläche.** Lehre aus dem shared-ci-Tag-Drift
  (2026-06-09): zentrale Artefakte brauchen enge Scopes und disziplinierte Releases.

---

## 5. Implementation Plan

- **Phase 1 (Paket-Gründung):** Repo `corefw` via `/onboard-repo` (Package-Profil),
  `_ci-pypi.yml` (ADR-226), Module `retry` + `errors`, 100 % Test-Coverage auf beiden
  (klein genug). Release `0.1.0` auf TestPyPI, dann PyPI.
- **Phase 2 (Erst-Konsumenten, beweisend):** researchfw ersetzt seine 4 Retry-Stellen +
  Exceptions erben von `IILError` (Aliase bleiben); aifw analog. Beide releasen minor.
  *Gate:* keine Verhaltensänderung — Retry-Parameter byte-gleich, bestehende Tests grün.
- **Phase 3 (Provenance + Observe):** promptfw stempelt `template_id` in `RenderedPrompt`;
  aifw übernimmt in `LLMResult`/`AIUsageLog.metadata`; researchfw implementiert
  `ObservableResult` für Such-Calls. Erste Cross-Paket-Auswertung (Kosten je Template) als
  Validations-Artefakt.
- **Phase 4:** Aufnahme in den iil-Cohort-Constraint-Snapshot (ADR-234 P0.5a), Eintrag in
  `registry/canonical.yaml`.

---

## 6. Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R-1 | Zentrale Dependency bricht Flotte (Version-Skew) | iil-Cohort-Pinning (ADR-234); semver-Disziplin; Phase 2 nur 2 Pilot-Konsumenten |
| R-2 | Core wächst zum Sammelbecken | §2 „Nicht in Scope"-Liste ist normativ; Erweiterungen nur per ADR-Amendment |
| R-3 | Verhaltensänderung beim Retry-Umzug | Phase-2-Gate: Parameter byte-gleich, Tests der Consumer unverändert grün |
| R-4 | Exception-Umbau bricht Consumer-`except`-Klauseln | Alt-Klassen bleiben als erbende Aliase bis zum jeweiligen Major-Release |

---

## 7. Konsequenzen

### 7.1 Positiv
- Eine Stelle für Retry-/Fehler-Semantik; Sicherheits-/Verhaltensfixes erreichen alle Pakete.
- Cost-Attribution bis auf Template-Ebene; Telemetrie über Paketgrenzen.
- ADR-245 (Policy-Engine) bekommt seine Fehlerkategorien geschenkt.

### 7.2 Trade-offs
- Ein weiteres zu pflegendes Paket + Release-Disziplin.
- promptfw/researchfw bekommen eine neue (kleine, framework-freie) Pflicht-Dependency.

### 7.3 Nicht in Scope
- Konsolidierung von Rate-Limiting/Caching (bewusst paket-spezifisch belassen).
- Async-API für promptfw (eigenes Vorhaben, baut auf diesem ADR auf).

---

## 8. Validation Criteria

- `grep -rn "wait_exponential" aifw/ researchfw/` zeigt nach Phase 2 **nur** Importe aus
  `corefw.retry`, keine lokalen Konfigurationen.
- Alle Exceptions der drei Frameworks sind `isinstance(e, IILError)` mit gesetzter `category`.
- Eine `AIUsageLog`-Query kann Kosten je `template_id` aggregieren (Nachweis-Query im
  corefw-README).
- Kill-Kriterium: Stehen nach **2026-09-30** weniger als 2 Pakete auf corefw ≥0.1, wird das
  Paket deprecated und die Duplikate bleiben akzeptierter Zustand (kein Zombie-Core).

---

## 9. Referenzen

- Codebase-Analyse 2026-06-12 (diese Session): Duplikations-Evidenz mit Pfaden/Zeilen.
- ADR-131 (iil-django-commons — Vorbild „eng geschnittene Shared-Module").
- ADR-226 (`_ci-pypi.yml` — Publish-Gate by construction).
- ADR-234 §P0.5a (iil-Cohort als Verteilungs-Disziplin).

---

## 10. Changelog

- **2026-06-12:** Initial (Proposed). Abgeleitet aus der Tier-4/5-Codebase-Analyse
  (6 parallele Explore-Agents, Duplikations-Befunde verifiziert).
