---
status: accepted
date: 2026-06-12
decision-makers: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-131, ADR-226, ADR-234]
implementation_status: none
last_reviewed: 2026-06-19
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

### 1.4 Entscheidungstreiber

- **Drift-Schutz an der Quelle:** 4× identisch eingefrorene Retry-Configs divergieren beim
  nächsten Fix garantiert still — eine Implementierung schließt die Klasse von Fehlern.
- **Maschinenlesbare Fehlerkategorien als Vorbedingung** für Policy-Routing (ADR-245) und
  sauberes Failover — heute pro Paket neu zu erraten.
- **Cross-Paket-Beobachtbarkeit:** Kosten-/Latenz-Fragen über Paketgrenzen müssen Queries
  werden, keine Forensik-Projekte.
- **Framework-Freiheit:** researchfw (pure async) darf keinen Django-Stack transitiv erben.
- **Kleine Bruchfläche:** zentrales Artefakt nur mit engem Scope + Release-Disziplin
  (Lehre shared-ci-Tag-Drift 2026-06-09).

---

## 2. Entscheidung

Wir extrahieren einen **schlanken Shared Runtime Core `iil-corefw`** (neues Repo `corefw`,
PyPI `iil-corefw`) mit genau vier Bausteinen:

1. **`corefw.retry`** — die heute 4× duplizierte tenacity-Konfiguration als benanntes,
   **erweiterbares Named-Preset-Registry** (`RetryPolicy.default()`, `RetryPolicy.api_call()`,
   …); Transient-Error-Mengen pro Provider-Typ konfigurierbar. **Bindung statt Schein-
   Einheitlichkeit:** eine Policy gilt nicht blind global, sondern wird an Operationstyp,
   Provider-Typ und **Idempotenz** der Operation gebunden (nicht-idempotente Calls erben nie
   ungefragt eine Retry-Policy). Der Trade-off ist bewusst: Zentralisierung kostet
   Koordination, wenn ein geteilter Default geändert wird — siehe §7.2 und §6 R-1.
2. **`corefw.errors`** — Basishierarchie `IILError(Exception)` mit Pflichtfeldern
   `category ∈ {CONFIGURATION, TRANSIENT, PERMANENT, QUOTA_LIMIT, AUTHORIZATION}`,
   `retryable: bool`, `user_message: str | None`. **Invarianten (normativ, im Paket per Test
   erzwungen):** `CONFIGURATION`/`AUTHORIZATION`/`PERMANENT` sind **nie** `retryable`;
   `TRANSIENT` ist `retryable`; `QUOTA_LIMIT` ist die Kategorie für „später wieder versuchen,
   aber nicht im selben Backoff-Fenster" und damit von `TRANSIENT` abgegrenzt (eigene,
   längere Policy statt sofortigem Retry) — `retryable` darf nicht frei gesetzt werden, wo
   die Kategorie es ausschließt. Die Paket-Exceptions (aifw/promptfw/researchfw) erben davon;
   bestehende Klassen bleiben als Aliase erhalten (kein Breaking Change vor jeweiligem Major).
3. **`corefw.observe`** — der Core liefert **nur das `ObservableResult`-Protocol** (`latency_ms`,
   `input_tokens`, `output_tokens`, `cost_estimate`, `provenance`) — ein reiner Typ.
   Der lifecycle-gebundene **Collector lebt auf der Consumer-Seite** (analog zum Sink, der
   schon in aifw liegt), **nicht im Core**: in pure-async researchfw (Bibliothek ohne
   App-Lifecycle) gibt es keinen klaren Owner/Flush für einen Core-In-Process-Collector —
   ein Collector im Core würde die nicht-verhandelbare „framework-frei"-Zusage intern brechen.
   Feldnamen lehnen sich beim Design an die OpenTelemetry-`gen_ai.*`-Konvention an (nur das
   **Vokabular**, nicht das SDK), damit ein späterer OTel-Sink ein dünner Adapter statt einer
   Übersetzungsschicht ist. (Protocol-Versionsvertrag → §7.4.)
4. **`corefw.provenance`** — Durchreich-Kontrakt für Prompt-Herkunft als **eingefrorener,
   getypter Kontrakt** (frozen dataclass / TypedDict), nicht als loses `dict`: Pflichtfelder
   `template_id`/`template_version`, optional `provider`/`operation`. promptfw stempelt sie in
   `RenderedPrompt`, aifw übernimmt sie in `LLMResult`/`AIUsageLog.metadata`. Ein **stehender
   Chain-Integritäts-Test** (nicht nur eine Einmal-Query) bricht, sobald die Herkunft auf
   irgendeinem Pfad promptfw→aifw verloren geht — sonst zahlt die Flotte die Paketkosten ohne
   den Typ-/Sicherheitsnutzen, der das Paket rechtfertigt. Damit wird Cost-Attribution bis
   zum Template möglich.

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

> **Gestaffeltes Commitment (Review-Entscheid 2026-06-19):** Die Charter bleibt vierteilig,
> aber die *bewiesene, typ-only* Hälfte (`retry`+`errors`) und die *protokoll-entwerfende*
> Hälfte (`observe`+`provenance`) haben **getrennte Reife-Gates**. retry+errors werden jetzt
> committet; observe+provenance werden erst **eingefroren**, wenn ein *lebender* Konsument
> existiert (ADR-245 als erster Failover-Consumer der Fehlerkategorien) — das Protokoll wird
> *nach* seinem Konsumenten entworfen, nicht davor. So reitet die spekulative Hälfte nicht auf
> der sicheren mit.

- **Phase 1 (Paket-Gründung):** Repo `corefw` via `/onboard-repo` (Package-Profil),
  `_ci-pypi.yml` (ADR-226), **`catalog-info.yaml`** (ADR-077: name/type/lifecycle/owner),
  Module `retry` + `errors`, 100 % Test-Coverage auf beiden (klein genug). Release `0.1.0`
  auf TestPyPI, dann PyPI. **Distribution = öffentliches PyPI** (nicht privater Index): die
  Flotte ist bereits durchgängig public-PyPI (`iil-*`); ein zweiter Verteilweg erhöht die
  Oberfläche unnötig. Schutz über Namens-Reservierung des `iil-`-Präfixes, OIDC-Publish-Gate
  (ADR-226) und Release-Verifikation gegen die kanonische Quelle (§6 R-1).
- **Phase 2 (Erst-Konsumenten, beweisend):** researchfw ersetzt seine 4 Retry-Stellen +
  Exceptions erben von `IILError` (Aliase bleiben); aifw analog. Beide releasen minor.
  *Gate:* keine Verhaltensänderung — Retry-Parameter byte-gleich, bestehende Tests grün
  **plus eine explizite Exception-Kompatibilitätsmatrix** (alte Klasse → neue Basisklasse →
  `category` → `retryable` → erwartete `except`-Wirkung): „Tests grün" allein reicht nicht,
  weil erbende Aliase Import-Breaks verhindern, aber nicht eine *veränderte* `except`-/Retry-
  Semantik (eine vorher nicht gefangene Exception kann jetzt über die Basisklasse gefangen werden).
- **Phase 3 (Provenance + Observe) — gegated:** *Vorbedingung:* ein lebender Konsument der
  Telemetrie-/Failover-Typen (ADR-245). Erst dann: promptfw stempelt `template_id` in
  `RenderedPrompt`; aifw übernimmt in `LLMResult`/`AIUsageLog.metadata`; researchfw
  implementiert `ObservableResult` für Such-Calls. Validierung ist eine **stehende**
  Cross-Paket-Prüfung (Kosten je `template_id`), kein Einmal-Query (§8). Fehlt der Konsument
  bis zum Stichtag, greift das observe/provenance-Kill-Kriterium (§8) — retry+errors bleiben
  davon unberührt bestehen.
- **Phase 4:** Aufnahme in den iil-Cohort-Constraint-Snapshot (ADR-234 P0.5a), Eintrag in
  `registry/canonical.yaml`.

### 5.1 Migrations-Tracking (Consumer × Baustein)

| Consumer | retry | errors | observe | provenance | Status |
|---|---|---|---|---|---|
| researchfw | ⬜ Phase 2 | ⬜ Phase 2 | ⬜ Phase 3 | n/a | not started |
| aifw | ⬜ Phase 2 | ⬜ Phase 2 | ⬜ Phase 3 (Sink) | ⬜ Phase 3 | not started |
| promptfw | n/a | ⬜ Phase 3 | ⬜ Phase 3 | ⬜ Phase 3 (Stempel) | not started |
| weitere (`learnfw`, `outlinefw`, …) | – | – | – | – | erst nach Phase-3-Validierung, je eigener Eintrag |

> Tabelle wird bei jedem Phasen-PR aktualisiert (⬜ → 🔶 → ✅); sie ist der
> ADR-138-Evidence-Träger für `implementation_status`.

---

## 6. Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R-1 | Zentrale Dependency bricht Flotte (Version-Skew **oder Common-Mode**) | iil-Cohort-Pinning (ADR-234); semver-Disziplin; Phase 2 nur 2 Pilot-Konsumenten. **Zusatz-Gate gegen Common-Mode:** Cohort-Pinning *absorbiert* Divergenz, *verstärkt* aber gemeinsames Versagen — ein schlechtes `corefw`-Release bricht per Konstruktion die ganze Flotte gleichzeitig (genau das Muster des shared-ci-Tag-Drift, nur als größeres Laufzeit-Artefakt). Daher: **Canary an *einem* Konsumenten für N Tage**, bevor die neue Version flottenweit gepinnt wird; Release-Datei gegen die kanonische Quelle diffen (nicht Tag blind vertrauen). |
| R-2 | Core wächst zum Sammelbecken | §2 „Nicht in Scope"-Liste ist normativ; Erweiterungen nur per ADR-Amendment **plus technische Barriere**: Import-Boundary-Tests + Allowlist erlaubter Top-Level-Module im CI (formales Amendment-Gebot allein wird umgangen). |
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
- Async-API für promptfw — **benanntes Folge-Vorhaben:** nach corefw Phase 2 als eigenes
  promptfw-Issue (Dual-API-Design sync/async, Jinja2-async); kein eigener ADR nötig, solange
  die Public-API additiv bleibt (adr-threshold-Policy).

### 7.4 Offene Punkte (deferred, nicht Accept-blockierend)
- **Versionierungs-Vertrag des `ObservableResult`-Protocols:** Protocol-Erweiterungen müssen
  additiv-optional sein (alte Consumer bleiben gültig); harte Regel wird mit corefw `0.2`
  im Paket-README fixiert — Entscheidung dort, nicht hier.

---

## 8. Validation Criteria

- `grep -rn "wait_exponential" aifw/ researchfw/` zeigt nach Phase 2 **nur** Importe aus
  `corefw.retry`, keine lokalen Konfigurationen.
- Alle Exceptions der drei Frameworks sind `isinstance(e, IILError)` mit gesetzter `category`.
- Eine `AIUsageLog`-Query kann Kosten je `template_id` aggregieren (Nachweis-Query im
  corefw-README).
- **Kill-Kriterium (Wert, nicht Adoption) — getrennt je Hälfte:**
  - *retry+errors:* Stehen nach **2026-09-30** weniger als 2 Pakete auf corefw ≥0.1, wird
    **dieser** Teil deprecated und die Duplikate bleiben akzeptierter Zustand.
  - *observe+provenance:* Reine Adoptions-Zählung greift hier nicht — „≥2 Pakete migriert" wäre
    durch Phase 2 ohnehin erfüllt und würde **nie feuern**. Stattdessen muss bis **2026-09-30**
    eine *stehende* (nicht einmalige) Cross-Paket-Prüfung „Kosten je `template_id`" produktiv
    in Nutzung sein; andernfalls werden observe/provenance deprecated — **retry/errors bleiben
    davon unabhängig bestehen** (gestaffeltes Commitment, §5).
- **Cohort-Support:** `iil-corefw` wird **nur als Teil des iil-Cohort-Snapshots** (ADR-234)
  unterstützt; Einzelversionen außerhalb des Cohorts sind explizit best-effort/unsupported
  (verhindert stillen Version-Skew bei Nicht-Cohort-Konsumenten).

---

## 9. Glossar

| Begriff | Bedeutung |
|---|---|
| **Alias (Exception-Alias)** | Alte Fehlerklasse bleibt bestehen und erbt von der neuen Basisklasse — bestehender Code, der sie fängt, funktioniert weiter. |
| **Cohort (iil-Cohort)** | Zentral getesteter, versions-kohärenter Satz interner `iil-*`-Bibliotheken, als Ganzes pinbar (ADR-234 P0.5a). |
| **Cost-Attribution** | Zuordnung von LLM-Kosten zum Verursacher — hier bis auf das einzelne Prompt-Template genau. |
| **Protocol (Python)** | Strukturelles Interface: eine Klasse erfüllt es, wenn sie die geforderten Attribute/Methoden hat — ohne davon erben zu müssen. |
| **Provenance** | Herkunftskette eines Ergebnisses — hier: welches Template in welcher Version einen LLM-Call erzeugt hat. |
| **Retry-Policy** | Benannte, zentral definierte Regel, wie oft und mit welchen Wartezeiten ein fehlgeschlagener Aufruf wiederholt wird. |
| **Semver** | Semantic Versioning (MAJOR.MINOR.PATCH) — Breaking Changes nur bei MAJOR-Sprung. |
| **Sink** | Austauschbares Ziel für Messdaten (z. B. Django-Datenbank, Logdatei); der Core misst, der Consumer entscheidet wohin. |
| **tenacity** | Python-Bibliothek für Retry-Logik; heute in aifw und researchfw direkt konfiguriert. |
| **transient** | Vorübergehender Fehler (z. B. Rate-Limit, Timeout) — Wiederholung ist sinnvoll; Gegenteil: permanent/Konfigurationsfehler. |

---

## 10. Referenzen

- Codebase-Analyse 2026-06-12 (diese Session): Duplikations-Evidenz mit Pfaden/Zeilen.
- ADR-131 (iil-django-commons — Vorbild „eng geschnittene Shared-Module").
- ADR-226 (`_ci-pypi.yml` — Publish-Gate by construction).
- ADR-234 §P0.5a (iil-Cohort als Verteilungs-Disziplin).

---

## 11. Changelog

- **2026-06-21 (Accepted):** Status `proposed → accepted`. Externe Zweitmeinung (2026-06-19)
  eingearbeitet, keine accept-blockierenden Punkte offen (§7.4 deferred). Keystone für
  ADR-244 (Severity-Enum-Quelle) + ADR-245 (lebender Konsument der observe/provenance-Hälfte);
  beide im selben Zug accepted. Implementierung bleibt phasen-/canary-gegated (§5, R-1).
- **2026-06-19 (Externe Zweitmeinung eingearbeitet):** 2 unabhängige externe Reviewer (beide
  „überarbeiten"), Step-5-Rückfluss-Tagging in `~/shared/adr-243-reviews-2026-06-19.md`.
  `[valid]`-Funde eingearbeitet: **gestaffeltes Commitment** (retry+errors jetzt, observe+
  provenance hinter eigenem Reife-Gate mit lebendem Konsument ADR-245; Charter bleibt 4-teilig,
  §5); **Kill-Kriterium auf Wert statt Adoption** umgestellt + je Hälfte getrennt (§8 — die alte
  Adoptions-Schwelle hätte für observe/provenance *nie gefeuert*); `corefw.observe` liefert **nur
  das Protocol**, Collector wandert auf Consumer-Seite (§2.3 — löst „framework-frei"-Inkonsistenz
  in pure-async); `corefw.provenance` als **getypter/eingefrorener Kontrakt + stehender
  Chain-Integritäts-Test** statt losem `dict` (§2.4); **Fehlerkategorie-Invarianten**
  `category`↔`retryable`, `QUOTA_LIMIT` vs `TRANSIENT` (§2.2); Retry-Policies an Operation/
  Provider/**Idempotenz** gebunden + Koordinationskosten benannt (§2.1); **Exception-
  Kompatibilitätsmatrix** als Phase-2-Gate (§5); **Canary-Gate gegen Common-Mode** + **Import-
  Boundary-Tests** (§6 R-1/R-2); **öffentliches PyPI begründet** (§5 Phase 1); **Cohort-Support-
  Status** dokumentiert (§8); OTel-`gen_ai.*`-**Vokabular** (nicht SDK) beim observe-Design (§2.3).
  Status unverändert **Proposed**. `[missversteht-Kontext]`: R2-AD-3 („provenance rechtfertigt
  das Paket nicht") — Paket trägt sich über retry/errors; Empfehlung dennoch übernommen.
- **2026-06-12 (Review-Fixup):** `/adr-review`-Findings eingearbeitet (Score 4.2/5,
  „Accept with changes"): §1.4 Entscheidungstreiber, §5.1 Migrations-Tracking-Tabelle,
  §7.4 Offene Punkte (Protocol-Versionierung), §9 Glossar, catalog-info.yaml in Phase 1,
  sync/async-Sicherheit in §2.3, promptfw-async als benanntes Folge-Vorhaben. Status
  unverändert Proposed (kein Same-Day-Accept; externe Zweitmeinung empfohlen).
- **2026-06-12:** Initial (Proposed). Abgeleitet aus der Tier-4/5-Codebase-Analyse
  (6 parallele Explore-Agents, Duplikations-Befunde verifiziert).
