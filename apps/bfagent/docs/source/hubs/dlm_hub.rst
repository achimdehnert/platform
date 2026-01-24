=========
DLM Hub
=========

.. note::
   **Documentation Lifecycle Management** | Status: Production Ready

Übersicht
=========

Der DLM Hub (Documentation Lifecycle Management) verwaltet den gesamten Lebenszyklus 
von Dokumentationen. Er analysiert Repositories auf Redundanzen, veraltete Dokumente 
und strukturelle Probleme.

Architektur
===========

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                       DLM HUB                                │
   ├─────────────────────────────────────────────────────────────┤
   │                                                             │
   │  Dashboard ──→ AnalysisRun ──→ AnalysisIssue               │
   │      │              │                │                      │
   │      ↓              ↓                ↓                      │
   │  Start Scan    Status Track     Issue Track                │
   │      │              │                │                      │
   │      ↓              ↓                ↓                      │
   │  DocumentAnalyzer ←─── MCPHub Client (Optional)            │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘

Models
======

AnalysisRun
-----------

Einzelner Analyse-Durchlauf:

.. code-block:: python

   class AnalysisRun(models.Model):
       SCAN_TYPE_CHOICES = [
           ("redundancy", "Redundancy Analysis"),
           ("freshness", "Freshness Check"),
           ("coverage", "Coverage Analysis"),
           ("full", "Full Analysis"),
       ]
       
       scan_path = models.CharField(max_length=500)
       scan_type = models.CharField(max_length=50, choices=SCAN_TYPE_CHOICES)
       model_used = models.CharField(max_length=100, default="llama3:8b")
       status = models.CharField(max_length=20)  # pending, running, completed, failed
       result_json = models.JSONField(null=True)

AnalysisIssue
-------------

Gefundene Probleme:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Issue Type
     - Beschreibung
   * - ``redundancy``
     - Doppelte oder überlappende Dokumentation
   * - ``outdated``
     - Veraltete Dokumentation
   * - ``structure``
     - Strukturelle Probleme
   * - ``orphan``
     - Verwaiste Dateien ohne Referenz
   * - ``broken_link``
     - Kaputte Links

Funktionen
==========

Dashboard
---------

**URL:** ``/dlm-hub/``

- Übersicht aller Analyse-Runs
- KPIs: Repositories, Dokumente, Aktualität
- Top-Issues nach Kategorie

Analyse starten
---------------

**URL:** ``/dlm-hub/analyze/``

.. code-block:: python

   # Views
   @login_required
   def start_analysis(request):
       """Startet neue Dokumentations-Analyse."""
       run = AnalysisRun.objects.create(
           scan_path=request.POST.get("path"),
           scan_type=request.POST.get("type", "full"),
           triggered_by=request.user
       )
       # Async Task starten
       analyze_documents.delay(run.id)
       return redirect("dlm_hub:dashboard")

Issue-Management
----------------

**URL:** ``/dlm-hub/issues/``

- Filtern nach Typ, Severity, Status
- Bulk-Aktionen (Archive, Ignore, Resolve)
- Action-Log für Audit-Trail

MCP Integration
===============

Der DLM Hub kann mit dem MCP-Hub Server kommunizieren:

.. code-block:: python

   from .services.mcphub_client import fetch_dlm_report_overview
   
   report = fetch_dlm_report_overview(
       base_url="http://mcphub-api:8080",
       timeout_seconds=2.0,
       cache_ttl_seconds=10,
   )

MCP Tools
---------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Tool
     - Beschreibung
   * - ``scan_repository``
     - Repository nach Docs scannen
   * - ``analyze_freshness``
     - Frische-Score berechnen
   * - ``cluster_by_application``
     - Docs nach App gruppieren
   * - ``generate_consolidated_docs``
     - Konsolidierte Docs erstellen
   * - ``deprecate_and_archive``
     - Veraltete Docs archivieren
   * - ``create_documentation_pr``
     - GitHub PR erstellen

Konfiguration
=============

Environment Variables
---------------------

.. code-block:: bash

   # MCPHub API URL
   MCPHUB_API_BASE_URL=http://mcphub-api:8080
   
   # GitHub Token für PR-Erstellung
   GITHUB_TOKEN=ghp_xxxxx
   
   # Default LLM für Analyse
   DLM_DEFAULT_MODEL=llama3:8b

URLs
====

.. code-block:: python

   # apps/dlm_hub/urls.py
   
   urlpatterns = [
       path("", views.dashboard, name="dashboard"),
       path("analyze/", views.start_analysis, name="start_analysis"),
       path("issues/", views.issue_list, name="issue_list"),
       path("issues/<uuid:pk>/", views.issue_detail, name="issue_detail"),
       path("runs/", views.run_list, name="run_list"),
       path("runs/<uuid:pk>/", views.run_detail, name="run_detail"),
   ]

Siehe auch
==========

.. toctree::
   :maxdepth: 1

   ../guides/session_handling_controlling
