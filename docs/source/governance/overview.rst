Governance (DDL) Übersicht
==========================

Das **Domain Development Lifecycle (DDL)** System implementiert einen
strukturierten Prozess für Feature-Entwicklung (ADR-017).

Komponenten
-----------

Business Cases
   Fachliche Anforderungen und Problemstellungen.

Use Cases
   Detaillierte Benutzerinteraktionen mit Flows.

ADRs
   Architecture Decision Records für technische Entscheidungen.

Reviews
   Freigabe-Workflow mit Audit Trail.

Conversations
   AI Inception-Dialoge zur Anforderungsermittlung.

Kernprinzip
-----------

**Keine Hardcoded Enums.** Alle Status-, Kategorie- und Prioritätsfelder
referenzieren ``platform.lkp_choice`` per Foreign Key.

Neue Werte → DB-Insert → sofort verfügbar. Kein Deployment nötig.

Datenbank-Schema
----------------

Alle Tabellen im ``platform`` Schema:

- ``platform.lkp_domain`` — Lookup-Kategorien
- ``platform.lkp_choice`` — Lookup-Werte
- ``platform.dom_business_case`` — Business Cases
- ``platform.dom_use_case`` — Use Cases
- ``platform.dom_adr`` — ADRs
- ``platform.dom_adr_use_case`` — ADR↔UC Verknüpfungen
- ``platform.dom_conversation`` — Inception-Dialoge
- ``platform.dom_review`` — Reviews
- ``platform.dom_status_history`` — Audit Trail

Referenz-ADRs
-------------

- **ADR-015**: Platform Governance System (Lookup-Pattern)
- **ADR-017**: Domain Development Lifecycle (dieses System)
- **ADR-020**: Dokumentationsstrategie (Sphinx + DB-driven)
