---
status: proposed
date: 2026-07-02
decision-makers: Achim Dehnert
consulted: –
informed: –
implementation_status: not-started
domains: [architecture, multi-tenancy, security, data-sovereignty]
scope: platform
amends: [ADR-109]
relates_to: [ADR-035, ADR-072, ADR-237, ADR-137]
tags: [multi-tenancy, tenant-id, security, fail-closed, drf, cross-tenant-leak, manager-contract]
---

# ADR-269 — Tenant-Scoping-Kontrakt: fehlender Tenant-Kontext MUSS fail-closed sein

> **Amends ADR-109**: ergänzt den Multi-Tenancy-Plattformstandard um einen **verbindlichen
> Sicherheits-Invarianten für den TenantAware-Manager** — der bislang ungeschriebene, faktisch
> divergent implementierte Umgang mit *fehlendem* Tenant-Kontext.
> **Nummer provisorisch (261) — Allokation zur Merge-Zeit (ADR-065).**

## Kontext

Die Fleet-Konvergenz-Runde 2026-07-02 (`~/shared/platform-audit-2026-07-02-fleet-convergence.md`,
Cluster D, 3 Repos + Muster) zeigt: das aus ADR-035/109 kopierte `TenantAwareManager` /
`for_tenant()` / `_tenant_id`-Muster behandelt **fehlenden oder `None`-Tenant-Kontext nicht
einheitlich** — und die Failure-Modes sind **gegenläufig**:

| Repo | Verhalten bei fehlendem Tenant-Kontext | Wirkung | Falsifikation |
|---|---|---|---|
| **weltenhub** | **fail-OPEN** — Manager liefert ungefilterte Queryset | **Cross-Tenant-READ-Leak** unter DRF-TokenAuth (kein Request-Middleware-Tenant gesetzt) | SURVIVES (Skeptiker, Quell-Lauf) |
| dev-hub | fail-CLOSED — stille 0 Zeilen | Daten „verschwinden" (Debugging-Falle), aber kein Leak | SURVIVES |
| ausschreibungs-hub | fail-CLOSED — 403 / leeres FK-Scoping | funktional korrekt, aber inkonsistent zu weltenhub | funktional bestätigt |

Derselbe Root-Cause (kopiertes Manager-Muster ohne definierten Null-Kontext-Pfad), **entgegengesetzte
Wirkung**. Der gefährliche Fall (fail-OPEN) ist ein **Datensouveränitäts-/Security-Perimeter-Bruch** und
damit nach ADR-Schwelle (Security-Perimeter, cross-cutting) ADR-pflichtig — nicht als weltenhub-Einzel-Patch.

ADR-109 macht Multi-Tenancy zur Pflicht, ADR-237 setzt row-level `tenant_id` als Default — **keiner**
spezifiziert, was bei **fehlendem** Kontext passieren muss. Diese Lücke schließt dieses ADR.

## Entscheidung

**Bei fehlendem/uneindeutigem Tenant-Kontext MUSS jeder tenant-scoped Datenzugriff fail-closed sein:
keine Zeilen liefern und (im Schreibpfad) hart ablehnen — niemals ungefiltert.**

1. **Manager-Kontrakt.** `TenantAwareManager.get_queryset()` ohne aktiven Tenant liefert `none()`
   (leeres Queryset), nicht das ungefilterte Queryset. `for_tenant(None)` ist ein definierter,
   sicherer Pfad (leer), kein Absturz und kein Voll-Zugriff.
2. **Explizit-Opt-out.** Cross-Tenant-Zugriff (Admin/Wartung) nur über einen **benannten,
   auditierten** Manager-Pfad (`all_tenants()` o. Ä.), nie implizit durch fehlenden Kontext.
3. **DRF-Härtung.** Für API-Zugänge ohne Session-Middleware (TokenAuth) MUSS die Tenant-Auflösung
   aus dem authentifizierten Principal erfolgen; ein `TenantScopedModelViewSet` als gemeinsame Basis
   erzwingt das Scoping auf Queryset-Ebene. **weltenhub PR #30 ist die Referenz-Implementierung.**
4. **Test-Invariante (ADR-074-konform).** Jedes tenant-scoped Model braucht einen Test
   `test_should_return_empty_when_tenant_context_missing` und einen Cross-Tenant-Isolationstest
   (Tenant A sieht Tenant B nicht — auch unter TokenAuth).

## Konsequenzen

- **Positiv:** schließt eine belegte Leak-Klasse; vereinheitlicht das divergente Verhalten auf die
  sichere Richtung; macht die Invariante testbar statt implizit.
- **Negativ / Risiko:** Repos, die heute (fahrlässig) auf fail-OPEN „funktionieren", können nach
  Umstellung leere Ergebnisse liefern, wo vorher (falsch) Daten kamen — das ist die **Aufdeckung**
  eines Bugs, kein Regress. Migrations-Reihenfolge: erst Tests, dann Manager-Flip.
- **Rollout:** in die `django_tenancy`-Basis (bzw. `iil-corefw`/tenancy-Paket) ziehen; Konsumenten
  erben den Fix per Bump. Betroffen zuerst: weltenhub (Leak, Prio 1), dann Audit aller Repos mit
  kopiertem Manager.

## Verifiziert / nicht verifiziert

- **Verifiziert:** weltenhub fail-OPEN + Leak (Skeptiker-SURVIVES, Quell-Lauf); dev-hub/ausschreibungs
  fail-CLOSED (divergente Wirkung). Belege: file:line in den `-processed`-Inboxen.
- **Nicht verifiziert:** vollständige Liste aller Repos mit kopiertem Manager — billigster Check ist
  `grep -rl 'TenantAwareManager\|def for_tenant' ~/github/*/` vor dem Rollout (Teil der Umsetzung).
