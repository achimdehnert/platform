API-Referenz
============

DDL Governance bietet eine Web-UI mit HTMX-basierter Interaktion.

Authentifizierung
-----------------

.. note::

   DDL Governance läuft als internes Tool im Docker-Netzwerk
   ``bf_platform_prod``. Aktuell keine Authentifizierung implementiert,
   da der Zugriff nur über den internen Nginx Reverse Proxy möglich ist.

   **Geplant (Prio niedrig)**: Integration mit BFAgent Auth-System
   (Groups: ``Superuser`` für vollen Zugang, ``Governance`` Gruppe
   für Lese-/Schreibzugriff).

URL-Struktur
------------

+---------------------------+----------------------------------+----------+
| URL                       | View                             | Methode  |
+===========================+==================================+==========+
| ``/``                     | Dashboard                        | GET      |
+---------------------------+----------------------------------+----------+
| ``/business-cases/``      | Business Case Liste              | GET      |
+---------------------------+----------------------------------+----------+
| ``/business-cases/<id>/`` | Business Case Detail             | GET      |
+---------------------------+----------------------------------+----------+
| ``/business-cases/new/``  | Business Case erstellen          | GET/POST |
+---------------------------+----------------------------------+----------+
| ``/use-cases/``           | Use Case Liste                   | GET      |
+---------------------------+----------------------------------+----------+
| ``/use-cases/<id>/``      | Use Case Detail                  | GET      |
+---------------------------+----------------------------------+----------+
| ``/health/``              | Health Check (JSON)              | GET      |
+---------------------------+----------------------------------+----------+

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

HTMX-Partials für dynamische Updates ohne Page-Reload:

+-------------------------------------+---------------------------------------+
| Partial Template                    | Funktion                              |
+=====================================+=======================================+
| ``partials/bc_list_rows.html``      | Business Case Tabellenzeilen          |
+-------------------------------------+---------------------------------------+
| ``partials/bc_stats.html``          | Dashboard Statistiken                 |
+-------------------------------------+---------------------------------------+
| ``partials/bc_status_badge.html``   | Status Badge mit Farbe/Icon           |
+-------------------------------------+---------------------------------------+

HTMX-Attribute:

.. code-block:: html

   <!-- Filter: Nur Drafts anzeigen -->
   <button hx-get="/business-cases/?status=draft"
           hx-target="#bc-list"
           hx-swap="innerHTML">
       Nur Drafts
   </button>

   <!-- Status ändern via HTMX -->
   <select hx-post="/business-cases/{{ bc.id }}/status/"
           hx-target="#status-badge"
           hx-swap="outerHTML">
       {% for status in statuses %}
       <option value="{{ status.id }}">{{ status.name }}</option>
       {% endfor %}
   </select>

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
