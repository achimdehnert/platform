---
id: ADR-231
status: proposed
date: 2026-05-30
decision-makers: Achim Dehnert
domains: [dev-hub, architecture, ssot, portal, drift-prevention]
supersedes: []
amends: [ADR-158-unified-documentation-architecture.md]
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

### Option C — Entkernung zu Thin BFF + Catalog-Service (GEWÄHLT)
- ✅ Behält die 40 % einzigartiger Wert als *dünnen, weitgehend zustandslosen* Read-/Join-Layer.
- ✅ Eliminiert die Migrations-/DB-Bruchfläche dort, wo sie unnötig ist.
- ✅ Erzwingt die ADR-158-„link-not-copy"-Disziplin strukturell auf *alle* Spokes.

## Decision Outcome

**Gewählt: Option C.** dev-hub wird in zwei klar getrennte Verantwortungen entkernt:

1. **`dev-hub-bff`** — dünner, (nahezu) zustandsloser Backend-for-Frontend: Portal/Audience-Navigator,
   Search, Doc-Health-Anzeige, Dashboards. Liest aus den Autoritäts-Quellen (Orchestrator-MCP, git,
   GitHub, Outline, techdocs-Projektion), **besitzt keine fachlichen Tabellen**. Vorbild: `controlling`.
2. **`catalog-service`** — der **einzige** zustandsbehaftete Dienst: der Komponenten-/Dependency-Graph
   (das einzige, das echte Persistenz *braucht*, weil es nirgendwo sonst existiert). Eigene, kleine,
   stabile DB; minimale Migrations-Fläche.

### Verbindliche Invariante (SSoT-Pointer)

> **Jede persistierte Zeile in dev-hub trägt einen Pointer auf ihre Autoritäts-Quelle
> (`headless_run_id`, git-SHA, GitHub-Release-ID, …) + Sync-Timestamp — oder sie darf nicht existieren.**
> Eigene Tabellen nur dort, wo dev-hub die *einzige* Quelle ist (catalog, portal-Config, audit/outbox).

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
1. **Welle 1:** ai_config-Keys → Orchestrator, dev-hub liest Routing (schließt zugleich Security-Finding).
2. **Welle 2:** agents_dashboard/adr_lifecycle bekommen SSoT-Pointer-Spalten → Drift-Guardian-Check; Inhalt wird Projektion.
3. **Welle 3:** repo_health/quality_agent als headless Crons deklarieren, App-Shells abräumen.
4. **Welle 4:** sw_templates entscheiden (Engine vs. catalog-Auflösung).
5. **Welle 5:** catalog als eigener Service herauslösen; BFF wird zustandslos (bis auf portal-Config/audit).

Jede Welle ist ein eigener, getesteter PR hinter dem **Dogfood-Doc-Health-Gate** (ADR-158/Phase 1).

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
