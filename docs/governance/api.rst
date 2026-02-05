API-Referenz
============

DDL Governance bietet eine Web-UI mit HTMX-basierter Interaktion.

URL-Struktur
------------

+---------------------------+----------------------------------+
| URL                       | View                             |
+===========================+==================================+
| ``/``                     | Dashboard                        |
+---------------------------+----------------------------------+
| ``/business-cases/``      | Business Case Liste              |
+---------------------------+----------------------------------+
| ``/business-cases/<id>/`` | Business Case Detail             |
+---------------------------+----------------------------------+
| ``/business-cases/new/``  | Business Case erstellen          |
+---------------------------+----------------------------------+
| ``/use-cases/``           | Use Case Liste                   |
+---------------------------+----------------------------------+
| ``/use-cases/<id>/``      | Use Case Detail                  |
+---------------------------+----------------------------------+
| ``/health/``              | Health Check (JSON)              |
+---------------------------+----------------------------------+

Views
-----

DashboardView
^^^^^^^^^^^^^

Zeigt Übersichts-Statistiken:

* Anzahl Business Cases (gesamt, draft, in review)
* Anzahl Use Cases
* Letzte Aktivitäten

.. code-block:: python

   class DashboardView(TemplateView):
       template_name = "governance/dashboard.html"

BusinessCaseListView
^^^^^^^^^^^^^^^^^^^^

Listet alle Business Cases mit Filterung:

.. code-block:: python

   class BusinessCaseListView(ListView):
       model = BusinessCase
       template_name = "governance/bc_list.html"
       context_object_name = "business_cases"
       paginate_by = 20

BusinessCaseDetailView
^^^^^^^^^^^^^^^^^^^^^^

Zeigt Details eines Business Case inkl. verknüpfter Use Cases:

.. code-block:: python

   class BusinessCaseDetailView(DetailView):
       model = BusinessCase
       template_name = "governance/bc_detail.html"

HTMX Integration
----------------

Partials
^^^^^^^^

HTMX-Partials für dynamische Updates:

* ``partials/bc_list_rows.html`` - Business Case Tabellenzeilen
* ``partials/bc_stats.html`` - Dashboard Statistiken
* ``partials/bc_status_badge.html`` - Status Badge

Beispiel HTMX-Request:

.. code-block:: html

   <button hx-get="/business-cases/?status=draft" 
           hx-target="#bc-list"
           hx-swap="innerHTML">
       Nur Drafts
   </button>

Health Check
------------

Endpoint für Monitoring:

.. code-block:: bash

   curl https://governance.iil.pet/health/
   # {"status": "healthy"}

Models API
----------

BusinessCase
^^^^^^^^^^^^

.. code-block:: python

   from governance.models import BusinessCase, LookupChoice
   
   # Alle Business Cases
   BusinessCase.objects.all()
   
   # Nach Status filtern
   BusinessCase.objects.filter(status__code="draft")
   
   # Mit Use Cases
   bc = BusinessCase.objects.get(code="BC-042")
   bc.use_cases.all()

LookupChoice
^^^^^^^^^^^^

.. code-block:: python

   from governance.models import LookupChoice
   
   # Alle Status-Optionen
   LookupChoice.objects.filter(domain__code="bc_status")
   
   # Aktive Prioritäten
   LookupChoice.objects.filter(
       domain__code="bc_priority",
       is_active=True
   ).order_by("sort_order")
