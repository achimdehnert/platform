BF Agent Platform Documentation
================================

Zentrale Dokumentation für das BF Agent Ecosystem.

.. image:: https://img.shields.io/badge/status-production-green
   :alt: Production Status

**Drei Säulen** (siehe :doc:`ADR-020 <governance/adr-020>`):

1. **Codebase** — autodoc aus Python Docstrings & Django Models
2. **Database** — generiert aus PostgreSQL Lookup- und Domain-Tabellen
3. **Governance** — ADRs, Business Cases, Use Cases aus DB + Markdown

.. toctree::
   :maxdepth: 2
   :caption: Architektur

   architecture/overview
   architecture/weltenhub
   architecture/bfagent
   architecture/travel_beat
   architecture/infrastructure

.. toctree::
   :maxdepth: 2
   :caption: Datenbank

   database/schema
   database/lookup_tables
   database/enrichment

.. toctree::
   :maxdepth: 2
   :caption: Governance (DDL)

   governance/overview
   governance/adrs
   governance/business_cases
   governance/use_cases

.. toctree::
   :maxdepth: 2
   :caption: API

   api/weltenhub
   api/endpoints

.. toctree::
   :maxdepth: 2
   :caption: Deployment

   deployment/infrastructure
   deployment/docker
   deployment/mcp-tools

Indices
-------

* :ref:`genindex`
* :ref:`search`
