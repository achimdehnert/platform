---
id: ADR-231
status: proposed
date: 2026-05-30
amended: 2026-05-30
decision-makers: Achim Dehnert
domains: [dev-hub, architecture, ssot, portal, drift-prevention]
supersedes: []
amends: [ADR-158-unified-documentation-architecture.md]
related: [ADR-050-platform-decomposition-hub-landscape.md, ADR-077-infrastructure-context-system.md, ADR-021-unified-deployment-pattern.md]
tags: [dev-hub, bff, catalog, ssot-pointer, read-projection, entkernung, stateful-surface]
---

# ADR-231: dev-hub 2.0 — Entkernung zu Thin BFF + Catalog-Service (Read-Projektionen statt geforkter Tabellen)

| Attribut | Wert |
|---|---|
| **Status** | Proposed |
| **Scope** | dev-hub (16 Apps) + SSoT-Topologie gegenüber Orchestrator/git/GitHub/Outline |
| **Datum** | 2026-05-30 |
| **Autor** | Achim Dehnert |
| **Amends** | ADR-158 (Unified Documentation Portal) — Portal-Rolle bleibt, „Monolith mit eigener DB"-Annahme fällt |
| **Relates to** | ADR-176 (MCP-SSoT), ADR-143/144/145 (Outline/Paperless/Knowledge), `policies/orchestrator.md` |

## Context and Problem Statement

Ein tiefer Audit von dev-hub (2026-05-30) + ein Prod-Incident am selben Tag legten ein
strukturelles Problem offen, das die Symptome (Sicherheits-Löcher, totes Test-Netz, blindes
Deploy-Gate) verbindet.

**Befund-Heatmap der 16 Apps:**
- **~40 % genuin einzigartig** (KEEP): `portal` (Audience-Navigator, Doc-Health), `search`
  (Cross-Source-Join), `catalog` (Komponenten-/Dependency-Graph — existiert nirgendwo sonst),
  `techdocs` (gepointerte Projektion mit `source_sha`), `controlling` (reines psycopg-Read-View
  über Orchestrator-`llm_calls` — das Vorbild), `core` (Tenancy/Audit/Outbox-Fundament).
- **~35 % forken Autoritäts-Zustand** (DEMOTE): `ai_config` (eigener Provider/Budget/**API-Key**-Store,
  null Orchestrator-Bezug — obwohl der Orchestrator der *deklarierte* LLM-Router ist), `agents_dashboard`
  (zweite Kopie der Run-Records ohne Rück-Link), `adr_lifecycle` (Parallel-ADR-Tabelle neben git+iil-adrfw),
  `releases` (Tracker neben GitHub-nativ).
- **~25 % Cron/Registry im App-Kostüm** (CUT): `repo_health` (Workstation-Cron, kann in Prod gar
  nicht laufen), `quality_agent` (delegiert ohnehin an Orchestrator), `sw_templates` (Scaffolder-Katalog
  **ohne** Scaffolder-Engine).

**Die gemeinsame Wurzel:** dev-hub besitzt persistenten Zustand (eigene DB + Migrationen), den es
größtenteils nicht besitzen sollte. Diese Besitz-Entscheidung ist die Bruchfläche:

> **Incident 2026-05-30:** eine routinemäßige auto-generierte Migration nahm Prod ~10 min runter
> (502) — `devhub_migrate` exit 1, web hängt auf `Created`. Ein *Aggregations-Portal* braucht keine
> Migrationen, die es selbst abschießen können.

**ADR-158 hat den richtigen Mechanismus bereits benannt** (Source-of-Truth-Matrix, „link-not-copy",
D-5 „KEINE bidirektionalen Syncs"). dev-hub erfüllt ihn für die *Fremdsysteme* (Outline/Paperless:
nur Deep-Links — `portal/services.py:resolve_outline_links` „KEIN Content-Copy") — **verletzt ihn
aber für die In-House-Quellen** (Orchestrator/git/Runs forken Tabellen). ADR-230 zieht ADR-158 zu
Ende: dieselbe Disziplin für *alle* Spokes, plus die strukturelle Konsequenz (Entkernung des
zustandsbehafteten Kerns).

## Decision Drivers

1. **Failure-Surface minimieren** — Migrationen/DB-Coupling, die ein read-only-Portal runterreißen, sind Negativwert.
2. **Eine kanonische Quelle je Information** (ADR-158-Prinzip) — Drift-Forks (ai_config-Keys, agents_dashboard-Runs) sind Schuld mit Zinsen.
3. **Sicherheits-Perimeter** — ai_config hortet API-Keys neben dem deklarierten Router (Orchestrator).
4. **„Physician, heal thyself"** — dev-hub überwacht alle Repos, war selbst der ungesündeste; ein Monitoring-Tool, das unzuverlässiger ist als das Überwachte, erzeugt falsche Sicherheit.
5. **Bestehenden Wert erhalten** — die 40 % (Portal/Katalog/Search/Join) haben keine Heimat sonst; Demolition wäre Wegwerfen.

## Considered Options

### Option A — Status quo (16-App-Monolith lassen)
- ❌ Die Fork-Tabellen driften weiter; die DB/Migrations-Bruchfläche bleibt (Incident-Wiederholung wahrscheinlich).
- ❌ ai_config-Keys + unauth-Altlasten bleiben strukturell begünstigt.

### Option B — Demolition (Backstage + Orchestrator-Dashboards + GitHub-nativ)
- ❌ Kein einziger gemeinsamer menschenseitiger Join; Audience-Navigator/Doc-Health-Score/Cross-Repo-Graph verlieren ihre Heimat.
- ❌ Backstage zu betreiben ist schwerer als das Bestehende; iil-spezifische Sicht ginge verloren.

### Option C — Entkernung zu Thin BFF + Catalog-Service (GEWÄHLT, in Rev 1 re-sequenziert)
- ✅ Behält die 40 % einzigartiger Wert als *dünnen, weitgehend zustandslosen* Read-/Join-Layer.
- ✅ Eliminiert die Migrations-/DB-Bruchfläche dort, wo sie unnötig ist.
- ✅ Erzwingt die ADR-158-„link-not-copy"-Disziplin strukturell auf *alle* Spokes.

### Option D — Modularer Monolith mit isoliertem Catalog-Schema (Rev 1 — als Frühphase von C übernommen)
Statt sofort ein neues Deploy-Artefakt (`catalog-service`) zu schaffen: `catalog` bleibt zunächst
*in* dev-hub, aber als **eigene Postgres-Schema-Zone mit getrenntem Migrations-Gate** (BFF- und
catalog-Migrationen separat deploy-/gatebar).
- ✅ Behebt den **Incident-Typ** (eine fehlschlagende Migration reißt nicht mehr alles runter) zu
  deutlich geringeren Betriebskosten — entscheidend bei Single-Entwickler + unreifer Deploy-Pipeline (AD-1).
- ❌ Weichere Laufzeit-Grenze; ohne Disziplin kann der Monolith wieder wachsen.
- **Konsequenz:** Rev 1 macht Option D zur **Phase 0**; der echte Service-Split (Option C Vollform)
  wird **deferred** und nur bei belegtem Bedarf gezogen (REC-7/REC-21).

## Decision Outcome

**Gewählt: Option C.** dev-hub wird in zwei klar getrennte Verantwortungen entkernt:

1. **`dev-hub-bff`** — dünner Backend-for-Frontend: Portal/Audience-Navigator, Search, Doc-Health-Anzeige,
   Dashboards. **Hart definiert (Rev 1, REC-2):** der BFF darf NUR Session-/Cache-/Portal-Config-/
   Audit-/Outbox-Zustand halten — **keine fachlichen Autoritätsdaten**. Vorbild: `controlling`.
2. **`catalog`** — der **einzige** zustandsbehaftete Bereich (Komponenten-/Dependency-Graph; existiert
   nirgendwo sonst). **Rev 1:** zunächst als **isolierte Postgres-Schema-Zone mit eigenem Migrations-Gate**
   *in* dev-hub (Option D, Phase 0) — eigener `catalog-service` erst bei belegtem Bedarf (deferred).
   **Rev 1.1 (Challenger):** der Katalog muss den **ADR-077-Daten-Kontrakt** (`catalog-info.yaml` →
   dev-hub-Catalog-API) erhalten — `catalog` schneidet ADR-077 nicht ab, sondern wird sein neuer Owner.
   dev-hub als Developer-Portal bleibt **konform zu ADR-050** (Portal-Rolle verfeinert, nicht ersetzt).

### Speicher-Modus-Taxonomie (Rev 1, REC-3 — „Read-Projektion" war zu unscharf)
Jede App-Datenhaltung wird genau einem Modus zugeordnet:
- **`live_read`** — synchrone Abfrage der Quelle, **keine** Persistenz (z. B. `controlling`).
- **`cached_read`** — Cache mit TTL, kein Wahrheits-Anspruch.
- **`read_projection`** — persistierte Projektionszeile, **nur** mit vollständigen Pointer-Metadaten (s. Invariante).
- **`authority-owned`** — dev-hub IST die Quelle (nur catalog, portal-config, audit/outbox).

**Resilienz-Regel (Rev 1.1, Challenger #1):** **ausfallkritische** Spokes (v. a. der Orchestrator,
der selbst pgvector-Ausfälle hatte) nutzen **`read_projection`** (gepointerte Kopie, übersteht
Quell-Ausfall), **nicht `live_read`** — sonst tauscht die Entkernung „veraltete lokale Daten" gegen
„gar keine Daten, wenn die Quelle weg ist". `live_read` nur für hochverfügbare/billige Quellen.

### Verbindliche Invariante (SSoT-Pointer)

> **Jede persistierte `read_projection`-Zeile trägt vollständige Pointer-Metadaten — oder sie darf
> nicht existieren.** Pflichtfelder (Rev 1, REC-4/REC-5): `tenant_id`, `source_system`, `source_id`,
> optional `source_sha`, `source_updated_at`, `synced_at`, `projection_version`, `sync_status`.
> `authority-owned`-Tabellen nur für catalog / portal-config / audit/outbox.

**Erzwingung (Rev 1):**
- **Migrations-Klassifikations-Gate (REC-20):** jede neue dev-hub-Migration muss im PR deklarieren, ob
  sie `authority-owned` / `read_projection` / `config` / `audit-outbox` / `catalog-owned` ist — ohne
  Klassifikation blockt das Gate.
- **`tenant_id` ist Teil der Invariante (REC-5):** je Projektor ein Cross-Tenant-Isolationstest (Leak bei einem Aggregationsportal besonders teuer, AD-14).
- **Ownership-Register (REC-1):** maschinenlesbare Datei `dev-hub/ownership.yaml` listet je App: `tier (KEEP|DEMOTE|CUT)`, `storage_mode`, `authority_source`, `write_allowed`, `pointer_fields`, `rebuild_command`. Der Doc-Health-Self-Audit-Gate prüft Vollständigkeit (REC-17/M28-1).

### Tier-Disposition (aus dem Audit)

| Tier | Apps | Maßnahme |
|------|------|----------|
| **KEEP** (echte SSoT/Join) | catalog → eigener Service; portal/search/controlling/techdocs/core → BFF | bleiben |
| **DEMOTE** → Read-Projektion (controlling-Muster) | ai_config, agents_dashboard, adr_lifecycle, releases | eigene Tabellen → Views/Cache mit SSoT-Pointer; **ai_config-Keys raus aus dev-hub-DB → Orchestrator** |
| **CUT** aus „App"-Framing | repo_health, quality_agent → headless Crons; sw_templates → echte Engine *oder* in `catalog` auflösen | vom Django-App-Skelett entkoppeln |

**Effekt:** 16 Apps → ~6 KEEP + 4 dünne Projektionen + 3 entkoppelte Crons. Die Angriffsfläche
(operations-SSH bereits gefixt, ai_config-Keys), die Drift-Quellen und ~⅓ Wartungsgewicht entfallen,
**ohne** den einzigartigen Wert zu verlieren.

### Inkrementeller Migrationspfad (kein Big-Bang — Lehre aus dem Incident)

> **Verpflichtungs-Scope (Rev 1.1, Challenger #2 + 🌀 ADR-201 smallest-viable):** Dieser ADR
> *committet* nur **Welle 0 + Welle 1** (Incident-Fix + Security). **Wellen 2–5 sind `proposed`
> und werden nach Welle 1 re-evaluiert** — dev-hub ist Infrastruktur, kein Umsatzträger; das volle
> 5-Wellen-Programm ist kein Blanko-Commitment.

0. **Welle 0 (Vorbedingung, Rev 1/REC-8):** den zu engen 60s-Deploy-Health-Gate fixen + catalog in eine
   isolierte Schema-Zone mit getrenntem Migrations-Gate legen (Option D). Ohne das baut jede weitere
   Welle operativ auf Sand (AD-12).
1. **Welle 1:** ai_config-Keys → Orchestrator; **Secrets-Migrationsnachweis (REC-12):** Keys aus DB
   *und* Backups/Dumps entfernt, Rotation erzwungen, Zugriffspfade getestet.
2. **Welle 2:** agents_dashboard → `read_projection`; **adr_lifecycle → `live_read` + git-Pointer:
   dev-hub schreibt KEINEN ADR-Status autoritativ** (Schreib-Intents landen in git/ADR-MCP, REC-11/REC-23).
3. **Welle 3:** repo_health/quality_agent als headless Jobs mit definiertem Owner/Scheduler/Secrets/
   Logs/Retry/Alerting + sichtbarer Health-Projektion im Portal (REC-13).
4. **Welle 4:** sw_templates **entscheiden** (nicht offen lassen): Catalog-Metadaten *oder* eigener
   Scaffolder-Backlog *oder* explizit deprecated (REC-14).
5. **Welle 5 (optional/deferred):** catalog als eigener Service herauslösen — nur bei belegtem Bedarf;
   **das neue Deploy-Artefakt erfordert dann eine ADR-021-Erweiterung** (Single-Service-Pipeline → +1 Service, Rev 1.1).

**Exit-Kriterien je Welle (Rev 1, REC-16/REC-24):** Datenmigration abgeschlossen · alte Schreibpfade
deaktiviert · alte Tabellen archiviert/gedroppt (nicht nur logisch tot) · Rollback-Pfad dokumentiert ·
**Parallelbetrieb** (alte vs. neue Anzeige verglichen, bis Projektion verifiziert) · Nutzerfluss getestet.
Jede Welle ist ein eigener PR hinter dem **Dogfood-Doc-Health-Gate** (Phase 1), erweitert um die
ADR-231-Invarianten-Checks (REC-17).

### Präzisierungen (Rev 1 — externe Zweitmeinung eingearbeitet, 2026-05-30)
Eine cross-provider-Review (Steelman → Advocatus Diabolus → Maintainer-2028) lieferte Befunde
`AD-1…15`/`M28-1…10`; nach Step-5-Tagging (`[valid]`/`[missversteht-Kontext]`/`[out-of-scope]`) eingearbeitet:
- **catalog Anti-Creep (REC-22, M28-2):** der catalog-Bereich bekommt **keine** Run-Records, keine
  ADR-Lifecycle-Wahrheit, keinen Release-Tracker, keine API-Key-/Budget-Ownership — sonst neuer Mini-Monolith.
- **catalog-Entitäten-Scope (REC-6, AD-11):** echte Ownership = Repo/Component/Dependency/Owner/Runtime/
  Deployment-*Beziehungen*; was aus Git/GitHub ableitbar ist, ist Projektion, nicht Ownership.
- **Orchestrator-Abhängigkeit als Contract (REC-19, AD-5):** benötigte MCP-Tools/Endpunkte, Timeouts,
  Versionierung und definiertes Verhalten bei pgvector-/Memory-Ausfall — nicht nur „akzeptiertes Risiko".
- **techdocs (REC-15, AD-8):** explizit `read_projection` mit `source_sha`, Rebuild-Kommando, Staleness-Anzeige.
- **Graceful Degradation je Quelle (REC-9, M28-4) + Source-Health-Dashboard (REC-10, M28-8):** als
  **Welle-Implementierungs-Vorgaben** (Anzeigezustand, Datenalter, Fallback, Timeout, TTL, Nutzerhinweis,
  Fehler-Audit) — Detail gehört in die jeweiligen Wellen-PRs, nicht in dieses Entscheidungs-Artefakt.
- **Kein Microservices-Prinzip (REC-25, PRO-8):** dies ist ein *begrenzter Zustands-Hoheits-Split* unter
  Single-Entwickler-Constraints, keine Microservice-Strategie aus Prinzip.
- **[out-of-scope]:** Event/Snapshot-Projection-Hub (OOB-3, Overengineering), Backstage (OOB-4, bereits
  verworfen), Static-Edge-Portal (OOB-6, zu restriktiv für Suche/Tenant/Audit) — nur als Vergleichsfolien notiert.

## Consequences

### Good
- Migrations-/DB-Bruchfläche dort eliminiert, wo sie unnötig ist (kein Incident-Replay).
- Eine kanonische Quelle je Information, strukturell erzwungen (SSoT-Pointer + Guardian).
- API-Keys verlassen die dev-hub-DB; der Orchestrator bleibt alleiniger Router (`policies/orchestrator.md`).
- Der einzigartige Wert (Portal/Katalog/Join) bleibt erhalten und wird *leichter* betreibbar.

### Bad / akzeptiert
- Mehrwöchiges Mehr-Wellen-Programm; jede Welle birgt Migrations-/Datenmigrations-Risiko (gemildert durch Dogfood-Gate + Wellen statt Big-Bang).
- BFF wird abhängiger von der Verfügbarkeit/stabiler API des Orchestrators (Resilienz: graceful degradation wie `controlling`/`resolve_outline_links` heute schon).
- `catalog`-Service = neuer Deploy-Artefakt (kleiner Service mehr).

### Confirmation
1. **SSoT-Pointer-Guardian** (ADR-054-kompatibel): eine dev-hub-Tabelle ohne Pointer-Spalte/Sync-Timestamp, die nicht in der KEEP-Whitelist (catalog/portal-config/audit/outbox) steht, ist ein Verstoß.
2. **Dogfood-Doc-Health-Gate** (Phase 1, live): jede Welle muss durch dev-hubs eigenen Audit.
3. **Pro Welle:** kein Netto-Zuwachs an Migrationen im BFF; ai_config-DB-Keys = 0 nach Welle 1.

## Open Questions

| # | Frage | Status |
|---|-------|--------|
| Q-1 | Wird das Portal real genutzt (Traffic auf devhub.iil.pet)? Falls ~niemand: Richtung „statischer Aggregator" statt BFF. | offen — Traffic-Logs prüfen |
| Q-2 | Exponiert der Orchestrator alle nötigen Daten über eine *stabile* API (nicht nur DB-Direktzugriff wie `controlling`)? | offen — Orchestrator-API-Audit |
| Q-3 | Datensouveränität: betreffen DEMOTE/CUT auch meiki-hub/ttz-hub-Sichten (Government/LRA)? | offen — vor Welle 2 klären |
| Q-4 | catalog-Service: eigene DB oder Schema im Bestehenden? Eigener Deploy vs. eingebettet? | offen — Welle 5 |

## More Information
- ADR-158 (Unified Documentation Portal) — wird hier amendiert (Portal-Rolle bleibt, Monolith-Annahme fällt).
- Audit-Report + Incident 2026-05-30 (dev-hub#62→#63 Migrations-Härtung; #59/#61 Security/Infra).
- `policies/orchestrator.md` (Orchestrator = Authoritative Source), ADR-176 (MCP-SSoT).
- Vorbild-Muster: `dev-hub/apps/controlling/services.py` (reines Read-View über Orchestrator).

## Glossar
> Zielgruppe: Fachpersonal ohne IT-Hintergrund. Alphabetisch, kontextbezogen.

* **BFF (Backend for Frontend)** — eine dünne Server-Schicht, die nur Daten *zusammenstellt und anzeigt*, aber selbst keine eigene Datenhaltung betreibt; sie liest aus den „echten" Quellen.
* **Entkernung** — das Herauslösen des zustandsbehafteten Kerns: aus einem großen Programm mit eigener Datenbank wird ein dünner Anzeige-Layer + ein kleiner, klar abgegrenzter Daten-Dienst.
* **Fork (von Zustand)** — eine zweite, eigene Kopie von Daten, deren „Original" woanders lebt; driftet mit der Zeit auseinander und ist die Hauptquelle von Inkonsistenz.
* **Katalog-Service** — der kleine eigenständige Dienst, der den Komponenten-/Abhängigkeits-Graphen hält (das Einzige, das wirklich eigene Persistenz braucht).
* **Migration (DB)** — ein Schritt, der das Datenbank-Schema ändert; schlägt er bei einem Deploy fehl, kann die ganze Anwendung ausfallen (so geschehen am 2026-05-30).
* **Projektion / Read-View** — eine Ansicht, die Daten *nur liest* und anzeigt, ohne eine eigene Kopie zu speichern; bleibt automatisch aktuell.
* **SSoT (Single Source of Truth)** — die *eine* maßgebliche Quelle für ein Datum; alle anderen verweisen darauf, statt es zu kopieren.
* **SSoT-Pointer** — ein Verweis (z. B. eine ID) in einer gespeicherten Zeile zurück auf ihre maßgebliche Quelle; ohne ihn ist nicht prüfbar, ob die Kopie noch stimmt.
